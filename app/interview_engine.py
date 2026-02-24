"""
interview_engine.py
====================
Pluggable interview engine.  Phase 1 uses structured clinical question
trees (zero API cost).  Phase 2: swap to LLMInterviewEngine with one
config change.

The engine decides what question to ask next based on the patient's
current state (symptoms selected, answers given, PMH, demographics).
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

CFG_DIR = Path(__file__).resolve().parent / "config"
TREE_DIR = CFG_DIR / "interview_trees"

MAX_FOLLOWUPS = 6


@dataclass
class Question:
    """A single question to present to the patient."""
    id: str
    text: str
    question_type: str   # single_choice | multi_choice | number | text | textarea | body_map | severity_slider
    options: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class InterviewEngine:
    """Base interface — subclass to implement different backends."""

    def get_next_question(self, patient_state) -> Optional[Question]:
        raise NotImplementedError

    def check_red_flags(self, patient_state) -> Optional[dict]:
        """Return a red-flag rule dict if triggered, else None."""
        with open(CFG_DIR / "red_flags.json") as f:
            rules = json.load(f)

        features = patient_state.to_feature_dict()

        for rule in rules:
            conditions = rule.get("conditions", {})
            all_met = all(features.get(k, 0) >= v for k, v in conditions.items())
            if "age_min" in rule and patient_state.age is not None:
                all_met = all_met and patient_state.age >= rule["age_min"]
            if all_met and conditions:
                return rule
        return None


class TreeInterviewEngine(InterviewEngine):
    """
    Structured clinical question trees — zero API cost, deterministic,
    clinically validated.  Each symptom category has a JSON file that
    defines a branching question flow.
    """

    def __init__(self):
        self._trees = {}
        self._baseline_questions = self._build_baseline_questions()
        self._load_trees()

    def _load_trees(self):
        if not TREE_DIR.exists():
            return
        for fp in TREE_DIR.glob("*.json"):
            with open(fp) as f:
                tree = json.load(f)
                self._trees[tree["symptom_id"]] = tree

    def _build_baseline_questions(self):
        """Questions always asked at the start of every interview."""
        return [
            Question(
                id="name",
                text="What\u2019s your first name?",
                question_type="text",
                metadata={
                    "placeholder": "Your first name",
                    "subtitle": "We\u2019ll use this to personalize your experience.",
                },
            ),
            Question(
                id="zip_code",
                text="What\u2019s your zip code?",
                question_type="text",
                metadata={
                    "placeholder": "e.g. 10001",
                    "subtitle": "We\u2019ll use this to find nearby medical facilities for you.",
                    "optional": True,
                    "pattern": "[0-9]{5}",
                },
            ),
            Question(
                id="answering_for",
                text="Are you filling this out for yourself or for someone else?",
                question_type="single_choice",
                options=[
                    {"value": "self", "label": "For myself", "icon": "user"},
                    {"value": "someone_else", "label": "For someone else", "icon": "users"},
                ],
            ),
            Question(
                id="answering_for_reason",
                text="Why are you filling this out for them?",
                question_type="single_choice",
                options=[
                    {"value": "parent_child", "label": "I\u2019m a parent or guardian of a child", "icon": "child"},
                    {"value": "confused", "label": "They are confused and unable to answer questions", "icon": "alert"},
                    {"value": "chronic_unable", "label": "They have a medical condition that prevents them from answering (can\u2019t speak, too sick)", "icon": "emergency"},
                ],
            ),
            Question(
                id="age",
                text="How old are you?",
                question_type="number",
                metadata={"min": 0, "max": 120, "placeholder": "Age in years"},
            ),
            Question(
                id="sex",
                text="What is your biological sex?",
                question_type="single_choice",
                options=[
                    {"value": "male", "label": "Male"},
                    {"value": "female", "label": "Female"},
                ],
            ),
            Question(
                id="symptoms",
                text="What\u2019s bothering you today?",
                question_type="textarea",
                metadata={
                    "placeholder": "For example: \u201cMy chest hurts and I feel short of breath\u201d",
                    "rows": 3,
                    "subtitle": "Use your own words \u2014 there\u2019s no wrong answer.",
                },
            ),
            Question(
                id="pmh",
                text="Do you have any health conditions or take any medications?",
                question_type="textarea",
                metadata={
                    "placeholder": "For example: \u201cdiabetes, blood pressure pills\u201d or \u201cnone\u201d",
                    "rows": 3,
                },
            ),
        ]

    def get_next_question(self, patient_state) -> Optional[Question]:
        answered_ids = {h["question_id"] for h in patient_state.interview_history}

        # Phase 1: baseline questions
        is_proxy = patient_state.answering_for and patient_state.answering_for != "self"
        for q in self._baseline_questions:
            if q.id not in answered_ids:
                if q.id == "answering_for_reason":
                    if patient_state.answering_for == "self":
                        continue
                if is_proxy and q.id == "age":
                    return Question(
                        id=q.id, text="How old is the patient?",
                        question_type=q.question_type, options=q.options,
                        metadata=q.metadata,
                    )
                if is_proxy and q.id == "sex":
                    return Question(
                        id=q.id, text="What is the patient\u2019s biological sex?",
                        question_type=q.question_type, options=q.options,
                        metadata=q.metadata,
                    )
                if is_proxy and q.id == "symptoms":
                    return Question(
                        id=q.id, text="What\u2019s bothering them today?",
                        question_type=q.question_type, options=q.options,
                        metadata=q.metadata,
                    )
                if is_proxy and q.id == "pmh":
                    return Question(
                        id=q.id,
                        text="Do they have any health conditions or take any medications?",
                        question_type=q.question_type, options=q.options,
                        metadata=q.metadata,
                    )
                return q

        # Phase 2: symptom-specific follow-up questions (capped)
        followup_count = sum(1 for h in patient_state.interview_history if "__" in h["question_id"])
        if followup_count >= MAX_FOLLOWUPS:
            return None

        generic_tree = self._trees.get("_generic")
        used_generic = False

        for symptom_id in patient_state.selected_symptoms:
            tree = self._trees.get(symptom_id)
            if not tree:
                if generic_tree and not used_generic:
                    tree = generic_tree
                    used_generic = True
                else:
                    continue

            label = tree["label"] if tree["symptom_id"] != "_generic" else "your symptoms"

            for node in tree.get("questions", []):
                qid = f"{symptom_id}__{node['id']}"
                if qid in answered_ids:
                    continue

                condition = node.get("condition")
                if condition:
                    dep_qid = f"{symptom_id}__{condition['question_id']}"
                    dep_answer = patient_state.interview_answers.get(dep_qid)
                    if dep_answer not in condition.get("values", []):
                        continue

                metadata = dict(node.get("metadata", {}))
                metadata["context"] = f"About {label.lower()}"

                return Question(
                    id=qid,
                    text=node["text"],
                    question_type=node.get("type", "single_choice"),
                    options=node.get("options", []),
                    metadata=metadata,
                )

        return None

    def estimate_total(self, patient_state):
        """Rough estimate of total questions for progress display."""
        total = len(self._baseline_questions)
        followup_est = 0
        generic_tree = self._trees.get("_generic")
        used_generic = False
        for sym_id in patient_state.selected_symptoms:
            tree = self._trees.get(sym_id)
            if not tree and generic_tree and not used_generic:
                tree = generic_tree
                used_generic = True
            if tree:
                followup_est += len(tree.get("questions", []))
        total += min(followup_est, MAX_FOLLOWUPS)
        return max(total, len(self._baseline_questions))


class LLMInterviewEngine(InterviewEngine):
    """
    LLM-powered interview engine (Phase 2 stub).
    Drop-in replacement for TreeInterviewEngine.

    To activate:
      1. pip install openai
      2. Set OPENAI_API_KEY environment variable
      3. Set INTERVIEW_ENGINE=llm in config
    """

    def get_next_question(self, patient_state) -> Optional[Question]:
        raise NotImplementedError(
            "LLM engine not yet implemented. Set INTERVIEW_ENGINE=tree "
            "to use structured clinical trees (zero cost)."
        )
