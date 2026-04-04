# import os
# import base64
# import random
# import logging
# from io import BytesIO
# from typing import Dict, Tuple, Optional
# from pathlib import Path

# from openai import OpenAI
# from PIL import Image

# logger = logging.getLogger(__name__)

# class ThumbnailService:
#     def __init__(self):
#         self.api_key = os.getenv("OPENAI_API_KEY")
#         if not self.api_key:
#             logger.warning("OPENAI_API_KEY not found in environment variables. Thumbnail generation will fail.")
        
#         self.client = OpenAI(api_key=self.api_key)
#         self.image_model = "gpt-image-1"  # Or "dall-e-3" depending on actual availability
        
#         # Standard thumbnail sizes
#         self.thumbnail_sizes = {
#             "youtube": (1280, 720),      # 16:9 HD
#             "youtube_max": (1920, 1080), # 16:9 Full HD
#             "square": (1080, 1080),      # Instagram/Spotify square
#             "spotify": (640, 640),       # Spotify cover
#             "soundcloud": (800, 800),    # SoundCloud
#         }

#     def choose_visual_focus(self, track_name: str, genre: str, mood: str) -> str:
#         """
#         Automatically choose visual focus: 'woman', 'car', or 'scenery'
#         based on genre, mood and track name.
#         """
#         t = track_name.lower()
#         g = genre.lower()
#         m = mood.lower()

#         # Keywords hinting strongly at cars / driving
#         car_keywords = [
#             "drive", "drift", "race", "racer", "turbo", "engine",
#             "highway", "midnight ride", "fast lane", "street run", "night ride"
#         ]

#         romantic_moods = [
#             "romantic", "love", "heartfelt", "sensual", "soft", "sweet",
#             "late night", "midnight love", "slow jam", "intimate"
#         ]

#         scenic_moods = [
#             "chill", "peaceful", "calm", "ambient", "dreamy", "nostalgic",
#             "sunset", "sunrise", "island", "ocean", "sky", "heavenly"
#         ]

#         # 1) If track explicitly about driving / racing -> car (strong rule)
#         if any(k in t for k in car_keywords):
#             return "car"

#         # 2) Base decision by genre/mood
#         if g in ["trap", "hiphop", "rap", "phonk", "drill", "edm", "house", "techno"]:
#             if any(k in m for k in ["energetic", "intense", "aggressive", "club"]):
#                 base = "woman"
#             else:
#                 base = "scenery"
#         elif g in ["rnb", "soul", "afrobeats", "pop", "kpop", "latin"]:
#             if any(k in m for k in romantic_moods) or "happy" in m or "uplifting" in m:
#                 base = "woman"
#             else:
#                 base = "scenery"
#         elif g in ["ambient", "lofi", "classical", "cinematic", "soundtrack"]:
#             base = "scenery"
#         else:
#             base = "scenery"

#         # 3) Extra rules: romantic -> bias to woman, scenic -> bias to scenery
#         if any(k in m for k in romantic_moods):
#             base = "woman"
#         if any(k in m for k in scenic_moods):
#             base = "scenery"

#         # 4) Add controlled randomness
#         roll = random.random()
#         if base == "woman":
#             # ~70% woman, 15% car, 15% scenery
#             if roll < 0.7:
#                 return "woman"
#             elif roll < 0.85:
#                 return "car"
#             else:
#                 return "scenery"
#         elif base == "scenery":
#             # ~60% scenery, 25% woman, 15% car
#             if roll < 0.6:
#                 return "scenery"
#             elif roll < 0.85:
#                 return "woman"
#             else:
#                 return "car"
#         else:  # base == "car"
#             # ~60% car, 25% woman, 15% scenery
#             if roll < 0.6:
#                 return "car"
#             elif roll < 0.85:
#                 return "woman"
#             else:
#                 return "scenery"

#     def build_image_prompt(self, track_name: str, genre: str, mood: str) -> str:
#         """
#         Build a comprehensive prompt based on track name, genre, and mood.
#         """
#         # Genre-specific visual elements
#         genre_visuals = {
#             "hiphop": "urban street photography, city nights, graffiti walls, studio lights",
#             "trap": "dark urban scenes, neon signs, luxury cars, nighttime cityscapes",
#             "lofi": "cozy room aesthetics, vinyl records, warm lighting, rainy windows, vintage equipment",
#             "edm": "vibrant neon lights, futuristic clubs, laser shows, colorful energy",
#             "house": "dance floor lights, DJ equipment, crowd silhouettes, vibrant atmosphere",
#             "techno": "industrial spaces, minimal lighting, geometric patterns, dark clubs",
#             "rock": "concert venues, electric guitars, stage lighting, raw energy",
#             "metal": "dark industrial settings, dramatic lighting, intense atmosphere",
#             "jazz": "dimly lit jazz clubs, saxophones, warm ambient lighting, intimate venues",
#             "classical": "concert halls, orchestral instruments, elegant spaces, dramatic lighting",
#             "pop": "colorful modern aesthetics, bright lights, contemporary settings",
#             "rnb": "smooth lighting, urban luxury, modern aesthetics, intimate settings",
#             "soul": "vintage aesthetics, warm tones, vinyl culture, retro vibes",
#             "ambient": "abstract landscapes, ethereal lighting, peaceful nature, minimalist spaces",
#             "electronic": "futuristic elements, synthesizer aesthetics, neon colors, modern tech",
#             "indie": "artistic spaces, natural lighting, creative environments, authentic vibes",
#             "folk": "natural settings, acoustic instruments, warm earthy tones, outdoor scenes",
#             "reggae": "tropical vibes, sunset colors, beach scenes, relaxed atmosphere",
#             "country": "rural landscapes, wooden textures, warm sunlight, americana aesthetics",
#             "blues": "vintage bars, old guitars, moody lighting, soulful atmosphere",
#             "afrobeats": "sunset cityscapes, palm trees, warm golden light, street dance, tropical energy",
#         }

#         # Mood-specific visual characteristics
#         mood_visuals = {
#             "energetic": "dynamic motion, vibrant colors, high contrast, explosive energy, fast movement",
#             "calm": "soft lighting, peaceful scenes, gentle colors, serene atmosphere, still compositions",
#             "melancholic": "muted colors, rainy scenes, solitary subjects, introspective mood, soft shadows",
#             "dark": "deep shadows, noir aesthetics, dramatic contrast, mysterious atmosphere",
#             "uplifting": "bright sunlight, golden hour, optimistic colors, ascending compositions",
#             "aggressive": "sharp angles, intense contrasts, bold colors, powerful imagery",
#             "dreamy": "soft focus, ethereal lighting, pastel tones, floating elements, surreal touches",
#             "nostalgic": "vintage filters, retro aesthetics, warm tones, timeless quality",
#             "mysterious": "fog, shadows, hidden elements, dramatic lighting, enigmatic subjects",
#             "romantic": "soft lighting, intimate settings, warm colors, emotional depth",
#             "intense": "dramatic lighting, powerful contrasts, bold compositions, striking visuals",
#             "peaceful": "nature scenes, soft colors, balanced composition, tranquil settings",
#             "sad": "overcast skies, muted palettes, empty spaces, solitary mood",
#             "happy": "bright colors, sunny scenes, joyful elements, positive energy",
#             "chill": "relaxed settings, comfortable spaces, easy-going vibes, laid-back atmosphere",
#         }

#         genre_lower = genre.lower()
#         mood_lower = mood.lower()

#         genre_visual = genre_visuals.get(genre_lower, "modern music aesthetics, creative atmosphere")
#         mood_visual = mood_visuals.get(mood_lower, "balanced composition, professional photography")

#         # Fuzzy mood match
#         if mood_visual == "balanced composition, professional photography":
#             for key in mood_visuals:
#                 if key in mood_lower:
#                     mood_visual = mood_visuals[key]
#                     break

#         # Decide subject automatically
#         visual_focus = self.choose_visual_focus(track_name, genre, mood)

#         if visual_focus == "woman":
#             woman_env_options = [
#                 "soft bokeh city lights in the background",
#                 "a neon-lit night street with blurred traffic lights",
#                 "a cozy indoor studio with dramatic shadows and rim lighting",
#                 "a dreamy, glowing sky with soft, abstract light shapes",
#                 "a sunset-lit balcony overlooking a distant city",
#                 "a minimal dark background with subtle colored light gradients",
#             ]
#             env_desc = random.choice(woman_env_options)

#             subject_block = (
#                 "primary subject: an elegant, stylish adult woman, tastefully dressed, "
#                 "close-up or mid-shot, with beautiful makeup and expressive eyes, "
#                 f"{env_desc}, cinematic and aesthetically pleasing, clearly non-explicit."
#             )

#         elif visual_focus == "car":
#             subject_block = (
#                 "primary subject: a luxury sports car with sleek curves, glossy reflections and dramatic lighting, "
#                 "no visible real-world brand logos, placed in a cinematic environment that matches the music mood."
#             )
#         else:  # scenery
#             subject_block = (
#                 "primary subject: a breathtaking cinematic scenery such as heavenly skies, glowing clouds, "
#                 "sunset cityscapes or magical landscapes, with deep depth-of-field and strong atmosphere."
#             )

#         prompt = f"""
# Photorealistic, highly detailed, professional album artwork.

# Music genre: {genre}
# Track mood: {mood}
# Track name inspiration: "{track_name}"

# Visual style: {genre_visual}
# Mood atmosphere: {mood_visual}
# {subject_block}

# Create a stunning album cover that captures the essence of this {genre} track with a {mood} mood.
# The image should be cinematically composed, with professional lighting and realistic textures.
# Focus on creating an atmospheric scene that visually represents the emotional tone of the music.

# IMPORTANT:
# - NO text, NO words, NO letters, NO logos anywhere in the image
# - No explicit or pornographic content, tasteful and classy only
# - Photorealistic or cinematic style (no flat cartoons)
# - Square composition suitable for album artwork
# - Rich details and textures
# """.strip()
#         return prompt

#     def resize_and_crop_to_16_9(self, image: Image.Image, target_size=(1920, 1080)) -> Image.Image:
#         """
#         Resize and center-crop to 16:9 without stretching.
#         """
#         target_w, target_h = target_size
#         src_w, src_h = image.size

#         # Compute scale preserving aspect ratio
#         scale = max(target_w / src_w, target_h / src_h)
#         new_size = (int(src_w * scale), int(src_h * scale))

#         # Resize with correct ratio
#         image = image.resize(new_size, Image.LANCZOS)

#         # Center crop
#         left = (image.width - target_w) // 2
#         top = (image.height - target_h) // 2
#         right = left + target_w
#         bottom = top + target_h

#         return image.crop((left, top, right, bottom))

#     def generate_thumbnail(
#         self,
#         track_name: str,
#         genre: str,
#         mood: str,
#         size_preset: str = "square",
#         output_path: str = None
#     ) -> Dict:
#         """
#         Generate thumbnail using OpenAI's image model.
#         Returns dictionary with path and metadata.
#         """
#         if not self.api_key:
#             raise ValueError("OpenAI API key is missing")

#         logger.info(f"Generating thumbnail for '{track_name}' ({genre}, {mood})")
        
#         # Build prompt
#         image_prompt = self.build_image_prompt(track_name, genre, mood)
        
#         # Determine base size (OpenAI DALL-E 3 supports specific sizes)
#         # We'll use a standard high-res size and then resize
#         base_size = "1024x1024"
#         if size_preset in ["youtube", "youtube_max"]:
#              # DALL-E 3 supports 1792x1024 for landscape
#              base_size = "1024x1024" # Stick to square for consistency unless model supports landscape natively well
        
#         try:
#             logger.info("Calling OpenAI API...")
#             response = self.client.images.generate(
#                 model=self.image_model,
#                 prompt=image_prompt,
#                 size=base_size,
#                 n=1,
#                 # response_format="b64_json"
#             )

#             b64_data = response.data[0].b64_json
#             img_bytes = base64.b64decode(b64_data)
#             image = Image.open(BytesIO(img_bytes)).convert("RGB")

#             # Resize to target thumbnail size

#             # Always resize to cinematic 16:9 — 1920×1080
#             target_width, target_height = (1920, 1080)
#             logger.info("Resizing and cropping to 16:9 (1920×1080)")
#             image = self.resize_and_crop_to_16_9(image, (target_width, target_height))

#             # target_width, target_height = self.thumbnail_sizes.get(size_preset, self.thumbnail_sizes["square"])
            
#             # if image.size != (target_width, target_height):
#             #     logger.info(f"Resizing to {target_width}x{target_height}...")
#             #     if size_preset in ["youtube", "youtube_max"]:
#             #         image = self.resize_and_crop_to_16_9(image, (target_width, target_height))
#             #     else:
#             #         image = image.resize((target_width, target_height), Image.LANCZOS)

#             # Save to file
#             if output_path:
#                 out = Path(output_path)
#                 out.parent.mkdir(parents=True, exist_ok=True)
#                 image.save(out, format="PNG", quality=95, optimize=True)
#                 logger.info(f"Thumbnail saved to {out}")
#                 return {
#                     "path": str(out),
#                     "width": target_width,
#                     "height": target_height,
#                     "prompt": image_prompt
#                 }
            
#             return {
#                 "image": image,
#                 "width": 1920,
#                 "height": 1080,
#                 # "width": target_width,
#                 # "height": target_height,
#                 "prompt": image_prompt
#             }

#         except Exception as e:
#             logger.error(f"Error generating thumbnail: {e}")
#             raise
import os
import base64
import random
import logging
from io import BytesIO
from typing import Dict
from pathlib import Path

from openai import OpenAI
from PIL import Image

logger = logging.getLogger(__name__)

class ThumbnailService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY missing")
        self.client = OpenAI(api_key=self.api_key)
        self.image_model = "gpt-image-1"
    def choose_visual_focus(self, track_name: str, genre: str, mood: str) -> str:
        """
        Choose visual focus: 'woman' (most common), 'car' (common), 'man' (very rare), or 'scenery'
        Client preference: Woman > Car > Scenery > Man (rare)
        """
        t = track_name.lower()
        g = genre.lower()
        m = mood.lower()

        car_keywords = [
            "drive", "drift", "race", "racer", "turbo", "engine",
            "highway", "midnight ride", "fast lane", "street run", "night ride"
        ]

        romantic_moods = [
            "romantic", "love", "heartfelt", "sensual", "soft", "sweet",
            "late night", "midnight love", "slow jam", "intimate"
        ]

        scenic_moods = [
            "chill", "peaceful", "calm", "ambient", "dreamy", "nostalgic",
            "sunset", "sunrise", "island", "ocean", "sky", "heavenly"
        ]

        # Strong rule: car keywords → always car
        if any(k in t for k in car_keywords):
            return "car"

        # Base decision by genre/mood (prefer woman over scenery)
        if g in ["trap", "hiphop", "rap", "phonk", "drill", "edm", "house", "techno"]:
            base = "woman"  # Default to woman for these genres
        elif g in ["rnb", "soul", "afrobeats", "pop", "kpop", "latin"]:
            base = "woman"  # Always woman for romantic/pop genres
        elif g in ["ambient", "lofi", "classical", "cinematic", "soundtrack"]:
            base = "scenery"  # Scenery for calm genres
        else:
            base = "woman"  # Default to woman

        # Mood overrides
        if any(k in m for k in romantic_moods):
            base = "woman"
        if any(k in m for k in scenic_moods):
            base = "scenery"

        # Controlled randomness with client preferences
        # Woman: 60%, Car: 30%, Scenery: 8%, Man: 2%
        import random
        roll = random.random()
        
        if base == "woman":
            # 70% woman, 20% car, 8% scenery, 2% man
            if roll < 0.70:
                return "woman"
            elif roll < 0.90:
                return "car"
            elif roll < 0.98:
                return "scenery"
            else:
                return "man"  # Very rare
                
        elif base == "scenery":
            # 50% scenery, 30% woman, 15% car, 5% man
            if roll < 0.50:
                return "scenery"
            elif roll < 0.80:
                return "woman"
            elif roll < 0.95:
                return "car"
            else:
                return "man"  # Rare
                
        else:  # base == "car"
            # 60% car, 30% woman, 8% scenery, 2% man
            if roll < 0.60:
                return "car"
            elif roll < 0.90:
                return "woman"
            elif roll < 0.98:
                return "scenery"
            else:
                return "man"  # Very rare


    def resize_and_crop_to_16_9(self, image: Image.Image, target_size=(1920, 1080)) -> Image.Image:
        """
        Resize and crop to 16:9 without stretching.
        Maintains aspect ratio and crops excess.
        """
        target_w, target_h = target_size
        src_w, src_h = image.size
        
        logger.info(f"Original size: {src_w}×{src_h}")
        
        # Calculate target aspect ratio
        target_ratio = target_w / target_h  # 16:9 = 1.777...
        src_ratio = src_w / src_h
        
        logger.info(f"Source ratio: {src_ratio:.3f}, Target ratio: {target_ratio:.3f}")
        
        # Scale to cover the target size (no stretching)
        if src_ratio > target_ratio:
            # Source is wider - fit to height
            scale = target_h / src_h
        else:
            # Source is taller - fit to width
            scale = target_w / src_w
        
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        
        logger.info(f"Scaling by {scale:.3f} to {new_w}×{new_h}")
        
        # Resize maintaining aspect ratio (no stretching!)
        image = image.resize((new_w, new_h), Image.LANCZOS)
        
        # Center crop to exact target size
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        right = left + target_w
        bottom = top + target_h
        
        logger.info(f"Cropping from ({left}, {top}) to ({right}, {bottom})")
        
        return image.crop((left, top, right, bottom))

    def build_image_prompt(self, track_name: str, genre: str, mood: str, visual_focus: str = "woman") -> str:
        """
        Build image prompt based on visual focus (woman, man, car, or scenery)
        """
        # Base style for all images
        base_style = f"""
Cinematic, extremely detailed photorealistic YouTube thumbnail.
Track name: "{track_name}"
Genre: {genre}
Mood: {mood}

High contrast, dramatic lighting, rich colors, sharp details.
Professional photography, artistic aesthetic.
16:9 landscape composition suitable for YouTube thumbnail.
"""

        # Subject-specific descriptions
        if visual_focus == "woman":
            subject = """
Primary subject: An elegant, stylish adult woman, tastefully dressed,
close-up or mid-shot, with beautiful makeup and expressive eyes.
Cinematic environment with soft bokeh city lights or neon-lit street in background.
Clearly non-explicit, classy and professional.
"""
        elif visual_focus == "man":
            subject = """
Primary subject: A stylish adult man, well-dressed in modern fashion,
close-up or mid-shot, with confident expression and strong presence.
Cinematic urban environment with dramatic lighting.
Professional and artistic composition.
"""
        elif visual_focus == "car":
            subject = """
Primary subject: A luxury sports car with sleek curves, glossy reflections and dramatic lighting.
No visible real-world brand logos.
Cinematic environment that matches the music mood (city night, highway, etc).
"""
        else:  # scenery
            subject = """
Primary subject: Breathtaking cinematic scenery such as heavenly skies, glowing clouds,
sunset cityscapes or magical landscapes.
Deep depth-of-field and strong atmosphere.
"""

        return f"""{base_style.strip()}

{subject.strip()}

IMPORTANT:
- Do NOT include any text, letters, watermarks, logos or typography
- No nudity or explicit content
- Photorealistic style with cinematic composition
        """.strip()

    def generate_thumbnail(self, track_name: str, genre: str, mood: str, output_path: str = None) -> Dict:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is missing")

        # Determine visual focus first
        visual_focus = self.choose_visual_focus(track_name, genre, mood)
        logger.info(f"Visual focus chosen: {visual_focus}")

        # Build prompt with visual focus
        prompt = self.build_image_prompt(track_name, genre, mood, visual_focus)
        base_size = "1536x1024"  # Landscape format

        logger.info("Calling OpenAI to generate image...")
        response = self.client.images.generate(
            model=self.image_model,
            prompt=prompt,
            size=base_size,
            n=1
        )

        b64_data = response.data[0].b64_json
        img_bytes = base64.b64decode(b64_data)
        image = Image.open(BytesIO(img_bytes)).convert("RGB")

        logger.info("Cropping to 16:9 (1920×1080)")
        image = self.resize_and_crop_to_16_9(image, (1920, 1080))

        # Save final PNG (no text overlay)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, format="PNG", quality=95, optimize=True)

        return {
            "path": str(out),
            "width": 1920,
            "height": 1080,
            "prompt": prompt
        }

        # image = Image.open(BytesIO(img_bytes)).convert("RGB")

        # logger.info("Cropping to cinematic 16:9 (1920×1080)")
        # image = self.resize_and_crop_to_16_9(image)

        # out = Path(output_path)
        # out.parent.mkdir(parents=True, exist_ok=True)
        # image.save(out, format="PNG", quality=95, optimize=True)

        return {
            "path": str(out),
            "width": 1920,
            "height": 1080,
            "prompt": prompt
        }
