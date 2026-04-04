from scipy.signal import butter, filtfilt
import numpy as np
import argparse
from scipy.io import wavfile
import pyloudnorm as pyln
import librosa
from scipy.signal import butter, lfilter, resample_poly
# -------------------------------------------------------
# Utility: safe butter filter (already similar to yours)
# -------------------------------------------------------


TARGET_SR = 48000  # modern standard for mastering export

GENRE_PRESETS = {
    # Existing
    "hiphop":   {"lufs": -10, "hp": 40,  "lp": 17000, "th": -18, "ratio": 2.5},
    "edm":      {"lufs": -8,  "hp": 50,  "lp": 19000, "th": -14, "ratio": 3.0},
    "lofi":     {"lufs": -16, "hp": 150, "lp": 10000, "th": -22, "ratio": 1.8},
    "pop":      {"lufs": -12, "hp": 60,  "lp": 18000, "th": -16, "ratio": 2.0},
    "trap":     {"lufs": -9,  "hp": 30,  "lp": 17000, "th": -18, "ratio": 3.0},
    "acoustic": {"lufs": -14, "hp": 80,  "lp": 16000, "th": -20, "ratio": 1.5},
    "rnb":      {"lufs": -11, "hp": 50,  "lp": 17500, "th": -18, "ratio": 2.0},
    "house":    {"lufs": -8,  "hp": 40,  "lp": 18000, "th": -14, "ratio": 3.0},
    "techno":   {"lufs": -8,  "hp": 35,  "lp": 18500, "th": -14, "ratio": 3.2},
    "indian":   {"lufs": -13, "hp": 90,  "lp": 15000, "th": -20, "ratio": 1.8},
    "default":  {"lufs": -14, "hp": 40,  "lp": 18000, "th": -18, "ratio": 2.0},

    # 🌍 World & Cultural
    "afrobeats":   {"lufs": -10, "hp": 45,  "lp": 18000, "th": -17, "ratio": 2.3},
    "latin":       {"lufs": -10, "hp": 45,  "lp": 18000, "th": -16, "ratio": 2.4},
    # "reggaeton":   {"lufs": -9,  "hp": 40,  "lp": 17500, "th": -16, "ratio": 3.0},
    "dancehall":   {"lufs": -9,  "hp": 35,  "lp": 17500, "th": -17, "ratio": 2.8},
    "kpop":        {"lufs": -11, "hp": 50,  "lp": 18500, "th": -16, "ratio": 2.3},
    "bollywood":   {"lufs": -13, "hp": 90,  "lp": 15500, "th": -20, "ratio": 1.8},

    # 🎧 Electronic & Club
    "dubstep":     {"lufs": -7,  "hp": 35,  "lp": 19000, "th": -13, "ratio": 3.5},
    "trance":      {"lufs": -8,  "hp": 40,  "lp": 19000, "th": -14, "ratio": 3.0},
    "hardstyle":   {"lufs": -6,  "hp": 35,  "lp": 20000, "th": -12, "ratio": 4.0},
    "drum_and_bass":{"lufs": -7,  "hp": 30,  "lp": 19000, "th": -13, "ratio": 3.2},
    "future_bass": {"lufs": -9,  "hp": 50,  "lp": 18500, "th": -15, "ratio": 2.8},
    "garage":      {"lufs": -9,  "hp": 45,  "lp": 17500, "th": -16, "ratio": 2.5},
    "breakbeat":   {"lufs": -8,  "hp": 40,  "lp": 18000, "th": -15, "ratio": 2.8},
    "electro":     {"lufs": -9,  "hp": 50,  "lp": 18500, "th": -15, "ratio": 2.8},
    "ambient":     {"lufs": -18, "hp": 80,  "lp": 14000, "th": -26, "ratio": 1.3},
    "downtempo":   {"lufs": -14, "hp": 80,  "lp": 14000, "th": -20, "ratio": 1.6},

    # 🎸 Rock & Band
    "rock":          {"lufs": -11, "hp": 60,  "lp": 17000, "th": -16, "ratio": 2.5},
    "alt_rock":      {"lufs": -11, "hp": 50,  "lp": 17500, "th": -16, "ratio": 2.4},
    "indie":         {"lufs": -12, "hp": 70,  "lp": 16500, "th": -18, "ratio": 2.0},
    "metal":         {"lufs": -9,  "hp": 40,  "lp": 18000, "th": -15, "ratio": 3.0},
    "punk":          {"lufs": -10, "hp": 50,  "lp": 17000, "th": -16, "ratio": 2.8},
    "grunge":        {"lufs": -11, "hp": 60,  "lp": 16000, "th": -18, "ratio": 2.3},
    "progressive":   {"lufs": -10, "hp": 50,  "lp": 18000, "th": -16, "ratio": 2.2},
    "post_rock":     {"lufs": -14, "hp": 100, "lp": 15000, "th": -22, "ratio": 1.7},

    # 🎼 Classical & Film
    "classical":   {"lufs": -20, "hp": 80,  "lp": 14000, "th": -28, "ratio": 1.2},
    "orchestral":  {"lufs": -18, "hp": 70,  "lp": 15000, "th": -26, "ratio": 1.4},
    "cinematic":   {"lufs": -16, "hp": 60,  "lp": 16000, "th": -22, "ratio": 1.6},
    "soundtrack":  {"lufs": -17, "hp": 70,  "lp": 15000, "th": -24, "ratio": 1.6},

    # 🎤 Vocal / Media
    "podcast":      {"lufs": -16, "hp": 80,  "lp": 14000, "th": -20, "ratio": 2.3},
    "audiobook":    {"lufs": -18, "hp": 80,  "lp": 13000, "th": -24, "ratio": 2.0},
    "speech":       {"lufs": -16, "hp": 100, "lp": 12000, "th": -20, "ratio": 2.5},

    # 🔥 Urban sub-styles
    "drill":        {"lufs": -9,  "hp": 35,  "lp": 17000, "th": -16, "ratio": 3.0},
    "cloud_rap":    {"lufs": -12, "hp": 60,  "lp": 15500, "th": -19, "ratio": 2.0},
    "emo_rap":      {"lufs": -11, "hp": 55,  "lp": 16000, "th": -18, "ratio": 2.0},
    "phonk":        {"lufs": -8,  "hp": 30,  "lp": 15000, "th": -15, "ratio": 3.5},

    # 🎷 Jazz & Soul
    "jazz":         {"lufs": -16, "hp": 90,  "lp": 15500, "th": -22, "ratio": 1.6},
    "neo_soul":     {"lufs": -13, "hp": 70,  "lp": 16000, "th": -18, "ratio": 2.0},
    "blues":        {"lufs": -14, "hp": 80,  "lp": 15000, "th": -20, "ratio": 1.8},
    "funk":         {"lufs": -11, "hp": 50,  "lp": 17000, "th": -17, "ratio": 2.5}
}

def butter_filter_zero_phase(data, cutoff, fs, type="low", order=4):
    nyq = 0.5 * fs
    norm = np.array(cutoff, ndmin=1) / nyq

    # Clamp to valid region
    norm = np.clip(norm, 0.001, 0.999)
    b, a = butter(order, norm, btype=type)
    return filtfilt(b, a, data)

# -------------------------------------------------------
# Multiband split + recombine
# -------------------------------------------------------
def split_bands(x, sr, low_split=120, high_split=4000, order=4):
    """
    Split into: low (< low_split), mid (low_split–high_split), high (> high_split)
    """
    nyq = 0.5 * sr
    low = butter_filter_zero_phase(x, low_split, sr, type='low', order=order)
    high = butter_filter_zero_phase(x, high_split, sr, type='high', order=order)
    band = butter_filter_zero_phase(
        x, [low_split / nyq * nyq, high_split / nyq * nyq],
        sr, type='band', order=order
    )
    return low, band, high



def smooth_compressor(x, threshold_dB=-18, ratio=2.0, attack_ms=5, release_ms=50, sr=44100, makeup_gain=2.0):
    """Smooth compressor with attack/release for natural sound"""
    threshold = 10 ** (threshold_dB / 20)
    
    # Convert ms to samples
    attack_samples = int(attack_ms * sr / 1000)
    release_samples = int(release_ms * sr / 1000)
    
    # Calculate envelope
    envelope = np.abs(x)
    
    # Smooth the envelope
    gain_reduction = np.ones_like(x)
    current_gain = 1.0
    
    for i in range(len(x)):
        # Calculate target gain
        if envelope[i] > threshold:
            target_gain = threshold / envelope[i]
            target_gain = target_gain + (1 - target_gain) * (1 / ratio)
        else:
            target_gain = 1.0
        
        # Smooth gain changes
        if target_gain < current_gain:
            # Attack
            current_gain += (target_gain - current_gain) / max(attack_samples, 1)
        else:
            # Release
            current_gain += (target_gain - current_gain) / max(release_samples, 1)
        
        gain_reduction[i] = current_gain
    
    # Apply compression
    compressed = x * gain_reduction
    
    # Makeup gain
    return compressed * (10 ** (makeup_gain / 20))



def anti_aliasing_upsample(x, sr, factor=2):
    """Upsample to reduce digital artifacts"""
    return resample_poly(x, factor, 1), sr * factor

def anti_aliasing_downsample(x, sr, factor=2):
    """Downsample back after processing"""
    return resample_poly(x, 1, factor), sr // factor



def smooth_noise_reduction(x, threshold_dB=-70):
    """Gentle noise reduction without artifacts"""
    threshold = 10 ** (threshold_dB / 20)
    
    # Very gentle noise gate with smooth transition
    output = np.zeros_like(x)
    for i, s in enumerate(x):
        abs_s = abs(s)
        if abs_s > threshold * 2:
            output[i] = s
        elif abs_s > threshold:
            # Smooth transition zone
            factor = (abs_s - threshold) / threshold
            output[i] = s * factor
        else:
            # Very quiet - reduce but don't eliminate
            output[i] = s * 0.1
    
    return output


def soft_limiter(x, ceiling_dB=-1.0):
    """Soft knee limiter that sounds smooth, not harsh"""
    ceiling = 10 ** (ceiling_dB / 20)
    
    # Soft knee limiting (smooth transition)
    output = np.zeros_like(x)
    for i, s in enumerate(x):
        abs_s = abs(s)
        if abs_s <= ceiling * 0.8:
            # Below threshold - no processing
            output[i] = s
        elif abs_s <= ceiling:
            # Soft knee region - gentle compression
            ratio = 1 + (abs_s / ceiling - 0.8) * 10
            output[i] = np.sign(s) * (ceiling * 0.8 + (abs_s - ceiling * 0.8) / ratio)
        else:
            # Hard limit (but we shouldn't get here often)
            output[i] = np.sign(s) * ceiling
    
    return output




def apply_multiband_compressor(x, sr, profile="neutral"):
    """
    Simple 3-band compressor with profile-based intensity.
    """
    low, mid, high = split_bands(x, sr)

    if profile == "club":        # EDM / Afrobeats / Trap / Reggaeton
        low_th, low_ratio  = -20, 3.5
        mid_th, mid_ratio  = -22, 3.0
        high_th, high_ratio = -24, 2.5
    elif profile == "clean":     # acoustic / jazz / classical
        low_th, low_ratio  = -24, 1.5
        mid_th, mid_ratio  = -26, 1.4
        high_th, high_ratio = -28, 1.3
    elif profile == "speech":    # podcast / VO
        low_th, low_ratio  = -22, 2.0
        mid_th, mid_ratio  = -20, 2.3
        high_th, high_ratio = -24, 1.8
    else:                        # neutral / pop / rock
        low_th, low_ratio  = -22, 2.5
        mid_th, mid_ratio  = -24, 2.2
        high_th, high_ratio = -26, 2.0

    low_c  = smooth_compressor(low,  threshold_dB=low_th,  ratio=low_ratio,  attack_ms=15, release_ms=120, sr=sr, makeup_gain=1.0)
    mid_c  = smooth_compressor(mid,  threshold_dB=mid_th,  ratio=mid_ratio,  attack_ms=10, release_ms=100, sr=sr, makeup_gain=1.0)
    high_c = smooth_compressor(high, threshold_dB=high_th, ratio=high_ratio, attack_ms=5,  release_ms=80,  sr=sr, makeup_gain=1.0)

    return low_c + mid_c + high_c




def gentle_clarity_boost(x, sr):
    """Gentle presence boost without harshness"""
    nyq = 0.5 * sr
    
    # Very gentle boost at 3-4 kHz (presence)
    center_freq = 3500 / nyq
    
    # Bandpass for presence
    b_low, a_low = butter(2, 2500 / nyq, btype='high')
    b_high, a_high = butter(2, 5000 / nyq, btype='low')
    
    presence = lfilter(b_low, a_low, x)
    presence = lfilter(b_high, a_high, presence)
    
    # Very subtle boost (only +1 dB)
    boost = 1.12
    return x + (presence * (boost - 1))

# -------------------------------------------------------
# Harmonic saturation (for “record” feel)
# -------------------------------------------------------
def harmonic_saturator(x, drive=1.5, mix=0.4):
    """
    Drive: how hard we push into tanh
    Mix:   wet/dry blend
    """
    if drive <= 0 or mix <= 0:
        return x

    y = np.tanh(x * drive)
    return (1.0 - mix) * x + mix * y

# -------------------------------------------------------
# Stereo Mid/Side widen, low mono
# -------------------------------------------------------
def ms_encode(L, R):
    mid = (L + R) * 0.5
    side = (L - R) * 0.5
    return mid, side

def ms_decode(mid, side):
    L = mid + side
    R = mid - side
    return L, R

def stereo_widen(L, R, sr, widen_amount=1.0, low_mono_hz=120):
    """
    widen_amount: 1.0 = no change, 1.1–1.3 = subtle, >1.4 aggressive
    """
    if widen_amount <= 1.0:
        return L, R

    mid, side = ms_encode(L, R)

    # HPF on side so low stays mono
    side_hp = butter_filter_zero_phase(side, low_mono_hz, sr, type="high", order=3)
    side_lp = side - side_hp  # what we removed from side (low content)

    widened_side = side_hp * widen_amount + side_lp  # widen only the highs

    L_out, R_out = ms_decode(mid, widened_side)
    return L_out, R_out

# -------------------------------------------------------
# Low-end tightening / gentle bump
# -------------------------------------------------------
def tighten_low_end(x, sr, center_hz=80, q=1.0, gain_db=1.5):
    """
    Very simple "EQ": compress lows via band and optionally boost slightly.
    """
    low, mid, high = split_bands(x, sr, low_split=center_hz*2, high_split=4000)
    # light comp on low
    low_c = smooth_compressor(low, threshold_dB=-24, ratio=2.0, attack_ms=20, release_ms=150, sr=sr, makeup_gain=0.0)
    # small gain
    gain_lin = 10 ** (gain_db / 20.0)
    low_c *= gain_lin
    return low_c + mid + high

# -------------------------------------------------------
# Genre → mastering profile (how "aggressive")
# -------------------------------------------------------
CLUB_GENRES = {
    "edm", "house", "techno", "dubstep", "trance", "hardstyle",
    "drum_and_bass", "future_bass", "garage", "breakbeat",
    "electro", "afrobeats", "reggaeton", "dancehall", "trap",
    "drill", "phonk", "kpop"
}

CLEAN_GENRES = {
    "acoustic", "lofi", "classical", "orchestral", "cinematic",
    "soundtrack", "jazz", "neo_soul", "blues", "ambient", "downtempo",
    "indian", "bollywood"
}

SPEECH_GENRES = {"podcast", "audiobook", "speech"}

def mastering_profile_from_genre(genre: str):
    g = genre.lower()
    if g in CLUB_GENRES:
        return "club"
    if g in CLEAN_GENRES:
        return "clean"
    if g in SPEECH_GENRES:
        return "speech"
    return "neutral"




def resample_to_target_sr(L, R, sr, target_sr=TARGET_SR):
    """
    High-quality resampling to target sample rate for export.
    Uses polyphase (resample_poly) and runs ONLY at the end,
    so it does not change your mastering behavior.
    """
    if sr == target_sr:
        return L, R, sr

    print(f"\n🔁 Resampling from {sr} Hz to {target_sr} Hz for export...")
    L_res = resample_poly(L, target_sr, sr)
    R_res = resample_poly(R, target_sr, sr)
    return L_res, R_res, target_sr



def analyze_and_master(input_wav, output_wav, genre="default", quality_mode="high"):
    """Universal mastering with genre-aware behavior & commercial feel."""
    
    print(f"\n🎧 Loading: {input_wav}")
    
    try:
        sr, audio = wavfile.read(input_wav)
        print(f"   Sample Rate: {sr} Hz")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Convert to float32 in -1..1
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float32) / 2147483648.0
    else:
        audio = audio.astype(np.float32)
    audio = np.clip(audio, -1.0, 1.0)
    
    # Mono → stereo
    if len(audio.shape) == 1:
        audio = np.stack([audio, audio], axis=1)
    
    L, R = audio[:, 0], audio[:, 1]
    
    # Optional upsample
    if quality_mode == "high":
        print("\n🔬 Upsampling for high-quality processing...")
        L, sr_high = anti_aliasing_upsample(L, sr, factor=2)
        R, sr_high = anti_aliasing_upsample(R, sr, factor=2)
        processing_sr = sr_high
    else:
        processing_sr = sr
    
    # -------- AI-ish analysis (same idea) --------
    print("\n🤖 Analyzing track...")
    mono = (L + R) / 2
    
    try:
        if len(mono) > processing_sr * 60:
            mono_analyze = mono[:processing_sr * 60]
        else:
            mono_analyze = mono
        
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=mono_analyze, sr=processing_sr))
        spectral_rolloff  = np.mean(librosa.feature.spectral_rolloff(y=mono_analyze, sr=processing_sr))
        rms               = np.mean(librosa.feature.rms(y=mono_analyze))
        
        print(f"   📊 Spectral Centroid: {spectral_centroid:.1f} Hz")
        print(f"   📊 RMS Energy: {rms:.3f}")
    except Exception as e:
        print(f"   ⚠️ Analysis failed ({e}), using defaults")
        spectral_centroid, spectral_rolloff, rms = 2000, 7000, 0.1
    
    # -------- Preset selection + tiny adjustments --------
    print("\n🧠 Optimizing settings...")
    genre = genre.lower()
    preset = GENRE_PRESETS.get(genre, GENRE_PRESETS["default"]).copy()
    
    # Small, conservative tweaks based on analysis
    if spectral_centroid < 1400:
        preset["hp"] = min(preset["hp"] + 15, 100)
        print(f"   ⚙️ Bass clarity: HP adjusted to {preset['hp']} Hz")
    if rms < 0.06:
        preset["ratio"] = min(preset["ratio"] + 0.3, 3.0)
        print(f"   ⚙️ Dynamics: Ratio adjusted to {preset['ratio']}")
    
    profile = mastering_profile_from_genre(genre)
    print(f"   🎚 Profile: {profile}")
    
    # -------- MASTERING CHAIN --------
    print("\n🔧 Applying mastering chain...")
    
    # 1) Noise reduction (very gentle)
    print("   1️⃣  Noise reduction...")
    L = smooth_noise_reduction(L, threshold_dB=-70)
    R = smooth_noise_reduction(R, threshold_dB=-70)
    
    # 2) HP / LP filters
    print("   2️⃣  High-pass / low-pass...")
    L = butter_filter_zero_phase(L, preset["hp"], processing_sr, type="high", order=3)
    R = butter_filter_zero_phase(R, preset["hp"], processing_sr, type="high", order=3)
    
    L = butter_filter_zero_phase(L, preset["lp"], processing_sr, type="low", order=4)
    R = butter_filter_zero_phase(R, preset["lp"], processing_sr, type="low", order=4)
    
    # 3) Multiband compression (per profile)
    print("   3️⃣  Multiband compression...")
    L = apply_multiband_compressor(L, processing_sr, profile=profile)
    R = apply_multiband_compressor(R, processing_sr, profile=profile)
    
    # 4) Core broadband compression (your original compressor, but slightly gentler)
    print("   4️⃣  Bus compression...")
    L = smooth_compressor(L, threshold_dB=preset["th"], ratio=preset["ratio"],
                          attack_ms=10, release_ms=120, sr=processing_sr, makeup_gain=1.0)
    R = smooth_compressor(R, threshold_dB=preset["th"], ratio=preset["ratio"],
                          attack_ms=10, release_ms=120, sr=processing_sr, makeup_gain=1.0)
    
    # 5) Bass tightening (stronger for club genres)
    if profile in ["club", "neutral"]:
        print("   5️⃣  Tightening low-end...")
        bass_bump = 2.0 if profile == "club" else 1.0
        L = tighten_low_end(L, processing_sr, center_hz=80, gain_db=bass_bump)
        R = tighten_low_end(R, processing_sr, center_hz=80, gain_db=bass_bump)
    
    # 6) Clarity boost (only if track is dark)
    if spectral_centroid < 2500:
        print("   6️⃣  Gentle clarity enhancement...")
        L = gentle_clarity_boost(L, processing_sr)
        R = gentle_clarity_boost(R, processing_sr)
    
    # 7) Harmonic saturation
    print("   7️⃣  Harmonic saturation...")
    if profile == "club":
        drive, mix = 2.0, 0.45
    elif profile == "clean":
        drive, mix = 1.2, 0.25
    elif profile == "speech":
        drive, mix = 1.1, 0.2
    else:
        drive, mix = 1.6, 0.35
    
    L = harmonic_saturator(L, drive=drive, mix=mix)
    R = harmonic_saturator(R, drive=drive, mix=mix)
    
    # 8) Stereo widening (stronger for club, very mild for clean)
    print("   8️⃣  Stereo imaging...")
    if profile == "club":
        widen = 1.25
    elif profile == "clean":
        widen = 1.08
    elif profile == "speech":
        widen = 1.02
    else:
        widen = 1.15
    
    L, R = stereo_widen(L, R, processing_sr, widen_amount=widen, low_mono_hz=120)
    
    # 9) Downsample if needed
    if quality_mode == "high":
        print("\n🔬 Downsampling to original rate...")
        L, _ = anti_aliasing_downsample(L, processing_sr, factor=2)
        R, _ = anti_aliasing_downsample(R, processing_sr, factor=2)
    
    # 10) Loudness normalization
    print("\n   9️⃣  Loudness normalization...")
    meter = pyln.Meter(sr)
    stereo_for_measurement = np.vstack([L, R]).T
    
    try:
        current_loudness = meter.integrated_loudness(stereo_for_measurement)
        target_lufs = preset["lufs"]
        gain = target_lufs - current_loudness
        gain = np.clip(gain, -6, 12)  # avoid insane boosts
        gain_lin = 10 ** (gain / 20)
        
        print(f"      Current: {current_loudness:.1f} LUFS → Target: {target_lufs} LUFS (Δ {gain:.1f} dB)")
        L *= gain_lin
        R *= gain_lin
    except Exception as e:
        print(f"      ⚠️ LUFS failed ({e}), using peak normalization")
        peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
        if peak > 0:
            L *= 0.9 / peak
            R *= 0.9 / peak


        # 11) Soft limiting + safety
    print("   🔟  Soft limiting & safety...")
    L = soft_limiter(L, ceiling_dB=-0.5)
    R = soft_limiter(R, ceiling_dB=-0.5)

    L = np.clip(L, -0.99, 0.99)
    R = np.clip(R, -0.99, 0.99)

    # 12) Ensure 48 kHz sample rate for export (after all processing)
    L, R, sr_out = resample_to_target_sr(L, R, sr, target_sr=TARGET_SR)

    # Export as 24-bit PCM (stored in 32-bit container)
    print(f"   1️⃣1️⃣  Exporting at {sr_out} Hz / 24-bit PCM...")

    stereo = np.stack([L, R], axis=1)

    # Triangular dither at 24-bit resolution
    # 24-bit full scale uses ±(2^23 - 1), so 1 LSB ≈ 1 / 2^23
        # Triangular dither (still very small, basically 24-bit style)
    dither_amp = 1.0 / (2**24)
    dither = np.random.triangular(-1, 0, 1, size=stereo.shape) * dither_amp
    stereo_dithered = np.clip(stereo + dither, -1.0, 1.0)

    # Quantize to full 32-bit range (normal playback loudness)
    stereo_i32 = np.int32(stereo_dithered * (2**31 - 1))

    wavfile.write(output_wav, sr_out, stereo_i32)


    print(f"\n✅ Mastered File Saved: {output_wav}")
    print(f"\n📋 Settings Applied:")
    print(f"   Genre: {genre}")
    print(f"   Profile: {profile}")
    print(f"   Quality Mode: {quality_mode.upper()}")
    print(f"   High-Pass: {preset['hp']} Hz")
    print(f"   Low-Pass: {preset['lp']} Hz")
    print(f"   Compression: {preset['ratio']}:1 @ {preset['th']} dB")
    print(f"   Target: {preset['lufs']} LUFS")
    print(f"   Export SR: {sr_out} Hz (48 kHz)")
    print(f"   Bit Depth: 24-bit PCM (int32 container)")

    
    # # 11) Soft limiting + safety
    # print("   🔟  Soft limiting & safety...")
    # L = soft_limiter(L, ceiling_dB=-0.5)
    # R = soft_limiter(R, ceiling_dB=-0.5)
    
    # L = np.clip(L, -0.99, 0.99)
    # R = np.clip(R, -0.99, 0.99)
    
    # # Export
    # print("   1️⃣1️⃣  Exporting...")
    # stereo = np.stack([L, R], axis=1)
    
    # dither = np.random.triangular(-1, 0, 1, stereo.shape) / 32768
    # stereo_dithered = stereo + dither
    # stereo_i16 = np.int16(np.clip(stereo_dithered, -1, 1) * 32767)
    
    # wavfile.write(output_wav, sr, stereo_i16)
    
    # print(f"\n✅ Mastered File Saved: {output_wav}")
    # print(f"\n📋 Settings Applied:")
    # print(f"   Genre: {genre}")
    # print(f"   Profile: {profile}")
    # print(f"   Quality Mode: {quality_mode.upper()}")
    # print(f"   High-Pass: {preset['hp']} Hz")
    # print(f"   Low-Pass: {preset['lp']} Hz")
    # print(f"   Compression: {preset['ratio']}:1 @ {preset['th']} dB")
    # print(f"   Target: {preset['lufs']} LUFS")



def interactive_mode():
    print("\n" + "="*60)
    print("🎚️  PROFESSIONAL AUDIO MASTERING TOOL")
    print("     (Clean, Artifact-Free Processing)")
    print("="*60 + "\n")
    
    input_wav = input("📁 Enter input WAV file path: ").strip()
    output_wav = input("💾 Enter output WAV file name: ").strip()
    
    print("\n📚 Available Genres:")
    genres = list(GENRE_PRESETS.keys())
    for i, g in enumerate(genres, 1):
        print(f"   {i:2d}. {g}")
    
    genre = input("\n🎵 Enter genre (or press Enter for 'default'): ").strip().lower()
    if not genre:
        genre = "default"
    
    quality = input("\n🔬 Quality mode? (high/normal, default=high): ").strip().lower()
    if quality not in ['high', 'normal']:
        quality = 'high'
    
    print("\n" + "="*60)
    analyze_and_master(input_wav, output_wav, genre=genre, quality_mode=quality)
    print("\n" + "="*60)
    print("✨ Processing complete!")
    print("="*60 + "\n")

# =======================================================
#  COMMAND LINE MODE
# =======================================================

def command_line_mode():
    parser = argparse.ArgumentParser(description='Professional Audio Mastering Tool')
    parser.add_argument('input', help='Input WAV file path')
    parser.add_argument('output', help='Output WAV file path')
    parser.add_argument('-g', '--genre', default='default', 
                       help='Genre preset (default: default)')
    parser.add_argument('-q', '--quality', default='high', 
                       choices=['high', 'normal'],
                       help='Quality mode (default: high)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    analyze_and_master(args.input, args.output, genre=args.genre, quality_mode=args.quality)
    print("\n" + "="*60)

# =======================================================
#  ENTRY POINT
# =======================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command_line_mode()
    else:
        interactive_mode()