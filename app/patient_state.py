"""
patient_state.py
=================
Accumulates patient answers throughout the interview.
Converts answers into a feature vector for the ML model.
Parses free-text symptom and PMH inputs via keyword matching.
"""

import re
import json
from pathlib import Path

CFG_DIR = Path(__file__).resolve().parent / "config"

# Symptom keywords: patient-friendly phrases → symptom category IDs.
# Multiple patterns can match, giving us multi-label classification.
SYMPTOM_KEYWORDS = {
    "chest_pain": [
        r"chest", r"heart\s*hurt", r"heart\s*pain", r"angina",
        r"chest\s*tight", r"chest\s*press",
    ],
    "shortness_of_breath": [
        r"breath", r"can'?t breathe", r"hard to breathe",
        r"short of breath", r"winded", r"gasp",
    ],
    "palpitations": [
        r"heart\s*rac", r"heart\s*beat", r"heart\s*flutter",
        r"palpitat", r"heart\s*pound", r"irregular\s*heart",
    ],
    "cough": [
        r"\bcough", r"bronchit", r"cold\b", r"congesti",
    ],
    "sore_throat": [
        r"sore\s*throat", r"throat\s*hurt", r"throat\s*pain", r"strep",
    ],
    "abdominal_pain": [
        r"stomach", r"belly", r"abdomen", r"abdominal",
        r"tummy", r"gut\s*pain", r"cramp",
    ],
    "nausea_vomiting": [
        r"nausea", r"throw\s*up", r"vomit", r"sick to my",
        r"puk", r"queasy",
    ],
    "diarrhea": [
        r"diarr", r"loose\s*stool", r"runny\s*stool",
    ],
    "gi_bleed": [
        r"blood.{0,10}stool", r"blood.{0,10}vomit", r"black\s*stool",
        r"rectal\s*bleed", r"bloody\s*stool",
    ],
    "constipation": [
        r"constipat", r"can'?t\s*(go|poop)",
    ],
    "fever": [
        r"fever", r"chills", r"temperature", r"hot\s*flash",
        r"sweating", r"flu\b",
    ],
    "headache": [
        r"headache", r"head\s*hurt", r"head\s*pain", r"migrain",
    ],
    "dizziness": [
        r"dizz", r"lightheaded", r"faint", r"vertigo",
        r"room\s*spin", r"pass\s*out", r"black\s*out",
    ],
    "weakness": [
        r"weak", r"tired", r"fatigue", r"no\s*energy",
        r"exhaust", r"run\s*down",
    ],
    "altered_mental": [
        r"confus", r"not\s*acting\s*right", r"not\s*making\s*sense",
        r"disoriented", r"memory",
    ],
    "numbness": [
        r"numb", r"tingl", r"pins\s*and\s*needle",
    ],
    "back_pain": [
        r"back\s*pain", r"back\s*hurt", r"lower\s*back",
        r"spine", r"sciatica", r"neck\s*(pain|hurt|ache|stiff)",
        r"neck\s*is\s*hurt", r"\bneck\b",
    ],
    "injury_fall": [
        r"\bfall\b", r"\bfell\b", r"injur", r"accident",
        r"hit\s*(my|by)", r"trauma",
    ],
    "fracture": [
        r"broke", r"broken", r"fractur",
    ],
    "extremity_pain": [
        r"arm\s*(hurt|pain)", r"leg\s*(hurt|pain)", r"knee",
        r"hip\s*pain", r"shoulder", r"ankle", r"wrist",
        r"elbow", r"joint", r"foot\s*pain",
    ],
    "laceration": [
        r"\bcut\b", r"wound", r"bleed", r"lacerat", r"stab",
    ],
    "urinary": [
        r"urin", r"pee", r"burn.{0,10}(pee|urin)",
        r"kidney", r"bladder",
    ],
    "rash": [
        r"rash", r"skin\s*(problem|issue)", r"hive", r"itch",
        r"bump", r"abscess", r"boil",
    ],
    "swelling": [
        r"swell", r"puffy", r"edema", r"bloat",
    ],
    "eye_problem": [
        r"\beyes?\b", r"vision", r"can'?t\s*see", r"\bblind",
        r"blurr", r"double\s*vision",
    ],
    "ear_problem": [
        r"ear\s*(ache|pain|hurt|infect)", r"hearing",
    ],
    "nosebleed": [
        r"nosebleed", r"nose\s*bleed",
    ],
    "vaginal_bleeding": [
        r"vaginal\s*bleed", r"period", r"menstrual",
    ],
    "pelvic_pain": [
        r"pelvic", r"ovary", r"ovarian",
    ],
    "pregnancy_related": [
        r"pregnan", r"baby", r"contraction",
    ],
    "anxiety_depression": [
        r"anxious", r"anxiety", r"panic", r"depress",
        r"sad\b", r"stress", r"nervous", r"worried",
    ],
    "suicide_self_harm": [
        r"suicid", r"self.?harm", r"kill\s*my", r"don'?t\s*want\s*to\s*live",
        r"end\s*(my|it)", r"hurt\s*myself",
    ],
    "psychosis": [
        r"hear.{0,10}voice", r"see.{0,10}thing", r"hallucin", r"paranoi",
    ],
    "substance_use": [
        r"alcohol", r"drug", r"drunk", r"high\b", r"withdraw",
        r"overdose",
    ],
    "allergic_reaction": [
        r"allerg", r"reaction", r"hive",
    ],
    "stroke_symptoms": [
        r"face\s*droop", r"slur", r"one\s*side", r"stroke",
        r"can'?t\s*move\s*(arm|leg|side)",
    ],
    "cardiac_arrest": [
        r"unresponsive", r"not\s*respond", r"heart\s*stop",
        r"no\s*pulse",
    ],
}

PMH_KEYWORDS = {
    "Diabetes": [
        r"diabet", r"sugar", r"insulin", r"a1c", r"blood\s*sugar",
        r"metformin", r"type\s*[12]",
    ],
    "High Blood Pressure": [
        r"blood\s*pressure", r"hypertens", r"bp\b",
        r"lisinopril", r"amlodipine", r"losartan",
    ],
    "Heart Problems": [
        r"heart\s*(disease|fail|attack|problem|condition|surgery)",
        r"coronary", r"bypass", r"stent", r"afib",
        r"atrial\s*fib", r"pacemaker", r"valve",
    ],
    "Blood Thinner / Clots": [
        r"blood\s*thin", r"warfarin", r"coumadin", r"eliquis",
        r"xarelto", r"clot", r"dvt", r"pe\b", r"anticoag",
    ],
    "High Cholesterol": [
        r"cholesterol", r"statin", r"lipid",
        r"atorvastatin", r"rosuvastatin",
    ],
    "Asthma / COPD": [
        r"asthma", r"copd", r"emphysema", r"inhaler",
        r"breathing\s*(problem|condition|disease)",
    ],
    "Depression / Anxiety": [
        r"depress", r"anxiety", r"mental\s*health",
        r"psych", r"antidepressant", r"ssri",
        r"lexapro", r"zoloft", r"prozac",
    ],
    "Thyroid Problems": [
        r"thyroid", r"levothyroxine", r"synthroid",
        r"hypothyroid", r"hyperthyroid",
    ],
    "Seizure Disorder": [
        r"seizur", r"epilep", r"convuls",
        r"keppra", r"dilantin",
    ],
    "Kidney Problems": [
        r"kidney", r"renal", r"dialysis",
    ],
    "Liver Problems": [
        r"liver", r"hepat", r"cirrhosis",
    ],
    "Stomach / Acid Reflux": [
        r"acid\s*reflux", r"gerd", r"heartburn", r"ulcer",
        r"omeprazole", r"pantoprazole",
    ],
    "Pain Condition": [
        r"chronic\s*pain", r"fibromyalg", r"pain\s*(management|doctor)",
        r"opioid", r"narcotic",
    ],
    "Cancer": [
        r"cancer", r"tumor", r"chemo", r"oncolog", r"leukemia",
        r"lymphoma",
    ],
    "Organ Transplant": [
        r"transplant",
    ],
    "HIV / Immunocompromised": [
        r"\bhiv\b", r"aids", r"immunocompromised",
        r"immune\s*(deficien|suppress)",
    ],
    "Autoimmune Disease": [
        r"lupus", r"rheumatoid", r"autoimmune", r"crohn",
        r"colitis", r"ms\b", r"multiple\s*sclerosis",
    ],
    "Psychiatric Condition": [
        r"bipolar", r"schizophren", r"psychos", r"lithium",
    ],
    "Osteoporosis": [
        r"osteopor", r"bone\s*(density|loss)",
    ],
    "Gout": [
        r"gout",
    ],
    "Dementia / Memory Problems": [
        r"dementia", r"alzheimer", r"memory\s*(loss|problem)",
    ],
    "Parkinson's Disease": [
        r"parkinson", r"tremor",
    ],
}


BODY_REGIONS = [
    {"id": "head", "label": "Head", "maps_to": [
        "headache", "dizziness", "eye_problem", "ear_problem", "nosebleed",
    ]},
    {"id": "throat", "label": "Throat", "maps_to": ["sore_throat"]},
    {"id": "chest", "label": "Chest", "maps_to": [
        "chest_pain", "cough",
    ]},
    {"id": "belly", "label": "Stomach / Belly", "maps_to": [
        "abdominal_pain", "nausea_vomiting", "diarrhea", "constipation",
    ]},
    {"id": "back", "label": "Back", "maps_to": ["back_pain"]},
    {"id": "arms", "label": "Arms / Hands", "maps_to": [
        "extremity_pain", "numbness", "swelling", "fracture", "laceration",
    ]},
    {"id": "legs", "label": "Legs / Feet", "maps_to": [
        "extremity_pain", "numbness", "swelling", "fracture", "laceration",
    ]},
    {"id": "skin", "label": "Skin", "maps_to": ["rash", "fever"]},
    {"id": "pelvic", "label": "Bathroom / Private", "maps_to": [
        "urinary", "pelvic_pain", "vaginal_bleeding", "pregnancy_related",
    ]},
    {"id": "mind", "label": "Emotions / Mind", "maps_to": [
        "anxiety_depression",
    ]},
    {"id": "whole_body", "label": "All Over", "maps_to": [
        "weakness", "fever",
    ]},
]

BODY_REGION_MAP = {r["id"]: r["maps_to"] for r in BODY_REGIONS}


def parse_symptom_text(text):
    """Parse free-text symptom description → list of matching symptom IDs."""
    if not text or not isinstance(text, str):
        return ["other"]
    text_lower = text.lower().strip()
    matched = []
    for cat_id, patterns in SYMPTOM_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                matched.append(cat_id)
                break
    return matched if matched else ["other"]


def parse_pmh_text(text):
    """Parse free-text PMH description → list of matching PMH category IDs."""
    if not text or not isinstance(text, str):
        return []
    text_lower = text.lower().strip()
    if text_lower in ("none", "no", "nothing", "n/a", "na", "nope", ""):
        return []
    matched = []
    for pmh_cat, patterns in PMH_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                matched.append(pmh_cat)
                break
    return matched


class PatientState:
    """Tracks all information gathered during the triage interview."""

    _group_map = None  # class-level cache

    def __init__(self):
        self.name = None
        self.answering_for = None          # "self", "parent_child", etc.
        self.age = None
        self.sex = None
        self.zip_code = None
        self.symptom_text = ""
        self.pmh_text = ""
        self.selected_body_regions = []    # body map region IDs
        self.selected_groups = []          # (legacy) symptom GROUP IDs
        self.selected_symptoms = []        # individual symptom IDs (for model)
        self.pmh = []
        self.interview_answers = {}
        self.interview_history = []
        self.red_flag_triggered = None
        self.phase = "welcome"

    @classmethod
    def _load_group_map(cls):
        if cls._group_map is None:
            with open(CFG_DIR / "symptom_groups.json") as f:
                groups = json.load(f)
            cls._group_map = {g["id"]: g["maps_to"] for g in groups}
        return cls._group_map

    def expand_groups_to_symptoms(self):
        """Expand selected groups into individual symptom IDs for the model."""
        gmap = self._load_group_map()
        expanded = []
        for gid in self.selected_groups:
            expanded.extend(gmap.get(gid, []))
        self.selected_symptoms = expanded

    def expand_body_regions_to_symptoms(self):
        """Expand selected body regions into symptom IDs."""
        expanded = set()
        for region_id in self.selected_body_regions:
            for sym_id in BODY_REGION_MAP.get(region_id, []):
                expanded.add(sym_id)
        self.selected_symptoms = list(expanded)

    def parse_symptoms_from_text(self):
        """Parse free-text and merge with any existing symptoms (e.g. from body map)."""
        text_symptoms = parse_symptom_text(self.symptom_text)
        merged = set(self.selected_symptoms)
        for s in text_symptoms:
            if s != "other":
                merged.add(s)
        if merged:
            self.selected_symptoms = list(merged)
        elif "other" in text_symptoms:
            self.selected_symptoms = ["other"]

    def parse_pmh_from_text(self):
        """Parse free-text PMH input into PMH category IDs."""
        self.pmh = parse_pmh_text(self.pmh_text)

    # ── Feature vector for model prediction ──────────────────────────
    def to_feature_dict(self):
        """Convert current state to a dict matching model feature columns."""
        features = {}

        with open(CFG_DIR / "symptom_categories.json") as f:
            sym_cats = json.load(f)
        for cat in sym_cats:
            features[cat["feature_col"]] = 1 if cat["id"] in self.selected_symptoms else 0

        with open(CFG_DIR / "pmh_categories.json") as f:
            pmh_cats = json.load(f)
        for cat in pmh_cats:
            features[cat["feature_col"]] = 1 if cat["id"] in self.pmh else 0

        features["age"] = self.age if self.age is not None else 40
        features["gender_male"] = 1 if self.sex == "male" else 0
        features["n_symptoms"] = len(self.selected_symptoms)
        features["n_comorbidities"] = len(self.pmh)

        return features

    def summary(self):
        """Return a human-readable summary of collected information."""
        parts = []
        if self.name:
            parts.append(f"Name: {self.name}")
        if self.age:
            parts.append(f"Age: {self.age}")
        if self.sex:
            parts.append(f"Sex: {self.sex}")
        if self.symptom_text:
            parts.append(f"Symptoms: {self.symptom_text}")
        elif self.selected_symptoms:
            parts.append(f"Symptoms: {', '.join(self.selected_symptoms)}")
        if self.pmh_text:
            parts.append(f"Medical history: {self.pmh_text}")
        elif self.pmh:
            parts.append(f"Medical history: {', '.join(self.pmh)}")
        return "; ".join(parts)
