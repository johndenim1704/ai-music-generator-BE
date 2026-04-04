import numpy as np
from scipy.io import wavfile
import os

# Create a simple test audio file (1 second of 440Hz tone - A note)
sample_rate = 44100
duration = 1.0  # seconds
frequency = 440.0  # Hz (A note)

# Generate time array
t = np.linspace(0, duration, int(sample_rate * duration))

# Generate stereo audio (left and right channels)
audio_left = np.sin(2 * np.pi * frequency * t) * 0.3
audio_right = np.sin(2 * np.pi * frequency * t) * 0.3

# Combine into stereo
stereo_audio = np.column_stack((audio_left, audio_right))

# Convert to 16-bit PCM
audio_int16 = np.int16(stereo_audio * 32767)

# Save as WAV file
output_path = "test_audio.wav"
wavfile.write(output_path, sample_rate, audio_int16)

print(f"✅ Test audio file created: {output_path}")
print(f"   Duration: {duration}s")
print(f"   Sample rate: {sample_rate} Hz")
print(f"   Frequency: {frequency} Hz (A note)")
print(f"   File size: {os.path.getsize(output_path) / 1024:.2f} KB")
