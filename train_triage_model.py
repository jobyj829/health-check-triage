#!/usr/bin/env python3
"""
train_triage_model.py
======================
Phase 2 of the VC Triage App: train and evaluate multi-class triage models,
generate safety rules, pre-compute evidence statistics, and save all artifacts
the web app needs to make predictions.

Models
------
- XGBoost (primary): best accuracy
- Logistic Regression (backup): interpretable coefficients for evidence

Safety
------
- Red-flag rules (hard-coded overrides) saved to red_flags.json
- Class weighting biases toward Level 1 (cannot miss emergencies)
- Calibrated probability outputs

Output (all saved to app/models/ and app/config/)
---------------------------------------------------
- triage_xgb.joblib, triage_lr.joblib, scaler.joblib
- feature_columns.json, red_flags.json
- evidence_stats.json (updated with model performance)
- training_report.txt
"""

import json
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from collections import Counter

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    accuracy_score, f1_score
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR   = Path(__file__).resolve().parent
DATA_PATH  = BASE_DIR / "outputs" / "triage_app" / "triage_dataset.csv.gz"
MODEL_DIR  = BASE_DIR / "app" / "models"
CFG_DIR    = BASE_DIR / "app" / "config"
REPORT_DIR = BASE_DIR / "outputs" / "triage_app"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

LEVEL_LABELS = {
    1: "Emergency Department",
    2: "Urgent Care",
    3: "Primary Care",
    4: "Specialist",
    5: "Reassurance",
}

# ═══════════════════════════════════════════════════════════════════════
# RED-FLAG RULES — hard-coded overrides that always recommend Level 1
# These fire DURING the interview (before the model).  The model is a
# secondary check; red flags are non-negotiable.
# ═══════════════════════════════════════════════════════════════════════
RED_FLAG_RULES = [
    {
        "id": "chest_pain_sob",
        "name": "Chest Pain + Shortness of Breath",
        "description": "Chest pain with difficulty breathing may indicate a heart attack or pulmonary embolism.",
        "conditions": {"sym_chest_pain": 1, "sym_shortness_of_breath": 1},
        "override_level": 1,
        "message": "You mentioned chest pain AND trouble breathing. This combination needs emergency evaluation right away."
    },
    {
        "id": "stroke_symptoms",
        "name": "Possible Stroke",
        "description": "Stroke symptoms require immediate emergency care (time-critical).",
        "conditions": {"sym_stroke_symptoms": 1},
        "override_level": 1,
        "message": "Your symptoms may indicate a stroke. Call 911 or go to the nearest Emergency Department immediately. Time is critical."
    },
    {
        "id": "cardiac_arrest",
        "name": "Cardiac Arrest / Unresponsive",
        "description": "Signs of cardiac arrest.",
        "conditions": {"sym_cardiac_arrest": 1},
        "override_level": 1,
        "message": "This is a life-threatening emergency. Call 911 immediately."
    },
    {
        "id": "anaphylaxis",
        "name": "Severe Allergic Reaction",
        "description": "Anaphylaxis can be fatal without immediate treatment.",
        "conditions": {"sym_anaphylaxis": 1},
        "override_level": 1,
        "message": "A severe allergic reaction needs emergency treatment right away. If you have an EpiPen, use it now and call 911."
    },
    {
        "id": "suicide_self_harm",
        "name": "Suicidal Thoughts / Self-Harm",
        "description": "Any mention of self-harm requires immediate crisis intervention.",
        "conditions": {"sym_suicide_self_harm": 1},
        "override_level": 1,
        "message": "If you or someone you know is thinking about self-harm, please call 988 (Suicide & Crisis Lifeline) or go to your nearest Emergency Department now. You are not alone."
    },
    {
        "id": "chest_pain_diabetes_elderly",
        "name": "Chest Pain + Diabetes + Age > 40",
        "description": "Diabetic patients over 40 with chest pain are at high risk for atypical MI.",
        "conditions": {"sym_chest_pain": 1, "pmh_diabetes": 1},
        "age_min": 40,
        "override_level": 1,
        "message": "You mentioned chest pain and you have diabetes. People with diabetes can have heart attacks with unusual symptoms. Please go to the Emergency Department."
    },
    {
        "id": "sob_heart_failure",
        "name": "Shortness of Breath + Heart Problems",
        "description": "Acute decompensated heart failure requires emergency care.",
        "conditions": {"sym_shortness_of_breath": 1, "pmh_heart_problems": 1},
        "override_level": 1,
        "message": "You're having trouble breathing and you have heart problems. This could mean your heart condition is getting worse. Please go to the Emergency Department."
    },
    {
        "id": "gi_bleed",
        "name": "Blood in Stool or Vomit",
        "description": "GI bleeding can be life-threatening.",
        "conditions": {"sym_gi_bleed": 1},
        "override_level": 1,
        "message": "Blood in your stool or vomit can be a sign of serious internal bleeding. Please go to the Emergency Department."
    },
    {
        "id": "altered_mental_status",
        "name": "Confusion / Not Acting Right",
        "description": "Altered mental status has many dangerous causes.",
        "conditions": {"sym_altered_mental": 1},
        "override_level": 1,
        "message": "Sudden confusion or change in behavior can be a sign of a serious medical problem. Please go to the Emergency Department."
    },
    {
        "id": "seizure",
        "name": "Seizure",
        "description": "New or prolonged seizures need emergency evaluation.",
        "conditions": {"sym_seizure": 1},
        "override_level": 1,
        "message": "Seizures need emergency medical evaluation. Please go to the Emergency Department."
    },
    {
        "id": "allergic_reaction_breathing",
        "name": "Allergic Reaction + Breathing Difficulty",
        "description": "Allergic reaction with breathing problems suggests anaphylaxis.",
        "conditions": {"sym_allergic_reaction": 1, "sym_shortness_of_breath": 1},
        "override_level": 1,
        "message": "An allergic reaction that makes it hard to breathe is an emergency. If you have an EpiPen, use it and call 911."
    },
    {
        "id": "abd_pain_blood_thinners",
        "name": "Abdominal Pain + Blood Thinners",
        "description": "Patients on anticoagulants with acute abdominal pain may have internal bleeding.",
        "conditions": {"sym_abdominal_pain": 1, "pmh_blood_thinner___clots": 1},
        "override_level": 1,
        "message": "You have belly pain and you take blood thinners. This combination could indicate internal bleeding. Please go to the Emergency Department."
    },
]


def main():
    print("=" * 70)
    print("  TRAIN TRIAGE MODEL")
    print("=" * 70)

    # ── 1. LOAD DATA ──────────────────────────────────────────────────
    print("\n[1/6] Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"    {len(df):,} rows, {len(df.columns)} columns")

    # ── 2. FEATURE SELECTION ──────────────────────────────────────────
    print("\n[2/6] Selecting features...")
    sym_cols = [c for c in df.columns if c.startswith("sym_")]
    pmh_cols = [c for c in df.columns if c.startswith("pmh_")]

    feature_cols = sym_cols + pmh_cols + ["age", "gender_male", "n_symptoms", "n_comorbidities"]
    target_col = "triage_level"

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    X = X.fillna(0)
    print(f"    {len(feature_cols)} features: {len(sym_cols)} symptom + {len(pmh_cols)} PMH + 4 demographic")
    print(f"    Target distribution: {dict(Counter(y))}")

    # ── 3. TRAIN/TEST SPLIT ──────────────────────────────────────────
    print("\n[3/6] Splitting train/test (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"    Train: {len(X_train):,}  Test: {len(X_test):,}")

    # Scale features
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    # ── 4. TRAIN MODELS ──────────────────────────────────────────────
    # Class weights: heavily penalise missing Level 1 (emergencies)
    class_counts = Counter(y_train)
    total = len(y_train)
    base_weights = {lvl: total / (5 * cnt) for lvl, cnt in class_counts.items()}
    base_weights[1] = base_weights[1] * 3.0  # triple the weight for emergencies
    print(f"\n[4/6] Training models...")
    print(f"    Class weights: { {k: round(v, 2) for k, v in base_weights.items()} }")

    # ── 4a. Logistic Regression (interpretable) ──
    print("    Training Logistic Regression...")
    lr = LogisticRegression(
        max_iter=2000,
        class_weight=base_weights,
        multi_class="multinomial",
        solver="lbfgs",
        C=1.0,
        random_state=42,
    )
    lr.fit(X_train_sc, y_train)

    # ── 4b. Random Forest (primary — fast, multi-threaded) ──
    print("    Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=500,
        max_depth=20,
        min_samples_leaf=10,
        class_weight=base_weights,
        n_jobs=-1,
        random_state=42,
        verbose=1,
    )
    rf_model.fit(X_train_sc, y_train)

    # ── 4c. Calibrate RF ──
    print("    Calibrating probabilities...")
    cal_gb = CalibratedClassifierCV(rf_model, method="isotonic", cv=3)
    cal_gb.fit(X_train_sc, y_train)

    # ── 5. EVALUATE ──────────────────────────────────────────────────
    print("\n[5/6] Evaluating models...")

    report_lines = []
    report_lines.append("TRIAGE MODEL TRAINING REPORT")
    report_lines.append("=" * 60)

    for name, model in [("Logistic Regression", lr),
                         ("Random Forest (calibrated)", cal_gb)]:
        y_pred = model.predict(X_test_sc)
        y_prob = model.predict_proba(X_test_sc)

        acc = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average="macro")
        f1_weighted = f1_score(y_test, y_pred, average="weighted")

        # Level 1 sensitivity (critical metric)
        level1_mask = y_test == 1
        level1_sens = (y_pred[level1_mask] == 1).mean() if level1_mask.sum() > 0 else 0

        report_lines.append(f"\n{'─' * 60}")
        report_lines.append(f"MODEL: {name}")
        report_lines.append(f"{'─' * 60}")
        report_lines.append(f"  Accuracy:           {acc:.4f}")
        report_lines.append(f"  F1 (macro):         {f1_macro:.4f}")
        report_lines.append(f"  F1 (weighted):      {f1_weighted:.4f}")
        report_lines.append(f"  Level 1 Sensitivity: {level1_sens:.4f}  {'*** CRITICAL ***' if level1_sens < 0.90 else 'OK'}")
        report_lines.append(f"\n  Classification Report:")

        cr = classification_report(
            y_test, y_pred,
            target_names=[f"L{i} {LEVEL_LABELS[i]}" for i in [1, 2, 3, 4, 5]],
        )
        for line in cr.split("\n"):
            report_lines.append(f"    {line}")

        cm = confusion_matrix(y_test, y_pred, labels=[1, 2, 3, 4, 5])
        report_lines.append(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
        report_lines.append(f"    {'':15s}" + "".join(f"{'L'+str(i):>8s}" for i in [1, 2, 3, 4, 5]))
        for i, row in zip([1, 2, 3, 4, 5], cm):
            report_lines.append(f"    {'L'+str(i)+' '+LEVEL_LABELS[i]:15s}" + "".join(f"{v:>8d}" for v in row))

        print(f"\n    {name}:")
        print(f"      Accuracy={acc:.3f}, F1={f1_weighted:.3f}, Level1 Sensitivity={level1_sens:.3f}")

    # ── 6. SAVE ARTIFACTS ────────────────────────────────────────────
    print("\n[6/6] Saving model artifacts...")

    joblib.dump(cal_gb, MODEL_DIR / "triage_xgb.joblib")
    joblib.dump(lr, MODEL_DIR / "triage_lr.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    print(f"    Saved models to {MODEL_DIR}")

    with open(MODEL_DIR / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"    Saved feature_columns.json ({len(feature_cols)} features)")

    with open(CFG_DIR / "red_flags.json", "w") as f:
        json.dump(RED_FLAG_RULES, f, indent=2)
    print(f"    Saved red_flags.json ({len(RED_FLAG_RULES)} rules)")

    # ── Update evidence stats with model performance ──
    evidence_path = CFG_DIR / "evidence_stats.json"
    if evidence_path.exists():
        with open(evidence_path) as f:
            evidence = json.load(f)
    else:
        evidence = {}

    y_pred_gb = cal_gb.predict(X_test_sc)
    level1_sens_gb = (y_pred_gb[y_test == 1] == 1).mean()
    evidence["model_performance"] = {
        "accuracy": round(float(accuracy_score(y_test, y_pred_gb)), 4),
        "f1_weighted": round(float(f1_score(y_test, y_pred_gb, average="weighted")), 4),
        "level1_sensitivity": round(float(level1_sens_gb), 4),
        "test_size": int(len(X_test)),
        "train_size": int(len(X_train)),
    }

    # Per-symptom evidence: model prediction distributions
    df_test = df.iloc[X_test.index].copy()
    df_test["model_pred"] = y_pred_gb
    for cat_id in evidence.get("by_symptom", {}):
        col = f"sym_{cat_id}"
        if col in df_test.columns:
            subset = df_test[df_test[col] == 1]
            if len(subset) > 20:
                evidence["by_symptom"][cat_id]["model_pred_pcts"] = {
                    int(lvl): round(100 * (subset["model_pred"] == lvl).mean(), 1)
                    for lvl in [1, 2, 3, 4, 5]
                }

    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"    Updated evidence_stats.json with model performance")

    # Feature importance (Random Forest)
    importances = rf_model.feature_importances_
    top_features = sorted(zip(feature_cols, importances), key=lambda x: -x[1])[:20]
    report_lines.append(f"\n{'─' * 60}")
    report_lines.append("TOP 20 FEATURE IMPORTANCES (XGBoost)")
    report_lines.append(f"{'─' * 60}")
    for feat, imp in top_features:
        report_lines.append(f"  {feat:40s}: {imp:.4f}")

    report_text = "\n".join(report_lines)
    with open(REPORT_DIR / "training_report.txt", "w") as f:
        f.write(report_text)
    print(f"    Saved training_report.txt")

    print(f"\n{report_text}")
    print("\n  Phase 2 complete.")


if __name__ == "__main__":
    main()
