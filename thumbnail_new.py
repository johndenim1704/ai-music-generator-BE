# import os
# import base64
# from pathlib import Path
# from io import BytesIO

# from openai import OpenAI
# from dotenv import load_dotenv
# from PIL import Image

# load_dotenv()

# # -------------------------
# # CONFIG
# # -------------------------

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# IMAGE_MODEL = "gpt-image-1"

# # Standard thumbnail sizes
# THUMBNAIL_SIZES = {
#     "youtube": (1280, 720),      # 16:9 HD
#     "youtube_max": (1920, 1080), # 16:9 Full HD
#     "square": (1080, 1080),      # Instagram/Spotify square
#     "spotify": (640, 640),       # Spotify cover
#     "soundcloud": (800, 800),    # SoundCloud
# }

# # -------------------------
# # PROMPT GENERATION
# # -------------------------

# def build_image_prompt(track_name: str, genre: str, mood: str) -> str:
#     """
#     Build a comprehensive prompt for gpt-image-1 based on track name, genre, and mood.
#     """
#     # Genre-specific visual elements
#     genre_visuals = {
#         "hiphop": "urban street photography, city nights, graffiti walls, studio lights",
#         "trap": "dark urban scenes, neon signs, luxury cars, nighttime cityscapes",
#         "lofi": "cozy room aesthetics, vinyl records, warm lighting, rainy windows, vintage equipment",
#         "edm": "vibrant neon lights, futuristic clubs, laser shows, colorful energy",
#         "house": "dance floor lights, DJ equipment, crowd silhouettes, vibrant atmosphere",
#         "techno": "industrial spaces, minimal lighting, geometric patterns, dark clubs",
#         "rock": "concert venues, electric guitars, stage lighting, raw energy",
#         "metal": "dark industrial settings, dramatic lighting, intense atmosphere",
#         "jazz": "dimly lit jazz clubs, saxophones, warm ambient lighting, intimate venues",
#         "classical": "concert halls, orchestral instruments, elegant spaces, dramatic lighting",
#         "pop": "colorful modern aesthetics, bright lights, contemporary settings",
#         "rnb": "smooth lighting, urban luxury, modern aesthetics, intimate settings",
#         "soul": "vintage aesthetics, warm tones, vinyl culture, retro vibes",
#         "ambient": "abstract landscapes, ethereal lighting, peaceful nature, minimalist spaces",
#         "electronic": "futuristic elements, synthesizer aesthetics, neon colors, modern tech",
#         "indie": "artistic spaces, natural lighting, creative environments, authentic vibes",
#         "folk": "natural settings, acoustic instruments, warm earthy tones, outdoor scenes",
#         "reggae": "tropical vibes, sunset colors, beach scenes, relaxed atmosphere",
#         "country": "rural landscapes, wooden textures, warm sunlight, americana aesthetics",
#         "blues": "vintage bars, old guitars, moody lighting, soulful atmosphere",
#         "afrobeats": "sunset cityscapes, palm trees, warm golden light, street dance, tropical energy",
#     }

#     # Mood-specific visual characteristics
#     mood_visuals = {
#         "energetic": "dynamic motion, vibrant colors, high contrast, explosive energy, fast movement",
#         "calm": "soft lighting, peaceful scenes, gentle colors, serene atmosphere, still compositions",
#         "melancholic": "muted colors, rainy scenes, solitary subjects, introspective mood, soft shadows",
#         "dark": "deep shadows, noir aesthetics, dramatic contrast, mysterious atmosphere",
#         "uplifting": "bright sunlight, golden hour, optimistic colors, ascending compositions",
#         "aggressive": "sharp angles, intense contrasts, bold colors, powerful imagery",
#         "dreamy": "soft focus, ethereal lighting, pastel tones, floating elements, surreal touches",
#         "nostalgic": "vintage filters, retro aesthetics, warm tones, timeless quality",
#         "mysterious": "fog, shadows, hidden elements, dramatic lighting, enigmatic subjects",
#         "romantic": "soft lighting, intimate settings, warm colors, emotional depth",
#         "intense": "dramatic lighting, powerful contrasts, bold compositions, striking visuals",
#         "peaceful": "nature scenes, soft colors, balanced composition, tranquil settings",
#         "sad": "overcast skies, muted palettes, empty spaces, solitary mood",
#         "happy": "bright colors, sunny scenes, joyful elements, positive energy",
#         "chill": "relaxed settings, comfortable spaces, easy-going vibes, laid-back atmosphere",
#     }

#     genre_lower = genre.lower()
#     mood_lower = mood.lower()

#     genre_visual = genre_visuals.get(genre_lower, "modern music aesthetics, creative atmosphere")
#     mood_visual = mood_visuals.get(mood_lower, "balanced composition, professional photography")

#     # Fuzzy mood match if no direct key
#     if mood_visual == "balanced composition, professional photography":
#         for key in mood_visuals:
#             if key in mood_lower:
#                 mood_visual = mood_visuals[key]
#                 break

#     prompt = f"""
# Photorealistic, highly detailed, professional album artwork.

# Music genre: {genre}
# Track mood: {mood}
# Track name inspiration: "{track_name}"

# Visual style: {genre_visual}
# Mood atmosphere: {mood_visual}

# Create a stunning album cover that captures the essence of this {genre} track with a {mood} mood.
# The image should be cinematically composed, with professional lighting and realistic textures.
# Focus on creating an atmospheric scene that visually represents the emotional tone of the music.

# IMPORTANT:
# - NO text, NO words, NO letters, NO logos anywhere in the image
# - Photorealistic or cinematic style (no flat cartoons)
# - Square composition suitable for album artwork
# - Rich details and textures
# """.strip()

#     return prompt


# # -------------------------
# # IMAGE GENERATION WITH gpt-image-1
# # -------------------------

# def generate_thumbnail_gpt_image(
#     track_name: str,
#     genre: str,
#     mood: str,
#     size_preset: str = "square",
#     out_path: str = "thumbnail.png",
#     quality: str = "hd",   # kept for UX, not directly used by API
# ) -> str:
#     """
#     Generate thumbnail using OpenAI's gpt-image-1 model.
#     Args match how main() calls this.
#     """

#     print("\n" + "=" * 60)
#     print("GENERATING THUMBNAIL WITH gpt-image-1")
#     print("=" * 60)

#     # 1) Build prompt from track + genre + mood
#     print("\n🎨 Building image prompt...")
#     image_prompt = build_image_prompt(track_name, genre, mood)

#     print("\n📝 Prompt:")
#     print("-" * 60)
#     print(image_prompt)
#     print("-" * 60)

#     # 2) Generate base 1024x1024 image, then resize to target
#     base_size = "1024x1024"
#     print(f"\n🖼️  Generating image with gpt-image-1...")
#     print(f"   Base size: {base_size}")
#     print("   This may take a bit...\n")

#     try:
#         response = client.images.generate(
#             model=IMAGE_MODEL,
#             prompt=image_prompt,
#             size=base_size,
#             n=1,
#         )

#         # ✅ Correct field for the current Images API: b64_json
#         b64_data = response.data[0].b64_json
#         img_bytes = base64.b64decode(b64_data)
#         image = Image.open(BytesIO(img_bytes)).convert("RGB")

#         print(f"✅ Image generated successfully at base size {image.size[0]}x{image.size[1]}")

#         # 3) Resize to target thumbnail size
#         target_width, target_height = THUMBNAIL_SIZES.get(size_preset, THUMBNAIL_SIZES["square"])
#         if image.size != (target_width, target_height):
#             print(f"📐 Resizing to {target_width}x{target_height}...")
#             image = image.resize((target_width, target_height), Image.LANCZOS)

#         # 4) Save
#         out = Path(out_path)
#         out.parent.mkdir(parents=True, exist_ok=True)
#         image.save(out, format="PNG", quality=100, optimize=True)

#         print(f"\n✅ Thumbnail saved: {out}")
#         print(f"   Final size: {target_width}x{target_height} pixels")

#         return str(out)

#     except Exception as e:
#         print(f"\n❌ Error generating image: {e}")
#         raise


# # -------------------------
# # MAIN WORKFLOW
# # -------------------------

# def main():
#     print("\n" + "=" * 60)
#     print("🎵 AI MUSIC THUMBNAIL GENERATOR (gpt-image-1)")
#     print("=" * 60)
#     print("\nGenerate photorealistic album artwork using OpenAI's gpt-image-1")
#     print("Based on track name, genre, and mood")
#     print("=" * 60)

#     if not os.getenv("OPENAI_API_KEY"):
#         print("\n❌ Error: OPENAI_API_KEY not found in environment variables")
#         print("   Please set it in your .env file or environment")
#         return

#     # STEP 1: INPUT
#     print("\n" + "=" * 60)
#     print("STEP 1: INPUT INFORMATION")
#     print("=" * 60)

#     track_name = input("\n🎵 Enter track name: ").strip()
#     if not track_name:
#         print("❌ Track name is required!")
#         return

#     genre = input("🎸 Enter genre (e.g., lofi, hiphop, afrobeats, edm, rock, jazz): ").strip()
#     if not genre:
#         genre = "electronic"
#         print(f"   Using default genre: {genre}")

#     print("\n💭 Enter the mood of your track.")
#     print("   Examples: energetic, calm, melancholic, dark, uplifting, dreamy,")
#     print("             aggressive, nostalgic, chill, intense, vibey, island vibes")

#     mood = input("\n💭 Mood: ").strip()
#     if not mood:
#         mood = "balanced"
#         print(f"   Using default mood: {mood}")

#     # STEP 2: SIZE
#     print("\n" + "=" * 60)
#     print("STEP 2: CHOOSE THUMBNAIL SIZE")
#     print("=" * 60)

#     print("\n📐 Available thumbnail sizes:")
#     print("1. Square (1080x1080) - Instagram, Spotify, Apple Music")
#     print("2. YouTube HD (1280x720)")
#     print("3. YouTube Full HD (1920x1080)")
#     print("4. Spotify Cover (640x640)")
#     print("5. SoundCloud (800x800)")

#     size_choice = input("\nChoose size (1-5, default: 1): ").strip() or "1"
#     size_map = {
#         "1": "square",
#         "2": "youtube",
#         "3": "youtube_max",
#         "4": "spotify",
#         "5": "soundcloud"
#     }
#     size_preset = size_map.get(size_choice, "square")

#     # STEP 3: QUALITY (UX only)
#     print("\n" + "=" * 60)
#     print("STEP 3: CHOOSE QUALITY (hint)")
#     print("=" * 60)

#     print("\n✨ Quality options:")
#     print("1. HD - Higher quality, more detailed (recommended)")
#     print("2. Standard - Conceptually lower cost (not enforced by API)")

#     quality_choice = input("\nChoose quality (1-2, default: 1): ").strip() or "1"
#     quality = "hd" if quality_choice == "1" else "standard"

#     # STEP 4: SUMMARY
#     print("\n" + "=" * 60)
#     print("STEP 4: SUMMARY")
#     print("=" * 60)

#     print(f"\n📋 Generation Summary:")
#     print(f"   Track: {track_name}")
#     print(f"   Genre: {genre}")
#     print(f"   Mood: {mood}")
#     print(f"   Size: {THUMBNAIL_SIZES[size_preset][0]}x{THUMBNAIL_SIZES[size_preset][1]}")
#     print(f"   Quality hint: {quality.upper()}")

#     proceed = input("\n▶️  Generate thumbnail? (y/n, default: y): ").strip().lower()
#     if proceed and proceed != "y":
#         print("❌ Generation cancelled")
#         return

#     output_file = input("\n💾 Output filename (default: thumbnail.png): ").strip()
#     output_file = output_file or "thumbnail.png"

#     try:
#         generate_thumbnail_gpt_image(
#             track_name=track_name,
#             genre=genre,
#             mood=mood,
#             size_preset=size_preset,
#             out_path=output_file,
#             quality=quality,
#         )

#         print("\n" + "=" * 60)
#         print("🎉 SUCCESS! Your thumbnail is ready!")
#         print("=" * 60)
#         print(f"\n📁 Saved to: {output_file}")
#         print("✨ No text overlay - pure visual artwork")
#         print("\n💡 Tip: You can later add text overlays with your own typography pipeline.")
#         print("=" * 60 + "\n")

#     except Exception as e:
#         print(f"\n❌ Failed to generate thumbnail: {e}")
#         print("\nPlease check:")
#         print("- Your OPENAI_API_KEY is valid and has access to gpt-image-1")
#         print("- You have API credits/limits available")
#         print("- Your internet connection is stable")


# if __name__ == "__main__":
#     main()


import os
import base64
from pathlib import Path
from io import BytesIO
import random

from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# -------------------------
# CONFIG
# -------------------------

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

IMAGE_MODEL = "gpt-image-1"

# Standard thumbnail sizes
THUMBNAIL_SIZES = {
    "youtube": (1280, 720),      # 16:9 HD
    "youtube_max": (1920, 1080), # 16:9 Full HD
    "square": (1080, 1080),      # Instagram/Spotify square
    "spotify": (640, 640),       # Spotify cover
    "soundcloud": (800, 800),    # SoundCloud
}

# -------------------------
# SUBJECT SELECTION LOGIC
# -------------------------

def choose_visual_focus(track_name: str, genre: str, mood: str) -> str:
    """
    Automatically choose visual focus: 'woman', 'car', or 'scenery'
    based on genre, mood and track name, with some randomness so it's
    not always the same subject type.
    """
    t = track_name.lower()
    g = genre.lower()
    m = mood.lower()

    # Keywords hinting strongly at cars / driving
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

    # 1) If track explicitly about driving / racing → car (strong rule)
    if any(k in t for k in car_keywords):
        return "car"

    # 2) Base decision by genre/mood
    if g in ["trap", "hiphop", "rap", "phonk", "drill", "edm", "house", "techno"]:
        if any(k in m for k in ["energetic", "intense", "aggressive", "club"]):
            base = "woman"
        else:
            base = "scenery"
    elif g in ["rnb", "soul", "afrobeats", "pop", "kpop", "latin"]:
        if any(k in m for k in romantic_moods) or "happy" in m or "uplifting" in m:
            base = "woman"
        else:
            base = "scenery"
    elif g in ["ambient", "lofi", "classical", "cinematic", "soundtrack"]:
        base = "scenery"
    else:
        base = "scenery"

    # 3) Extra rules: romantic → bias to woman, scenic → bias to scenery
    if any(k in m for k in romantic_moods):
        base = "woman"
    if any(k in m for k in scenic_moods):
        base = "scenery"

    # 4) Add controlled randomness so it's not always the same:
    # Mostly women, sometimes cars, sometimes scenery.
    roll = random.random()
    if base == "woman":
        # ~70% woman, 15% car, 15% scenery
        if roll < 0.7:
            return "woman"
        elif roll < 0.85:
            return "car"
        else:
            return "scenery"
    elif base == "scenery":
        # ~60% scenery, 25% woman, 15% car
        if roll < 0.6:
            return "scenery"
        elif roll < 0.85:
            return "woman"
        else:
            return "car"
    else:  # base == "car"
        # ~60% car, 25% woman, 15% scenery
        if roll < 0.6:
            return "car"
        elif roll < 0.85:
            return "woman"
        else:
            return "scenery"



# -------------------------
# PROMPT GENERATION
# -------------------------

def build_image_prompt(
    track_name: str,
    genre: str,
    mood: str,
) -> str:
    """
    Build a comprehensive prompt for gpt-image-1 based on track name, genre, and mood.
    Subject (woman/car/scenery) is auto-selected.
    """
    # Genre-specific visual elements
    genre_visuals = {
        "hiphop": "urban street photography, city nights, graffiti walls, studio lights",
        "trap": "dark urban scenes, neon signs, luxury cars, nighttime cityscapes",
        "lofi": "cozy room aesthetics, vinyl records, warm lighting, rainy windows, vintage equipment",
        "edm": "vibrant neon lights, futuristic clubs, laser shows, colorful energy",
        "house": "dance floor lights, DJ equipment, crowd silhouettes, vibrant atmosphere",
        "techno": "industrial spaces, minimal lighting, geometric patterns, dark clubs",
        "rock": "concert venues, electric guitars, stage lighting, raw energy",
        "metal": "dark industrial settings, dramatic lighting, intense atmosphere",
        "jazz": "dimly lit jazz clubs, saxophones, warm ambient lighting, intimate venues",
        "classical": "concert halls, orchestral instruments, elegant spaces, dramatic lighting",
        "pop": "colorful modern aesthetics, bright lights, contemporary settings",
        "rnb": "smooth lighting, urban luxury, modern aesthetics, intimate settings",
        "soul": "vintage aesthetics, warm tones, vinyl culture, retro vibes",
        "ambient": "abstract landscapes, ethereal lighting, peaceful nature, minimalist spaces",
        "electronic": "futuristic elements, synthesizer aesthetics, neon colors, modern tech",
        "indie": "artistic spaces, natural lighting, creative environments, authentic vibes",
        "folk": "natural settings, acoustic instruments, warm earthy tones, outdoor scenes",
        "reggae": "tropical vibes, sunset colors, beach scenes, relaxed atmosphere",
        "country": "rural landscapes, wooden textures, warm sunlight, americana aesthetics",
        "blues": "vintage bars, old guitars, moody lighting, soulful atmosphere",
        "afrobeats": "sunset cityscapes, palm trees, warm golden light, street dance, tropical energy",
    }

    # Mood-specific visual characteristics
    mood_visuals = {
        "energetic": "dynamic motion, vibrant colors, high contrast, explosive energy, fast movement",
        "calm": "soft lighting, peaceful scenes, gentle colors, serene atmosphere, still compositions",
        "melancholic": "muted colors, rainy scenes, solitary subjects, introspective mood, soft shadows",
        "dark": "deep shadows, noir aesthetics, dramatic contrast, mysterious atmosphere",
        "uplifting": "bright sunlight, golden hour, optimistic colors, ascending compositions",
        "aggressive": "sharp angles, intense contrasts, bold colors, powerful imagery",
        "dreamy": "soft focus, ethereal lighting, pastel tones, floating elements, surreal touches",
        "nostalgic": "vintage filters, retro aesthetics, warm tones, timeless quality",
        "mysterious": "fog, shadows, hidden elements, dramatic lighting, enigmatic subjects",
        "romantic": "soft lighting, intimate settings, warm colors, emotional depth",
        "intense": "dramatic lighting, powerful contrasts, bold compositions, striking visuals",
        "peaceful": "nature scenes, soft colors, balanced composition, tranquil settings",
        "sad": "overcast skies, muted palettes, empty spaces, solitary mood",
        "happy": "bright colors, sunny scenes, joyful elements, positive energy",
        "chill": "relaxed settings, comfortable spaces, easy-going vibes, laid-back atmosphere",
    }

    genre_lower = genre.lower()
    mood_lower = mood.lower()

    genre_visual = genre_visuals.get(genre_lower, "modern music aesthetics, creative atmosphere")
    mood_visual = mood_visuals.get(mood_lower, "balanced composition, professional photography")

    # Fuzzy mood match if no direct key
    if mood_visual == "balanced composition, professional photography":
        for key in mood_visuals:
            if key in mood_lower:
                mood_visual = mood_visuals[key]
                break

    # Decide subject automatically
    visual_focus = choose_visual_focus(track_name, genre, mood)

    if visual_focus == "woman":
    # Randomize the environment a bit so it's not always the same vibe
        woman_env_options = [
            "soft bokeh city lights in the background",
            "a neon-lit night street with blurred traffic lights",
            "a cozy indoor studio with dramatic shadows and rim lighting",
            "a dreamy, glowing sky with soft, abstract light shapes",
            "a sunset-lit balcony overlooking a distant city",
            "a minimal dark background with subtle colored light gradients",
        ]
        env_desc = random.choice(woman_env_options)

        subject_block = (
            "primary subject: an elegant, stylish adult woman, tastefully dressed, "
            "close-up or mid-shot, with beautiful makeup and expressive eyes, "
            f"{env_desc}, cinematic and aesthetically pleasing, clearly non-explicit."
        )

    elif visual_focus == "car":
        subject_block = (
            "primary subject: a luxury sports car with sleek curves, glossy reflections and dramatic lighting, "
            "no visible real-world brand logos, placed in a cinematic environment that matches the music mood."
        )
    else:  # scenery
        subject_block = (
            "primary subject: a breathtaking cinematic scenery such as heavenly skies, glowing clouds, "
            "sunset cityscapes or magical landscapes, with deep depth-of-field and strong atmosphere."
        )

    prompt = f"""
Photorealistic, highly detailed, professional album artwork.

Music genre: {genre}
Track mood: {mood}
Track name inspiration: "{track_name}"

Visual style: {genre_visual}
Mood atmosphere: {mood_visual}
{subject_block}

Create a stunning album cover that captures the essence of this {genre} track with a {mood} mood.
The image should be cinematically composed, with professional lighting and realistic textures.
Focus on creating an atmospheric scene that visually represents the emotional tone of the music.

IMPORTANT:
- NO text, NO words, NO letters, NO logos anywhere in the image
- No explicit or pornographic content, tasteful and classy only
- Photorealistic or cinematic style (no flat cartoons)
- Square composition suitable for album artwork
- Rich details and textures
""".strip()

    return prompt


# -------------------------
# IMAGE GENERATION WITH gpt-image-1
# -------------------------

def resize_and_crop_to_16_9(image: Image.Image, target_size=(1920, 1080)) -> Image.Image:
    """
    Resize and center-crop to 16:9 without stretching.
    """
    target_w, target_h = target_size
    src_w, src_h = image.size

    # Compute scale preserving aspect ratio
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (int(src_w * scale), int(src_h * scale))

    # Resize with correct ratio
    image = image.resize(new_size, Image.LANCZOS)

    # Center crop
    left = (image.width - target_w) // 2
    top = (image.height - target_h) // 2
    right = left + target_w
    bottom = top + target_h

    return image.crop((left, top, right, bottom))



def generate_thumbnail_gpt_image(
    track_name: str,
    genre: str,
    mood: str,
    size_preset: str = "square",
    out_path: str = "thumbnail.png",
    quality: str = "hd",   # UX only
) -> str:
    """
    Generate thumbnail using OpenAI's gpt-image-1 model.
    """

    print("\n" + "=" * 60)
    print("GENERATING THUMBNAIL WITH gpt-image-1")
    print("=" * 60)

    # 1) Build prompt
    print("\n🎨 Building image prompt...")
    image_prompt = build_image_prompt(track_name, genre, mood)

    print("\n📝 Prompt:")
    print("-" * 60)
    print(image_prompt)
    print("-" * 60)

    # base_size = "1024x1024"
    base_size = "1536x1024"  # Native 16:9 from OpenAI
    print(f"\n🖼️  Generating image with gpt-image-1...")
    print(f"   Base size: {base_size}")
    print("   This may take a bit...\n")

    try:
        response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=image_prompt,
            size=base_size,
            n=1,
        )

        b64_data = response.data[0].b64_json
        img_bytes = base64.b64decode(b64_data)
        image = Image.open(BytesIO(img_bytes)).convert("RGB")

        print(f"✅ Image generated successfully at base size {image.size[0]}x{image.size[1]}")

        # Resize to target thumbnail size
        target_width, target_height = THUMBNAIL_SIZES.get(size_preset, THUMBNAIL_SIZES["square"])
        if image.size != (target_width, target_height):
            print(f"📐 Resizing to {target_width}x{target_height}...")
            # image = image.resize((target_width, target_height), Image.LANCZOS)
            image = resize_and_crop_to_16_9(image, (target_width, target_height))


        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, format="PNG", quality=100, optimize=True)

        print(f"\n✅ Thumbnail saved: {out}")
        print(f"   Final size: {target_width}x{target_height} pixels")

        return str(out)

    except Exception as e:
        print(f"\n❌ Error generating image: {e}")
        raise


# -------------------------
# MAIN WORKFLOW
# -------------------------

def main():
    print("\n" + "=" * 60)
    print("🎵 AI MUSIC THUMBNAIL GENERATOR (gpt-image-1)")
    print("=" * 60)
    print("\nGenerate photorealistic album artwork using OpenAI's gpt-image-1")
    print("Based on track name, genre, and mood; subject auto-selected (woman / car / scenery)")
    print("=" * 60)

    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        return

    # STEP 1: INPUT
    print("\n" + "=" * 60)
    print("STEP 1: INPUT INFORMATION")
    print("=" * 60)

    track_name = input("\n🎵 Enter track name: ").strip()
    if not track_name:
        print("❌ Track name is required!")
        return

    genre = input("🎸 Enter genre (e.g., lofi, hiphop, afrobeats, edm, rock, jazz): ").strip()
    if not genre:
        genre = "electronic"
        print(f"   Using default genre: {genre}")

    print("\n💭 Enter the mood of your track.")
    print("   Examples: energetic, calm, melancholic, dark, uplifting, dreamy,")
    print("             aggressive, nostalgic, chill, intense, vibey, island vibes")

    mood = input("\n💭 Mood: ").strip()
    if not mood:
        mood = "balanced"
        print(f"   Using default mood: {mood}")

    # STEP 2: SIZE
    print("\n" + "=" * 60)
    print("STEP 2: CHOOSE THUMBNAIL SIZE")
    print("=" * 60)

    print("\n📐 Available thumbnail sizes:")
    print("1. Square (1080x1080) - Instagram, Spotify, Apple Music")
    print("2. YouTube HD (1280x720)")
    print("3. YouTube Full HD (1920x1080)")
    print("4. Spotify Cover (640x640)")
    print("5. SoundCloud (800x800)")

    size_choice = input("\nChoose size (1-5, default: 1): ").strip() or "1"
    size_map = {
        "1": "square",
        "2": "youtube",
        "3": "youtube_max",
        "4": "spotify",
        "5": "soundcloud"
    }
    size_preset = size_map.get(size_choice, "square")

    # STEP 3: QUALITY (UX hint)
    print("\n" + "=" * 60)
    print("STEP 3: CHOOSE QUALITY (hint)")
    print("=" * 60)

    print("\n✨ Quality options:")
    print("1. HD - Higher quality, more detailed (recommended)")
    print("2. Standard - Conceptually lower cost (not enforced by API)")

    quality_choice = input("\nChoose quality (1-2, default: 1): ").strip() or "1"
    quality = "hd" if quality_choice == "1" else "standard"

    # STEP 4: SUMMARY
    print("\n" + "=" * 60)
    print("STEP 4: SUMMARY")
    print("=" * 60)

    auto_focus = choose_visual_focus(track_name, genre, mood)

    print(f"\n📋 Generation Summary:")
    print(f"   Track: {track_name}")
    print(f"   Genre: {genre}")
    print(f"   Mood: {mood}")
    print(f"   Auto visual focus: {auto_focus}")
    print(f"   Size: {THUMBNAIL_SIZES[size_preset][0]}x{THUMBNAIL_SIZES[size_preset][1]}")
    print(f"   Quality hint: {quality.upper()}")

    proceed = input("\n▶️  Generate thumbnail? (y/n, default: y): ").strip().lower()
    if proceed and proceed != "y":
        print("❌ Generation cancelled")
        return

    output_file = input("\n💾 Output filename (default: thumbnail.png): ").strip()
    output_file = output_file or "thumbnail.png"

    try:
        generate_thumbnail_gpt_image(
            track_name=track_name,
            genre=genre,
            mood=mood,
            size_preset=size_preset,
            out_path=output_file,
            quality=quality,
        )

        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Your thumbnail is ready!")
        print("=" * 60)
        print(f"\n📁 Saved to: {output_file}")
        print("✨ No text overlay - pure visual artwork")
        print("\n💡 Tip: You can later add text overlays with your own typography pipeline.")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Failed to generate thumbnail: {e}")
        print("\nPlease check:")
        print("- Your OPENAI_API_KEY is valid and has access to gpt-image-1")
        print("- You have API credits/limits available")
        print("- Your internet connection is stable")


if __name__ == "__main__":
    main()


