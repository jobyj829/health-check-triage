"""
routes.py
==========
Flask routes for the triage app.
Manages the interview flow: welcome → baseline → follow-ups → results.
"""

from flask import (
    Flask, render_template, request, session, redirect, url_for, jsonify
)
from .patient_state import PatientState
from .interview_engine import TreeInterviewEngine
from .model import predict
from .evidence import get_evidence
import json, os

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.secret_key = os.environ.get("SECRET_KEY", "triage-app-dev-key-change-in-prod")

engine = TreeInterviewEngine()


def _get_state() -> PatientState:
    """Restore PatientState from session."""
    state = PatientState()
    data = session.get("patient", {})
    state.name = data.get("name")
    state.answering_for = data.get("answering_for")
    state.age = data.get("age")
    state.sex = data.get("sex")
    state.zip_code = data.get("zip_code")
    state.symptom_text = data.get("symptom_text", "")
    state.pmh_text = data.get("pmh_text", "")
    state.selected_body_regions = data.get("body_regions", [])
    state.selected_symptoms = data.get("symptoms", [])
    state.pmh = data.get("pmh", [])
    state.interview_answers = data.get("answers", {})
    state.interview_history = data.get("history", [])
    state.red_flag_triggered = data.get("red_flag")
    state.phase = data.get("phase", "welcome")
    return state


def _save_state(state: PatientState):
    """Persist PatientState to session."""
    session["patient"] = {
        "name": state.name,
        "answering_for": state.answering_for,
        "age": state.age,
        "sex": state.sex,
        "zip_code": state.zip_code,
        "symptom_text": state.symptom_text,
        "pmh_text": state.pmh_text,
        "body_regions": state.selected_body_regions,
        "symptoms": state.selected_symptoms,
        "pmh": state.pmh,
        "answers": state.interview_answers,
        "history": state.interview_history,
        "red_flag": state.red_flag_triggered,
        "phase": state.phase,
    }


@app.route("/")
def welcome():
    session.clear()
    return render_template("welcome.html")


@app.route("/start", methods=["POST"])
def start():
    """User accepted disclaimer → begin interview."""
    state = PatientState()
    state.phase = "baseline"
    _save_state(state)
    return redirect(url_for("interview"))


@app.route("/interview")
def interview():
    state = _get_state()
    if state.red_flag_triggered:
        return redirect(url_for("results"))

    question = engine.get_next_question(state)
    if question is None:
        return redirect(url_for("results"))

    return render_template(
        "interview.html",
        question=question,
        progress=len(state.interview_history) + 1,
        total=engine.estimate_total(state),
        patient_name=state.name or "",
    )


@app.route("/answer", methods=["POST"])
def answer():
    """Process an answer and advance the interview."""
    state = _get_state()

    qid = request.form.get("question_id", "")
    qtype = request.form.get("question_type", "")
    qtext = request.form.get("question_text", "")

    if qtype == "multi_choice":
        raw = request.form.getlist("answer")
    else:
        raw = request.form.get("answer", "")

    state.interview_answers[qid] = raw
    answer_display = raw if isinstance(raw, str) else ", ".join(raw)

    if isinstance(raw, list):
        labels = request.form.getlist("answer_label")
        answer_display = ", ".join(labels) if labels else ", ".join(raw)

    state.interview_history.append({
        "question_id": qid,
        "question_text": qtext,
        "answer": raw,
        "answer_display": answer_display,
    })

    # Update state from baseline answers
    if qid == "name":
        state.name = raw.strip().title() if isinstance(raw, str) else ""
    elif qid == "answering_for":
        state.answering_for = raw
    elif qid == "answering_for_reason":
        state.answering_for = raw
        if raw == "confused":
            state.red_flag_triggered = {
                "id": "mental_status_confused",
                "name": "Confusion / Altered Mental Status",
                "message": (
                    "If the person you\u2019re helping is confused and unable "
                    "to answer questions, this may indicate a serious condition "
                    "such as a stroke, severe infection, or other emergency. "
                    "Please call 911 or go to the nearest Emergency Department "
                    "right away."
                ),
                "override_level": 1,
            }
            _save_state(state)
            return redirect(url_for("results"))
        # chronic_unable: patient has a pre-existing condition that prevents
        # them from answering (e.g., nonverbal, paralyzed). This is NOT an
        # emergency by itself — continue the interview normally and let the
        # decision tree / model determine the appropriate care level.
    elif qid == "age":
        try:
            state.age = int(raw)
        except (ValueError, TypeError):
            state.age = 40
    elif qid == "sex":
        state.sex = raw
    elif qid == "symptoms":
        state.symptom_text = raw if isinstance(raw, str) else " ".join(raw)
        state.parse_symptoms_from_text()
    elif qid == "pmh":
        state.pmh_text = raw if isinstance(raw, str) else " ".join(raw)
        state.parse_pmh_from_text()
    elif qid == "zip_code":
        state.zip_code = raw.strip() if isinstance(raw, str) else None

    # Red flag check: mental status flags fire immediately (handled above).
    # All other red flags fire after baseline intake is complete so we collect
    # PMH and zip code for the triage-nurse summary and facility finder.
    BASELINE_IDS = {"name", "answering_for", "age", "sex",
                    "symptoms", "pmh", "zip_code"}
    answered_ids = {h["question_id"] for h in state.interview_history}
    baseline_complete = BASELINE_IDS.issubset(answered_ids)

    if baseline_complete or "__" in qid:
        red_flag = engine.check_red_flags(state)
        if red_flag:
            state.red_flag_triggered = red_flag
            _save_state(state)
            return redirect(url_for("results"))

    _save_state(state)
    return redirect(url_for("interview"))


@app.route("/results")
def results():
    state = _get_state()
    prediction = predict(state)
    evidence = get_evidence(state, prediction)
    return render_template(
        "results.html",
        prediction=prediction,
        evidence=evidence,
        state=state,
    )


@app.route("/restart")
def restart():
    session.clear()
    return redirect(url_for("welcome"))
