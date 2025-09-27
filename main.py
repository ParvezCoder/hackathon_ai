# main.py
import os
import json
import re

# Optional: load .env if you use it (safe fallback if python-dotenv missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Filenames used by app.py
PROFILES_FILE = "synthetic_roommate_profiles_pakistan_400.json"
LISTINGS_FILE = "housing_listings_pakistan_400.json"

# ---------------------------
# Basic helpers (exported)
# ---------------------------
def load_json_file(path):
    """Load and return JSON data from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_budget(text):
    if text is None:
        return None
    try:
        # if it's already an int
        if isinstance(text, (int, float)):
            return int(text)
        m = re.search(r"(\d{3,})", str(text).replace(",", ""))
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None

def normalize_sleep(text):
    if not text:
        return "Unknown"
    text = text.lower()
    if any(w in text for w in ["night", "late", "night owl"]):
        return "Night owl"
    if any(w in text for w in ["early", "morning", "early bird"]):
        return "Early bird"
    if any(w in text for w in ["day", "afternoon", "daytime"]):
        return "Daytime"
    return "Unknown"

def normalize_cleanliness(text):
    if not text:
        return "Moderate"
    text = text.lower()
    if "tidy" in text or "clean" in text or "neat" in text:
        return "Tidy"
    if "messy" in text or "untidy" in text:
        return "Messy"
    return "Moderate"

def normalize_noise(text):
    if not text:
        return "Moderate"
    text = text.lower()
    if "quiet" in text:
        return "Quiet"
    if "tolerant" in text or "ok with noise" in text:
        return "Tolerant"
    return "Moderate"

def normalize_study(text):
    if not text:
        return "Regular"
    text = text.lower()
    if "online" in text:
        return "Online classes"
    if "late" in text or "night" in text:
        return "Late-night study"
    return "Regular"

def parse_raw_profile(raw):
    """Turn a raw profile (string or dict) into structured dict."""
    if isinstance(raw, dict):
        # prefer structured fields if present
        text = raw.get("raw_profile_text") or raw.get("bio") or ""
        budget = normalize_budget(raw.get("budget_PKR") or raw.get("budget") or raw.get("expected_rent"))
    else:
        text = str(raw or "")
        budget = normalize_budget(text)

    sleep = normalize_sleep(text)
    clean = normalize_cleanliness(text)
    noise = normalize_noise(text)
    study = normalize_study(text)
    food = "Flexible"
    if "vegetarian" in text.lower():
        food = "Vegetarian"

    return {
        "raw_text": text,
        "budget_PKR": budget,
        "sleep_schedule": sleep,
        "cleanliness": clean,
        "noise_tolerance": noise,
        "study_habits": study,
        "food_pref": food,
    }

# ---------------------------
# Rule-based room matcher
# ---------------------------
def room_hunter(listings, profile, top_n=5):
    """
    listings: list of listing dicts (from JSON)
    profile: dict with keys e.g. city, budget_PKR, sleep_schedule, cleanliness, noise_tolerance, study_habits, food_pref
    Returns up to top_n matching listings (rule-based).
    """
    if listings is None:
        return []
    matches = []
    city = (profile.get("city") or "").strip().lower()
    budget = normalize_budget(profile.get("budget_PKR"))

    for l in listings:
        # skip if not available (safe check for missing fields)
        if str(l.get("availability", "available")).strip().lower() not in ("available", "yes", "true"):
            continue

        # city match if provided
        listing_city = (l.get("city") or l.get("location") or "").strip().lower()
        if city and listing_city and city != listing_city:
            continue

        # rent/budget check
        rent = normalize_budget(l.get("monthly_rent_PKR") or l.get("rent") or l.get("price"))
        if budget:
            if rent is None:
                # if listing has no rent, allow but de-prioritize
                pass
            else:
                if abs(rent - budget) / max(1, budget) > 0.15:
                    continue
        else:
            # no user budget -> accept small rents by default
            if rent and rent > 30000:
                continue

        # Optional lifestyle checks: only enforce if listing declares these fields
        # This makes matcher flexible with partial datasets.
        if profile.get("sleep_schedule") and l.get("sleep_schedule"):
            if profile["sleep_schedule"] != l["sleep_schedule"]:
                continue
        if profile.get("cleanliness") and l.get("cleanliness"):
            if profile["cleanliness"] != l["cleanliness"]:
                continue
        if profile.get("noise_tolerance") and l.get("noise_tolerance"):
            if profile["noise_tolerance"] != l["noise_tolerance"]:
                continue

        # if passes filters, add to matches
        matches.append(l)
        if len(matches) >= top_n:
            break

    # If not enough matches, return best-effort results (relax city check)
    if len(matches) < top_n and city:
        for l in listings:
            if l in matches:
                continue
            if str(l.get("availability", "available")).strip().lower() not in ("available", "yes", "true"):
                continue
            rent = normalize_budget(l.get("monthly_rent_PKR") or l.get("rent") or l.get("price"))
            if budget and rent and abs(rent - budget) / max(1, budget) > 0.25:
                continue
            matches.append(l)
            if len(matches) >= top_n:
                break

    return matches[:top_n]

# ---------------------------
# Local pipeline (pairwise scoring) — optional
# ---------------------------
def score_pair(p1, p2):
    score = 0
    breakdown = []
    # Sleep (30)
    sleep_pts = 30 if p1.get("sleep_schedule") == p2.get("sleep_schedule") else 0
    score += sleep_pts; breakdown.append(("sleep", sleep_pts))
    # Clean (25)
    clean_pts = 25 if p1.get("cleanliness") == p2.get("cleanliness") else (10 if "Moderate" in (p1.get("cleanliness"), p2.get("cleanliness")) else 0)
    score += clean_pts; breakdown.append(("cleanliness", clean_pts))
    # Noise (15)
    noise_pts = 15 if p1.get("noise_tolerance") == p2.get("noise_tolerance") else (5 if "Moderate" in (p1.get("noise_tolerance"), p2.get("noise_tolerance")) else 0)
    score += noise_pts; breakdown.append(("noise", noise_pts))
    # Study (15)
    study_pts = 15 if p1.get("study_habits") == p2.get("study_habits") else 5
    score += study_pts; breakdown.append(("study", study_pts))
    # Budget (15)
    b1, b2 = p1.get("budget_PKR") or 0, p2.get("budget_PKR") or 0
    if b1 and b2:
        diff = abs(b1 - b2) / max(1, max(b1, b2))
        if diff <= 0.15:
            budget_pts = 15
        elif diff <= 0.30:
            budget_pts = 7
        else:
            budget_pts = 0
    else:
        budget_pts = 7
    score += budget_pts; breakdown.append(("budget", budget_pts))
    return min(score, 100), breakdown

def local_pipeline(profiles_data, listings_data, top_n=5):
    parsed = []
    for p in profiles_data:
        # If profile already structured, prefer fields
        if isinstance(p, dict) and any(k in p for k in ("budget_PKR","sleep_schedule","cleanliness")):
            parsed.append({
                "id": p.get("id"),
                "budget_PKR": normalize_budget(p.get("budget_PKR") or p.get("budget")),
                "sleep_schedule": p.get("sleep_schedule") or normalize_sleep(p.get("raw_profile_text") or ""),
                "cleanliness": p.get("cleanliness") or normalize_cleanliness(p.get("raw_profile_text") or ""),
                "noise_tolerance": p.get("noise_tolerance") or normalize_noise(p.get("raw_profile_text") or ""),
                "study_habits": p.get("study_habits") or normalize_study(p.get("raw_profile_text") or ""),
                "raw_text": p.get("raw_profile_text") or p.get("bio") or ""
            })
        else:
            parsed.append(parse_raw_profile(p.get("raw_profile_text") if isinstance(p, dict) else p))
    # pairwise scoring (limited to first 30 to save time)
    results = []
    n = min(len(parsed), 30)
    for i in range(n):
        for j in range(i+1, n):
            s, breakdown = score_pair(parsed[i], parsed[j])
            results.append({
                "pair": (parsed[i].get("id"), parsed[j].get("id")),
                "score": s,
                "breakdown": breakdown
            })
    results_sorted = sorted(results, key=lambda x: -x["score"])
    return results_sorted[:top_n]

# End of file
