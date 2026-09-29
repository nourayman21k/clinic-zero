"""Token usage with vs. without the Jev router, traced to two LangSmith projects.

Run:  uv run python -m clinic_zero.compare
Then open smith.langchain.com -> projects clinicdesk-with-jev / clinicdesk-without-jev -> Runs.
"""
import os
import uuid

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import tracing_context

from . import run_turn
from .graph import build_graph

TEST_MESSAGES = [
    "Hi, I want to book a checkup with a dentist next week.",
    "I need to cancel my appointment.",
    "How much does a root canal cost?",
    "Hello, what are your clinic hours?",
]


def decline(payload: dict) -> bool:
    print(f"  (auto-declined {payload['action']})")
    return False


def total_tokens(result: dict) -> int:
    return sum((m.usage_metadata or {}).get("total_tokens", 0)
               for m in result["messages"] if isinstance(m, AIMessage))


def run_condition(use_jev: bool, project: str) -> list[dict]:
    graph = build_graph(use_jev=use_jev)
    run_id = uuid.uuid4().hex[:8]
    rows = []

    with tracing_context(project_name=project, metadata={"use_jev": use_jev}):
        for i, msg in enumerate(TEST_MESSAGES):
            result = run_turn(graph, msg, thread_id=f"{project}-{run_id}-{i}", approve=decline)
            if not use_jev:
                routing = "all tools"
            elif result.get("general_chat"):
                routing = "general_chat"
            else:
                routing = ", ".join(result.get("selected_tools") or []) or "fallback: all tools"
            rows.append({"message": msg, "tokens": total_tokens(result), "routing": routing})

    return rows


def main() -> None:
    load_dotenv(override=True)
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY is empty in .env - runs will not reach LangSmith, local totals only.\n")
        os.environ["LANGSMITH_TRACING"] = "false"

    with_jev = run_condition(True, "clinicdesk-with-jev")
    without_jev = run_condition(False, "clinicdesk-without-jev")
    wait_for_all_tracers()

    print(f"\n{'message':55} {'with jev':>9} {'baseline':>9}  routing")
    for a, b in zip(with_jev, without_jev):
        print(f"{a['message'][:55]:55} {a['tokens']:>9} {b['tokens']:>9}  {a['routing']}")
    total_a = sum(r["tokens"] for r in with_jev)
    total_b = sum(r["tokens"] for r in without_jev)
    scoped = sum(r["routing"] != "fallback: all tools" for r in with_jev)
    print(f"{'TOTAL':55} {total_a:>9} {total_b:>9}")
    if total_b:
        print(f"\nJev saved {total_b - total_a} tokens ({(total_b - total_a) / total_b:.0%}); "
              f"{scoped}/{len(with_jev)} turns were scoped, {len(with_jev) - scoped} fell back to all tools.")


if __name__ == "__main__":
    main()
