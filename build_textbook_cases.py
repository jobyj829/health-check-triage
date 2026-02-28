#!/usr/bin/env python3
"""
build_textbook_cases.py
========================
Generates synthetic training examples from emergency medicine textbook
knowledge (Emergency Medicine Oral Board Review Illustrated; Case Files
Emergency Medicine, 3rd ed).

Each case encodes a clinically unambiguous presentation as a feature vector
using the same 67 columns as the real MIMIC/NHAMCS dataset, paired with the
textbook-correct triage level.  Cases are replicated with slight age jitter
to give them statistical weight during training.

Output
------
- outputs/triage_app/textbook_cases.csv.gz
  Columns: all 67 feature columns + triage_level + source ("textbook")

Usage
-----
    python build_textbook_cases.py
    # Then re-run train_triage_model.py to merge into training pipeline
"""

import json
import random
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "app" / "models"
OUT_DIR = BASE_DIR / "outputs" / "triage_app"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(MODEL_DIR / "feature_columns.json") as f:
    FEATURE_COLS = json.load(f)

random.seed(42)
np.random.seed(42)

# ═══════════════════════════════════════════════════════════════════════
# TEXTBOOK CASE DEFINITIONS
# Each dict: symptoms (list), pmh (list), age_range (tuple), gender_male
# (0/1/None=random), triage_level (1-5), label (for audit), repeats
# ═══════════════════════════════════════════════════════════════════════

TEXTBOOK_CASES = [
    # ──────────────────────────────────────────────────────────────────
    # LEVEL 1 — EMERGENCY DEPARTMENT (true emergencies)
    # ──────────────────────────────────────────────────────────────────

    # Acute MI — classic presentation (Oral Board Cases 7, 33, 35; Case Files Appendix A)
    {"symptoms": ["chest_pain"], "pmh": ["heart_problems", "high_blood_pressure", "diabetes"],
     "age_range": (50, 80), "gender_male": 1, "triage_level": 1,
     "label": "Acute MI classic — elderly male, cardiac risk factors", "repeats": 60},

    {"symptoms": ["chest_pain", "nausea_vomiting", "shortness_of_breath"],
     "pmh": ["diabetes"], "age_range": (45, 75), "gender_male": None, "triage_level": 1,
     "label": "Acute MI — chest pain + nausea + SOB + diabetes", "repeats": 60},

    {"symptoms": ["chest_pain", "shortness_of_breath"], "pmh": ["high_blood_pressure"],
     "age_range": (55, 85), "gender_male": 1, "triage_level": 1,
     "label": "Acute MI — chest pain + SOB + hypertension, older male", "repeats": 50},

    # Aortic dissection (Oral Board; Case Files Appendix A — 5 life-threatening chest pain)
    {"symptoms": ["chest_pain", "back_pain"], "pmh": ["high_blood_pressure"],
     "age_range": (50, 80), "gender_male": 1, "triage_level": 1,
     "label": "Aortic dissection — tearing chest/back pain + HTN", "repeats": 60},

    # Pulmonary embolism (Case Files Appendix A; Oral Board Case 9)
    {"symptoms": ["chest_pain", "shortness_of_breath"], "pmh": ["blood_thinner___clots"],
     "age_range": (30, 70), "gender_male": None, "triage_level": 1,
     "label": "Pulmonary embolism — chest pain + SOB + clot history", "repeats": 50},

    {"symptoms": ["shortness_of_breath", "chest_pain"], "pmh": [],
     "age_range": (25, 55), "gender_male": 0, "triage_level": 1,
     "label": "PE — SOB + chest pain in young female (OCP risk)", "repeats": 40},

    # Subarachnoid hemorrhage (Oral Board Cases 52, 59, 62)
    {"symptoms": ["headache"], "pmh": ["high_blood_pressure"],
     "age_range": (35, 65), "gender_male": None, "triage_level": 1,
     "label": "SAH — thunderclap headache + hypertension", "repeats": 60},

    # Meningitis (Oral Board Cases 53, 68; Case Files Case 42)
    {"symptoms": ["headache", "fever"], "pmh": [],
     "age_range": (18, 50), "gender_male": None, "triage_level": 1,
     "label": "Meningitis — headache + fever + neck stiffness", "repeats": 60},

    {"symptoms": ["headache", "fever", "altered_mental"], "pmh": [],
     "age_range": (20, 60), "gender_male": None, "triage_level": 1,
     "label": "Meningitis — headache + fever + AMS", "repeats": 50},

    # Neutropenic fever (Case Files; Oral Board Case 95)
    {"symptoms": ["fever"], "pmh": ["cancer", "hiv___immunocompromised"],
     "age_range": (30, 70), "gender_male": None, "triage_level": 1,
     "label": "Neutropenic fever — fever + immunocompromised", "repeats": 60},

    {"symptoms": ["fever"], "pmh": ["hiv___immunocompromised"],
     "age_range": (25, 65), "gender_male": None, "triage_level": 1,
     "label": "Fever in HIV/immunocompromised patient", "repeats": 50},

    # AAA (Case Files Cases 20, 21; Oral Board)
    {"symptoms": ["abdominal_pain", "back_pain", "dizziness"],
     "pmh": ["high_blood_pressure"], "age_range": (60, 85), "gender_male": 1,
     "triage_level": 1,
     "label": "AAA — abd pain + back pain + dizziness in elderly male", "repeats": 60},

    {"symptoms": ["abdominal_pain", "dizziness"], "pmh": ["high_blood_pressure"],
     "age_range": (65, 85), "gender_male": 1, "triage_level": 1,
     "label": "AAA — abd pain + lightheaded in elderly hypertensive male", "repeats": 50},

    # Ectopic pregnancy (Oral Board Case 40; Case Files)
    {"symptoms": ["abdominal_pain", "pelvic_pain", "vaginal_bleeding"],
     "pmh": [], "age_range": (18, 40), "gender_male": 0, "triage_level": 1,
     "label": "Ruptured ectopic — pelvic pain + vaginal bleeding", "repeats": 50},

    # Cauda equina (Oral Board Cases 54, 80)
    {"symptoms": ["back_pain", "weakness", "numbness"], "pmh": [],
     "age_range": (30, 70), "gender_male": None, "triage_level": 1,
     "label": "Cauda equina — back pain + bilateral weakness + numbness", "repeats": 60},

    # Stroke (Oral Board Cases 10, 24, 31)
    {"symptoms": ["weakness", "numbness", "headache"], "pmh": ["high_blood_pressure"],
     "age_range": (55, 85), "gender_male": None, "triage_level": 1,
     "label": "Stroke — one-sided weakness + numbness + headache + HTN", "repeats": 60},

    {"symptoms": ["weakness", "dizziness"], "pmh": ["high_blood_pressure", "diabetes"],
     "age_range": (60, 85), "gender_male": None, "triage_level": 1,
     "label": "Stroke — weakness + dizziness + multiple risk factors", "repeats": 50},

    # Status epilepticus (Oral Board Cases 34, 47)
    {"symptoms": ["seizure", "altered_mental"], "pmh": ["seizure_disorder"],
     "age_range": (20, 70), "gender_male": None, "triage_level": 1,
     "label": "Status epilepticus — seizure + AMS", "repeats": 50},

    # Epiglottitis / deep space infection (Case Files Case 1 Table 1-2)
    {"symptoms": ["sore_throat", "fever", "shortness_of_breath"],
     "pmh": [], "age_range": (3, 50), "gender_male": None, "triage_level": 1,
     "label": "Epiglottitis — sore throat + fever + SOB (stridor/drooling)", "repeats": 50},

    # Necrotizing fasciitis (Oral Board Cases 30, 57)
    {"symptoms": ["rash", "fever"], "pmh": ["diabetes"],
     "age_range": (40, 75), "gender_male": None, "triage_level": 1,
     "label": "Necrotizing fasciitis — spreading rash + fever + diabetes", "repeats": 50},

    # Sepsis (Oral Board Cases 3, 38, 45)
    {"symptoms": ["fever", "altered_mental", "shortness_of_breath"],
     "pmh": [], "age_range": (50, 85), "gender_male": None, "triage_level": 1,
     "label": "Sepsis — fever + AMS + SOB in elderly", "repeats": 50},

    {"symptoms": ["fever", "weakness", "dizziness"], "pmh": ["kidney_problems"],
     "age_range": (55, 85), "gender_male": None, "triage_level": 1,
     "label": "Sepsis — fever + weakness in patient with renal disease", "repeats": 40},

    # Acute glaucoma / retinal artery occlusion (Oral Board Cases 11, 16)
    {"symptoms": ["eye_problem", "headache", "nausea_vomiting"],
     "pmh": [], "age_range": (50, 80), "gender_male": None, "triage_level": 1,
     "label": "Acute angle-closure glaucoma — eye pain + headache + nausea", "repeats": 50},

    {"symptoms": ["eye_problem"], "pmh": ["heart_problems", "high_blood_pressure"],
     "age_range": (60, 85), "gender_male": None, "triage_level": 1,
     "label": "Central retinal artery occlusion — sudden vision loss + vascular RF", "repeats": 40},

    # Testicular torsion (Oral Board Case 42)
    {"symptoms": ["abdominal_pain", "nausea_vomiting"], "pmh": [],
     "age_range": (12, 25), "gender_male": 1, "triage_level": 1,
     "label": "Testicular torsion — lower abd pain + nausea in young male", "repeats": 40},

    # DKA (Oral Board Case 38; Case Files)
    {"symptoms": ["nausea_vomiting", "abdominal_pain", "weakness"],
     "pmh": ["diabetes"], "age_range": (15, 50), "gender_male": None, "triage_level": 1,
     "label": "DKA — nausea + abd pain + weakness in diabetic", "repeats": 50},

    # GI bleed + blood thinners (already red-flagged but needs model backup)
    {"symptoms": ["abdominal_pain", "gi_bleed", "dizziness"],
     "pmh": ["blood_thinner___clots"], "age_range": (55, 85), "gender_male": None,
     "triage_level": 1,
     "label": "GI bleed — abd pain + GI bleed + dizzy on anticoagulant", "repeats": 40},

    # Pneumothorax (Case Files)
    {"symptoms": ["chest_pain", "shortness_of_breath"], "pmh": ["asthma___copd"],
     "age_range": (18, 35), "gender_male": 1, "triage_level": 1,
     "label": "Pneumothorax — acute chest pain + SOB in young tall male", "repeats": 40},

    # Acute appendicitis (Case Files Case 11)
    {"symptoms": ["abdominal_pain", "fever", "nausea_vomiting"], "pmh": [],
     "age_range": (10, 40), "gender_male": None, "triage_level": 1,
     "label": "Acute appendicitis — RLQ pain + fever + nausea", "repeats": 50},

    # ──────────────────────────────────────────────────────────────────
    # LEVEL 2 — URGENT CARE (needs same-day eval, not life-threatening)
    # ──────────────────────────────────────────────────────────────────

    # Musculoskeletal chest pain (Case Files Case 1 approach; common benign)
    {"symptoms": ["chest_pain"], "pmh": [],
     "age_range": (18, 35), "gender_male": None, "triage_level": 2,
     "label": "MSK chest pain — young, no risk factors, reproducible", "repeats": 60},

    # Uncomplicated fracture (Oral Board; Case Files)
    {"symptoms": ["fracture", "extremity_pain"], "pmh": [],
     "age_range": (15, 60), "gender_male": None, "triage_level": 2,
     "label": "Simple fracture — extremity pain + suspected fracture", "repeats": 50},

    {"symptoms": ["fracture", "injury_fall"], "pmh": [],
     "age_range": (20, 65), "gender_male": None, "triage_level": 2,
     "label": "Fracture after fall — needs imaging", "repeats": 50},

    # Kidney stones (Case Files; Oral Board)
    {"symptoms": ["abdominal_pain", "urinary", "back_pain"], "pmh": [],
     "age_range": (25, 60), "gender_male": 1, "triage_level": 2,
     "label": "Kidney stone — flank pain + urinary + back pain", "repeats": 50},

    # Laceration needing repair
    {"symptoms": ["laceration", "injury_fall"], "pmh": [],
     "age_range": (15, 65), "gender_male": None, "triage_level": 2,
     "label": "Laceration — wound needing closure", "repeats": 40},

    # Asthma exacerbation moderate (Case Files)
    {"symptoms": ["shortness_of_breath", "cough"], "pmh": ["asthma___copd"],
     "age_range": (15, 50), "gender_male": None, "triage_level": 2,
     "label": "Moderate asthma exacerbation — SOB + cough + asthma hx", "repeats": 50},

    # Peritonsillar abscess (Case Files Case 1)
    {"symptoms": ["sore_throat", "fever"], "pmh": [],
     "age_range": (18, 40), "gender_male": None, "triage_level": 2,
     "label": "Peritonsillar abscess — severe sore throat + fever", "repeats": 40},

    # DVT (Oral Board; Case Files)
    {"symptoms": ["swelling", "extremity_pain"], "pmh": ["blood_thinner___clots"],
     "age_range": (35, 75), "gender_male": None, "triage_level": 2,
     "label": "DVT — unilateral leg swelling + pain + clot history", "repeats": 40},

    # Pyelonephritis (Case Files)
    {"symptoms": ["fever", "urinary", "back_pain"], "pmh": [],
     "age_range": (20, 55), "gender_male": 0, "triage_level": 2,
     "label": "Pyelonephritis — fever + urinary symptoms + flank pain", "repeats": 40},

    # Migraine with concerning features (Oral Board)
    {"symptoms": ["headache", "nausea_vomiting"], "pmh": [],
     "age_range": (20, 45), "gender_male": 0, "triage_level": 2,
     "label": "Severe migraine — headache + vomiting, needs eval", "repeats": 40},

    # Concussion (Case Files trauma cases)
    {"symptoms": ["injury_fall", "headache", "dizziness"], "pmh": [],
     "age_range": (15, 50), "gender_male": None, "triage_level": 2,
     "label": "Concussion — fall + headache + dizziness", "repeats": 40},

    # Cellulitis (Case Files)
    {"symptoms": ["rash", "fever", "swelling"], "pmh": [],
     "age_range": (25, 65), "gender_male": None, "triage_level": 2,
     "label": "Cellulitis — rash + fever + swelling, needs antibiotics", "repeats": 40},

    # ──────────────────────────────────────────────────────────────────
    # LEVEL 3 — PRIMARY CARE (next-day evaluation appropriate)
    # ──────────────────────────────────────────────────────────────────

    # Headache — non-specific, no red flags
    {"symptoms": ["headache"], "pmh": [],
     "age_range": (20, 45), "gender_male": None, "triage_level": 3,
     "label": "Tension headache — no red flags, young patient", "repeats": 50},

    # UTI uncomplicated (Case Files)
    {"symptoms": ["urinary"], "pmh": [],
     "age_range": (18, 45), "gender_male": 0, "triage_level": 3,
     "label": "Simple UTI — urinary symptoms, young female", "repeats": 50},

    # Non-specific belly pain, young
    {"symptoms": ["abdominal_pain"], "pmh": [],
     "age_range": (18, 35), "gender_male": None, "triage_level": 3,
     "label": "Non-specific abd pain — young, no red flags", "repeats": 50},

    # Chronic back pain
    {"symptoms": ["back_pain"], "pmh": [],
     "age_range": (25, 50), "gender_male": None, "triage_level": 3,
     "label": "Chronic mechanical back pain — no red flags", "repeats": 50},

    # Chronic neck pain
    {"symptoms": ["back_pain"], "pmh": [],
     "age_range": (30, 55), "gender_male": None, "triage_level": 3,
     "label": "Chronic neck/back pain — postural, no red flags", "repeats": 40},

    # Non-specific dizziness, orthostatic
    {"symptoms": ["dizziness"], "pmh": [],
     "age_range": (20, 45), "gender_male": None, "triage_level": 3,
     "label": "Orthostatic dizziness — young, no neuro signs", "repeats": 40},

    # GERD (Case Files)
    {"symptoms": ["chest_pain", "nausea_vomiting"], "pmh": ["stomach___acid_reflux"],
     "age_range": (25, 55), "gender_male": None, "triage_level": 3,
     "label": "GERD — chest burning + nausea + known reflux", "repeats": 40},

    # ──────────────────────────────────────────────────────────────────
    # LEVEL 4 — SPECIALIST (not emergency, targeted referral)
    # ──────────────────────────────────────────────────────────────────

    # Migraine — known pattern (Neurology)
    {"symptoms": ["headache"], "pmh": ["pain_condition"],
     "age_range": (20, 45), "gender_male": 0, "triage_level": 4,
     "label": "Chronic migraine — known pattern, needs neurology", "repeats": 40},

    # Recurrent palpitations (Cardiology)
    {"symptoms": ["palpitations"], "pmh": [],
     "age_range": (25, 50), "gender_male": None, "triage_level": 4,
     "label": "Recurrent palpitations — needs cardiology workup", "repeats": 40},

    # Chronic joint pain (Rheumatology)
    {"symptoms": ["extremity_pain", "swelling"], "pmh": ["autoimmune_disease"],
     "age_range": (30, 65), "gender_male": 0, "triage_level": 4,
     "label": "Chronic joint pain — autoimmune, needs rheumatology", "repeats": 40},

    # Chronic pelvic pain (GYN)
    {"symptoms": ["pelvic_pain"], "pmh": [],
     "age_range": (20, 45), "gender_male": 0, "triage_level": 4,
     "label": "Chronic pelvic pain — needs GYN eval", "repeats": 40},

    # Recurrent ear problem (ENT)
    {"symptoms": ["ear_problem"], "pmh": [],
     "age_range": (5, 50), "gender_male": None, "triage_level": 4,
     "label": "Recurrent ear problems — needs ENT referral", "repeats": 30},

    # ──────────────────────────────────────────────────────────────────
    # LEVEL 5 — REASSURANCE (self-care appropriate)
    # ──────────────────────────────────────────────────────────────────

    # Mild headache, young, no PMH
    {"symptoms": ["headache"], "pmh": [],
     "age_range": (18, 30), "gender_male": None, "triage_level": 5,
     "label": "Mild tension headache — young, healthy", "repeats": 50},

    # Viral URI / cold
    {"symptoms": ["cough", "sore_throat"], "pmh": [],
     "age_range": (18, 45), "gender_male": None, "triage_level": 5,
     "label": "Viral URI — cough + sore throat, no fever", "repeats": 60},

    # Mild sore throat, no fever
    {"symptoms": ["sore_throat"], "pmh": [],
     "age_range": (18, 40), "gender_male": None, "triage_level": 5,
     "label": "Viral pharyngitis — mild sore throat only", "repeats": 50},

    # Mild dizziness, resolves on standing
    {"symptoms": ["dizziness"], "pmh": [],
     "age_range": (18, 30), "gender_male": None, "triage_level": 5,
     "label": "Positional lightheadedness — benign, young", "repeats": 40},

    # Minor rash, no fever
    {"symptoms": ["rash"], "pmh": [],
     "age_range": (18, 50), "gender_male": None, "triage_level": 5,
     "label": "Minor contact dermatitis — mild rash, no systemic", "repeats": 40},

    # Mild nausea, self-limited
    {"symptoms": ["nausea_vomiting"], "pmh": [],
     "age_range": (18, 35), "gender_male": None, "triage_level": 5,
     "label": "Mild gastroenteritis — self-limited nausea", "repeats": 40},

    # Mild anxiety symptoms
    {"symptoms": ["anxiety_depression"], "pmh": [],
     "age_range": (18, 40), "gender_male": None, "triage_level": 5,
     "label": "Mild anxiety — no crisis features", "repeats": 40},

    # Insomnia
    {"symptoms": ["anxiety_depression"], "pmh": ["depression___anxiety"],
     "age_range": (25, 55), "gender_male": None, "triage_level": 5,
     "label": "Insomnia / chronic mild anxiety — established care", "repeats": 30},
]


def _make_row(case_def):
    """Build a single feature-vector row from a case definition."""
    row = {col: 0 for col in FEATURE_COLS}

    for sym in case_def["symptoms"]:
        col = f"sym_{sym}"
        if col in row:
            row[col] = 1

    for pmh in case_def.get("pmh", []):
        col = f"pmh_{pmh}"
        if col in row:
            row[col] = 1

    lo, hi = case_def["age_range"]
    row["age"] = random.randint(lo, hi)

    gm = case_def.get("gender_male")
    if gm is None:
        row["gender_male"] = random.choice([0, 1])
    else:
        row["gender_male"] = gm

    row["n_symptoms"] = sum(1 for c in FEATURE_COLS if c.startswith("sym_") and row[c] == 1)
    row["n_comorbidities"] = sum(1 for c in FEATURE_COLS if c.startswith("pmh_") and row[c] == 1)

    row["triage_level"] = case_def["triage_level"]
    row["source"] = "textbook"
    row["case_label"] = case_def["label"]

    return row


def main():
    print("=" * 70)
    print("  BUILD TEXTBOOK SYNTHETIC CASES")
    print("=" * 70)

    rows = []
    for case_def in TEXTBOOK_CASES:
        repeats = case_def.get("repeats", 50)
        for _ in range(repeats):
            rows.append(_make_row(case_def))

    df = pd.DataFrame(rows)
    print(f"\n  Total synthetic rows: {len(df):,}")
    print(f"  Unique case patterns: {len(TEXTBOOK_CASES)}")
    print(f"\n  Triage level distribution:")
    for lvl in sorted(df["triage_level"].unique()):
        n = (df["triage_level"] == lvl).sum()
        print(f"    Level {lvl}: {n:,}")

    audit_cols = ["case_label", "triage_level", "age", "gender_male", "n_symptoms", "n_comorbidities"]
    print(f"\n  Sample rows:")
    for _, r in df[audit_cols].drop_duplicates(subset=["case_label"]).head(10).iterrows():
        print(f"    L{r['triage_level']} | age={r['age']:3d} | {r['case_label']}")

    out_path = OUT_DIR / "textbook_cases.csv.gz"
    save_cols = FEATURE_COLS + ["triage_level", "source"]
    df[save_cols].to_csv(out_path, index=False, compression="gzip")
    print(f"\n  Saved to {out_path}")
    print(f"  File size: {out_path.stat().st_size / 1024:.1f} KB")
    print("\n  Done. Run train_triage_model.py to merge into training.")


if __name__ == "__main__":
    main()
