import sqlite3
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from .db import CHECKPOINTS_PATH
from .router import router_node
from .tools import tools

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.5)
llm_with_tools = llm.bind_tools(tools)  # fallback: all 10 tools, used when Jev isn't confident

SYSTEM_PROMPT = """You are ClinicDesk, the front-desk assistant for a dental clinic.

Use the available tools to look up patients, doctors, availability, treatment prices,
and clinic info, and to book, cancel, or reschedule appointments, or register new patients.

Always confirm the specific patient, doctor, date, and time with the user before calling
a write tool (book_appointment, cancel_appointment, reschedule_appointment, register_patient).
Never invent ids, dates, or prices - look them up with the read tools first."""


class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    response: str = ""
    selected_tools: list[str] = Field(default_factory=list)  # filled by router_node
    general_chat: bool = False  # True when Jev is confident no tool is needed at all
    jev_label: str = ""  # Jev's raw pick, kept even when confidence is below the threshold
    jev_confidence: float = 0.0


def agent_node(state: State) -> dict:
    if state.general_chat:
        llm_scoped = llm  # Jev is confident no tool is needed -> pure reasoning, no tools bound
    elif state.selected_tools:
        active_tools = [t for t in tools if t.name in state.selected_tools]
        llm_scoped = llm.bind_tools(active_tools)
    else:
        llm_scoped = llm_with_tools  # not confident either way -> fall back to the full toolset

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state.messages
    response = llm_scoped.invoke(messages)
    return {"messages": [response]}


def agent_node_baseline(state: State) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state.messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


checkpoint_conn = sqlite3.connect(CHECKPOINTS_PATH, check_same_thread=False)
checkpointer = SqliteSaver(checkpoint_conn)
checkpointer.setup()


def build_graph(use_jev: bool = True):
    """use_jev=True: router_node scopes the tools each turn. False: the baseline that always binds all 10."""
    graph = StateGraph(State)

    if use_jev:
        graph.add_node("router_node", router_node)
        graph.add_node("agent_node", agent_node)
        graph.add_edge(START, "router_node")
        graph.add_edge("router_node", "agent_node")
    else:
        graph.add_node("agent_node", agent_node_baseline)
        graph.add_edge(START, "agent_node")

    graph.add_node("tools", ToolNode(tools))
    graph.add_conditional_edges("agent_node", tools_condition)
    graph.add_edge("tools", "agent_node")

    return graph.compile(checkpointer=checkpointer)
