@'
>> # ComplianceGuard — Multi-Agent Contract Review
>> 
>> ![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
>> ![LangGraph](https://img.shields.io/badge/LangGraph-1.0-FF6F61)
>> ![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
>> ![Groq](https://img.shields.io/badge/Groq-GPT--OSS--120B-F55036)
>> ![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5-4B8BBE)
>> ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
>> ![Status](https://img.shields.io/badge/Status-Complete-brightgreen)
>> 
>> A **multi-agent AI system** that reviews vendor agreements for compliance
>> violations and pauses for **human approval** before finalizing.
>> 
>> Demonstrates: **agentic orchestration**, **conditional routing**,
>> **retrieval-augmented rules lookup**, and **human-in-the-loop** workflows.
>> 
>> ---
>> 
>> ## Why Agentic AI?
>> 
>> Traditional LLM applications are single-pass: prompt → response. Real
>> business workflows need:
>> 
>> - **Specialization** — different experts for different parts of a document
>> - **Orchestration** — a supervisor that decides who handles what
>> - **Grounding** — every claim tied to a retrievable rule
>> - **Oversight** — a human must approve high-stakes decisions
>> 
>> ComplianceGuard shows all four.
>> 
>> ---
>> 
>> ## Architecture
>> 
>> ┌─────────────────────┐
>> │ Upload Contract │
>> └──────────┬──────────┘
>> ↓
>> ┌──────────────────────────┐
>> │ CLASSIFIER │
>> │ (legal / finance / gen) │
>> └────────────┬─────────────┘
>> ↓
>> [conditional edge: pick specialist]
>> ↓
>> ┌─────────────────────────┼──────────────────────────┐
>> ↓ ↓ ↓
>> ┌─────────┐ ┌───────────┐ ┌──────────┐
>> │ LEGAL │ │ FINANCE │ │ GENERAL │
>> │ Specialist│ │ Specialist│ │ Specialist│
>> └────┬────┘ └─────┬─────┘ └────┬─────┘
>> └────────────────────┬───┴────────────────────────┘
>> ↓
>> ┌───────────────┐
>> │ AGGREGATOR │
>> │ Report Writer│
>> └───────┬───────┘
>> ↓
>> ┌──────────────────────────┐
>> │ HUMAN APPROVAL GATE │
>> │ (LangGraph interrupt) │
>> │ ──────────────────── │
>> │ [✓ Approve] [✗ Reject] │
>> └─────────────┬────────────┘
>> ↓
>> ┌───────────────┐
>> │ Final State │
>> │ + Audit Log │
>> └───────────────┘
>> 
>> text
>> 
>> Every specialist retrieves relevant rules from a **vector store** built on
>> ChromaDB + sentence-transformers (RAG).
>> 
>> ---
>> 
>> ## Demo
>> 
>> ![ComplianceGuard UI](docs/screenshot.png)
>> 
>> *Multi-agent review with a pause for human approval.*
>> 
>> ---
>> 
>> ## Features
>> 
>> - 🎯 **Supervisor architecture** — classifier routes to the right specialist
>> - 🧠 **Multi-agent collaboration** — legal, finance, and general specialists
>> - 📚 **RAG-grounded rules** — compliance rules retrieved semantically
>> - ⏸️ **Human-in-the-loop** — LangGraph `interrupt()` pauses for approval
>> - 💾 **Persistent checkpoints** — SQLite saves state across restarts
>> - 🔁 **Resumable execution** — `Command(resume=...)` continues where it paused
>> - 🌐 **Django web UI** — upload, review, approve/reject
>> - 📝 **Markdown-rendered reports** — professional output
>> 
>> ---
>> 
>> ## Tech Stack
>> 
>> | Layer | Tool |
>> |-------|------|
>> | **Orchestration** | LangGraph 1.0 (StateGraph, conditional edges, interrupt) |
>> | **LLM** | Groq GPT-OSS-120B (free tier) |
>> | **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`, 384-d) |
>> | **Vector Store** | ChromaDB (persistent) |
>> | **Checkpointer** | langgraph-checkpoint-sqlite (persistent agent state) |
>> | **Web** | Django 6.1 |
>> | **Parsing** | pypdf, python-docx |
>> 
>> ---

## Setup

### 1. Clone & install

```powershell
git clone https://github.com/mxolisi78/ComplianceGuard.git
cd ComplianceGuard
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

2. Get a Groq API key (free)
Sign up at https://console.groq.com → API Keys → Create API Key.

3. Configure environment
💡 Tip: copy .env.example to .env and fill in your values.

powershell
copy .env.example .env
Set your key in .env:

env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=openai/gpt-oss-120b
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
4. Seed the compliance rules
powershell
python seed_rules.py
Expected: Added 10 rules. Total: 10.

5. Run
powershell
python manage.py migrate
python manage.py runserver
Open http://127.0.0.1:8000/

Usage
Paste a contract into the textarea (or upload PDF/DOCX)

Click "Run Compliance Review"

Wait ~10-15 seconds while the agent team analyzes the document

Review the compliance report

Approve or Reject with optional notes

See the final decision on the review page

Reviews persist across server restarts via SQLite checkpointing.

Project Structure
text
ComplianceGuard/
├── agents/                       # LangGraph agent definitions
│   ├── simple_agent.py           # 2-node demo
│   ├── supervisor_graph.py       # multi-agent (no HITL)
│   └── supervisor_hitl.py        # with human approval
├── src/
│   ├── config.py                 # reads .env
│   ├── rules_store.py            # ChromaDB for compliance rules
│   └── graph_runner.py           # Django-friendly wrapper + SQLite checkpointer
├── reviews/                      # Django app
│   ├── views.py                  # home, start, review_detail, decide
│   ├── urls.py
│   └── templates/reviews/
├── data/
│   ├── rules/rules.json          # seed compliance rules
│   ├── chroma_db/                # vector store
│   └── checkpoints.sqlite        # agent state
├── compliance_web/               # Django project
├── seed_rules.py
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
What I Learned
Agentic AI is about state, not prompts. The magic is in the graph —
routing, pausing, resuming. The LLM calls are almost incidental.

Human-in-the-loop is a design pattern, not a feature. LangGraph's
interrupt() + Command(resume=...) makes it explicit and testable.

Checkpointing changes everything. Once state survives restarts, agents
become production infrastructure, not demos.

Multi-agent is a spectrum. A supervisor routing to specialists is
often enough. You don't need 20 agents.

RAG and agents compose naturally. Retrieval grounds the specialist's
analysis; the specialist's output feeds the aggregator. No plumbing needed.

Limitations
Single-user, no auth — all reviewers share the dashboard

No role-based approval — anyone can approve any review

No streaming — the report appears when complete

Only 10 rules — real compliance needs hundreds; the rules.json format scales

Groq dependency — requires internet + API key for LLM calls

Future Work
Authentication + RBAC — separate reviewer vs. admin roles

Live agent trace — stream each agent's step to the UI

Multi-tenant rules — different rule sets per organization

Contract diffing — compare two versions of a contract

Export to PDF — signed compliance reports for records

Deploy — Railway/Render with Postgres-backed checkpointing

License
MIT — see LICENSE.

Author
Mxolisi Maseko

GitHub: @mxolisi78

LinkedIn: Mxolisi Maseko
'@ | Out-File -FilePath README.md -Encoding utf8

text

## 5.5 — Git init & push

```powershell
git init
git branch -M main
git add .
git status