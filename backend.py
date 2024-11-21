from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import random
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Define valid moods
VALID_MOODS = ["Depression", "Stress"]

# Define paths to music directories
DEPRESSION_MUSIC_DIR = "depression_musics"
STRESS_MUSIC_DIR = "overcome_stress_music_generated"

# Define paths to music storage
OUTPUT_AUDIO_FILE = "generated_music.wav"  # File path for generated music

# Define the input schema
class MoodRequest(BaseModel):
    mood: str

# Endpoint to generate music based on mood
@app.post("/generate_music/")
def generate_music(request: MoodRequest):
    mood = request.mood.capitalize()
    
    if mood not in VALID_MOODS:
        raise HTTPException(status_code=400, detail="Invalid mood. Choose 'Depression' or 'Stress'.")

    # Custom logic for depression music
    if mood == "Depression":
        return {"message": "Cannot generate music for 'Depression' at the moment."}

    # File check for the generated audio
    if not os.path.exists(OUTPUT_AUDIO_FILE):
        raise HTTPException(status_code=404, detail="Music file not found.")

    # Return the music file dynamically
    return FileResponse(
        path=OUTPUT_AUDIO_FILE,
        filename="generated_music.wav",
        media_type="audio/wav",
    )

# New endpoint to play random music based on selected mood
@app.post("/play_music/")
def play_music(request: MoodRequest):
    mood = request.mood.capitalize()
    if mood not in VALID_MOODS:
        raise HTTPException(status_code=400, detail="Invalid mood. Choose 'Depression' or 'Stress'.")

    # Select the appropriate directory based on mood
    music_dir = DEPRESSION_MUSIC_DIR if mood == "Depression" else STRESS_MUSIC_DIR

    # Check if the directory exists
    if not os.path.exists(music_dir):
        raise HTTPException(status_code=500, detail=f"No music directory found for mood '{mood}'.")

    # Get all music files from the directory
    music_files = [file for file in os.listdir(music_dir) if file.endswith(".mp3")]
    if not music_files:
        raise HTTPException(status_code=404, detail=f"No music files found in the '{mood}' category.")

    # Randomly select a music file
    selected_music = random.choice(music_files)

    # Return the path to the selected music file
    return {
        "message": f"Playing random music for mood '{mood}'",
        "music_file_path": f"{music_dir}/{selected_music}"
    }

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Music Generation and Playback API!"}
