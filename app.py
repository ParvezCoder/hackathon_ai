import streamlit as st
import json
from main import (
    load_json_file,
    local_pipeline,
    room_hunter,
    PROFILES_FILE,
    LISTINGS_FILE,
)

# Page Config
st.set_page_config(page_title="Room Matcher AI", page_icon="🏠", layout="wide")

st.title("🏠 Room Matcher AI — Smarter Student Living")
st.write("Find your ideal roommate and housing match with AI-powered or offline rule-based matching.")

# Sidebar Mode Selection
st.sidebar.header("⚙️ Settings")
mode = st.sidebar.radio("Choose Mode:", [ "Online (Agent SDK)", "Degraded Mode (Offline)"])
top_n = st.sidebar.slider("Number of Matches to Show", 1, 20, 5)

# Load datasets
try:
    profiles = load_json_file(PROFILES_FILE)
    listings = load_json_file(LISTINGS_FILE)
except FileNotFoundError:
    st.error("⚠️ JSON files missing. Please place them in the same folder as app.py/main.py")
    st.stop()

# ---------------- FORM ----------------
with st.form("user_profile_form"):
    st.subheader("📋 Enter Your Information")

    city = st.text_input("🏙️ City", placeholder="e.g., Karachi, Lahore, Islamabad")
    budget = st.number_input("💰 Budget (PKR)", min_value=5000, max_value=200000, step=1000)

    sleep_schedule = st.selectbox(
        "🛌 What is your sleep schedule?",
        ["Early bird", "Daytime", "Night owl"]
    )

    cleanliness = st.selectbox(
        "🧹 How tidy are you?",
        ["Tidy", "Moderate", "Messy"]
    )

    noise_tolerance = st.selectbox(
        "🔊 How much noise can you tolerate?",
        ["Quiet", "Moderate", "Tolerant"]
    )

    study_habits = st.text_input(
        "📖 What are your study habits like?",
        placeholder="e.g., Online classes, Regular, Late-night study"
    )

    food_pref = st.text_input(
        "🍲 Do you have any food preferences?",
        placeholder="e.g., Vegetarian, Flexible, Non-veg"
    )

    submitted = st.form_submit_button("🔍 Find Matches")

# ---------------- RESULTS ----------------
if submitted:
    user_profile = {
        "city": city,
        "budget_PKR": budget,
        "sleep_schedule": sleep_schedule,
        "cleanliness": cleanliness,
        "noise_tolerance": noise_tolerance,
        "study_habits": study_habits,
        "food_pref": food_pref,
    }

    if mode == "Degraded Mode (Offline)":
        st.subheader("📊 Top Matches (Offline Rule-based)")
        with st.spinner("Finding best matches locally..."):
            results = local_pipeline(profiles, listings, top_n=top_n)

        if not results:
            st.warning("No matches found.")
        else:
            for res in results:
                with st.expander(f"Pair {res['pair']} — Score: {res['score']}"):
                    st.json(res)

    else:
        st.subheader("☁️ Online Agent SDK Mode")
        st.info("🔧 Online Agent SDK integration required. Currently running in demo mode.")
        st.write("You can still use **Degraded Mode (Offline)** from the sidebar to see rule-based results.")
