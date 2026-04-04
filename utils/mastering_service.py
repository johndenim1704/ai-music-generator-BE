"""
Audio Mastering Service
Provides professional audio mastering functionality with genre-specific presets.
"""
import numpy as np
import librosa
import pyloudnorm as pyln
from scipy.signal import butter, filtfilt, lfilter, resample_poly
from scipy.io import wavfile
from scipy.io.wavfile import WavFileWarning
import os
import time
from typing import Dict, Tuple, Optional, Callable
import logging

logger = logging.getLogger(__name__)

# Target sample rate for mastering export
TARGET_SR = 48000

# Genre presets with mastering parameters
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

    # World & Cultural
    "afrobeats":   {"lufs": -10, "hp": 45,  "lp": 18000, "th": -17, "ratio": 2.3},
    "latin":       {"lufs": -10, "hp": 45,  "lp": 18000, "th": -16, "ratio": 2.4},
    "reggaeton":   {"lufs": -9,  "hp": 40,  "lp": 18000, "th": -16, "ratio": 2.6},
    "dancehall":   {"lufs": -9,  "hp": 35,  "lp": 17500, "th": -17, "ratio": 2.8},
    "kpop":        {"lufs": -11, "hp": 50,  "lp": 18500, "th": -16, "ratio": 2.3},
    "bollywood":   {"lufs": -13, "hp": 90,  "lp": 15500, "th": -20, "ratio": 1.8},

    # Electronic & Club
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

    # Rock & Band
    "rock":          {"lufs": -11, "hp": 60,  "lp": 17000, "th": -16, "ratio": 2.5},
    "alt_rock":      {"lufs": -11, "hp": 50,  "lp": 17500, "th": -16, "ratio": 2.4},
    "indie":         {"lufs": -12, "hp": 70,  "lp": 16500, "th": -18, "ratio": 2.0},
    "metal":         {"lufs": -9,  "hp": 40,  "lp": 18000, "th": -15, "ratio": 3.0},
    "punk":          {"lufs": -10, "hp": 50,  "lp": 17000, "th": -16, "ratio": 2.8},
    "grunge":        {"lufs": -11, "hp": 60,  "lp": 16000, "th": -18, "ratio": 2.3},
    "progressive":   {"lufs": -10, "hp": 50,  "lp": 18000, "th": -16, "ratio": 2.2},
    "post_rock":     {"lufs": -14, "hp": 100, "lp": 15000, "th": -22, "ratio": 1.7},

    # Classical & Film
    "classical":   {"lufs": -20, "hp": 80,  "lp": 14000, "th": -28, "ratio": 1.2},
    "orchestral":  {"lufs": -18, "hp": 70,  "lp": 15000, "th": -26, "ratio": 1.4},
    "cinematic":   {"lufs": -16, "hp": 60,  "lp": 16000, "th": -22, "ratio": 1.6},
    "soundtrack":  {"lufs": -17, "hp": 70,  "lp": 15000, "th": -24, "ratio": 1.6},

    # Vocal / Media
    "podcast":      {"lufs": -16, "hp": 80,  "lp": 14000, "th": -20, "ratio": 2.3},
    "audiobook":    {"lufs": -18, "hp": 80,  "lp": 13000, "th": -24, "ratio": 2.0},
    "speech":       {"lufs": -16, "hp": 100, "lp": 12000, "th": -20, "ratio": 2.5},

    # Urban sub-styles
    "drill":        {"lufs": -9,  "hp": 35,  "lp": 17000, "th": -16, "ratio": 3.0},
    "cloud_rap":    {"lufs": -12, "hp": 60,  "lp": 15500, "th": -19, "ratio": 2.0},
    "emo_rap":      {"lufs": -11, "hp": 55,  "lp": 16000, "th": -18, "ratio": 2.0},
    "phonk":        {"lufs": -8,  "hp": 30,  "lp": 15000, "th": -15, "ratio": 3.5},

    # Jazz & Soul
    "jazz":         {"lufs": -16, "hp": 90,  "lp": 15500, "th": -22, "ratio": 1.6},
    "neo_soul":     {"lufs": -13, "hp": 70,  "lp": 16000, "th": -18, "ratio": 2.0},
    "blues":        {"lufs": -14, "hp": 80,  "lp": 15000, "th": -20, "ratio": 1.8},
    "funk":         {"lufs": -11, "hp": 50,  "lp": 17000, "th": -17, "ratio": 2.5}
}

# Genre profile mapping
CLUB_GENRES = {
    "edm", "house", "techno", "dubstep", "trance", "hardstyle",
    "drum_and_bass", "future_bass", "garage", "breakbeat",
    "electro", "afrobeats", "dancehall", "trap",
    "drill", "phonk", "kpop"
}

CLEAN_GENRES = {
    "acoustic", "lofi", "classical", "orchestral", "cinematic",
    "soundtrack", "jazz", "neo_soul", "blues", "ambient", "downtempo",
    "indian", "bollywood"
}

SPEECH_GENRES = {"podcast", "audiobook", "speech"}


class MasteringService:
    """Professional audio mastering service"""
    
    @staticmethod
    def get_available_genres() -> Dict[str, Dict]:
        """Return all available genre presets"""
        return GENRE_PRESETS.copy()
    
    @staticmethod
    def butter_filter_zero_phase(data: np.ndarray, cutoff: float, fs: int, 
                                  filter_type: str = "low", order: int = 4) -> np.ndarray:
        """Apply zero-phase butterworth filter"""
        nyq = 0.5 * fs
        norm = np.array(cutoff, ndmin=1) / nyq
        norm = np.clip(norm, 0.001, 0.999)
        b, a = butter(order, norm, btype=filter_type)
        return filtfilt(b, a, data)
    
    @staticmethod
    def split_bands(x: np.ndarray, sr: int, low_split: int = 120, 
                    high_split: int = 4000, order: int = 4) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Split audio into low, mid, and high frequency bands"""
        nyq = 0.5 * sr
        low = MasteringService.butter_filter_zero_phase(x, low_split, sr, filter_type='low', order=order)
        high = MasteringService.butter_filter_zero_phase(x, high_split, sr, filter_type='high', order=order)
        band = MasteringService.butter_filter_zero_phase(
            x, [low_split / nyq * nyq, high_split / nyq * nyq],
            sr, filter_type='band', order=order
        )
        return low, band, high
    
    @staticmethod
    def smooth_compressor(x: np.ndarray, threshold_dB: float = -18, ratio: float = 2.0,
                         attack_ms: float = 5, release_ms: float = 50, sr: int = 44100,
                         makeup_gain: float = 2.0) -> np.ndarray:
        """Smooth compressor with attack/release for natural sound"""
        threshold = 10 ** (threshold_dB / 20)
        
        attack_samples = int(attack_ms * sr / 1000)
        release_samples = int(release_ms * sr / 1000)
        
        envelope = np.abs(x)
        gain_reduction = np.ones_like(x)
        current_gain = 1.0
        
        for i in range(len(x)):
            if envelope[i] > threshold:
                target_gain = threshold / envelope[i]
                target_gain = target_gain + (1 - target_gain) * (1 / ratio)
            else:
                target_gain = 1.0
            
            if target_gain < current_gain:
                current_gain += (target_gain - current_gain) / max(attack_samples, 1)
            else:
                current_gain += (target_gain - current_gain) / max(release_samples, 1)
            
            gain_reduction[i] = current_gain
        
        compressed = x * gain_reduction
        return compressed * (10 ** (makeup_gain / 20))
    
    @staticmethod
    def anti_aliasing_upsample(x: np.ndarray, sr: int, factor: int = 2) -> Tuple[np.ndarray, int]:
        """Upsample to reduce digital artifacts"""
        return resample_poly(x, factor, 1), sr * factor
    
    @staticmethod
    def anti_aliasing_downsample(x: np.ndarray, sr: int, factor: int = 2) -> Tuple[np.ndarray, int]:
        """Downsample back after processing"""
        return resample_poly(x, 1, factor), sr // factor
    
    @staticmethod
    def smooth_noise_reduction(x: np.ndarray, threshold_dB: float = -70) -> np.ndarray:
        """Gentle noise reduction without artifacts (vectorized)"""
        threshold = 10 ** (threshold_dB / 20)
        abs_x = np.abs(x)
        factor = np.where(
            abs_x > threshold * 2, 1.0,
            np.where(abs_x > threshold, (abs_x - threshold) / threshold, 0.1)
        )
        return x * factor
    
    @staticmethod
    def soft_limiter(x: np.ndarray, ceiling_dB: float = -1.0) -> np.ndarray:
        """Soft knee limiter that sounds smooth (vectorized)"""
        ceiling = 10 ** (ceiling_dB / 20)
        knee_low = ceiling * 0.8
        abs_x = np.abs(x)
        sign_x = np.sign(x)
        # Soft-knee ratio for the transition zone
        knee_ratio = 1.0 + (abs_x / ceiling - 0.8) * 10
        knee_out = sign_x * (knee_low + (abs_x - knee_low) / np.maximum(knee_ratio, 1e-6))
        return np.where(abs_x <= knee_low, x,
               np.where(abs_x <= ceiling, knee_out,
                        sign_x * ceiling))
    
    @staticmethod
    def apply_multiband_compressor(x: np.ndarray, sr: int, profile: str = "neutral") -> np.ndarray:
        """Simple 3-band compressor with profile-based intensity"""
        low, mid, high = MasteringService.split_bands(x, sr)
        
        if profile == "club":
            low_th, low_ratio = -20, 3.5
            mid_th, mid_ratio = -22, 3.0
            high_th, high_ratio = -24, 2.5
        elif profile == "clean":
            low_th, low_ratio = -24, 1.5
            mid_th, mid_ratio = -26, 1.4
            high_th, high_ratio = -28, 1.3
        elif profile == "speech":
            low_th, low_ratio = -22, 2.0
            mid_th, mid_ratio = -20, 2.3
            high_th, high_ratio = -24, 1.8
        else:
            low_th, low_ratio = -22, 2.5
            mid_th, mid_ratio = -24, 2.2
            high_th, high_ratio = -26, 2.0
        
        low_c = MasteringService.smooth_compressor(low, threshold_dB=low_th, ratio=low_ratio,
                                                   attack_ms=15, release_ms=120, sr=sr, makeup_gain=1.0)
        mid_c = MasteringService.smooth_compressor(mid, threshold_dB=mid_th, ratio=mid_ratio,
                                                   attack_ms=10, release_ms=100, sr=sr, makeup_gain=1.0)
        high_c = MasteringService.smooth_compressor(high, threshold_dB=high_th, ratio=high_ratio,
                                                    attack_ms=5, release_ms=80, sr=sr, makeup_gain=1.0)
        
        return low_c + mid_c + high_c
    
    @staticmethod
    def gentle_clarity_boost(x: np.ndarray, sr: int) -> np.ndarray:
        """Gentle presence boost without harshness"""
        nyq = 0.5 * sr
        
        b_low, a_low = butter(2, 2500 / nyq, btype='high')
        b_high, a_high = butter(2, 5000 / nyq, btype='low')
        
        presence = lfilter(b_low, a_low, x)
        presence = lfilter(b_high, a_high, presence)
        
        boost = 1.12
        return x + (presence * (boost - 1))
    
    @staticmethod
    def harmonic_saturator(x: np.ndarray, drive: float = 1.5, mix: float = 0.4) -> np.ndarray:
        """Add harmonic saturation for warmth"""
        if drive <= 0 or mix <= 0:
            return x
        
        y = np.tanh(x * drive)
        return (1.0 - mix) * x + mix * y
    
    @staticmethod
    def ms_encode(L: np.ndarray, R: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Encode to mid/side"""
        mid = (L + R) * 0.5
        side = (L - R) * 0.5
        return mid, side
    
    @staticmethod
    def ms_decode(mid: np.ndarray, side: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Decode from mid/side"""
        L = mid + side
        R = mid - side
        return L, R
    
    @staticmethod
    def stereo_widen(L: np.ndarray, R: np.ndarray, sr: int, 
                    widen_amount: float = 1.0, low_mono_hz: int = 120) -> Tuple[np.ndarray, np.ndarray]:
        """Stereo widening with low-end mono preservation"""
        if widen_amount <= 1.0:
            return L, R
        
        mid, side = MasteringService.ms_encode(L, R)
        
        side_hp = MasteringService.butter_filter_zero_phase(side, low_mono_hz, sr, filter_type="high", order=3)
        side_lp = side - side_hp
        
        widened_side = side_hp * widen_amount + side_lp
        
        L_out, R_out = MasteringService.ms_decode(mid, widened_side)
        return L_out, R_out
    
    @staticmethod
    def tighten_low_end(x: np.ndarray, sr: int, center_hz: int = 80, 
                       q: float = 1.0, gain_db: float = 1.5) -> np.ndarray:
        """Tighten and enhance low-end"""
        low, mid, high = MasteringService.split_bands(x, sr, low_split=center_hz*2, high_split=4000)
        low_c = MasteringService.smooth_compressor(low, threshold_dB=-24, ratio=2.0,
                                                   attack_ms=20, release_ms=150, sr=sr, makeup_gain=0.0)
        gain_lin = 10 ** (gain_db / 20.0)
        low_c *= gain_lin
        return low_c + mid + high
    
    @staticmethod
    def mastering_profile_from_genre(genre: str) -> str:
        """Determine mastering profile from genre"""
        g = genre.lower()
        if g in CLUB_GENRES:
            return "club"
        if g in CLEAN_GENRES:
            return "clean"
        if g in SPEECH_GENRES:
            return "speech"
        return "neutral"
    
    @staticmethod
    def resample_to_target_sr(L: np.ndarray, R: np.ndarray, sr: int, 
                             target_sr: int = TARGET_SR) -> Tuple[np.ndarray, np.ndarray, int]:
        """High-quality resampling to target sample rate"""
        if sr == target_sr:
            return L, R, sr
        
        logger.info(f"Resampling from {sr} Hz to {target_sr} Hz for export...")
        L_res = resample_poly(L, target_sr, sr)
        R_res = resample_poly(R, target_sr, sr)
        return L_res, R_res, target_sr
    
    @staticmethod
    def master_audio(input_path: str, output_path: str, genre: str = "default", 
                    quality_mode: str = "high", log_callback: Optional[Callable[[str], None]] = None) -> Dict:
        """
        Master an audio file with genre-specific processing
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save mastered audio
            genre: Genre preset to use
            quality_mode: "high" or "normal"
            
        Returns:
            Dictionary with processing metadata
        """
        start_time = time.time()
        
        def log(msg: str):
            logger.info(msg)
            if log_callback:
                try:
                    log_callback(msg)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        log("Loading audio file for processing...")
        
        try:
            # Suppress WavFileWarning for non-data chunks (metadata)
            import warnings
            file_ext = os.path.splitext(input_path)[1].lower()
            
            if file_ext == ".wav":
                # Load WAV files using scipy
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=wavfile.WavFileWarning)
                    sr, audio = wavfile.read(input_path)
                log(f"Sample Rate: {sr} Hz")
            else:
                # Load MP3 and other formats using librosa
                audio, sr = librosa.load(input_path, sr=None, mono=False)
                log(f"Sample Rate: {sr} Hz (loaded via librosa)")
                # Convert to the same format as wavfile.read for compatibility
                if audio.ndim == 1:
                    # Mono audio
                    audio = (audio * 32768).astype(np.int16)
                else:
                    # Stereo audio
                    audio = (audio.T * 32768).astype(np.int16)
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            raise ValueError(f"Failed to load audio file: {e}")
        
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
            log("Upsampling for high-quality processing...")
            L, sr_high = MasteringService.anti_aliasing_upsample(L, sr, factor=2)
            R, sr_high = MasteringService.anti_aliasing_upsample(R, sr, factor=2)
            processing_sr = sr_high
        else:
            processing_sr = sr
        
        # Analysis
        log("Analyzing track...")
        mono = (L + R) / 2
        
        try:
            if len(mono) > processing_sr * 60:
                mono_analyze = mono[:processing_sr * 60]
            else:
                mono_analyze = mono
            
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=mono_analyze, sr=processing_sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=mono_analyze, sr=processing_sr))
            rms = np.mean(librosa.feature.rms(y=mono_analyze))
            
            
            log(f"Spectral Centroid: {spectral_centroid:.1f} Hz")
            log(f"RMS Energy: {rms:.3f}")
        except Exception as e:
            logger.warning(f"Analysis failed ({e}), using defaults")
            spectral_centroid, spectral_rolloff, rms = 2000, 7000, 0.1
        
        # Preset selection
        log("Optimizing settings...")
        genre = genre.lower()
        preset = GENRE_PRESETS.get(genre, GENRE_PRESETS["default"]).copy()
        
        # Small adjustments based on analysis
        if spectral_centroid < 1400:
            preset["hp"] = min(preset["hp"] + 15, 100)
            log(f"Bass clarity: HP adjusted to {preset['hp']} Hz")
        if rms < 0.06:
            preset["ratio"] = min(preset["ratio"] + 0.3, 3.0)
            log(f"Dynamics: Ratio adjusted to {preset['ratio']}")
        
        profile = MasteringService.mastering_profile_from_genre(genre)
        log(f"Profile: {profile}")
        
        # MASTERING CHAIN
        log("Applying mastering chain...")
        
        # 1) Noise reduction
        log("1. Noise reduction...")
        L = MasteringService.smooth_noise_reduction(L, threshold_dB=-70)
        R = MasteringService.smooth_noise_reduction(R, threshold_dB=-70)
        
        # 2) HP / LP filters
        log("2. High-pass / low-pass...")
        L = MasteringService.butter_filter_zero_phase(L, preset["hp"], processing_sr, filter_type="high", order=3)
        R = MasteringService.butter_filter_zero_phase(R, preset["hp"], processing_sr, filter_type="high", order=3)
        
        L = MasteringService.butter_filter_zero_phase(L, preset["lp"], processing_sr, filter_type="low", order=4)
        R = MasteringService.butter_filter_zero_phase(R, preset["lp"], processing_sr, filter_type="low", order=4)
        
        # 3) Multiband compression
        log("3. Multiband compression...")
        L = MasteringService.apply_multiband_compressor(L, processing_sr, profile=profile)
        R = MasteringService.apply_multiband_compressor(R, processing_sr, profile=profile)
        
        # 4) Bus compression
        log("4. Bus compression...")
        L = MasteringService.smooth_compressor(L, threshold_dB=preset["th"], ratio=preset["ratio"],
                                              attack_ms=10, release_ms=120, sr=processing_sr, makeup_gain=1.0)
        R = MasteringService.smooth_compressor(R, threshold_dB=preset["th"], ratio=preset["ratio"],
                                              attack_ms=10, release_ms=120, sr=processing_sr, makeup_gain=1.0)
        
        # 5) Bass tightening
        if profile in ["club", "neutral"]:
            log("5. Tightening low-end...")
            bass_bump = 2.0 if profile == "club" else 1.0
            L = MasteringService.tighten_low_end(L, processing_sr, center_hz=80, gain_db=bass_bump)
            R = MasteringService.tighten_low_end(R, processing_sr, center_hz=80, gain_db=bass_bump)
        
        # 6) Clarity boost
        if spectral_centroid < 2500:
            log("6. Gentle clarity enhancement...")
            L = MasteringService.gentle_clarity_boost(L, processing_sr)
            R = MasteringService.gentle_clarity_boost(R, processing_sr)
        
        # 7) Harmonic saturation
        log("7. Harmonic saturation...")
        if profile == "club":
            drive, mix = 2.0, 0.45
        elif profile == "clean":
            drive, mix = 1.2, 0.25
        elif profile == "speech":
            drive, mix = 1.1, 0.2
        else:
            drive, mix = 1.6, 0.35
        
        L = MasteringService.harmonic_saturator(L, drive=drive, mix=mix)
        R = MasteringService.harmonic_saturator(R, drive=drive, mix=mix)
        
        # 8) Stereo widening
        log("8. Stereo imaging...")
        if profile == "club":
            widen = 1.25
        elif profile == "clean":
            widen = 1.08
        elif profile == "speech":
            widen = 1.02
        else:
            widen = 1.15
        
        L, R = MasteringService.stereo_widen(L, R, processing_sr, widen_amount=widen, low_mono_hz=120)
        
        # 9) Downsample if needed
        if quality_mode == "high":
            log("Downsampling to original rate...")
            L, _ = MasteringService.anti_aliasing_downsample(L, processing_sr, factor=2)
            R, _ = MasteringService.anti_aliasing_downsample(R, processing_sr, factor=2)
        
        # 10) Loudness normalization
        log("9. Loudness normalization...")
        meter = pyln.Meter(sr)
        stereo_for_measurement = np.vstack([L, R]).T
        
        try:
            current_loudness = meter.integrated_loudness(stereo_for_measurement)
            target_lufs = preset["lufs"]
            gain = target_lufs - current_loudness
            gain = np.clip(gain, -6, 12)
            gain_lin = 10 ** (gain / 20)
            
            log(f"Current: {current_loudness:.1f} LUFS → Target: {target_lufs} LUFS (Δ {gain:.1f} dB)")
            L *= gain_lin
            R *= gain_lin
        except Exception as e:
            logger.warning(f"LUFS failed ({e}), using peak normalization")
            current_loudness = -14.0  # default value
            target_lufs = preset["lufs"]
            peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
            if peak > 0:
                L *= 0.9 / peak
                R *= 0.9 / peak
        
        # 11) Soft limiting
        log("10. Soft limiting & safety...")
        L = MasteringService.soft_limiter(L, ceiling_dB=-0.5)
        R = MasteringService.soft_limiter(R, ceiling_dB=-0.5)
        
        L = np.clip(L, -0.99, 0.99)
        R = np.clip(R, -0.99, 0.99)
        
        # 12) Resample to 48 kHz
        L, R, sr_out = MasteringService.resample_to_target_sr(L, R, sr, target_sr=TARGET_SR)
        
        # Export as 24-bit PCM
        log("Finalizing and exporting mastered audio...")
        
        stereo = np.stack([L, R], axis=1)
        
        # Triangular dither
        dither_amp = 1.0 / (2**24)
        dither = np.random.triangular(-1, 0, 1, size=stereo.shape) * dither_amp
        stereo_dithered = np.clip(stereo + dither, -1.0, 1.0)
        
        # Quantize to 32-bit
        stereo_i32 = np.int32(stereo_dithered * (2**31 - 1))
        
        wavfile.write(output_path, sr_out, stereo_i32)
        
        processing_time = time.time() - start_time
        
        log("Mastering process complete!")
        log(f"Processing time: {processing_time:.2f}s")
        
        return {
            "genre": genre,
            "profile": profile,
            "quality_mode": quality_mode,
            "original_lufs": float(current_loudness),
            "target_lufs": float(target_lufs),
            "sample_rate": sr_out,
            "bit_depth": "24-bit PCM (int32 container)",
            "processing_time": processing_time,
            "settings": {
                "high_pass": preset["hp"],
                "low_pass": preset["lp"],
                "compression_ratio": preset["ratio"],
                "compression_threshold": preset["th"]
            }
        }
