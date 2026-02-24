"""
model.py
=========
Loads the trained triage model and makes predictions.
Applies red-flag safety overrides before returning results.
Selects specific specialist when referral is indicated, using
complaint-to-diagnosis data from Arvig et al. WestJEM 2022.
"""

import json
import numpy as np
import joblib
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "models"
CFG_DIR = Path(__file__).resolve().parent / "config"

LEVEL_LABELS = {
    1: "Go to the Emergency Department",
    2: "Visit an Urgent Care Center",
    3: "See Your Primary Care Doctor",
    4: "Consider Seeing a Specialist",
    5: "You're Likely Okay",
}

_specialist_map = None

def _load_specialist_map():
    global _specialist_map
    if _specialist_map is None:
        with open(CFG_DIR / "complaint_specialist_map.json") as f:
            _specialist_map = json.load(f)["complaint_map"]
    return _specialist_map


def get_specialist_for_symptoms(selected_symptoms, patient_state=None):
    """Select the most appropriate specialist based on the patient's symptoms.

    Uses discharge-diagnosis distributions from Arvig et al. WestJEM 2022
    (223,612 ED visits) to determine which specialist is most likely to
    manage the underlying condition.

    Returns a dict with: specialist, secondary, rationale, diagnosis_distribution
    """
    smap = _load_specialist_map()

    if not selected_symptoms:
        entry = smap.get("other", {})
        return {
            "specialist": entry.get("primary_specialist", "Internal Medicine Specialist"),
            "secondary": entry.get("secondary_specialist"),
            "rationale": entry.get("rationale", ""),
            "diagnosis_distribution": entry.get("diagnosis_distribution", {}),
        }

    HIGH_PRIORITY_SYMPTOMS = [
        "chest_pain", "shortness_of_breath", "stroke_symptoms",
        "cardiac_arrest", "gi_bleed", "altered_mental",
        "suicide_self_harm", "psychosis",
    ]
    for sym in HIGH_PRIORITY_SYMPTOMS:
        if sym in selected_symptoms and sym in smap:
            entry = smap[sym]
            return {
                "specialist": entry["primary_specialist"],
                "secondary": entry.get("secondary_specialist"),
                "rationale": entry["rationale"],
                "diagnosis_distribution": entry.get("diagnosis_distribution", {}),
            }

    for sym in selected_symptoms:
        if sym in smap and sym != "other":
            entry = smap[sym]
            sex = getattr(patient_state, "sex", None) if patient_state else None
            specialist = entry["primary_specialist"]
            secondary = entry.get("secondary_specialist")
            if sym == "pelvic_pain" and sex == "male":
                specialist = "Urologist"
                secondary = None
            return {
                "specialist": specialist,
                "secondary": secondary,
                "rationale": entry["rationale"],
                "diagnosis_distribution": entry.get("diagnosis_distribution", {}),
            }

    entry = smap.get("other", {})
    return {
        "specialist": entry.get("primary_specialist", "Internal Medicine Specialist"),
        "secondary": entry.get("secondary_specialist"),
        "rationale": entry.get("rationale", ""),
        "diagnosis_distribution": entry.get("diagnosis_distribution", {}),
    }

LEVEL_COLORS = {
    1: "red",
    2: "orange",
    3: "yellow",
    4: "blue",
    5: "green",
}

LEVEL_URGENCY = {
    1: "Call 911 or go to your nearest Emergency Department now.",
    2: "Visit an Urgent Care center today. Don't wait more than a few hours.",
    3: "Make an appointment with your doctor in the next 1-2 days.",
    4: "Consider making an appointment with a specialist.",
    5: "Your symptoms are likely not serious, but watch for changes.",
}

_model = None
_scaler = None
_feature_cols = None


def _load():
    global _model, _scaler, _feature_cols
    if _model is None:
        _model = joblib.load(MODEL_DIR / "triage_xgb.joblib")
        _scaler = joblib.load(MODEL_DIR / "scaler.joblib")
        with open(MODEL_DIR / "feature_columns.json") as f:
            _feature_cols = json.load(f)


def predict(patient_state):
    """
    Run the triage model on the patient state.
    Returns a dict with: level, label, color, urgency, probabilities,
    risk_factors, red_flag (if any).
    """
    _load()

    # Check red flags first
    if patient_state.red_flag_triggered:
        rule = patient_state.red_flag_triggered
        return {
            "level": 1,
            "label": LEVEL_LABELS[1],
            "color": LEVEL_COLORS[1],
            "urgency": LEVEL_URGENCY[1],
            "probabilities": {1: 0.99, 2: 0.005, 3: 0.003, 4: 0.001, 5: 0.001},
            "red_flag": rule,
            "risk_factors": [rule["message"]],
            "confidence": "high",
        }

    features = patient_state.to_feature_dict()
    X = np.array([[features.get(col, 0) for col in _feature_cols]])
    X_sc = _scaler.transform(X)

    probas = _model.predict_proba(X_sc)[0]
    classes = _model.classes_
    prob_dict = {int(cls): float(p) for cls, p in zip(classes, probas)}

    predicted_level = int(classes[np.argmax(probas)])

    # Conservative safety bias: escalate to ER only when the model
    # assigns substantial probability to Level 1.  The MIMIC-trained
    # model has a baseline P(L1) of ~15-25% for almost every
    # presentation (ED-population bias), so the threshold must be
    # high enough to avoid sending benign cases (sore throat, rash,
    # blurry vision) to the ER.
    p1 = prob_dict.get(1, 0)
    if p1 > 0.40 and predicted_level != 1:
        predicted_level = 1
    elif p1 > 0.30 and predicted_level in (2, 3):
        predicted_level = 1

    # Conservative: high-risk PMH with any active symptom → at least PCP
    HIGH_RISK_PMH = {
        "Heart Problems", "Diabetes", "Blood Thinner / Clots",
        "Cancer", "HIV / Immunocompromised", "Organ Transplant",
        "Kidney Problems", "Liver Problems",
    }
    has_high_risk_pmh = any(p in HIGH_RISK_PMH for p in patient_state.pmh)
    if has_high_risk_pmh and predicted_level >= 4:
        predicted_level = 3

    # Fractures / injuries need imaging — at minimum Urgent Care
    URGENT_CARE_MIN_SYMPTOMS = {"fracture", "injury_fall", "laceration"}
    if any(s in URGENT_CARE_MIN_SYMPTOMS for s in patient_state.selected_symptoms):
        if predicted_level >= 3:
            predicted_level = 2

    # Conservative: multiple symptoms with any high-risk → at least UC
    if len(patient_state.selected_symptoms) >= 3 and predicted_level >= 3:
        predicted_level = 2

    risk_factors = _identify_risk_factors(patient_state, prob_dict)

    confidence = "high" if max(probas) > 0.5 else "moderate" if max(probas) > 0.3 else "low"

    specialist_info = get_specialist_for_symptoms(
        patient_state.selected_symptoms, patient_state
    )

    # PCP-first complaints: these should go through primary care before
    # being referred to a specialist.  If the model predicts Level 4
    # (specialist), downgrade to Level 3 (PCP) and flag the specialist
    # as a potential referral from the PCP.
    PCP_FIRST_SYMPTOMS = {
        "abdominal_pain", "nausea_vomiting", "diarrhea", "constipation",
        "urinary", "headache",
        "cough", "sore_throat",
        "other",
    }
    pcp_first = any(s in PCP_FIRST_SYMPTOMS for s in patient_state.selected_symptoms)
    if pcp_first and predicted_level == 4:
        predicted_level = 3
        specialist_info["pcp_first"] = True

    label = LEVEL_LABELS[predicted_level]
    if predicted_level == 4 and specialist_info.get("specialist"):
        sp = specialist_info['specialist']
        article = "an" if sp[0].upper() in "AEIOU" else "a"
        label = f"See {article} {sp}"

    return {
        "level": predicted_level,
        "label": label,
        "color": LEVEL_COLORS[predicted_level],
        "urgency": LEVEL_URGENCY[predicted_level],
        "probabilities": prob_dict,
        "red_flag": None,
        "risk_factors": risk_factors,
        "confidence": confidence,
        "specialist": specialist_info,
    }


def _identify_risk_factors(patient_state, prob_dict):
    """Generate plain-language risk factor explanations."""
    factors = []

    with open(CFG_DIR / "symptom_categories.json") as f:
        sym_map = {c["id"]: c["label"] for c in json.load(f)}

    high_risk_symptoms = [
        "chest_pain", "shortness_of_breath", "stroke_symptoms",
        "altered_mental", "gi_bleed", "seizure", "cardiac_arrest",
    ]
    for sym in patient_state.selected_symptoms:
        if sym in high_risk_symptoms:
            label = sym_map.get(sym, sym)
            factors.append(f"You mentioned \"{label}\" — this symptom can sometimes be serious.")

    if patient_state.age and patient_state.age >= 65:
        factors.append("Your age (65+) means some conditions carry higher risk.")

    high_risk_pmh = ["Heart Problems", "Diabetes", "Blood Thinner / Clots",
                     "Cancer", "HIV / Immunocompromised", "Organ Transplant"]
    for pmh in patient_state.pmh:
        if pmh in high_risk_pmh:
            factors.append(f"Your medical history includes \"{pmh}\" — this may affect your risk.")

    if len(patient_state.selected_symptoms) >= 3:
        factors.append("You reported multiple symptoms, which may indicate a more complex condition.")

    return factors
