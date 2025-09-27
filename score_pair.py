
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
