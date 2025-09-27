import streamlit as st
from main import load_json_file, room_hunter, PROFILES_FILE, LISTINGS_FILE

# Page settings
st.set_page_config(page_title="Room Matcher AI", page_icon="🏠", layout="wide")
st.title("🏠 Room Matcher AI — Find Your Perfect Room & Roommate")

# Load housing listings
try:
    listings = load_json_file(LISTINGS_FILE)
except FileNotFoundError:
    st.error("⚠️ housing_listings_pakistan_400.json not found!")
    st.stop()

st.write("Fill in your details and get the best housing suggestions in your city.")

# ---------------- FORM ----------------
with st.form("user_profile_form"):
    st.subheader("📋 Your Information")

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

    submitted = st.form_submit_button("🔍 Find Matching Rooms")

# ---------------- RESULTS ----------------
if submitted:
    user_profile = {
        "city": city,
        "budget_PKR": budget,
    }

    st.subheader("🏠 Suggested Rooms")
    matches = room_hunter(listings, user_profile)

    if not matches:
        st.warning("No matching rooms found. Try adjusting your budget or city.")
    else:
        for room in matches:
            with st.container():
                st.markdown(f"### 📍 {room.get('area', 'Unknown Area')} — {room.get('city', '')}")
                st.write(f"💰 Rent: **{room.get('monthly_rent_PKR', 'N/A')} PKR**")
                st.write(f"🏡 Listing ID: {room.get('listing_id', 'N/A')}")
                st.write("---")
