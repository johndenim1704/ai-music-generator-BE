import librosa
import numpy as np
import ollama
import logging

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
logger = logging.getLogger(__name__)

class TrackTitleService:
    def analyze_track_for_naming(self, path, sr=44100, duration=60.0):
        logger.info(f"[SERVICE] Starting audio analysis for: {path}")
        logger.info(f"[SERVICE] Loading audio with sr={sr}, duration={duration}")
        y, sr = librosa.load(path, sr=sr, mono=True, duration=duration)
        logger.info(f"[SERVICE] Audio loaded, trimming silence...")
        y, _ = librosa.effects.trim(y)

        logger.info(f"[SERVICE] Extracting tempo...")
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        logger.info(f"[SERVICE] Tempo extracted: {tempo:.2f} BPM")
        
        logger.info(f"[SERVICE] Extracting spectral features...")
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        rms = librosa.feature.rms(y=y).mean()
        zcr = librosa.feature.zero_crossing_rate(y=y).mean()

        logger.info(f"[SERVICE] Detecting musical key...")
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_name = NOTE_NAMES[int(np.argmax(chroma.mean(axis=1)))]
        logger.info(f"[SERVICE] Key detected: {key_name}")

        features = {
            "tempo_bpm": float(tempo),
            "centroid_hz": float(centroid),
            "rms": float(rms),
            "zcr": float(zcr),
            "key": key_name
        }
        logger.info(f"[SERVICE] Audio analysis complete: {features}")
        return features

    def describe_track_for_titles(self, features, genre: str) -> str:
        logger.info(f"[SERVICE] Building track description for genre: {genre}")
        tempo = features["tempo_bpm"]
        centroid = features["centroid_hz"]
        rms = features["rms"]
        zcr = features["zcr"]
        key = features["key"]

        if tempo < 80:
            tempo_desc = "slow"
        elif tempo < 110:
            tempo_desc = "medium tempo"
        elif tempo < 140:
            tempo_desc = "uptempo"
        else:
            tempo_desc = "fast and energetic"

        if centroid < 1500:
            tone_desc = "dark and warm"
        elif centroid < 2500:
            tone_desc = "balanced"
        else:
            tone_desc = "bright and edgy"

        if rms < 0.03:
            energy_desc = "low energy, chill"
        elif rms < 0.07:
            energy_desc = "moderate energy"
        else:
            energy_desc = "high energy and powerful"

        if zcr < 0.05:
            perc_desc = "smooth and sustained"
        elif zcr < 0.12:
            perc_desc = "groovy"
        else:
            perc_desc = "very percussive and punchy"

        genre = genre.lower()
        description = (
            f"This is an instrumental {genre} track with no vocals. "
            f"It is {tempo_desc} (~{tempo:.0f} BPM), {tone_desc}, and {energy_desc}. "
            f"The overall feel is {perc_desc}. The musical key feels like {key}."
        )
        logger.info(f"[SERVICE] Track description created: {description}")
        return description

    def build_title_prompt(self, description: str, num_titles: int):
        return f"""
Suggest one original track title based on the mood, energy and feel below.

Description:
\"\"\"{description}\"\"\"

Rules:
- No genre names (no "hiphop beat" etc.)
- EXACTLY ONE WORD only
- Memorable, streaming-friendly
- Return ONLY the single word, nothing else
"""

    def generate_titles(self, audio_path: str, genre: str, num_titles: int = 10):
        logger.info(f"[SERVICE] === Starting title generation ===")
        logger.info(f"[SERVICE] Audio path: {audio_path}, Genre: {genre}, Num titles: {num_titles}")
        
        feats = self.analyze_track_for_naming(audio_path)
        desc = self.describe_track_for_titles(feats, genre)
        prompt = self.build_title_prompt(desc, num_titles)
        logger.info(f"[SERVICE] Prompt built, sending to LLM...")

        logger.info(f"[SERVICE] Calling Ollama LLM (model: llama3.2:latest)...")
        result = ollama.chat(
            model="llama3.2:latest",
            messages=[
                {"role": "system", "content": "You are a creative music naming assistant."},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.9, "num_predict": 256}
        )
        logger.info(f"[SERVICE] LLM response received")
        logger.info(f"[SERVICE] === Title generation complete ===")
        return result["message"]["content"]
