"""
A minimal LangGraph agent.

Demonstrates the core pieces:
  - StateGraph with a typed state
  - Nodes (functions that update state)
  - Edges (transitions between nodes)
  - Compilation and invocation
"""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from src.config import GROQ_API_KEY, LLM_MODEL


# 1. Define the state schema — the "memory" passed between nodes
class AgentState(TypedDict):
    question: str
    draft: str
    final: str


# 2. Initialize the LLM
llm = ChatGroq(api_key=GROQ_API_KEY, model=LLM_MODEL, temperature=0.2)


# 3. Define node functions
def draft_answer(state: AgentState) -> AgentState:
    """First pass: ask the LLM a direct question."""
    prompt = f"Answer this in one sentence: {state['question']}"
    response = llm.invoke(prompt)
    return {"draft": response.content.strip()}


def polish_answer(state: AgentState) -> AgentState:
    """Second pass: rewrite the draft to be more formal."""
    prompt = (
        f"Rewrite the following answer to be more formal and concise. "
        f"Return only the rewritten answer.\n\nDraft: {state['draft']}"
    )
    response = llm.invoke(prompt)
    return {"final": response.content.strip()}


# 4. Build the graph
def build_agent():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("drafter", draft_answer)
    graph.add_node("polisher", polish_answer)

    # Add edges (flow)
    graph.add_edge(START, "drafter")
    graph.add_edge("drafter", "polisher")
    graph.add_edge("polisher", END)

    return graph.compile()


# 5. Run it
if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke({"question": "What is a vendor agreement?"})

    print("=== Draft ===")
    print(result["draft"])
    print()
    print("=== Polished ===")
    print(result["final"])