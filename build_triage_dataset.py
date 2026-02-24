#!/usr/bin/env python3
"""
build_triage_dataset.py
========================
Phase 1 of the VC Triage App: build a labeled dataset from the full
MIMIC-IV-ED cohort (all ED visits, not just sepsis) for training a
patient-facing triage risk-assessment model.

Pipeline
--------
1. Load all 425K+ ED visits (edstays + triage + demographics)
2. Map 60K+ free-text chief complaints → ~45 standardised symptom categories
3. Map home medications (medrecon) → ~22 past-medical-history flags
4. Link admission / ICU / mortality outcomes
5. Assign 5-level triage outcome labels
6. Engineer patient-reportable features
7. Save final dataset + lookup configs for the app

Output
------
- outputs/triage_app/triage_dataset.parquet   (one row per ED visit)
- app/config/symptom_categories.json          (symptom ontology)
- app/config/pmh_categories.json              (PMH mapping)
- app/config/medication_map.json              (med → PMH)
- outputs/triage_app/dataset_summary.txt      (audit / QC report)
"""

import os
import re
import json
import duckdb
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
DB_PATH    = BASE_DIR / "outputs" / "sepsis.duckdb"
ED_DIR     = BASE_DIR / "mimic-iv-ed-2.2" / "ed"
HOSP_DIR   = BASE_DIR / "mimic-iv-3.1" / "hosp"
ICU_DIR    = BASE_DIR / "mimic-iv-3.1" / "icu"
OUT_DIR    = BASE_DIR / "outputs" / "triage_app"
APP_CFG    = BASE_DIR / "app" / "config"
OUT_DIR.mkdir(parents=True, exist_ok=True)
APP_CFG.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════
# SYMPTOM ONTOLOGY — maps chief-complaint keywords → patient-friendly
# categories.  Order matters: first match wins.
# ═══════════════════════════════════════════════════════════════════════
SYMPTOM_RULES = [
    # ── Highest-acuity / red-flag symptoms first ──
    ("cardiac_arrest",      r"\b(cardiac arrest|code blue|pea|asystol|pulseless)\b",
     "Heart Stopped / Not Responsive"),
    ("stroke_symptoms",     r"\b(stroke|cva|tia|facial droop|slurred speech|hemipar|hemipleg)\b",
     "Stroke Symptoms"),
    ("anaphylaxis",         r"\b(anaphyla|angioedema)\b",
     "Severe Allergic Reaction"),
    ("suicide_self_harm",   r"\b(suicid|self.?harm|self.?inflict|overdose|si |s/i |s\.i\b|si/hi)\b",
     "Thoughts of Self-Harm"),
    ("psychosis",           r"\b(psychos|hallucin|delusion|paranoi)\b",
     "Seeing / Hearing Things"),
    ("seizure",             r"\b(seizur|convuls|epilep|status epilep)\b",
     "Seizure"),
    ("altered_mental",      r"\b(altered mental|ams|aoc|confus|unresponsive|obtund|lethar|encephalop)\b",
     "Confusion / Not Acting Right"),

    # ── Chest / Cardiopulmonary ──
    ("chest_pain",          r"\b(chest pain|chest tight|cp |angina|chest press)\b",
     "Chest Pain"),
    ("shortness_of_breath", r"\b(dyspnea|sob |shortness of breath|difficulty breathing|respiratory distress|can'?t breathe)\b",
     "Trouble Breathing"),
    ("palpitations",        r"\b(palpitat|heart rac|irregular heart|afib|atrial fib|svt|tachycard)\b",
     "Heart Racing / Fluttering"),
    ("cough",               r"\b(cough|bronchit|pneumonia|uri |upper resp)\b",
     "Cough / Cold Symptoms"),
    ("sore_throat",         r"\b(sore throat|pharyngit|tonsill|throat pain)\b",
     "Sore Throat"),

    # ── Abdominal / GI ──
    ("abdominal_pain",      r"\b(abd.?pain|abdominal|epigastr|rlq|ruq|llq|luq|flank pain|stomach)\b",
     "Belly Pain"),
    ("nausea_vomiting",     r"\b(nausea|vomit|emesis|n/?v\b|throw.?up)\b",
     "Nausea / Throwing Up"),
    ("diarrhea",            r"\b(diarr|loose stool|gastroenter)\b",
     "Diarrhea"),
    ("gi_bleed",            r"\b(gi bleed|brbpr|melena|hemat[eo]chez|blood.?stool|rectal bleed|hematemesis|blood.?vomit)\b",
     "Blood in Stool or Vomit"),
    ("constipation",        r"\b(constipat|obstipat|impaction)\b",
     "Constipation"),

    # ── Fever / Infection ──
    ("fever",               r"\b(fever|febrile|chills|temp \d|ili\b|influenza)\b",
     "Fever / Chills"),

    # ── Neurological ──
    ("headache",            r"\b(headache|migrain|head.?ache|cephalgia)\b",
     "Headache"),
    ("dizziness",           r"\b(dizz|vertigo|lightheaded|presyncop|syncop|faint|pass.?out)\b",
     "Dizziness / Feeling Faint"),
    ("weakness",            r"\b(weakness|weak|fatigue|malaise|generalized weakness)\b",
     "Feeling Weak / Tired"),
    ("numbness",            r"\b(numb|tingl|paresthes|radiculop)\b",
     "Numbness / Tingling"),

    # ── Musculoskeletal / Trauma ──
    ("back_pain",           r"\b(back pain|low.?back|lumbar|lbp|sciatica)\b",
     "Back Pain"),
    ("injury_fall",         r"\b(fall|s/?p fall|trauma|mvc|mva|assault|accident|struck|hit by)\b",
     "Injury / Fall"),
    ("fracture",            r"\b(fractur|broken|fx )\b",
     "Possible Broken Bone"),
    ("extremity_pain",      r"\b(arm pain|leg pain|knee pain|hip pain|shoulder|ankle|wrist|elbow|joint pain|extremity)\b",
     "Arm / Leg / Joint Pain"),
    ("laceration",          r"\b(lacerat|lac |wound|cut |stab|puncture)\b",
     "Cut / Wound"),

    # ── Urinary / Renal ──
    ("urinary",             r"\b(urin|uti|dysuria|hematuria|kidney stone|renal colic|flank)\b",
     "Urinary Problems"),

    # ── Skin ──
    ("rash",                r"\b(rash|cellulitis|abscess|skin infect|dermatit|hives|urticaria)\b",
     "Skin Problem / Rash"),
    ("swelling",            r"\b(swell|edema|dvt|deep vein|leg swell)\b",
     "Swelling"),

    # ── Eyes / ENT ──
    ("eye_problem",         r"\b(eye pain|vision|visual|blind|eye swell|conjunctiv|red eye)\b",
     "Eye Problem"),
    ("ear_problem",         r"\b(ear pain|earache|otit|hearing)\b",
     "Ear Problem"),
    ("nosebleed",           r"\b(epistaxis|nosebleed|nose bleed)\b",
     "Nosebleed"),

    # ── OB/GYN ──
    ("vaginal_bleeding",    r"\b(vaginal bleed|pv bleed|menorrh|metrorrh|ectopic|miscarr)\b",
     "Vaginal Bleeding"),
    ("pelvic_pain",         r"\b(pelvic pain|ovarian|pid )\b",
     "Pelvic Pain"),
    ("pregnancy_related",   r"\b(pregnan|labor|contraction|ob eval)\b",
     "Pregnancy Concern"),

    # ── Psychiatric / Behavioural ──
    ("anxiety_depression",  r"\b(anxiety|panic|depress|psychiatric|behavioral|agitat|psych eval)\b",
     "Feeling Anxious or Sad"),
    ("substance_use",       r"\b(etoh|alcohol|intox|withdraw|detox|drug|cocaine|heroin|opioid)\b",
     "Alcohol / Drug Related"),

    # ── Miscellaneous ──
    ("allergic_reaction",   r"\b(allergic|allergy|reaction|hives)\b",
     "Allergic Reaction"),
    ("abnormal_labs",       r"\b(abnormal lab|lab.?value|elevated|anemia|hyperkal|hyponatr)\b",
     "Abnormal Lab Results"),
    ("medication_refill",   r"\b(med.?refill|prescription|rx refill|medication)\b",
     "Medication Refill"),
    ("follow_up",           r"\b(follow.?up|f/?u |post.?op|wound.?check|suture remov)\b",
     "Follow-Up Visit"),
]

# ═══════════════════════════════════════════════════════════════════════
# PMH MAPPING — medication therapeutic class (etcdescription) keywords
# → patient-friendly PMH categories
# ═══════════════════════════════════════════════════════════════════════
PMH_MED_RULES = {
    "Diabetes": [
        r"antidiabetic", r"insulin", r"sulfonylurea", r"metformin",
        r"sglt2", r"glp-1", r"dpp-4", r"thiazolidinedione", r"meglitinide",
    ],
    "High Blood Pressure": [
        r"antihypertensive", r"ace inhibitor", r"arb\b", r"angiotensin",
        r"calcium channel", r"beta.?blocker", r"beta adrenergic.*antag",
        r"alpha.*blocker", r"diuretic", r"hydrochlorothiazide",
    ],
    "Heart Problems": [
        r"cardiac", r"antiarrhythmic", r"nitrate", r"digoxin", r"heart failure",
        r"antianginal",
    ],
    "Blood Thinner / Clots": [
        r"anticoagulant", r"antithrombotic", r"antiplatelet", r"warfarin",
        r"thrombin inhibitor", r"factor xa",
    ],
    "High Cholesterol": [
        r"statin", r"hmg.?coa", r"antilipemic", r"cholesterol", r"fibrate",
    ],
    "Asthma / COPD": [
        r"asthma", r"copd", r"bronchodilat", r"leukotriene", r"inhaled cortico",
        r"beta.?2.*agonist",
    ],
    "Depression / Anxiety": [
        r"antidepress", r"ssri", r"snri", r"anxiolytic", r"benzodiazepine",
        r"serotonin",
    ],
    "Thyroid Problems": [
        r"thyroid",
    ],
    "Seizure Disorder": [
        r"anticonvulsant", r"antiepileptic", r"seizure",
    ],
    "Kidney Problems": [
        r"renal", r"erythropoietin", r"epo\b", r"phosphate binder",
    ],
    "Liver Problems": [
        r"hepat", r"liver",
    ],
    "Stomach / Acid Reflux": [
        r"proton pump", r"antacid", r"h2.*antagonist", r"gerd",
    ],
    "Pain Condition": [
        r"opioid.*analges", r"narcotic", r"pain\b",
    ],
    "Cancer": [
        r"antineoplast", r"chemother", r"oncolog",
    ],
    "Organ Transplant": [
        r"immunosuppress", r"transplant", r"calcineurin",
    ],
    "HIV / Immunocompromised": [
        r"antiretroviral", r"hiv",
    ],
    "Autoimmune Disease": [
        r"biologic.*modifier", r"dmard", r"tnf inhibitor", r"autoimmune",
    ],
    "Psychiatric Condition": [
        r"antipsychotic", r"lithium", r"mood stabiliz",
    ],
    "Osteoporosis": [
        r"bisphosphonate", r"osteopor",
    ],
    "Gout": [
        r"antigout", r"uric acid",
    ],
    "Dementia / Memory Problems": [
        r"cholinesterase", r"alzheimer", r"dementia", r"memantine",
    ],
    "Parkinson's Disease": [
        r"parkinson", r"dopamine agonist", r"levodopa",
    ],
}

# ═══════════════════════════════════════════════════════════════════════
# ICD CODE MAPPING — for specialty-appropriate diagnoses (Level 4)
# ═══════════════════════════════════════════════════════════════════════
SPECIALTY_ICD_PREFIXES = {
    "Orthopedic": [
        "M", "S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
        "71", "72", "73", "8",
    ],
    "Dermatology": [
        "L", "68", "69", "70",
    ],
    "Ophthalmology": [
        "H0", "H1", "H2", "H3", "H4", "H5",
        "36", "37",
    ],
    "Psychiatry": [
        "F", "29", "30", "31",
    ],
    "ENT": [
        "H6", "H7", "H8", "H9", "J0", "J3",
        "38", "47",
    ],
}

SELF_LIMITING_ICD = [
    r"^J06",   # Acute upper respiratory infection
    r"^J00",   # Common cold
    r"^J20",   # Acute bronchitis
    r"^R51",   # Headache (unspecified)
    r"^K52",   # Noninfective gastroenteritis
    r"^A09",   # Infectious diarrhea
    r"^R11",   # Nausea and vomiting
    r"^R10",   # Abdominal pain (unspecified)
    r"^L03",   # Cellulitis (mild)
    r"^T14",   # Injury, unspecified
    r"^R05",   # Cough
    r"^M54",   # Back pain
    r"^R42",   # Dizziness
    r"^46",    # Migraine (ICD-9)
    r"^780",   # General symptoms
    r"^460",   # Acute nasopharyngitis (ICD-9)
    r"^465",   # Acute URI (ICD-9)
    r"^558",   # Gastroenteritis (ICD-9)
    r"^787",   # Nausea/vomiting (ICD-9)
    r"^789",   # Abdominal pain (ICD-9)
    r"^724",   # Back pain (ICD-9)
    r"^784",   # Headache (ICD-9)
]


def classify_chief_complaint(text):
    """Map a chief-complaint string to a list of symptom category IDs."""
    if not text or not isinstance(text, str):
        return ["other"]
    text_lower = text.lower().strip()
    matched = []
    for cat_id, pattern, _ in SYMPTOM_RULES:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matched.append(cat_id)
    return matched if matched else ["other"]


def build_pmh_flags(med_desc):
    """Map a medication etcdescription to matching PMH categories."""
    if not med_desc or not isinstance(med_desc, str):
        return []
    desc_lower = med_desc.lower()
    matched = []
    for pmh_cat, patterns in PMH_MED_RULES.items():
        for pat in patterns:
            if re.search(pat, desc_lower, re.IGNORECASE):
                matched.append(pmh_cat)
                break
    return matched


def is_specialty_icd(code):
    """Return the specialty name if the ICD code is specialty-appropriate."""
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    for specialty, prefixes in SPECIALTY_ICD_PREFIXES.items():
        for pfx in prefixes:
            if code.startswith(pfx):
                return specialty
    return None


def is_self_limiting(code):
    """Return True if the ICD code is typically self-limiting."""
    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    return any(re.match(pat, code) for pat in SELF_LIMITING_ICD)


# ═══════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  BUILD TRIAGE APP DATASET")
    print("  Source: Full MIMIC-IV-ED cohort (all ED visits)")
    print("=" * 70)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    # ── 1. BASE COHORT ─────────────────────────────────────────────────
    print("\n[1/7] Loading base cohort (edstays + triage + demographics)...")
    df = con.execute("""
        SELECT
            e.subject_id,
            e.hadm_id,
            e.stay_id,
            e.intime,
            e.outtime,
            e.gender,
            e.race,
            e.arrival_transport,
            e.disposition,
            t.temperature,
            t.heartrate,
            t.resprate,
            t.o2sat,
            t.sbp,
            t.dbp,
            t.pain,
            t.acuity   AS esi,
            t.chiefcomplaint,
            p.anchor_age AS age,
            p.dod
        FROM ed_edstays  e
        JOIN ed_triage    t ON e.stay_id = t.stay_id
        JOIN patients     p ON e.subject_id = p.subject_id
        WHERE p.anchor_age >= 18
    """).fetchdf()
    print(f"    Loaded {len(df):,} adult ED visits")

    # ── 2. SYMPTOM CATEGORIES ──────────────────────────────────────────
    print("\n[2/7] Mapping chief complaints → symptom categories...")
    df["symptom_cats"] = df["chiefcomplaint"].apply(classify_chief_complaint)
    df["primary_symptom"] = df["symptom_cats"].apply(lambda x: x[0])
    df["n_symptoms"] = df["symptom_cats"].apply(len)

    all_cat_ids = set()
    for cats in df["symptom_cats"]:
        all_cat_ids.update(cats)

    cat_id_to_label = {cat_id: label for cat_id, _, label in SYMPTOM_RULES}
    cat_id_to_label["other"] = "Other / Not Listed"

    for cat_id in sorted(all_cat_ids):
        col = f"sym_{cat_id}"
        df[col] = df["symptom_cats"].apply(lambda x, c=cat_id: 1 if c in x else 0)

    symptom_counts = Counter()
    for cats in df["symptom_cats"]:
        symptom_counts.update(cats)

    print(f"    {len(all_cat_ids)} symptom categories identified")
    print(f"    Top 10: {symptom_counts.most_common(10)}")

    # ── 3. PMH FROM MEDRECON ───────────────────────────────────────────
    print("\n[3/7] Loading medrecon → PMH flags...")
    con_mem = duckdb.connect(":memory:")
    medrecon = con_mem.execute(f"""
        SELECT subject_id, stay_id, name, etcdescription
        FROM read_csv_auto('{ED_DIR / 'medrecon.csv.gz'}')
    """).fetchdf()
    con_mem.close()
    print(f"    Loaded {len(medrecon):,} medication records")

    stay_pmh = defaultdict(set)
    etc_series = medrecon["etcdescription"].fillna("")
    sid_series = medrecon["stay_id"]
    for pmh_cat, patterns in PMH_MED_RULES.items():
        combined = "|".join(patterns)
        mask = etc_series.str.contains(combined, case=False, na=False)
        for sid in sid_series[mask].unique():
            stay_pmh[sid].add(pmh_cat)

    all_pmh_cats = sorted(set().union(*stay_pmh.values())) if stay_pmh else []
    for pmh_cat in all_pmh_cats:
        col = f"pmh_{pmh_cat.lower().replace(' ', '_').replace('/', '_')}"
        df[col] = df["stay_id"].apply(lambda sid, c=pmh_cat: 1 if c in stay_pmh.get(sid, set()) else 0)

    df["n_comorbidities"] = df["stay_id"].apply(lambda sid: len(stay_pmh.get(sid, set())))
    print(f"    {len(all_pmh_cats)} PMH categories mapped")
    pmh_dist = {cat: df[f"pmh_{cat.lower().replace(' ', '_').replace('/', '_')}"].sum()
                for cat in all_pmh_cats}
    print(f"    Top PMH: {sorted(pmh_dist.items(), key=lambda x: -x[1])[:8]}")

    # ── 4. OUTCOMES ────────────────────────────────────────────────────
    print("\n[4/7] Linking admission / ICU / mortality outcomes...")

    admitted = con.execute("""
        SELECT DISTINCT e.stay_id, a.hadm_id, a.admission_type, a.deathtime,
               a.hospital_expire_flag
        FROM ed_edstays e
        JOIN admissions a ON e.hadm_id = a.hadm_id
        WHERE e.hadm_id IS NOT NULL
    """).fetchdf()
    admitted_map = dict(zip(admitted["stay_id"], admitted["hospital_expire_flag"]))
    death_map = dict(zip(admitted["stay_id"], admitted["deathtime"].notna()))

    icu_stays = con.execute("""
        SELECT DISTINCT e.stay_id
        FROM ed_edstays e
        JOIN icustays i ON e.hadm_id = i.hadm_id
        WHERE e.hadm_id IS NOT NULL
    """).fetchdf()
    icu_set = set(icu_stays["stay_id"])

    df["was_admitted"] = df["hadm_id"].notna().astype(int)
    df["went_to_icu"] = df["stay_id"].isin(icu_set).astype(int)
    df["died_in_hospital"] = df["stay_id"].map(death_map).fillna(False).infer_objects(copy=False).astype(int)

    print(f"    Admitted: {df['was_admitted'].sum():,}")
    print(f"    ICU: {df['went_to_icu'].sum():,}")
    print(f"    Died: {df['died_in_hospital'].sum():,}")

    # ── 4b. ADVANCED LAB WORKUP ─────────────────────────────────────────
    print("\n[4b] Flagging ED stays with advanced lab orders...")
    ADVANCED_LAB_ITEMS = [
        51002, 52642, 51003,   # Troponin (T, T high-sens, I)
        50915, 51196, 52551,   # D-dimer
        50963,                 # BNP
        50813, 52442,          # Lactate
    ]
    item_list = ",".join(str(i) for i in ADVANCED_LAB_ITEMS)

    con_lab = duckdb.connect(":memory:")
    adv_lab_stays = con_lab.execute(f"""
        WITH ed_times AS (
            SELECT stay_id, hadm_id, intime, outtime
            FROM read_csv_auto('{ED_DIR / 'edstays.csv.gz'}')
            WHERE hadm_id IS NOT NULL
        )
        SELECT DISTINCT et.stay_id
        FROM ed_times et
        JOIN read_csv_auto('{HOSP_DIR / 'labevents.csv.gz'}') le
          ON et.hadm_id = le.hadm_id
        WHERE le.itemid IN ({item_list})
          AND le.charttime >= et.intime
          AND le.charttime <= et.outtime
    """).fetchdf()
    con_lab.close()
    adv_lab_set = set(adv_lab_stays["stay_id"])
    df["had_advanced_labs"] = df["stay_id"].isin(adv_lab_set).astype(int)
    print(f"    {len(adv_lab_set):,} stays had advanced labs (troponin/D-dimer/BNP/lactate)")

    # ── 5. ED DIAGNOSES ────────────────────────────────────────────────
    print("\n[5/7] Loading ED diagnoses for label assignment...")
    con_mem2 = duckdb.connect(":memory:")
    ed_dx = con_mem2.execute(f"""
        SELECT stay_id, icd_code, icd_title, seq_num
        FROM read_csv_auto('{ED_DIR / 'diagnosis.csv.gz'}')
    """).fetchdf()
    con_mem2.close()
    print(f"    Loaded {len(ed_dx):,} diagnosis records")

    primary_dx = ed_dx[ed_dx["seq_num"] == 1].set_index("stay_id")

    df["primary_icd"] = df["stay_id"].map(primary_dx["icd_code"])
    df["primary_dx_title"] = df["stay_id"].map(primary_dx["icd_title"])
    df["specialty_match"] = df["primary_icd"].apply(is_specialty_icd)
    df["self_limiting_dx"] = df["primary_icd"].apply(is_self_limiting)

    # ED length of stay in hours
    df["ed_los_hours"] = (
        (pd.to_datetime(df["outtime"]) - pd.to_datetime(df["intime"]))
        .dt.total_seconds() / 3600
    )

    # ── 6. TRIAGE LEVEL ASSIGNMENT ────────────────────────────────────
    print("\n[6/7] Assigning 5-level triage outcome labels...")

    def assign_triage_level(row):
        """
        Level 1 — ED: ICU, death, ESI 1, any admission, OR discharged
                  but had advanced workup (troponin/D-dimer/BNP/lactate)
        Level 2 — Urgent Care: discharged, NO advanced labs, basic workup
                  only (CBC/BMP/UA/X-ray level), ESI 3-5
        Level 3 — Primary Care: discharged, could wait 1-2 days
        Level 4 — Specialist: discharged with specialty-appropriate Dx
        Level 5 — Reassurance: self-limiting, minimal intervention
        """
        # Any admission, ICU, death, or ESI 1 → ED
        if row["went_to_icu"] == 1 or row["died_in_hospital"] == 1:
            return 1
        if row["esi"] == 1:
            return 1
        if row["was_admitted"] == 1:
            return 1

        # From here: not admitted (discharged from ED)
        # Discharged but had advanced labs → still ED-level
        if row["had_advanced_labs"] == 1:
            return 1

        # Left without being seen → Reassurance
        if row["disposition"] in ("LEFT WITHOUT BEING SEEN", "ELOPED",
                                   "LEFT AGAINST MEDICAL ADVICE"):
            return 5

        # Self-limiting + quick visit → Reassurance
        if row["self_limiting_dx"] and row.get("esi", 3) >= 4 and row["ed_los_hours"] < 4:
            return 5

        # Specialty-appropriate discharged diagnosis
        if row["specialty_match"] is not None and row.get("esi", 3) >= 3:
            return 4

        # Very quick, low-acuity discharge → Reassurance
        if row.get("esi", 3) >= 4 and row["ed_los_hours"] < 4:
            return 5

        # Self-limiting diagnosis (any remaining) → Reassurance
        if row["self_limiting_dx"]:
            return 5

        # Longer ED stay (ESI 3) without advanced labs → Primary Care
        if row.get("esi", 3) <= 3 and row["ed_los_hours"] >= 4:
            return 3

        # Remaining discharged, basic workup → Urgent Care
        return 2

    df["triage_level"] = df.apply(assign_triage_level, axis=1)

    level_labels = {
        1: "Emergency Department",
        2: "Urgent Care",
        3: "Primary Care",
        4: "Specialist",
        5: "Reassurance",
    }
    print("    Level distribution:")
    for lvl in sorted(df["triage_level"].unique()):
        n = (df["triage_level"] == lvl).sum()
        pct = 100 * n / len(df)
        print(f"      Level {lvl} ({level_labels.get(lvl, '?')}): {n:,} ({pct:.1f}%)")

    # ── 7. FINAL FEATURE SET & SAVE ──────────────────────────────────
    print("\n[7/7] Engineering final features and saving...")

    symptom_cols = [c for c in df.columns if c.startswith("sym_")]
    pmh_cols = [c for c in df.columns if c.startswith("pmh_")]

    feature_cols = (
        ["stay_id", "subject_id", "age", "gender", "esi",
         "primary_symptom", "n_symptoms", "n_comorbidities",
         "temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp", "pain",
         "ed_los_hours", "was_admitted", "went_to_icu", "died_in_hospital",
         "had_advanced_labs",
         "triage_level", "disposition", "primary_icd", "primary_dx_title",
         "specialty_match", "self_limiting_dx", "chiefcomplaint"]
        + symptom_cols + pmh_cols
    )

    df_out = df[feature_cols].copy()
    df_out["gender_male"] = (df_out["gender"] == "M").astype(int)

    out_path = OUT_DIR / "triage_dataset.csv.gz"
    df_out.to_csv(out_path, index=False, compression="gzip")
    print(f"    Saved {len(df_out):,} rows to {out_path}")

    # ── SAVE CONFIG FILES FOR THE APP ─────────────────────────────────
    symptom_config = []
    for cat_id, _, label in SYMPTOM_RULES:
        cnt = int(df[f"sym_{cat_id}"].sum()) if f"sym_{cat_id}" in df.columns else 0
        if cnt > 0:
            symptom_config.append({
                "id": cat_id,
                "label": label,
                "count_in_training": cnt,
                "feature_col": f"sym_{cat_id}",
            })
    symptom_config.append({
        "id": "other",
        "label": "Other / Not Listed",
        "count_in_training": int(df["sym_other"].sum()) if "sym_other" in df.columns else 0,
        "feature_col": "sym_other",
    })
    with open(APP_CFG / "symptom_categories.json", "w") as f:
        json.dump(symptom_config, f, indent=2)
    print(f"    Saved symptom_categories.json ({len(symptom_config)} categories)")

    pmh_config = []
    for pmh_cat in all_pmh_cats:
        col = f"pmh_{pmh_cat.lower().replace(' ', '_').replace('/', '_')}"
        cnt = int(df[col].sum()) if col in df.columns else 0
        pmh_config.append({
            "id": pmh_cat,
            "label": pmh_cat,
            "count_in_training": cnt,
            "feature_col": col,
        })
    with open(APP_CFG / "pmh_categories.json", "w") as f:
        json.dump(pmh_config, f, indent=2)
    print(f"    Saved pmh_categories.json ({len(pmh_config)} categories)")

    med_map_config = {cat: patterns for cat, patterns in PMH_MED_RULES.items()}
    with open(APP_CFG / "medication_map.json", "w") as f:
        json.dump(med_map_config, f, indent=2)

    # ── SUMMARY REPORT ────────────────────────────────────────────────
    report = []
    report.append("TRIAGE APP DATASET — BUILD SUMMARY")
    report.append("=" * 50)
    report.append(f"Total ED visits (adults): {len(df):,}")
    report.append(f"Date range: {df['intime'].min()} to {df['intime'].max()}")
    report.append(f"")
    report.append("TRIAGE LEVEL DISTRIBUTION:")
    for lvl in sorted(df["triage_level"].unique()):
        n = (df["triage_level"] == lvl).sum()
        pct = 100 * n / len(df)
        mort = df.loc[df["triage_level"] == lvl, "died_in_hospital"].mean() * 100
        report.append(f"  Level {lvl} ({level_labels[lvl]:20s}): {n:>7,} ({pct:5.1f}%)  mortality={mort:.2f}%")
    report.append("")
    report.append("ESI DISTRIBUTION:")
    for esi_val in sorted(df["esi"].dropna().unique()):
        n = (df["esi"] == esi_val).sum()
        report.append(f"  ESI {int(esi_val)}: {n:>7,}")
    report.append("")
    report.append(f"SYMPTOM CATEGORIES: {len(symptom_cols)}")
    report.append(f"PMH CATEGORIES: {len(pmh_cols)}")
    report.append(f"FEATURE COLUMNS: {len(feature_cols) + 1}")
    report.append("")
    report.append("TOP 15 SYMPTOM CATEGORIES:")
    for cat_id, cnt in symptom_counts.most_common(15):
        label = cat_id_to_label.get(cat_id, cat_id)
        report.append(f"  {label:35s}: {cnt:>7,}")
    report.append("")
    report.append("TOP 10 PMH CATEGORIES:")
    for cat, cnt in sorted(pmh_dist.items(), key=lambda x: -x[1])[:10]:
        report.append(f"  {cat:35s}: {cnt:>7,}")

    report_text = "\n".join(report)
    with open(OUT_DIR / "dataset_summary.txt", "w") as f:
        f.write(report_text)
    print(f"\n{report_text}")

    # ── EVIDENCE STATS (pre-computed for the app) ─────────────────────
    evidence = {}
    evidence["total_patients"] = int(len(df))
    evidence["level_distribution"] = {
        int(lvl): {
            "count": int(n),
            "pct": round(100 * n / len(df), 1),
            "label": level_labels[lvl],
        }
        for lvl, n in df["triage_level"].value_counts().items()
    }

    evidence["by_symptom"] = {}
    for cat_id, _, label in SYMPTOM_RULES:
        col = f"sym_{cat_id}"
        if col in df.columns:
            subset = df[df[col] == 1]
            if len(subset) > 50:
                evidence["by_symptom"][cat_id] = {
                    "label": label,
                    "n": int(len(subset)),
                    "level_pcts": {
                        int(lvl): round(100 * (subset["triage_level"] == lvl).mean(), 1)
                        for lvl in [1, 2, 3, 4, 5]
                    },
                    "icu_rate": round(100 * subset["went_to_icu"].mean(), 1),
                    "mortality_rate": round(100 * subset["died_in_hospital"].mean(), 1),
                }

    with open(APP_CFG / "evidence_stats.json", "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"    Saved evidence_stats.json")

    con.close()
    print("\n  Phase 1 complete.")


if __name__ == "__main__":
    main()
