"""
Wrapper around the HITL supervisor graph.

Provides a Django-friendly interface:
  - start_review(document)  → returns thread_id
  - get_state(thread_id)    → current status + payload
  - resume_review(thread_id, approval, notes) → completes the run
  - list_reviews()          → all threads and their states
"""
import uuid
from pathlib import Path
from typing import Optional

from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.supervisor_hitl import build_hitl_graph
from src.config import PROJECT_ROOT


CHECKPOINT_DB = PROJECT_ROOT / "data" / "checkpoints.sqlite"
CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)

# One shared checkpointer + compiled graph
_checkpointer_ctx = SqliteSaver.from_conn_string(str(CHECKPOINT_DB))
_checkpointer = _checkpointer_ctx.__enter__()   # keep it open for process lifetime
_graph = build_hitl_graph(checkpointer=_checkpointer)


def start_review(document: str) -> str:
    """Start a new review. Returns a thread_id you can use to resume."""
    thread_id = f"review-{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}
    _graph.invoke({"document": document}, config=config)
    return thread_id


def get_state(thread_id: str) -> Optional[dict]:
    """Return the current state of a review (paused or completed)."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = _graph.get_state(config)
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
    """List all thread_ids we've seen in the checkpoint DB."""
    # SqliteSaver doesn't expose a simple list API, so we query the DB directly
    import sqlite3
    con = sqlite3.connect(str(CHECKPOINT_DB))
    try:
        cur = con.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY rowid DESC")
        return [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()