"""100-question benchmark: every question runs with and without the Jev router.

Run:     uv run python -m clinic_zero.benchmark            (resumes if results already exist)
         uv run python -m clinic_zero.benchmark --fresh    (start over)
         uv run python -m clinic_zero.benchmark --report   (only print the report)

Each turn is saved to results/benchmark.jsonl as soon as it finishes, so a run stopped by
Groq's daily limit picks up where it left off. Traces go to the LangSmith projects
clinicdesk-bench-with-jev / clinicdesk-bench-without-jev.
"""
import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import tracing_context

from . import run_turn
from .benchmark_questions import QUESTIONS
from .compare import decline
from .db import PROJECT_ROOT
from .router import TOOL_GROUPS

RESULTS_PATH = PROJECT_ROOT / "results" / "benchmark.jsonl"
CONDITIONS = {"jev": "clinicdesk-bench-with-jev", "baseline": "clinicdesk-bench-without-jev"}
WRITE_TOOLS = {"book_appointment", "cancel_appointment", "reschedule_appointment", "register_patient"}
MAX_WAIT_S = 15 * 60  # a longer Groq cool-down means the daily quota is spent -> stop and resume later


class QuotaExhausted(Exception):
    pass


def retry_after(error: Exception) -> float:
    """Groq puts the cool-down in the message: 'Please try again in 1m12.5s'."""
    m = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", str(error))
    if not m:
        return 30.0
    h, mins, s = (float(x) if x else 0.0 for x in m.groups())
    return h * 3600 + mins * 60 + s + 1


def is_rate_limit(error: Exception) -> bool:
    return getattr(error, "status_code", None) == 429 or "rate limit" in str(error).lower()


def run_one(graph, qid: int, expected: str, question: str, condition: str) -> dict:
    record = {"id": qid, "condition": condition, "expected": expected, "question": question}
    other_errors = 0

    while True:
        thread_id = f"bench-{condition}-{qid}-{time.time_ns()}"  # fresh thread per attempt
        start = time.perf_counter()
        try:
            with tracing_context(project_name=CONDITIONS[condition],
                                 metadata={"question_id": qid, "expected": expected, "use_jev": condition == "jev"}):
                result = run_turn(graph, question, thread_id=thread_id, approve=decline)
            break
        except Exception as e:
            if is_rate_limit(e):
                wait = retry_after(e)
                # the daily cap is a rolling 24h window: waiting frees ~1K tokens every few minutes, not enough to progress
                if wait > MAX_WAIT_S or "per day" in str(e):
                    raise QuotaExhausted(str(e)) from e
                print(f"    rate limited, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            other_errors += 1
            if other_errors >= 3:
                return record | {"error": f"{type(e).__name__}: {str(e)[:500]}", "total_tokens": 0}
            print(f"    {type(e).__name__}, retrying ({other_errors}/3): {str(e)[:150]}")

    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    usage = [m.usage_metadata or {} for m in ai_messages]
    return record | {
        "total_tokens": sum(u.get("total_tokens", 0) for u in usage),
        "input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "llm_calls": len(ai_messages),
        "tools_called": [tc["name"] for m in ai_messages for tc in m.tool_calls],
        "jev_label": result.get("jev_label") or None,
        "jev_confidence": result.get("jev_confidence") if condition == "jev" else None,
        "selected_tools": result.get("selected_tools", []),
        "general_chat": result.get("general_chat", False),
        "latency_s": round(time.perf_counter() - start, 2),
        "answer": ai_messages[-1].content[:500] if ai_messages else "",
        "error": None,
    }


def load_results() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    with open(RESULTS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run(fresh: bool) -> None:
    from .graph import build_graph

    load_dotenv(override=True)
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY is empty in .env - results are saved locally only.\n")
        os.environ["LANGSMITH_TRACING"] = "false"

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    if fresh and RESULTS_PATH.exists():
        RESULTS_PATH.unlink()
    done = {(r["id"], r["condition"]) for r in load_results()}
    graphs = {"jev": build_graph(use_jev=True), "baseline": build_graph(use_jev=False)}

    todo = [(qid, c) for qid in range(len(QUESTIONS)) for c in CONDITIONS if (qid, c) not in done]
    print(f"{len(done)} turns already done, {len(todo)} to go.")

    with open(RESULTS_PATH, "a", encoding="utf-8") as out:
        for n, (qid, condition) in enumerate(todo, 1):
            expected, question = QUESTIONS[qid]
            print(f"[{n}/{len(todo)}] q{qid:03d} {condition:8} {question[:60]}")
            try:
                record = run_one(graphs[condition], qid, expected, question, condition)
            except QuotaExhausted as e:
                print(f"\nGroq daily quota reached - stopping. Re-run the same command later to resume.\n  {str(e)[:300]}")
                break
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            if record["error"]:
                print(f"    FAILED: {record['error'][:150]}")
            else:
                routed = f"  jev={record['jev_label']} ({record['jev_confidence']:.2f})" if condition == "jev" else ""
                print(f"    {record['total_tokens']} tokens, tools={record['tools_called']}{routed}")

    wait_for_all_tracers()
    report()


def behaved_as_expected(r: dict) -> bool | None:
    """Did the agent reach the right tool? None for write intents: they rightly ask for details first."""
    if r["error"]:
        return False
    if r["expected"] == "general_chat":
        return not r["tools_called"]
    if r["expected"] in WRITE_TOOLS:
        return None
    return r["expected"] in r["tools_called"]


def pct(a: float, b: float) -> str:
    return f"{a / b:.0%}" if b else "-"


def report() -> None:
    results = load_results()
    by_key = {(r["id"], r["condition"]): r for r in results}
    pairs = [(by_key[(i, "jev")], by_key[(i, "baseline")])
             for i in range(len(QUESTIONS)) if (i, "jev") in by_key and (i, "baseline") in by_key]
    if not pairs:
        print("No complete question pairs yet.")
        return

    ok_pairs = [(j, b) for j, b in pairs if not j["error"] and not b["error"]]
    tok_j = sum(j["total_tokens"] for j, _ in ok_pairs)
    tok_b = sum(b["total_tokens"] for _, b in ok_pairs)
    print(f"\n=== {len(pairs)}/{len(QUESTIONS)} questions run on both graphs "
          f"({len(ok_pairs)} without errors on either side) ===\n")

    print("TOKENS (Groq only - the Jev router runs locally and costs no API tokens)")
    print(f"  with Jev : {tok_j:>8}  total   {tok_j / max(len(ok_pairs), 1):>7.0f} per question")
    print(f"  baseline : {tok_b:>8}  total   {tok_b / max(len(ok_pairs), 1):>7.0f} per question")
    if tok_b:
        print(f"  saved    : {tok_b - tok_j:>8}  ({(tok_b - tok_j) / tok_b:.1%})")
    inp_j = sum(j.get("input_tokens", 0) for j, _ in ok_pairs)
    inp_b = sum(b.get("input_tokens", 0) for _, b in ok_pairs)
    print(f"  input tokens only: {inp_j} vs {inp_b} ({pct(inp_b - inp_j, inp_b)} saved)")
    lat_j = sum(j["latency_s"] for j, _ in ok_pairs) / max(len(ok_pairs), 1)
    lat_b = sum(b["latency_s"] for _, b in ok_pairs) / max(len(ok_pairs), 1)
    print(f"  mean latency: {lat_j:.2f}s with Jev vs {lat_b:.2f}s baseline (Jev time included)\n")

    jev_runs = [j for j, _ in pairs if not j["error"]]
    correct = sum(j["jev_label"] == j["expected"] for j in jev_runs)
    confident = [j for j in jev_runs if j["selected_tools"] or j["general_chat"]]
    confident_ok = sum(j["jev_label"] == j["expected"] for j in confident)
    print("JEV ROUTER")
    print(f"  label accuracy        : {correct}/{len(jev_runs)} ({pct(correct, len(jev_runs))})")
    print(f"  confident (>= 0.75)   : {len(confident)}/{len(jev_runs)} scoped, "
          f"{len(jev_runs) - len(confident)} fell back to all tools")
    print(f"  accuracy when confident: {confident_ok}/{len(confident)} ({pct(confident_ok, len(confident))})")
    wrong_scoped = [j for j in confident if j["jev_label"] != j["expected"]
                    and j["expected"] not in TOOL_GROUPS.get(j["jev_label"], [j["jev_label"]])]
    print(f"  confident AND the needed tool was not bound: {len(wrong_scoped)}")
    for j in wrong_scoped[:15]:
        print(f"    q{j['id']:03d} expected {j['expected']:22} got {j['jev_label']} ({j['jev_confidence']:.2f})  {j['question'][:50]}")
    print()

    print("RELIABILITY")
    for name, idx in (("with Jev", 0), ("baseline", 1)):
        errs = [p[idx] for p in pairs if p[idx]["error"]]
        judged = [behaved_as_expected(p[idx]) for p in pairs]
        judged = [x for x in judged if x is not None]
        print(f"  {name}: {len(errs)} errors;  reached the expected tool (read intents + no tool for chat): "
              f"{sum(judged)}/{len(judged)} ({pct(sum(judged), len(judged))})")
        for e in errs[:5]:
            print(f"    q{e['id']:03d} {e['error'][:140]}")
    print()

    print(f"{'PER CATEGORY':24} {'n':>3} {'jev tok':>8} {'base tok':>8} {'saved':>6} {'router':>7} {'ok jev':>7} {'ok base':>7}")
    cats = defaultdict(list)
    for j, b in pairs:
        cats[j["expected"]].append((j, b))
    for cat, ps in cats.items():
        ok = [(j, b) for j, b in ps if not j["error"] and not b["error"]]
        tj = sum(j["total_tokens"] for j, _ in ok) / max(len(ok), 1)
        tb = sum(b["total_tokens"] for _, b in ok) / max(len(ok), 1)
        router = sum(j["jev_label"] == cat for j, _ in ps)
        bj = [behaved_as_expected(j) for j, _ in ps]
        bb = [behaved_as_expected(b) for _, b in ps]
        okj = "n/a" if bj[0] is None else pct(sum(bj), len(bj))
        okb = "n/a" if bb[0] is None else pct(sum(bb), len(bb))
        print(f"  {cat:22} {len(ps):>3} {tj:>8.0f} {tb:>8.0f} {pct(tb - tj, tb):>6} {pct(router, len(ps)):>7} {okj:>7} {okb:>7}")

    confusion = Counter((j["expected"], j["jev_label"]) for j in jev_runs if j["jev_label"] != j["expected"])
    if confusion:
        print("\nMOST COMMON MISROUTES (expected -> Jev label)")
        for (exp, got), n in confusion.most_common(8):
            print(f"  {n:>2}x {exp} -> {got}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fresh", action="store_true", help="discard saved results and start over")
    parser.add_argument("--report", action="store_true", help="only print the report from saved results")
    args = parser.parse_args()
    report() if args.report else run(fresh=args.fresh)


if __name__ == "__main__":
    main()
