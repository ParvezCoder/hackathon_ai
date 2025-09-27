import json
import re

# ---------------------------
# SIMPLE RULE-BASED HELPERS
# ---------------------------
def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_budget(text):
    # attempt to extract digits
    m = re.search(r"(\d{3,})", text.replace(",", ""))
    if m:
        return int(m.group(1))
    return None

def normalize_sleep(text):
    text = text.lower()
    if any(w in text for w in ["night", "late", "late-night", "night owl"]):
        return "Night owl"
    if any(w in text for w in ["early", "morning", "early bird"]):
        return "Early bird"
    if any(w in text for w in ["day", "afternoon", "daytime"]):
        return "Daytime"
    return "Unknown"


def normalize_cleanliness(text):
    text = text.lower()
    if "tidy" in text or "clean" in text or "neat" in text:
        return "Tidy"
    if "messy" in text or "untidy" in text:
        return "Messy"
    return "Moderate"

def normalize_noise(text):
    text = text.lower()
    if "quiet" in text:
        return "Quiet"
    if "tolerant" in text or "ok with noise" in text:
        return "Tolerant"
    return "Moderate"




def normalize_study(text):
    text = text.lower()
    if "online" in text:
        return "Online classes"
    if "late" in text or "night" in text:
        return "Late-night study"
    return "Regular"

def parse_raw_profile(raw):
    # raw_profile_text likely has short descriptors — use heuristics
    budget = normalize_budget(raw) or None
    sleep = normalize_sleep(raw)
    clean = normalize_cleanliness(raw)
    noise = normalize_noise(raw)
    study = normalize_study(raw)
    food = "Flexible"
    # quick checks
    if "vegetarian" in raw.lower():
        food = "Vegetarian"
    return {
        "raw_text": raw,
        "budget_PKR": budget,
        "sleep_schedule": sleep,
        "cleanliness": clean,
        "noise_tolerance": noise,
        "study_habits": study,
        "food_pref": food,
    }
