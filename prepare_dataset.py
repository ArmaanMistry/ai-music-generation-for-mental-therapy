import pandas as pd
import os
import shutil

def main():
    # Data source
    filename = r"data\static_annotations_averaged_songs_1_2000.csv"
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    print(df.columns)

    # Remove unnecessary columns (Valence-related columns)
    # col_info = list(enumerate(df.columns))
    # df.drop(columns=[col_info[i][1] for i in range(2, 7)], inplace=True)
    df.drop(columns=["valence_std", "arousal_std"], axis=1, inplace=True)

    # Remove unnecessary columns (Arousal-related columns)
    # col_info = list(enumerate(df.columns))
    # df.drop(columns=[col_info[i][1] for i in range(3, 8)], inplace=True)

    # Rename columns for consistency
    df.rename(columns={'valence_mean': 'valence'}, inplace=True)
    df.rename(columns={'arousal_mean': 'arousal'}, inplace=True)

    print('test')
    print(df.head())

    # Mean normalize values
    df['valence'] -= 5
    df['arousal'] -= 5

    # Function to map valence and arousal to feelings
    def feeling_map(s):
        if s['valence'] >= 0 and s['arousal'] >= 0:
            return 0  # Happy
        if s['valence'] >= 0 and s['arousal'] < 0:
            return 1  # Calm
        if s['valence'] < 0 and s['arousal'] >= 0:
            return 2  # Angry
        if s['valence'] < 0 and s['arousal'] < 0:
            return 3  # Sad

    # Feeling labels corresponding to the integer returned by feeling_map
    feeling_labels = ["Happy", "Calm", "Angry", "Sad"]

    # Add a new column for "Feeling" by mapping the integers to their corresponding labels
    df["Feeling"] = df.apply(lambda row: feeling_labels[feeling_map(row)], axis=1)

    # Print the first few rows of the updated dataframe
    print(df.head())

    print(df.value_counts("Feeling"))

    # Create a dictionary to store song_id by mood category
    mood_dict = {
        "Happy": df[df["Feeling"] == "Happy"]['song_id'].tolist(),
        "Calm": df[df["Feeling"] == "Calm"]['song_id'].tolist(),
        "Angry": df[df["Feeling"] == "Angry"]['song_id'].tolist(),
        "Sad": df[df["Feeling"] == "Sad"]['song_id'].tolist()
    }

    # Print the dictionary of song_ids by mood
    print("Song IDs by Mood Category:")
    for mood, songs in mood_dict.items():
        print(f"{mood}: {songs[:5]}...")

    # Path where the audio files are located

    audio_directory = os.path.join("..", "the_dataset", "MEMD_audio")
    audio_directory = os.path.abspath(audio_directory)  # Convert to absolute path
    # audio_directory = r"data\audio_songs"  # Change to the path of your dataset audio files
    output_directory = r"categorized_songs"  # Output directory to copy sorted songs

    # Create the output directories for each category if they do not exist
    for mood in mood_dict.keys():
        category_dir = os.path.join(output_directory, mood)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

    # Copy the audio files into their respective folders
    for mood, song_ids in mood_dict.items():
        category_dir = os.path.join(output_directory, mood)
        for song_id in song_ids:
            # Assuming the audio files are named with the song_id (e.g., 1001.mp3)
            song_filename = f"{song_id}.mp3"
            source_path = os.path.join(audio_directory, song_filename)
            
            # Check if the file exists before attempting to copy it
            if os.path.exists(source_path):
                destination_path = os.path.join(category_dir, song_filename)
                shutil.copy(source_path, destination_path)
                print(f"Copied {song_filename} to {category_dir}")
            else:
                print(f"Warning: {song_filename} not found in {audio_directory}")

if __name__ == "__main__":
    main()
