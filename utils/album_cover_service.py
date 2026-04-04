import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Dict

import ollama
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import gc
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# -------------------------
# CONFIG
# -------------------------

LLM_MODEL = "llama3.2:latest"
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"

# Global pipeline instance (loaded once)
pipe = None


class AlbumCoverService:
    """Service for generating AI-powered album covers using Llama 3.2 and Stable Diffusion 1.5"""
    
    def __init__(self):
        region = os.getenv('AWS_REGION', 'eu-north-1')
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=region,
            config=boto3.session.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )
        )
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        self.region = region
        logger.info("[ALBUM_COVER_SERVICE] Service initialized")

    # -------------------------
    # LLM: Prompt Generation
    # -------------------------

    def build_llama_prompt(self, track_name: str, genre: str) -> str:
        """Build the instruction for Llama 3.2 to generate image prompt and text styling"""
        return f"""
You are an album cover art designer and expert AI image prompt engineer.

Your job:
- Take a music track title and genre
- Imagine the mood, atmosphere, visuals, and color palette
- Write a SINGLE, strong image generation prompt for Stable Diffusion
- Design UNIQUE text styling that perfectly matches THIS SPECIFIC track and genre

Input:
- Track name: "{track_name}"
- Genre: {genre}
- Assume the song is instrumental (no vocals).

Requirements for the image prompt:
- 1 sentence only, no line breaks.
- Describe the mood and atmosphere implied by the title and genre.
- Describe visual style (e.g. abstract, cinematic, neon, glitch, minimalist, anime, futuristic, retro, etc).
- Mention a clear color palette (e.g. deep purples and blues, warm oranges, neon pink and cyan).
- Mention some visual elements or composition (e.g. city at night, floating shapes, cosmic scene, street at dusk, abstract waves).
- The background image MUST NOT contain any text, words, letters, logos, or typography.
- Suitable for a square digital album cover.

Requirements for text styling (BE CREATIVE AND VARY YOUR CHOICES):
- Analyze the track name and genre to choose a UNIQUE font family that matches the visual style:
  * Electronic/EDM/Techno → "DejaVu Sans Bold" or "Liberation Sans Bold"
  * Lo-fi/Chill → "DejaVu Serif" or "Liberation Serif"
  * Hip-hop/Trap → "DejaVu Sans Bold" or "Liberation Sans Bold"
  * Jazz/Soul → "DejaVu Serif" or "Liberation Serif"
  * Rock/Metal → "DejaVu Sans Bold" or "Liberation Sans Bold"
  * Synthwave/Vaporwave → "DejaVu Sans Mono Bold"
  * Ambient/Experimental → "DejaVu Sans" or "Liberation Sans"
  * Classical → "DejaVu Serif" or "Liberation Serif"
  
  Choose from these available fonts (pick ONE specific font name):
  - DejaVu Sans, DejaVu Sans Bold
  - DejaVu Serif, DejaVu Serif Bold
  - DejaVu Sans Mono, DejaVu Sans Mono Bold
  - Liberation Sans, Liberation Sans Bold
  - Liberation Serif, Liberation Serif Bold
  
- Choose a text color that CONTRASTS with the background colors you described:
  * If background is dark → use "white", "neon cyan", "gold", "bright pink"
  * If background is light → use "black", "deep purple", "navy blue"
  * For neon/vibrant backgrounds → use complementary neon colors
  
- Position is ALWAYS "center" (required)

- Choose effects that enhance the mood:
  * "glow" - for neon, cyberpunk, futuristic themes
  * "shadow" - for depth, drama, contrast
  * "outline" - for busy backgrounds, maximalist designs
  * "glow and shadow" - for extra dramatic effect

IMPORTANT: Make each cover UNIQUE by varying the FONT FAMILY. Don't use the same font repeatedly. Consider the specific vibe of THIS track name and genre to pick the perfect font.

Output JSON ONLY in this form:

{{
  "prompt": "one single-sentence prompt for the image model",
  "text_style": {{
    "font_family": "specific font name like DejaVu Sans Bold, Liberation Serif, etc.",
    "color": "specific color name or hex code",
    "position": "center",
    "effects": "glow" or "shadow" or "outline" or "glow and shadow" or "none"
  }}
}}
"""

    def generate_image_prompt_with_llama(self, track_name: str, genre: str) -> Tuple[str, Dict]:
        """
        Call Llama 3.2 via Ollama and get back a prompt string and text styling info.
        Returns: (image_prompt, text_style_dict)
        """
        logger.info(f"[ALBUM_COVER] Generating image prompt for track: {track_name}, genre: {genre}")
        
        prompt_text = self.build_llama_prompt(track_name, genre)

        logger.info("[ALBUM_COVER] Calling Ollama LLM...")
        resp = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You output JSON only."},
                {"role": "user", "content": prompt_text},
            ],
            options={
                "temperature": 0.5
            },
        )

        content = resp["message"]["content"].strip()
        logger.debug(f"[ALBUM_COVER] LLM response: {content}")

        # Try to parse JSON directly
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: extract JSON blob
            logger.warning("[ALBUM_COVER] Failed to parse JSON directly, extracting JSON blob")
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end <= start:
                raise ValueError(f"LLM did not return JSON:\n{content}")
            json_str = content[start:end]
            data = json.loads(json_str)

        if "prompt" not in data:
            raise ValueError(f"No 'prompt' key in LLM JSON:\n{data}")
        
        # Extract text style, with defaults if not provided
        text_style = data.get("text_style", {
            "font_family": "DejaVu Sans Bold",
            "color": "white",
            "position": "center",
            "effects": "shadow"
        })

        logger.info(f"[ALBUM_COVER] Image prompt generated: {data['prompt']}")
        logger.info(f"[ALBUM_COVER] Text style: {text_style}")
        
        return data["prompt"], text_style

    # -------------------------
    # Text Overlay
    # -------------------------

    def get_font_path(self, font_family: str, size: int) -> ImageFont.FreeTypeFont:
        """
        Get the exact font based on font family name.
        Maps font names to Linux system font paths (for Docker).
        """
        font_family_lower = font_family.lower()
        
        # Direct mapping of font family names to Linux paths
        font_map = {
            # DejaVu fonts (commonly available in Linux)
            "dejavu sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "dejavu sans bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "dejavu serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "dejavu serif bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "dejavu sans mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "dejavu sans mono bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            
            # Liberation fonts (alternative to Microsoft fonts)
            "liberation sans": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "liberation sans bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "liberation serif": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "liberation serif bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        }
        
        # Try exact match first
        if font_family_lower in font_map:
            path = font_map[font_family_lower]
            if Path(path).exists():
                try:
                    logger.debug(f"[ALBUM_COVER] Using font: {path}")
                    return ImageFont.truetype(path, size)
                except Exception as e:
                    logger.warning(f"[ALBUM_COVER] Failed to load font {path}: {e}")
        
        # Try partial match
        for font_name, path in font_map.items():
            if font_name in font_family_lower and Path(path).exists():
                try:
                    logger.debug(f"[ALBUM_COVER] Using font (partial match): {path}")
                    return ImageFont.truetype(path, size)
                except Exception as e:
                    logger.warning(f"[ALBUM_COVER] Failed to load font {path}: {e}")
        
        # Fallback to DejaVu Sans (most common)
        fallback_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        try:
            if Path(fallback_path).exists():
                logger.warning(f"[ALBUM_COVER] Using fallback font: {fallback_path}")
                return ImageFont.truetype(fallback_path, size)
        except Exception as e:
            logger.error(f"[ALBUM_COVER] Failed to load fallback font: {e}")
        
        # Ultimate fallback
        logger.warning("[ALBUM_COVER] Using PIL default font")
        return ImageFont.load_default()

    def parse_color(self, color_str: str) -> tuple:
        """Convert color string to RGB tuple with expanded color palette."""
        color_lower = color_str.lower().strip()
        
        # Expanded color palette for variety
        colors = {
            # Basic colors
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "blue": (0, 100, 255),
            "green": (0, 255, 0),
            "yellow": (255, 255, 0),
            
            # Neon colors
            "cyan": (0, 255, 255),
            "neon cyan": (0, 255, 255),
            "neon": (0, 255, 255),
            "magenta": (255, 0, 255),
            "neon pink": (255, 16, 240),
            "neon green": (57, 255, 20),
            "neon yellow": (255, 255, 102),
            "neon orange": (255, 153, 51),
            
            # Metallic colors
            "gold": (255, 215, 0),
            "silver": (192, 192, 192),
            "bronze": (205, 127, 50),
            "copper": (184, 115, 51),
            
            # Natural colors
            "orange": (255, 165, 0),
            "purple": (160, 32, 240),
            "pink": (255, 105, 180),
            "bright pink": (255, 20, 147),
            "lavender": (230, 230, 250),
            "turquoise": (64, 224, 208),
            "teal": (0, 128, 128),
            
            # Deep/Dark colors
            "navy": (0, 0, 128),
            "navy blue": (0, 0, 128),
            "deep purple": (75, 0, 130),
            "deep blue": (0, 51, 102),
            "maroon": (128, 0, 0),
            "dark red": (139, 0, 0),
            
            # Pastel colors
            "pastel pink": (255, 209, 220),
            "pastel blue": (174, 198, 207),
            "pastel purple": (179, 158, 181),
            
            # Warm colors
            "crimson": (220, 20, 60),
            "coral": (255, 127, 80),
            "peach": (255, 218, 185),
        }
        
        # Check if it's a known color (check for partial matches)
        for name, rgb in colors.items():
            if name in color_lower:
                return rgb
        
        # Try to parse hex color (#RRGGBB or #RGB)
        if "#" in color_str:
            hex_color = color_str.replace("#", "").strip()
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            elif len(hex_color) == 3:
                return tuple(int(c*2, 16) for c in hex_color)
        
        # Default to white
        return (255, 255, 255)

    def add_text_to_image(
        self,
        image: Image.Image,
        text: str,
        text_style: dict,
    ) -> Image.Image:
        """
        Add styled text overlay to the generated image.
        
        Args:
            image: PIL Image to add text to
            text: The text to add (track name)
            text_style: Dictionary with font_family, color, position, effects
        
        Returns:
            PIL Image with text overlay
        """
        logger.info(f"[ALBUM_COVER] Adding text overlay: '{text}'")
        img_width, img_height = image.size
        
        # Create a copy to work with
        img_with_text = image.copy()
        
        # Determine font size based on image size and text length
        base_size = img_width // 10
        font_size = max(30, min(base_size, img_width // (len(text) // 2 + 1)))
        logger.debug(f"[ALBUM_COVER] Font size: {font_size}")
        
        # Get font based on font family
        font_family = text_style.get("font_family", "DejaVu Sans Bold")
        font = self.get_font_path(font_family, font_size)
        
        # Parse color
        text_color = self.parse_color(text_style.get("color", "white"))
        logger.debug(f"[ALBUM_COVER] Text color: {text_color}")
        
        # Create drawing context
        draw = ImageDraw.Draw(img_with_text)
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Determine position - ALWAYS CENTER
        position = "center"
        x = (img_width - text_width) // 2
        y = (img_height - text_height) // 2
        logger.debug(f"[ALBUM_COVER] Text position: ({x}, {y})")
        
        # Apply effects
        effects = text_style.get("effects", "shadow").lower()
        logger.debug(f"[ALBUM_COVER] Applying effects: {effects}")
        
        if "glow" in effects:
            # Create glow effect
            glow_img = Image.new("RGBA", img_with_text.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            
            # Draw multiple layers for glow
            for offset in range(6, 0, -2):
                alpha = int(255 * (offset / 6) * 0.5)
                glow_color = text_color + (alpha,)
                for dx in range(-offset, offset+1):
                    for dy in range(-offset, offset+1):
                        glow_draw.text((x + dx, y + dy), text, font=font, fill=glow_color)
            
            # Blur the glow
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(4))
            img_with_text = Image.alpha_composite(img_with_text.convert("RGBA"), glow_img).convert("RGB")
            draw = ImageDraw.Draw(img_with_text)
        
        if "shadow" in effects:
            # Add shadow
            shadow_color = (0, 0, 0) if sum(text_color) > 384 else (255, 255, 255)
            shadow_offset = max(2, font_size // 20)
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
        
        if "outline" in effects:
            # Add outline
            outline_color = (0, 0, 0) if sum(text_color) > 384 else (255, 255, 255)
            outline_width = max(2, font_size // 30)
            for dx in range(-outline_width, outline_width+1):
                for dy in range(-outline_width, outline_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color)
        
        logger.info("[ALBUM_COVER] Text overlay added successfully")
        return img_with_text

    # -------------------------
    # Image Generation
    # -------------------------

    def load_sd_pipeline(self):
        """
        Load SD 1.5 pipeline - much lighter than SDXL.
        Uses only ~2GB RAM vs SDXL's ~7GB.
        """
        global pipe
        
        if pipe is not None:
            logger.info("[ALBUM_COVER] SD pipeline already loaded")
            return pipe
        
        logger.info("[ALBUM_COVER] Loading Stable Diffusion 1.5 model...")
        logger.info("[ALBUM_COVER] (Lighter and faster than SDXL - only ~2GB)")
        
        try:
            # Load SD 1.5
            pipe = StableDiffusionPipeline.from_pretrained(
                IMAGE_MODEL,
                torch_dtype=torch.float32,
                safety_checker=None,  # Disable for faster loading
            )
            
            # Use faster scheduler
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
            
            # Check for GPU availability
            if torch.cuda.is_available():
                pipe.to("cuda")
                logger.info("[ALBUM_COVER] Using CUDA GPU acceleration")
            else:
                pipe.to("cpu")
                logger.warning("[ALBUM_COVER] Using CPU (no GPU detected - will be slower)")
            
            # Enable memory optimizations
            pipe.enable_attention_slicing()
            
            logger.info("[ALBUM_COVER] SD 1.5 model loaded successfully!")
            
        except Exception as e:
            logger.error(f"[ALBUM_COVER] Error loading model: {e}", exc_info=True)
            raise
        
        return pipe

    def generate_cover_image_local(
        self,
        image_prompt: str,
        track_name: str,
        text_style: dict,
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        add_text: bool = True,
    ) -> Image.Image:
        """
        Use local Stable Diffusion 1.5 to generate an image,
        then add styled text overlay.
        
        Args:
            image_prompt: Text description of the image
            track_name: Name of the track to overlay on the image
            text_style: Dictionary with styling info from Llama
            num_inference_steps: More steps = better quality but slower
            guidance_scale: How closely to follow the prompt
            add_text: Whether to add text overlay
        
        Returns:
            PIL Image object
        """
        
        # Load model if not already loaded
        pipeline = self.load_sd_pipeline()
        
        logger.info("[ALBUM_COVER] Generating image with Stable Diffusion 1.5...")
        logger.info(f"[ALBUM_COVER] Steps: {num_inference_steps}, Guidance: {guidance_scale}")
        
        try:
            # Generate image (512x512 is SD 1.5's native resolution)
            result = pipeline(
                prompt=image_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                height=512,
                width=512,
            )
            
            image = result.images[0]
            logger.info("[ALBUM_COVER] Base image generated (512x512)")
            
            # Upscale to 1024x1024 for better quality
            image = image.resize((1024, 1024), Image.LANCZOS)
            logger.info("[ALBUM_COVER] Image upscaled to 1024x1024")
            
            # Add text overlay if requested
            if add_text:
                logger.info(f"[ALBUM_COVER] Adding text overlay: '{track_name}'")
                logger.info(f"[ALBUM_COVER] Font: {text_style.get('font_family', 'default')}")
                logger.info(f"[ALBUM_COVER] Color: {text_style.get('color', 'white')}")
                logger.info(f"[ALBUM_COVER] Effects: {text_style.get('effects', 'none')}")
                
                image = self.add_text_to_image(image, track_name, text_style)
            
            # Free up memory
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("[ALBUM_COVER] Image generation complete")
            return image
            
        except Exception as e:
            logger.error(f"[ALBUM_COVER] Error generating image: {e}", exc_info=True)
            raise

    # -------------------------
    # S3 Upload
    # -------------------------

    def upload_to_s3(self, image: Image.Image, track_name: str) -> str:
        """
        Upload generated cover image to S3 and return a presigned URL.
        
        Args:
            image: PIL Image to upload
            track_name: Track name for filename
        
        Returns:
            Presigned S3 URL (valid for 7 days) of the uploaded image
        """
        logger.info(f"[ALBUM_COVER] Uploading cover to S3 for track: {track_name}")
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                image.save(tmp_file, format="PNG", quality=95)
                tmp_path = tmp_file.name
            
            # Generate S3 key
            safe_track_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in track_name)
            safe_track_name = safe_track_name.replace(' ', '_')
            s3_key = f"album-covers/{safe_track_name}_{os.urandom(4).hex()}.png"
            
            logger.info(f"[ALBUM_COVER] Uploading to S3 key: {s3_key}")
            
            # Upload to S3
            self.s3_client.upload_file(
                tmp_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'image/png'}
            )
            
            # Generate presigned URL (valid for 7 days)
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=604800  # 7 days in seconds
            )
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            logger.info(f"[ALBUM_COVER] Upload successful, presigned URL generated (valid for 7 days)")
            logger.debug(f"[ALBUM_COVER] Presigned URL: {presigned_url}")
            return presigned_url
            
        except ClientError as e:
            logger.error(f"[ALBUM_COVER] S3 upload failed: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[ALBUM_COVER] Error during upload: {e}", exc_info=True)
            raise

    # -------------------------
    # Main Generation Method
    # -------------------------

    def generate_album_cover(
        self,
        track_name: str,
        genre: str,
        quality: str = "balanced",
        add_text: bool = True,
    ) -> Tuple[str, str, Dict]:
        """
        Complete album cover generation pipeline.
        
        Args:
            track_name: Name of the track
            genre: Music genre
            quality: Quality preset (fast/balanced/high)
            add_text: Whether to add track name overlay
        
        Returns:
            Tuple of (cover_url, image_prompt, text_style)
        """
        logger.info(f"[ALBUM_COVER] === Starting album cover generation ===")
        logger.info(f"[ALBUM_COVER] Track: {track_name}, Genre: {genre}, Quality: {quality}")
        
        # Map quality to parameters
        quality_map = {
            "fast": (15, 7.0),
            "balanced": (25, 7.5),
            "high": (35, 8.0),
        }
        steps, guidance = quality_map.get(quality.lower(), (25, 7.5))
        
        try:
            # 1. Generate image prompt with Llama
            image_prompt, text_style = self.generate_image_prompt_with_llama(track_name, genre)
            
            # 2. Generate cover image with Stable Diffusion
            image = self.generate_cover_image_local(
                image_prompt,
                track_name,
                text_style,
                num_inference_steps=steps,
                guidance_scale=guidance,
                add_text=add_text,
            )
            
            # 3. Upload to S3
            cover_url = self.upload_to_s3(image, track_name)
            
            logger.info(f"[ALBUM_COVER] === Album cover generation complete ===")
            return cover_url, image_prompt, text_style
            
        except Exception as e:
            logger.error(f"[ALBUM_COVER] Generation failed: {e}", exc_info=True)
            raise
