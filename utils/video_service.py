import os
import subprocess
import logging
import uuid
import tempfile

logger = logging.getLogger(__name__)

class VideoService:
    def get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of the audio file in seconds using ffprobe."""
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            # Fallback: return None or raise. 
            # If we can't get duration, we might risk infinite loop with -loop 1 if -shortest fails.
            # But let's try to proceed without it or assume a safe default? 
            # Better to raise error or return None and let caller handle.
            return None

    def generate_video(self, image_path: str, audio_path: str, output_path: str):
        """
        Generates an MP4 video from an image and an audio file using ffmpeg (CPU only).
        """
        try:
            # Get audio duration to force exact length
            duration = self.get_audio_duration(audio_path)
            
            command = [
                "ffmpeg",
                "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-preset", "ultrafast"
            ]

            if duration:
                # Add explicit duration + small buffer to ensure audio isn't cut off too early
                command.extend(["-t", str(duration)])
            else:
                # Fallback to shortest if duration detection failed
                command.append("-shortest")

            command.append(output_path)

            logger.info(f"Running ffmpeg command (CPU): {' '.join(command)}")
            
            # Run ffmpeg with timeout (e.g., 5 minutes max)
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300 # 5 minutes timeout
            )

            if process.returncode != 0:
                logger.error(f"FFmpeg failed: {process.stderr}")
                raise RuntimeError(f"FFmpeg error: {process.stderr}")

            logger.info(f"Video generated successfully at {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg process timed out")
            raise RuntimeError("Video generation timed out")
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            raise e
