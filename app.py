# app.py
import streamlit as st
from main import load_json_file, room_hunter, local_match, PROFILES_FILE, LISTINGS_FILE

st.set_page_config(page_title="Room Matcher AI", page_icon="🏠", layout="wide")

st.title("🏠 Room Matcher AI")
st.subheader("Find Your Perfect Room & Roommate")
st.write("Fill in your details below and get AI-powered housing & roommate matches.")

# ---------------- LOAD DATA ----------------
try:
    listings = load_json_file(LISTINGS_FILE)
except FileNotFoundError:
    st.error("⚠️ housing_listings_pakistan_400.json not found!")
    st.stop()

# ---------------- MODE TOGGLE ----------------
st.sidebar.title("⚙️ Settings")
degraded = st.sidebar.checkbox("Enable Degraded Mode (offline)", value=False)

# ---------------- FORM ----------------
with st.form("user_profile_form"):
    st.subheader("📋 Your Profile")

    city = st.text_input("🏙️ City", placeholder="e.g., Karachi, Lahore, Islamabad")
    budget = st.number_input("💰 Budget (PKR)", min_value=5000, max_value=200000, step=1000)
    sleep_schedule = st.selectbox("🛌 Sleep schedule?", ["Early bird", "Daytime", "Night owl"])
    cleanliness = st.selectbox("🧹 How tidy are you?", ["Tidy", "Moderate", "Messy"])
    noise_tolerance = st.selectbox("🔊 Noise tolerance?", ["Quiet", "Moderate", "Tolerant"])
    study_habits = st.text_input("📖 Study habits", placeholder="e.g., Online classes, Regular, Late-night study")
    food_pref = st.text_input("🍲 Food preference", placeholder="e.g., Vegetarian, Flexible, Non-veg")

    submitted = st.form_submit_button("🔍 Find Matching Rooms")

# ---------------- RESULTS ----------------
if submitted:
    user_profile = {
        "city": city,
        "budget_PKR": budget,
        "sleep_schedule": sleep_schedule,
        "cleanliness": cleanliness,
        "noise_tolerance": noise_tolerance,
        "study_habits": study_habits,
        "food_pref": food_pref
    }

    st.subheader("🏠 Suggested Rooms")

    if degraded:
        # User query string for degraded mode
        query_str = f"{city} {budget} {sleep_schedule} {cleanliness} {noise_tolerance} {study_habits} {food_pref}"
        matches = local_match(query_str, listings)
        st.info("⚡ Degraded Mode active — showing offline TF-IDF matches")
    else:
        matches = room_hunter(listings, user_profile)
        st.info("✨ Normal Mode active — rule-based filtering")

    if not matches:
        st.warning("⚠️ No matching rooms found. Try adjusting your budget or city.")
    else:
        for room in matches:
            with st.container():
                st.markdown(f"### 📍 {room.get('area', 'Unknown Area')} — {room.get('city', '')}")
                st.write(f"💰 Rent: **{room.get('monthly_rent_PKR', 'N/A')} PKR**")
                st.write(f"🏡 Listing ID: {room.get('listing_id', 'N/A')}")
                st.write("---")
