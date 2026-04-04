import librosa
import numpy as np
import ollama

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']
feats = {}
def analyze_track_for_naming(path, sr=44100, duration=60.0):
    """
    Load up to `duration` seconds of audio and extract features
    that are useful for naming (not for mastering).
    """
    y, sr = librosa.load(path, sr=sr, mono=True, duration=duration)

    # Trim silence at head/tail to avoid messing up RMS/tempo
    y, _ = librosa.effects.trim(y)

    # Tempo (BPM)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo)

    # Spectral centroid (brightness)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    centroid_mean = float(np.mean(centroid))

    # RMS (energy)
    rms = librosa.feature.rms(y=y)
    rms_mean = float(np.mean(rms))

    # Zero crossing rate (percussiveness/noisiness)
    zcr = librosa.feature.zero_crossing_rate(y)
    zcr_mean = float(np.mean(zcr))

    # Rough key estimation via chroma
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    key_index = int(np.argmax(chroma_mean))
    key_name = NOTE_NAMES[key_index]

    return {
        "tempo_bpm": tempo,
        "centroid_hz": centroid_mean,
        "rms": rms_mean,
        "zcr": zcr_mean,
        "key": key_name
    }


def describe_track_for_titles(features, genre: str) -> str:
    tempo = features["tempo_bpm"]
    centroid = features["centroid_hz"]
    rms = features["rms"]
    zcr = features["zcr"]
    key = features["key"]

    # Tempo buckets
    if tempo < 80:
        tempo_desc = "slow"
    elif tempo < 110:
        tempo_desc = "medium tempo"
    elif tempo < 140:
        tempo_desc = "uptempo"
    else:
        tempo_desc = "fast and energetic"

    # Brightness
    if centroid < 1500:
        tone_desc = "dark and warm"
    elif centroid < 2500:
        tone_desc = "balanced"
    else:
        tone_desc = "bright and edgy"

    # Energy (RMS)
    if rms < 0.03:
        energy_desc = "low energy, chill"
    elif rms < 0.07:
        energy_desc = "moderate energy"
    else:
        energy_desc = "high energy and powerful"

    # Percussiveness
    if zcr < 0.05:
        perc_desc = "smooth and sustained"
    elif zcr < 0.12:
        perc_desc = "groovy"
    else:
        perc_desc = "very percussive and punchy"

    genre = genre.lower()

    description = (
        f"This is an instrumental {genre} track, with no vocals. "
        f"It is {tempo_desc} (around {tempo:.0f} BPM), {tone_desc}, "
        f"and {energy_desc}. The overall feel is {perc_desc}. "
        f"The main musical key center feels like {key}."
    )
    print(f"Track Description: {description}")
    return description


def build_title_prompt(description: str, num_titles: int = 10):
    return f"""
You are a music creative assistant.

Based on the following description of an instrumental track, 
suggest {num_titles} original, creative track titles.

The titles should:
- Fit the mood, energy, and style of the description
- Not include the genre name itself (no "Hiphop Beat" etc.)
- Be short and memorable (1–4 words)
- Work well for a streaming platform release

Track description:
\"\"\" 
{description}
\"\"\"

Return the titles as a numbered list.
Note: Do not include any additional commentary or explanation. Return only the list of titles.
"""




    # Define the model name
model = "llama3.2:latest"

def generate_titles(audio_path, genre="", num_titles=10):
    feats = analyze_track_for_naming(audio_path)
    desc = describe_track_for_titles(feats, genre)
    prompt = build_title_prompt(desc, num_titles=num_titles)
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": "You are a creative music naming assistant."},
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": 0.9,
            "num_predict": 256
        }
    )

    return response["message"]["content"]









    
if __name__ == "__main__":
    audio_file = input("Enter path to audio file: ")
    genre = input("Enter genre of the audio file: ")
    titles = generate_titles(audio_file, genre=genre, num_titles=10)
    print("\nSuggested Track Titles:\n")
    print(titles)