import json
from pathlib import Path

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

import markdown as md
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph_runner import (
    start_review, get_state, resume_review, list_reviews,
)


def _list_reviews_for_home():
    """Helper: build the review list used by the home template."""
    reviews = []
    for tid in list_reviews():
        state = get_state(tid)
        if state is None:
            continue
        reviews.append({
            "thread_id": tid,
            "doc_type": state["values"].get("doc_type", "—"),
            "is_paused": state["is_paused"],
            "is_complete": state["is_complete"],
            "approval": state["values"].get("approval", ""),
            "preview": (state["values"].get("document", "")[:80] + "..."),
        })
    return reviews


def home(request):
    """Homepage: shows the upload form and list of reviews."""
    return render(request, "reviews/home.html", {
        "reviews": _list_reviews_for_home(),
    })


@require_POST
def start(request):
    """Start a new review from pasted text or uploaded file."""
    doc_text = request.POST.get("document_text", "").strip()

    # Also support file upload
    file = request.FILES.get("document_file")
    if file and not doc_text:
        try:
            if file.name.endswith(".pdf"):
                import pypdf
                reader = pypdf.PdfReader(file)
                doc_text = "\n".join((p.extract_text() or "") for p in reader.pages)
            elif file.name.endswith(".docx"):
                import docx
                d = docx.Document(file)
                doc_text = "\n".join(p.text for p in d.paragraphs)
            else:
                doc_text = file.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return render(request, "reviews/home.html", {
                "error": f"Could not read file: {e}",
                "reviews": _list_reviews_for_home(),
            })

    if not doc_text:
        return render(request, "reviews/home.html", {
            "error": "Please paste some text or upload a file.",
            "reviews": _list_reviews_for_home(),
        })

    thread_id = start_review(doc_text)
    return redirect("review_detail", thread_id=thread_id)


def review_detail(request, thread_id):
    state = get_state(thread_id)
    if state is None:
        return render(request, "reviews/not_found.html", status=404)

    # Render markdown in the report
    report_html = md.markdown(
        state["values"].get("final_report", ""),
        extensions=["nl2br", "sane_lists"],
    )

    return render(request, "reviews/detail.html", {
        "thread_id": thread_id,
        "state": state,
        "values": state["values"],
        "report_html": report_html,
        "interrupt": state["interrupt"],
    })


@require_POST
def decide(request, thread_id):
    """Handle approve/reject decision."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    approval = data.get("approval")
    notes = data.get("notes", "")

    if approval not in ("approved", "rejected"):
        return JsonResponse(
            {"ok": False, "error": "approval must be 'approved' or 'rejected'."},
            status=400,
        )

    try:
        final = resume_review(thread_id, approval, notes)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({
        "ok": True,
        "approval": final.get("approval"),
        "notes": final.get("approver_notes", ""),
    })
