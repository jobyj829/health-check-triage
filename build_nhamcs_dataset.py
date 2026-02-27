#!/usr/bin/env python3
"""
build_nhamcs_dataset.py
========================
Reads NHAMCS Emergency Department public use fixed-width files (2018-2021)
from the CDC and converts them into the same feature schema used by the
MIMIC-based triage dataset, so the two can be merged for multi-center
model training.

Source: CDC National Hospital Ambulatory Medical Care Survey
       https://www.cdc.gov/nchs/nhamcs/
       Files are freely downloadable with no registration.
"""

import re
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
NHAMCS_DIR = BASE_DIR / "nhamcs_data"
OUT_DIR = BASE_DIR / "outputs" / "triage_app"
APP_CFG = BASE_DIR / "app" / "config"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Column specifications for fixed-width parsing (0-indexed start, end)
# Derived from ed21inp.txt SAS INPUT statements (@pos is 1-indexed)
COLSPECS_2021 = {
    "VMONTH":    (0, 2),
    "AGE":       (15, 18),
    "AGER":      (18, 19),
    "SEX":       (24, 25),
    "IMMEDR":    (66, 68),
    "PAINSCALE": (68, 70),
    "RFV1":      (72, 77),
    "RFV2":      (77, 82),
    "RFV3":      (82, 87),
    "DIAG1":     (121, 125),
    "DIAG2":     (125, 129),
    "DIAG3":     (129, 133),
    "ASTHMA":    (153, 154),
    "CANCER":    (154, 155),
    "CKD":       (156, 157),
    "COPD":      (157, 158),
    "CHF":       (158, 159),
    "CAD":       (159, 160),
    "DIABTYP1":  (161, 162),
    "DIABTYP2":  (162, 163),
    "DIABTYP0":  (163, 164),
    "ESRD":      (164, 165),
    "EDHIV":     (166, 167),
    "HTN":       (168, 169),
    "SUBSTAB":   (172, 173),
    "NOCHRON":   (173, 174),
    "ANYIMAGE":  (205, 206),
    "LOV":       (11, 15),
    "WAITTIME":  (7, 11),
    "LEFTAMA":   (490, 491),
    "DOA":       (491, 492),
    "DIEDED":    (492, 493),
    "TRANPSYC":  (494, 495),
    "TRANOTH":   (495, 496),
    "ADMITHOS":  (496, 497),
    "OBSHOS":    (497, 498),
    "OBSDIS":    (498, 499),
    "HDSTAT":    (526, 528),
    "REGION":    (625, 626),
}

# RFV code ranges → our symptom category IDs
# Based on CDC Reason for Visit Classification (RFVC)
RFV_TO_SYMPTOM = {
    "chest_pain":          range(10500, 10504),
    "fever":               range(10050, 10124),
    "weakness":            [10150, 10200, 10250],
    "dizziness":           [10300, 12250],
    "swelling":            [10351],
    "allergic_reaction":   [10900],
    "anxiety_depression":  list(range(11000, 11106)) + list(range(11150, 11306)),
    "substance_use":       list(range(11400, 11502)),
    "psychosis":           [11550],
    "numbness":            list(range(12200, 12205)),
    "headache":            [12100, 12101, 12070],
    "palpitations":        list(range(12600, 12604)) + [12650, 12700],
    "eye_problem":         list(range(13050, 13055)) + list(range(13100, 13404)),
    "ear_problem":         list(range(13450, 13654)),
    "nosebleed":           [14051],
    "shortness_of_breath": [14150, 14200, 14250] + list(range(14300, 14303)),
    "cough":               [14400, 14450, 14500, 14501, 14750],
    "sore_throat":         list(range(14550, 14557)) + [14600],
    "nausea_vomiting":     [15250, 15300],
    "abdominal_pain":      list(range(15400, 15454)) + [15350],
    "gi_bleed":            [15800, 15801, 15802],
    "constipation":        [15900],
    "diarrhea":            [15950],
    "urinary":             list(range(16400, 16404)) + list(range(16450, 16604))
                           + list(range(16650, 16703)) + [16750],
    "vaginal_bleeding":    list(range(17550, 17554)),
    "pelvic_pain":         list(range(17750, 17754)),
    "pregnancy_related":   list(range(17900, 17911)),
    "rash":                list(range(18400, 18404)) + [18600, 18601, 18650]
                           + list(range(18700, 18703)) + [18750],
    "back_pain":           list(range(19050, 19107)) + list(range(19100, 19107)),
    "neck_pain":           list(range(19000, 19007)),
    "extremity_pain":      list(range(19150, 19607)),
    "fracture":            list(range(5005, 5051)),
    "injury_fall":         list(range(5105, 5131)) + list(range(5405, 5431)),
    "laceration":          list(range(5205, 5231)) + list(range(5305, 5326)),
    "suicide_self_harm":   [5705, 5706],
    "altered_mental":      [12150],
    "stroke_symptoms":     [12300, 12350, 12352],
}

# Flatten the mapping for quick lookup: rfv_code -> [symptom_ids]
_RFV_LOOKUP = {}
for sym_id, codes in RFV_TO_SYMPTOM.items():
    for code in codes:
        _RFV_LOOKUP.setdefault(code, []).append(sym_id)


def rfv_to_symptoms(rfv1, rfv2, rfv3):
    """Map up to 3 RFV codes to a list of symptom category IDs."""
    matched = []
    for code in [rfv1, rfv2, rfv3]:
        if pd.isna(code) or code <= 0:
            continue
        code_int = int(code)
        if code_int in _RFV_LOOKUP:
            matched.extend(_RFV_LOOKUP[code_int])
        else:
            # Try the 3-digit prefix (broader category)
            prefix = code_int // 10
            for full_code, syms in _RFV_LOOKUP.items():
                if full_code // 10 == prefix:
                    matched.extend(syms)
                    break
    return list(set(matched)) if matched else ["other"]


def load_nhamcs_year(year):
    """Load one year of NHAMCS ED fixed-width data."""
    yy = str(year)[2:]
    # Try multiple naming patterns
    for name in [f"ED{year}", f"ed{year}", f"ED{yy}", f"ed{yy}"]:
        path = NHAMCS_DIR / name
        if path.exists():
            break
    else:
        print(f"    WARNING: No data file found for {year}")
        return None

    print(f"    Loading {path.name}...")

    cols = list(COLSPECS_2021.keys())
    specs = [COLSPECS_2021[c] for c in cols]

    df = pd.read_fwf(path, colspecs=specs, header=None, names=cols,
                     dtype=str, na_values=["-9", "-8", "-7", ""])

    # Convert numeric columns
    for col in cols:
        if col not in ("DIAG1", "DIAG2", "DIAG3"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["year"] = year
    print(f"      {len(df):,} records")
    return df


def assign_triage_level(row):
    """
    Assign 5-level triage label using NHAMCS disposition variables.
    Mirrors the MIMIC logic as closely as possible.
    """
    # Level 1: Admitted, died, DOA, transferred, or high-acuity triage
    if row.get("DIEDED") == 1 or row.get("DOA") == 1:
        return 1
    if row.get("ADMITHOS") == 1 or row.get("OBSHOS") == 1:
        return 1
    if row.get("TRANOTH") == 1 or row.get("TRANPSYC") == 1:
        return 1
    immedr = row.get("IMMEDR")
    if immedr == 1:  # Immediate (ESI 1)
        return 1
    if immedr == 2:  # Emergent (ESI 2)
        return 1

    # From here: discharged from ED
    if row.get("LEFTAMA") == 1:
        return 5

    # Low-acuity (ESI 4-5) and short visit → Reassurance
    lov = row.get("LOV", 0)
    if immedr in (4, 5) and (pd.isna(lov) or lov < 240):
        return 5

    # Observation then discharged → Urgent Care
    if row.get("OBSDIS") == 1:
        return 2

    # Semi-urgent (ESI 3) and longer visit → Primary Care
    if immedr == 3 and not pd.isna(lov) and lov >= 240:
        return 3

    # Remaining discharged → Urgent Care
    return 2


def main():
    print("=" * 70)
    print("  BUILD NHAMCS DATASET")
    print("  Source: CDC NHAMCS ED Public Use Files 2018-2021")
    print("=" * 70)

    # Load symptom categories from the app config (to align features)
    with open(APP_CFG / "symptom_categories.json") as f:
        sym_cats = json.load(f)
    sym_ids = {cat["id"] for cat in sym_cats}

    with open(APP_CFG / "pmh_categories.json") as f:
        pmh_cats = json.load(f)

    # ── 1. LOAD ALL YEARS ─────────────────────────────────────────────
    print("\n[1/5] Loading NHAMCS data files...")
    frames = []
    for year in [2018, 2019, 2020, 2021]:
        df_year = load_nhamcs_year(year)
        if df_year is not None:
            frames.append(df_year)

    if not frames:
        print("ERROR: No NHAMCS data loaded!")
        return

    df = pd.concat(frames, ignore_index=True)
    print(f"\n    Total records: {len(df):,}")

    # Filter to adults (age >= 18)
    df = df[df["AGE"] >= 18].copy()
    print(f"    Adults (≥18): {len(df):,}")

    # ── 2. MAP SYMPTOMS ──────────────────────────────────────────────
    print("\n[2/5] Mapping RFV codes → symptom categories...")
    df["symptom_cats"] = df.apply(
        lambda r: rfv_to_symptoms(r["RFV1"], r["RFV2"], r["RFV3"]), axis=1
    )
    df["primary_symptom"] = df["symptom_cats"].apply(lambda x: x[0])
    df["n_symptoms"] = df["symptom_cats"].apply(len)

    # Create binary symptom columns (same as MIMIC)
    for cat in sym_cats:
        cat_id = cat["id"]
        col = cat["feature_col"]
        # neck_pain maps to back_pain feature
        if cat_id == "back_pain":
            df[col] = df["symptom_cats"].apply(
                lambda x: 1 if "back_pain" in x or "neck_pain" in x else 0
            )
        else:
            df[col] = df["symptom_cats"].apply(
                lambda x: 1 if cat_id in x else 0
            )

    symptom_counts = Counter()
    for cats in df["symptom_cats"]:
        symptom_counts.update(cats)
    print(f"    Top 10: {symptom_counts.most_common(10)}")

    # ── 3. MAP PMH ──────────────────────────────────────────────────
    print("\n[3/5] Mapping comorbidity flags → PMH categories...")

    # NHAMCS comorbidity variable → our PMH category
    PMH_MAP = {
        "Diabetes":              lambda r: r.get("DIABTYP1") == 1 or r.get("DIABTYP2") == 1 or r.get("DIABTYP0") == 1,
        "High Blood Pressure":   lambda r: r.get("HTN") == 1,
        "Heart Problems":        lambda r: r.get("CHF") == 1 or r.get("CAD") == 1,
        "Asthma / COPD":         lambda r: r.get("ASTHMA") == 1 or r.get("COPD") == 1,
        "Cancer":                lambda r: r.get("CANCER") == 1,
        "Kidney Problems":       lambda r: r.get("CKD") == 1 or r.get("ESRD") == 1,
        "HIV / Immunocompromised": lambda r: r.get("EDHIV") == 1,
    }

    for pmh_cat_cfg in pmh_cats:
        pmh_id = pmh_cat_cfg["id"]
        col = pmh_cat_cfg["feature_col"]
        if pmh_id in PMH_MAP:
            df[col] = df.apply(PMH_MAP[pmh_id], axis=1).astype(int)
        else:
            df[col] = 0

    df["n_comorbidities"] = sum(
        df[cat["feature_col"]] for cat in pmh_cats
    )

    pmh_totals = {cat["id"]: int(df[cat["feature_col"]].sum()) for cat in pmh_cats}
    active = {k: v for k, v in pmh_totals.items() if v > 0}
    print(f"    Active PMH categories: {active}")

    # ── 4. ASSIGN TRIAGE LEVELS ──────────────────────────────────────
    print("\n[4/5] Assigning triage levels...")
    df["triage_level"] = df.apply(assign_triage_level, axis=1)

    print("    Level distribution:")
    level_labels = {1: "Emergency Department", 2: "Urgent Care",
                    3: "Primary Care", 4: "Specialist", 5: "Reassurance"}
    for lvl in sorted(df["triage_level"].unique()):
        n = (df["triage_level"] == lvl).sum()
        pct = 100 * n / len(df)
        print(f"      Level {lvl} ({level_labels.get(lvl, '?'):20s}): {n:>7,} ({pct:5.1f}%)")

    # ── 5. BUILD FINAL DATASET ───────────────────────────────────────
    print("\n[5/5] Building final feature matrix...")

    df["gender_male"] = (df["SEX"] == 1).astype(int)
    df["age"] = df["AGE"].fillna(40).astype(int)
    df["source"] = "nhamcs"

    # Outcome columns (for compatibility with MIMIC dataset)
    df["was_admitted"] = ((df["ADMITHOS"] == 1) | (df["OBSHOS"] == 1)).astype(int)
    df["went_to_icu"] = 0  # Not available in NHAMCS public use
    df["died_in_hospital"] = ((df["DIEDED"] == 1) | (df["DOA"] == 1)).astype(int)

    sym_feature_cols = [cat["feature_col"] for cat in sym_cats]
    pmh_feature_cols = [cat["feature_col"] for cat in pmh_cats]

    output_cols = (
        ["age", "gender_male", "n_symptoms", "n_comorbidities",
         "triage_level", "was_admitted", "went_to_icu", "died_in_hospital",
         "source", "year", "primary_symptom"]
        + sym_feature_cols + pmh_feature_cols
    )

    df_out = df[output_cols].copy()

    out_path = OUT_DIR / "nhamcs_dataset.csv.gz"
    df_out.to_csv(out_path, index=False, compression="gzip")
    print(f"\n    Saved {len(df_out):,} rows to {out_path}")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"NHAMCS DATASET SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total adult ED visits: {len(df_out):,}")
    print(f"Years: 2018-2021")
    print(f"Source: CDC NHAMCS Public Use Files")
    print(f"Symptom features: {len(sym_feature_cols)}")
    print(f"PMH features: {len(pmh_feature_cols)}")
    print(f"Admitted: {df_out['was_admitted'].sum():,} ({100*df_out['was_admitted'].mean():.1f}%)")
    print(f"Died: {df_out['died_in_hospital'].sum():,} ({100*df_out['died_in_hospital'].mean():.1f}%)")


if __name__ == "__main__":
    main()
