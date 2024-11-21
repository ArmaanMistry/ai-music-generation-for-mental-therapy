import streamlit as st
import requests
import random
import time

# Set page title and layout
st.set_page_config(page_title="AI Music Therapy Platform", layout="centered")

# Title and description
st.title("AI Music Therapy Platform")
st.write("""
Welcome to the AI-powered music therapy platform designed to enhance your mental well-being. 
Select your current mood, and let the system generate soothing music tailored to help improve your emotional state.
""")

# Sidebar for navigation
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Go to", ["Home", "About"])

# FastAPI endpoint URL
FASTAPI_URL = "http://localhost:8000/play_music/"

# Main Interface
if menu == "Home":
    # Step 1: Select Mood
    st.subheader("Step 1: Select Your Current Mood")
    mood = st.selectbox(
        "How are you feeling today?",
        ["Select your mood", "Depression", "Stress"]
    )

    # Display a motivational quote based on mood selection
    if mood == "Depression":
        st.info("Remember: Even the darkest night will end, and the sun will rise.")
    elif mood == "Stress":
        st.info("Take a deep breath. It's just a bad day, not a bad life.")

    # Step 2: Generate Music
    st.subheader("Step 2: Generate Therapeutic Music")

    if mood == "Depression":
        st.error("Cannot generate music for 'Depression' at the moment. Please select a different mood.")
    elif mood != "Select your mood":
        generate_btn = st.button("Generate Music 🎵")
        
        if generate_btn:
            st.success("Generating music... 🎶 Please relax and rest. The music will be ready soon.")
            
            # Simulate a 30-45 seconds wait
            wait_time = random.randint(30, 45)
            with st.spinner(f"Generating music..."):
                time.sleep(wait_time)
            
            # Send request to FastAPI to get the music file path
            try:
                response = requests.post(FASTAPI_URL, json={"mood": mood})
                if response.status_code == 200:
                    data = response.json()
                    music_file_path = data["music_file_path"]
                    
                    st.subheader("Now Playing")
                    st.audio(music_file_path, format='audio/mp3')
                else:
                    st.error("Failed to get music. Please try again.")
            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to the server: {e}")

elif menu == "About":
    st.subheader("About the Project")
    st.write("""
    This platform leverages AI and music therapy principles to generate music aimed at improving mental health.
    It is designed to support users facing challenges related to depression and stress.
    """)
