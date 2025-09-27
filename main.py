# main.py
import os
import json
import re
from dotenv import load_dotenv
from instructions import ROOM_HUNTER_INSTRUCTIONS, ROOM_HUNTER_TOOL_DESC, WINGMAN_TOOL_DESC, RED_FLAG_TOOL_DESC,  MATCH_SCORE_TOOL_DESC, WINGMAN_INSTRUCTIONS, RED_FLAG_INSTRUCTIONS, MATCH_SCORE_INSTRUCTIONS, PROFILE_READER_INSTRUCTIONS
# Try to import agents SDK — if not available, we'll still run degraded local pipeline
try:
    from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI
    AGENTS_SDK_AVAILABLE = True
except Exception:
    AGENTS_SDK_AVAILABLE = False

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Files (assumed in same dir)
PROFILES_FILE = "synthetic_roommate_profiles_pakistan_400.json"
LISTINGS_FILE = "housing_listings_pakistan_400.json"


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

def score_pair(p1, p2):
    # Simple weighted scoring (0-100)
    score = 0
    max_score = 100
    breakdown = []
    # Sleep schedule: 30 points
    sleep_pts = 30 if p1["sleep_schedule"] == p2["sleep_schedule"] else 0
    score += sleep_pts
    breakdown.append(("sleep", sleep_pts))
    # Cleanliness: 25
    clean_pts = 25 if p1["cleanliness"] == p2["cleanliness"] else (10 if p1["cleanliness"] == "Moderate" or p2["cleanliness"] == "Moderate" else 0)
    score += clean_pts
    breakdown.append(("cleanliness", clean_pts))
    # Noise tolerance: 15
    noise_pts = 15 if p1["noise_tolerance"] == p2["noise_tolerance"] else (5 if "Moderate" in (p1["noise_tolerance"], p2["noise_tolerance"]) else 0)
    score += noise_pts
    breakdown.append(("noise", noise_pts))
    # Study habits: 15
    study_pts = 15 if p1["study_habits"] == p2["study_habits"] else 5
    score += study_pts
    breakdown.append(("study", study_pts))
    # Budget: 15 (full if within 15%)
    b1, b2 = p1.get("budget_PKR") or 0, p2.get("budget_PKR") or 0
    if b1 and b2:
        diff = abs(b1 - b2) / max(b1, b2)
        if diff <= 0.15:
            budget_pts = 15
        elif diff <= 0.30:
            budget_pts = 7
        else:
            budget_pts = 0
    else:
        budget_pts = 7  # unknown budgets: neutral
    score += budget_pts
    breakdown.append(("budget", budget_pts))
    return min(score, max_score), breakdown

def find_red_flags(p1, p2):
    flags = []
    # Opposite schedules + loud activity words
    loud_words = ["tabla", "drums", "music", "party", "guests", "concert"]
    if p1["sleep_schedule"] != p2["sleep_schedule"]:
        # check if either mentions loud words in raw_text
        if any(w in (p1.get("raw_text","") + p2.get("raw_text","")).lower() for w in loud_words):
            flags.append({"flag": "Sleep schedule conflict with loud activities", "severity": "High"})
        else:
            flags.append({"flag": "Different sleep schedules", "severity": "Medium"})
    # Cleanliness mismatch
    if (p1["cleanliness"] == "Tidy" and p2["cleanliness"] == "Messy") or (p2["cleanliness"] == "Tidy" and p1["cleanliness"] == "Messy"):
        flags.append({"flag": "Strong cleanliness mismatch", "severity": "High"})
    # Budget mismatch >30%
    b1, b2 = p1.get("budget_PKR") or 0, p2.get("budget_PKR") or 0
    if b1 and b2:
        if abs(b1 - b2) / max(b1, b2) > 0.30:
            flags.append({"flag": "Large budget mismatch", "severity": "Medium"})
    return flags

def wingman_explain(p1, p2, score, breakdown, flags):
    expl = []
    expl.append(f"Compatibility score: {score}/100.")
    # top contributors
    sorted_breakdown = sorted(breakdown, key=lambda x: -x[1])
    expl.append("Top factors: " + ", ".join([f"{k}({v})" for k, v in sorted_breakdown[:3]]))
    if flags:
        expl.append("Concerns: " + "; ".join([f"{f['flag']} [{f['severity']}]" for f in flags]))
    # compromises
    compromises = []
    if p1["sleep_schedule"] != p2["sleep_schedule"]:
        compromises.append("Agree on quiet hours or use headphones for late-night activities.")
    if (p1["cleanliness"] == "Tidy" and p2["cleanliness"] == "Messy") or (p2["cleanliness"] == "Tidy" and p1["cleanliness"] == "Messy"):
        compromises.append("Create a simple chore schedule and common-area rules.")
    if compromises:
        expl.append("Suggested compromises: " + " / ".join(compromises))
    return "\n".join(expl)

def room_hunter(listings, profile):
    # return up to 5 listings in same city within +/-15% of budget
    matches = []
    city = (profile.get("city") or "").lower()
    budget = profile.get("budget_PKR")
    for l in listings:
        if l.get("availability","").lower() != "available":
            continue
        if city and l.get("city","").lower() != city:
            continue
        rent = l.get("monthly_rent_PKR") or 0
        if not budget:
            # unknown budget -> accept if rent <= 30000 (safe default)
            if rent <= 30000:
                matches.append(l)
        else:
            if abs(rent - budget) / max(1, budget) <= 0.15:
                matches.append(l)
        if len(matches) >= 5:
            break
    return matches

# ---------------------------
# Degraded local pipeline
# ---------------------------
def local_pipeline(profiles_data, listings_data, top_n=5):
    # Parse raw profiles into structured
    parsed_profiles = []
    for p in profiles_data:
        parsed = parse_raw_profile(p.get("raw_profile_text",""))
        # keep city/area and id if present
        parsed["id"] = p.get("id")
        parsed["city"] = p.get("city")
        parsed["area"] = p.get("area")
        # if dataset already has structured fields, prefer them
        for k in ["budget_PKR", "sleep_schedule", "cleanliness", "noise_tolerance", "study_habits", "food_pref"]:
            if p.get(k) is not None:
                parsed[k] = p.get(k)
        parsed_profiles.append(parsed)

    # For demonstration: compute pairwise scores for first 30 profiles (to limit work)
    results = []
    n = min(len(parsed_profiles), 30)
    for i in range(n):
        for j in range(i+1, n):
            p1 = parsed_profiles[i]
            p2 = parsed_profiles[j]
            score, breakdown = score_pair(p1, p2)
            flags = find_red_flags(p1, p2)
            explanation = wingman_explain(p1, p2, score, breakdown, flags)
            # optionally find room listings that fit both budgets and same city
            combined_budget = None
            if p1.get("budget_PKR") and p2.get("budget_PKR"):
                combined_budget = int((p1["budget_PKR"] + p2["budget_PKR"]) / 2)
            # pick listings in the city
            sample_profile_for_room_hunt = {"city": p1.get("city"), "budget_PKR": combined_budget}
            rooms = room_hunter(listings_data, sample_profile_for_room_hunt)
            results.append({
                "pair": (p1.get("id"), p2.get("id")),
                "score": score,
                "breakdown": breakdown,
                "flags": flags,
                "explanation": explanation,
                "room_suggestions": [{"listing_id": r.get("listing_id"), "area": r.get("area"), "monthly_rent_PKR": r.get("monthly_rent_PKR")} for r in rooms]
            })
    # sort desc by score and return top_n matches
    results_sorted = sorted(results, key=lambda x: -x["score"])
    return results_sorted[:top_n]

# ---------------------------
# Main entry
# ---------------------------
def main():
    # load datasets
    try:
        profiles = load_json_file(PROFILES_FILE)
        listings = load_json_file(LISTINGS_FILE)
    except FileNotFoundError as e:
        print("Make sure both JSON files are in the same folder as main.py:")
        print(" -", PROFILES_FILE)
        print(" -", LISTINGS_FILE)
        raise e

    if GEMINI_API_KEY and AGENTS_SDK_AVAILABLE:

        external_client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=GEMINI_API_KEY
        )

        model = OpenAIChatCompletionsModel(
            openai_client=external_client,
            model="gemini-2.5-flash"
        )

        # Sub agents (populate instructions and tool descriptions)
        match_score_agent = Agent(
            name="Match_Score_Agent",
            instructions=MATCH_SCORE_INSTRUCTIONS,
            model=model,
        )

        red_flag_agent = Agent(
            name="Red_Flag_Agent",
            instructions=RED_FLAG_INSTRUCTIONS,
            model=model,
        )

        wingman_agent = Agent(
            name="Wing_man_Agent",
            instructions=WINGMAN_INSTRUCTIONS,
            model=model,
        )

        room_hunter_agent = Agent(
            name="Room_Hunter_Agent",
            instructions=ROOM_HUNTER_INSTRUCTIONS,
            model=model,
        )

        # Main profile reader agent with tools
        profile_reader_agent = Agent(
            name="Profile_Reader_Agent",
            model=model,
            instructions=PROFILE_READER_INSTRUCTIONS,
            tools=[
                match_score_agent.as_tool(
                    tool_name="match_score_agent",
                    tool_description=MATCH_SCORE_TOOL_DESC
                ),
                red_flag_agent.as_tool(
                    tool_name="red_flag_agent",
                    tool_description=RED_FLAG_TOOL_DESC
                ),
                wingman_agent.as_tool(
                    tool_name="wing_man_agent",
                    tool_description=WINGMAN_TOOL_DESC
                ),
                room_hunter_agent.as_tool(
                    tool_name="room_hunter_agent",
                    tool_description=ROOM_HUNTER_TOOL_DESC
                ),
            ]
        )

        # Example run using Runner (depends on agents SDK specifics)
        user_input = input("Enter a short query or 'demo' to run demo offline-like pipeline: ").strip()
        if user_input.lower() == "demo":
            # fallback to local demonstration
            print("Running local demo (rule-based) on loaded data...")
            top_matches = local_pipeline(profiles, listings, top_n=5)
            print(json.dumps(top_matches, indent=2, ensure_ascii=False))
            return

        # otherwise pass the user input to agent runner (this is SDK-specific)
        print("Running profile_reader_agent through Runner (OpenAI Agent SDK)...")
        result = Runner.run_sync(profile_reader_agent, f"{user_input}")
        print("FINAL OUTPUT:")
        print(result.final_output)

    else:
        # Degraded/local mode
        if not GEMINI_API_KEY:
            print("No GEMINI_API_KEY found — running degraded local pipeline (offline mode).")
        else:
            print("Agents SDK not available — running degraded local pipeline.")
        top_matches = local_pipeline(profiles, listings, top_n=10)
        print("Top matches (local rule-based):")
        print(json.dumps(top_matches, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
