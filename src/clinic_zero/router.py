import os
from functools import lru_cache

from langsmith import traceable

from .tools import tools

JEV_MODEL = os.getenv("JEV_MODEL", "Qwen/Qwen3.5-4B")  
CONFIDENCE_THRESHOLD = 0.75

TOOL_DESCRIPTIONS = "\n".join(f"- {t.name}: {t.description}" for t in tools)

TOOL_LABELS = [t.name for t in tools] + ["general_chat"]

# A write tool needs ids that only the read tools can find, so scoping to the write tool alone
# would leave the agent unable to look anything up. Each label maps to the tools it depends on.
TOOL_GROUPS = {
    "book_appointment": ["search_patient", "list_doctors", "check_availability", "register_patient", "book_appointment"],
    "cancel_appointment": ["search_patient", "get_patient_history", "cancel_appointment"],
    "reschedule_appointment": ["search_patient", "get_patient_history", "check_availability", "reschedule_appointment"],
    "register_patient": ["search_patient", "register_patient"],
    "check_availability": ["list_doctors", "check_availability"],
}


@lru_cache(maxsize=1)
def get_decider():
    """Loads the local open-alternative-jev model once, on first use."""
    import torch
    from so1 import Decider

    return Decider.from_pretrained(JEV_MODEL, backend="hf", dtype=torch.bfloat16)


@traceable(name="jev_router", run_type="chain")
def classify_with_jev(user_message: str, tool_descriptions: str = TOOL_DESCRIPTIONS) -> dict:
    """Runs the local open-alternative-jev model to classify which tool (if any) this message needs."""
    from so1 import Choice

    decisions = get_decider().decide(
        state=f"{tool_descriptions}\n\nUser message: {user_message}",
        questions=[Choice("route", TOOL_LABELS)],
        mode="separate",  # avoids the packed-mode cross-question contamination noted in the repo's README
    )
    result = decisions[0]
    return {"label": result.choice, "confidence": result.confidence}


def router_node(state) -> dict:
    last_user_msg = state.messages[-1].content
    classification = classify_with_jev(last_user_msg)
    label = classification["label"]
    confidence = classification["confidence"]
    raw = {"jev_label": label, "jev_confidence": confidence}

    if confidence < CONFIDENCE_THRESHOLD:
        return {"selected_tools": [], "general_chat": False, **raw}

    if label == "general_chat":
        return {"selected_tools": [], "general_chat": True, **raw}
    return {"selected_tools": TOOL_GROUPS.get(label, [label]), "general_chat": False, **raw}
