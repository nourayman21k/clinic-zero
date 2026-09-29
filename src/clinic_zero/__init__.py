import uuid
from typing import Callable

from langchain_core.messages import HumanMessage
from langgraph.types import Command


def ask_approval(payload: dict) -> bool:
    print("Needs human approval:", payload)
    return input("Approve? (y/n): ").strip().lower() == "y"


def run_turn(graph, user_text: str, thread_id: str, approve: Callable[[dict], bool] = ask_approval) -> dict:
    # thread_id is the checkpointer's key: every invoke scoped to the same thread_id shares
    # message history and lets an interrupt() pause/resume correctly.
    cfg = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(content=user_text)]}, config=cfg)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        result = graph.invoke(Command(resume={"approved": approve(payload)}), config=cfg)

    return result


def main() -> None:
    import argparse

    from .graph import build_graph

    parser = argparse.ArgumentParser(description="ClinicDesk front-desk assistant")
    parser.add_argument("--no-jev", action="store_true", help="skip the Jev router and always bind all tools")
    parser.add_argument("--thread", default=None, help="resume a conversation by thread_id")
    args = parser.parse_args()

    graph = build_graph(use_jev=not args.no_jev)
    thread_id = args.thread or str(uuid.uuid4())
    print(f"ClinicDesk (thread {thread_id}) - type 'exit' to quit.")

    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_text.lower() in {"exit", "quit"}:
            break
        if user_text:
            result = run_turn(graph, user_text, thread_id)
            print("ClinicDesk:", result["messages"][-1].content)
