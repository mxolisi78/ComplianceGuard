"""
Multi-agent supervisor architecture.

Flow:
  START → Classifier → [conditional] → Specialist → Aggregator → END
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from src.config import GROQ_API_KEY, LLM_MODEL
from src.rules_store import search_rules


# ---------- State ----------
class ReviewState(TypedDict):
    document: str
    doc_type: str
    findings: list[str]
    final_report: str


# ---------- LLM ----------
llm = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=0.2)


# ---------- Nodes ----------
def classifier_node(state: ReviewState) -> dict:
    prompt = f"""Classify the following document into exactly ONE category.
Return ONLY the category name, nothing else.

Categories:
- legal:      contracts, agreements, terms, liability, IP, confidentiality
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

List 2-4 findings, one per line. Prefix each with LEGAL: . Be concise and specific."""

    response = llm.invoke(prompt).content.strip()
    findings = [line.strip() for line in response.split("\n") if line.strip().startswith("LEGAL:")]
    return {"findings": findings}


def finance_specialist_node(state: ReviewState) -> dict:
    hits = search_rules("payment terms late penalties costs fees", top_k=5)
    rules_text = "\n".join(f"- [{h['id']}] {h['text']}" for h in hits)

    prompt = f"""You are a FINANCE compliance specialist. Review the document against these rules:

RULES:
{rules_text}

DOCUMENT:
{state['document'][:2500]}

List 2-4 findings, one per line. Prefix each with FINANCE: . Be concise and specific."""

    response = llm.invoke(prompt).content.strip()
    findings = [line.strip() for line in response.split("\n") if line.strip().startswith("FINANCE:")]
    return {"findings": findings}


def general_specialist_node(state: ReviewState) -> dict:
    prompt = f"""You are a GENERAL compliance reviewer. Summarize any concerns in the document.

DOCUMENT:
{state['document'][:2500]}

List 2-3 findings, one per line. Prefix each with GENERAL: ."""

    response = llm.invoke(prompt).content.strip()
    findings = [line.strip() for line in response.split("\n") if line.strip().startswith("GENERAL:")]
    return {"findings": findings}


def aggregator_node(state: ReviewState) -> dict:
    findings_text = "\n".join(state.get("findings", [])) or "(no findings)"

    prompt = f"""You are a COMPLIANCE REPORT WRITER.

Combine the specialist findings below into a clean, professional summary.
Structure:
  - Document type
  - Key concerns (bullet list)
  - Overall recommendation: APPROVE / REVIEW / REJECT

Specialist findings:
{findings_text}"""

    report = llm.invoke(prompt).content.strip()
    return {"final_report": report}


# ---------- Router ----------
def route_by_type(state: ReviewState) -> Literal["legal_specialist", "finance_specialist", "general_specialist"]:
    return f"{state['doc_type']}_specialist"


# ---------- Graph ----------
def build_supervisor_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("legal_specialist", legal_specialist_node)
    graph.add_node("finance_specialist", finance_specialist_node)
    graph.add_node("general_specialist", general_specialist_node)
    graph.add_node("aggregator", aggregator_node)

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
    graph.add_edge("aggregator", END)

    return graph.compile()


# ---------- CLI ----------
if __name__ == "__main__":
    agent = build_supervisor_graph()

    samples = {
        "Legal-heavy": """
        VENDOR AGREEMENT

        1. LIABILITY. The Vendor shall have unlimited liability for all damages
        arising from this agreement. The Client's liability is capped at $100.
        Indemnification is provided solely by the Vendor.

        2. INTELLECTUAL PROPERTY. All IP created shall belong exclusively to the Client.

        3. CONFIDENTIALITY. Confidentiality obligations shall survive indefinitely.
        """,
        "Finance-heavy": """
        PAYMENT TERMS

        Invoices are due Net 90 days from receipt. Late payments incur a 5% monthly
        penalty. All costs are non-refundable. Additional fees may apply without notice.
        """,
    }

    for label, doc in samples.items():
        print("=" * 70)
        print(f"DOCUMENT: {label}")
        print("=" * 70)
        result = agent.invoke({"document": doc})
        print(f"\nClassified as: {result['doc_type']}\n")
        print(f"Findings ({len(result['findings'])}):")
        for f in result["findings"]:
            print(f"  {f}")
        print(f"\n--- Final Report ---\n{result['final_report']}")
        print()