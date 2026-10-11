"""
Wrapper around the HITL supervisor graph.

Provides a Django-friendly interface:
  - start_review(document)  -> returns thread_id
  - get_state(thread_id)    -> current status + payload
  - resume_review(thread_id, approval, notes) -> completes the run
  - list_reviews()          -> all threads and their states

Uses MemorySaver (in-memory) — reviews do NOT persist across restarts.
Suitable for the free-tier deploy. Swap to SqliteSaver (with a persistent
disk) for persistent deployments.
"""
import uuid
from typing import Optional

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from agents.supervisor_hitl import build_hitl_graph


# In-memory checkpointer — shared for the process lifetime
_checkpointer = MemorySaver()
_graph = build_hitl_graph(checkpointer=_checkpointer)

# Track known thread_ids ourselves (MemorySaver doesn't expose a list API)
_known_threads = []


def start_review(document: str) -> str:
    """Start a new review. Returns a thread_id you can use to resume."""
    thread_id = f"review-{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}
    _graph.invoke({"document": document}, config=config)
    _known_threads.append(thread_id)
    return thread_id


def get_state(thread_id: str) -> Optional[dict]:
    """Return the current state of a review (paused or completed)."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = _graph.get_state(config)
    except Exception:
        return None

    if not snapshot or not snapshot.values:
        return None

    values = dict(snapshot.values)

    # Extract interrupt payload if the graph is currently paused
    interrupt_payload = None
    for task in snapshot.tasks:
        for intr in getattr(task, "interrupts", []) or []:
            interrupt_payload = intr.value
            break
        if interrupt_payload:
            break

    return {
        "thread_id": thread_id,
        "values": values,
        "is_paused": bool(interrupt_payload),
        "interrupt": interrupt_payload,
        "is_complete": snapshot.next == (),
    }


def resume_review(thread_id: str, approval: str, notes: str = "") -> dict:
    """Resume a paused review with the human decision."""
    config = {"configurable": {"thread_id": thread_id}}
    final = _graph.invoke(
        Command(resume={"approval": approval, "notes": notes}),
        config=config,
    )
    return dict(final)


def list_reviews():
    """List all thread_ids we've seen in this process."""
    return list(reversed(_known_threads))
