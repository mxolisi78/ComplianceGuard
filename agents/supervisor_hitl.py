"""
Multi-agent supervisor with Human-in-the-Loop approval gate.

Flow:
  START → Classifier → [conditional] → Specialist → Aggregator
       → Human Approval Gate (interrupt) → END

The graph PAUSES at the approval node and resumes with a human decision.
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_groq import ChatGroq

from src.config import GROQ_API_KEY, LLM_MODEL
from src.rules_store import search_rules


# ---------- State ----------
class ReviewState(TypedDict):
    document: str
    doc_type: str
    findings: list[str]
    final_report: str
    approval: str           # "approved" | "rejected"
    approver_notes: str


# ---------- LLM ----------
llm = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=0.2)


# ---------- Nodes ----------
def classifier_node(state: ReviewState) -> dict:
    prompt = f"""Classify the following document into exactly ONE category.
Return ONLY the category name.

Categories:
- legal:      contracts, agreements, liability, IP, confidentiality
- finance:    payment terms, invoices, costs, fees, penalties
- general:    anything else

Document:
{state['document'][:1500]}

Category:"""

    response = llm.invoke(prompt).content.strip().lower()
    if "legal" in response:
        doc_type = "legal"
    elif "finance" in response:
        doc_type = "finance"
    else:
        doc_type = "general"
    return {"doc_type": doc_type, "findings": []}


def legal_specialist_node(state: ReviewState) -> dict:
    hits = search_rules("legal liability termination confidentiality intellectual property", top_k=5)
    rules_text = "\n".join(f"- [{h['id']}] {h['text']}" for h in hits)
    prompt = f"""You are a LEGAL compliance specialist. Review the document against these rules:

RULES:
{rules_text}

DOCUMENT:
{state['document'][:2500]}

List 2-4 findings, one per line. Prefix each with LEGAL: ."""
    response = llm.invoke(prompt).content.strip()
    findings = [l.strip() for l in response.split("\n") if l.strip().startswith("LEGAL:")]
    return {"findings": findings}


def finance_specialist_node(state: ReviewState) -> dict:
    hits = search_rules("payment terms late penalties costs fees", top_k=5)
    rules_text = "\n".join(f"- [{h['id']}] {h['text']}" for h in hits)
    prompt = f"""You are a FINANCE compliance specialist. Review the document against these rules:

RULES:
{rules_text}

DOCUMENT:
{state['document'][:2500]}

List 2-4 findings, one per line. Prefix each with FINANCE: ."""
    response = llm.invoke(prompt).content.strip()
    findings = [l.strip() for l in response.split("\n") if l.strip().startswith("FINANCE:")]
    return {"findings": findings}


def general_specialist_node(state: ReviewState) -> dict:
    prompt = f"""You are a GENERAL compliance reviewer. List concerns in the document.
DOCUMENT:
{state['document'][:2500]}
List 2-3 findings, one per line. Prefix each with GENERAL: ."""
    response = llm.invoke(prompt).content.strip()
    findings = [l.strip() for l in response.split("\n") if l.strip().startswith("GENERAL:")]
    return {"findings": findings}


def aggregator_node(state: ReviewState) -> dict:
    findings_text = "\n".join(state.get("findings", [])) or "(no findings)"
    prompt = f"""You are a COMPLIANCE REPORT WRITER.
Combine the specialist findings into a professional summary.

IMPORTANT: Use PLAIN TEXT only. Do NOT use markdown symbols like **, ##, or backticks.

Structure:
  Document Type: ...
  Key Concerns:
    - concern 1
    - concern 2
  Overall Recommendation: APPROVE / REVIEW / REJECT
  Rationale: ...

Findings:
{findings_text}"""
    return {"final_report": llm.invoke(prompt).content.strip()}


def human_approval_node(state: ReviewState) -> dict:
    """
    Pause execution and wait for human input.
    The value passed to interrupt() is returned to the caller.
    On resume, Command(resume=...) provides the human's response.
    """
    decision = interrupt({
        "message": "Review the compliance report and approve or reject.",
        "document_type": state["doc_type"],
        "findings_count": len(state["findings"]),
        "final_report": state["final_report"],
    })

    # decision should be a dict: {"approval": "approved"|"rejected", "notes": "..."}
    return {
        "approval": decision.get("approval", "unknown"),
        "approver_notes": decision.get("notes", ""),
    }


# ---------- Router ----------
def route_by_type(state: ReviewState) -> Literal["legal_specialist", "finance_specialist", "general_specialist"]:
    return f"{state['doc_type']}_specialist"


# ---------- Graph ----------
def build_hitl_graph(checkpointer=None):
    graph = StateGraph(ReviewState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("legal_specialist", legal_specialist_node)
    graph.add_node("finance_specialist", finance_specialist_node)
    graph.add_node("general_specialist", general_specialist_node)
    graph.add_node("aggregator", aggregator_node)
    graph.add_node("human_approval", human_approval_node)

    graph.add_edge(START, "classifier")
    graph.add_conditional_edges(
        "classifier",
        route_by_type,
        {
            "legal_specialist": "legal_specialist",
            "finance_specialist": "finance_specialist",
            "general_specialist": "general_specialist",
        },
    )
    graph.add_edge("legal_specialist", "aggregator")
    graph.add_edge("finance_specialist", "aggregator")
    graph.add_edge("general_specialist", "aggregator")
    graph.add_edge("aggregator", "human_approval")
    graph.add_edge("human_approval", END)

    # MemorySaver keeps state between the interrupt and the resume
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)