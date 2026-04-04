
# import os
# import json
# from pathlib import Path

# import ollama
# from dotenv import load_dotenv
# import torch
# from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
# from PIL import Image, ImageDraw, ImageFont, ImageFilter
# import gc

# load_dotenv()  # reads .env file

# # -------------------------
# # CONFIG
# # -------------------------

# LLM_MODEL = "llama3.2:latest"   # local via Ollama
# IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"  # Lighter SD 1.5 model

# # Global pipeline instance (loaded once)
# pipe = None


# # -------------------------
# # LLM: prompt generation with Llama 3.2
# # -------------------------

# def build_llama_prompt(track_name: str, genre: str) -> str:
#     """
#     Build the instruction for Llama 3.2:
#     We want it to output a single JSON object with a 'prompt' string and 'text_style' object.
#     """
#     return f"""
# You are an album cover art designer and expert AI image prompt engineer.

# Your job:
# - Take a music track title and genre
# - Imagine the mood, atmosphere, visuals, and color palette
# - Write a SINGLE, strong image generation prompt for Stable Diffusion
# - Design text styling that will blend perfectly with the cover image

# Input:
# - Track name: "{track_name}"
# - Genre: {genre}
# - Assume the song is instrumental (no vocals).

# Requirements for the image prompt:
# - 1 sentence only, no line breaks.
# - Describe the mood and atmosphere implied by the title and genre.
# - Describe visual style (e.g. abstract, cinematic, neon, glitch, minimalist, anime, futuristic, retro, etc).
# - Mention a clear color palette (e.g. deep purples and blues, warm oranges, neon pink and cyan).
# - Mention some visual elements or composition (e.g. city at night, floating shapes, cosmic scene, street at dusk, abstract waves).
# - The background image MUST NOT contain any text, words, letters, logos, or typography.
# - Suitable for a square digital album cover.

# Requirements for text styling:
# - Choose a font style that matches the genre and mood (e.g. bold sans-serif, elegant serif, futuristic, handwritten, graffiti, retro, minimalist)
# - Choose a text color that contrasts well with the expected background
# - Choose a text position (top, center, bottom)
# - Optionally suggest effects like glow, shadow, or outline

# Output JSON ONLY in this form:

# {{
#   "prompt": "one single-sentence prompt for the image model",
#   "text_style": {{
#     "font_style": "bold modern sans-serif" or "elegant serif" or "retro" or "futuristic" or "graffiti",
#     "color": "white" or "black" or "neon cyan" or "gold" or specific hex like "#FF00FF",
#     "position": "top" or "center" or "bottom",
#     "effects": "glow" or "shadow" or "outline" or "none"
#   }}
# }}
# """


# def generate_image_prompt_with_llama(track_name: str, genre: str) -> tuple[str, dict]:
#     """
#     Call Llama 3.2 via Ollama and get back a prompt string and text styling info.
#     Returns: (image_prompt, text_style_dict)
#     """

#     prompt_text = build_llama_prompt(track_name, genre)

#     resp = ollama.chat(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": "You output JSON only."},
#             {"role": "user", "content": prompt_text},
#         ],
#         options={
#             "temperature": 0.5
#         },
#     )

#     content = resp["message"]["content"].strip()

#     # Try to parse JSON directly
#     try:
#         data = json.loads(content)
#     except json.JSONDecodeError:
#         # Fallback: extract JSON blob
#         start = content.find("{")
#         end = content.rfind("}") + 1
#         if start == -1 or end <= start:
#             raise ValueError(f"LLM did not return JSON:\n{content}")
#         json_str = content[start:end]
#         data = json.loads(json_str)

#     if "prompt" not in data:
#         raise ValueError(f"No 'prompt' key in LLM JSON:\n{data}")
    
#     # Extract text style, with defaults if not provided
#     text_style = data.get("text_style", {
#         "font_style": "bold sans-serif",
#         "color": "white",
#         "position": "center",
#         "effects": "shadow"
#     })

#     return data["prompt"], text_style


# # -------------------------
# # Text overlay with smart styling
# # -------------------------

# def get_font_path(style: str, size: int) -> ImageFont.FreeTypeFont:
#     """
#     Get the best matching font based on style description.
#     Falls back to system fonts on macOS.
#     """
#     style_lower = style.lower()
    
#     # macOS system fonts paths
#     font_paths = {
#         "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
#         "serif": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
#         "elegant": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
#         "modern": "/System/Library/Fonts/Supplemental/Arial.ttf",
#         "futuristic": "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
#         "retro": "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
#         "graffiti": "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
#         "handwritten": "/System/Library/Fonts/Supplemental/Brush Script.ttf",
#     }
    
#     # Try to match font style
#     for key, path in font_paths.items():
#         if key in style_lower and Path(path).exists():
#             try:
#                 return ImageFont.truetype(path, size)
#             except:
#                 pass
    
#     # Fallback to Helvetica (always available on macOS)
#     try:
#         return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
#     except:
#         # Ultimate fallback
#         return ImageFont.load_default()


# def parse_color(color_str: str) -> tuple:
#     """Convert color string to RGB tuple."""
#     color_lower = color_str.lower().strip()
    
#     # Common color names
#     colors = {
#         "white": (255, 255, 255),
#         "black": (0, 0, 0),
#         "red": (255, 0, 0),
#         "blue": (0, 100, 255),
#         "cyan": (0, 255, 255),
#         "neon cyan": (0, 255, 255),
#         "magenta": (255, 0, 255),
#         "yellow": (255, 255, 0),
#         "gold": (255, 215, 0),
#         "silver": (192, 192, 192),
#         "orange": (255, 165, 0),
#         "purple": (160, 32, 240),
#         "pink": (255, 105, 180),
#         "green": (0, 255, 0),
#     }
    
#     # Check if it's a known color
#     for name, rgb in colors.items():
#         if name in color_lower:
#             return rgb
    
#     # Try to parse hex color (#RRGGBB or #RGB)
#     if "#" in color_str:
#         hex_color = color_str.replace("#", "").strip()
#         if len(hex_color) == 6:
#             return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
#         elif len(hex_color) == 3:
#             return tuple(int(c*2, 16) for c in hex_color)
    
#     # Default to white
#     return (255, 255, 255)


# def add_text_to_image(
#     image: Image.Image,
#     text: str,
#     text_style: dict,
# ) -> Image.Image:
#     """
#     Add styled text overlay to the generated image.
    
#     Args:
#         image: PIL Image to add text to
#         text: The text to add (track name)
#         text_style: Dictionary with font_style, color, position, effects
    
#     Returns:
#         PIL Image with text overlay
#     """
#     img_width, img_height = image.size
    
#     # Create a copy to work with
#     img_with_text = image.copy()
    
#     # Determine font size based on image size and text length
#     base_size = img_width // 10  # Adjusted for 512x512
#     font_size = max(30, min(base_size, img_width // (len(text) // 2 + 1)))
    
#     # Get font
#     font_style_str = text_style.get("font_style", "bold sans-serif")
#     font = get_font_path(font_style_str, font_size)
    
#     # Parse color
#     text_color = parse_color(text_style.get("color", "white"))
    
#     # Create drawing context
#     draw = ImageDraw.Draw(img_with_text)
    
#     # Get text bounding box
#     bbox = draw.textbbox((0, 0), text, font=font)
#     text_width = bbox[2] - bbox[0]
#     text_height = bbox[3] - bbox[1]
    
#     # Determine position
#     position = text_style.get("position", "center").lower()
#     margin = img_height // 10
    
#     if position == "top":
#         x = (img_width - text_width) // 2
#         y = margin
#     elif position == "bottom":
#         x = (img_width - text_width) // 2
#         y = img_height - text_height - margin
#     else:  # center
#         x = (img_width - text_width) // 2
#         y = (img_height - text_height) // 2
    
#     # Apply effects
#     effects = text_style.get("effects", "shadow").lower()
    
#     if "glow" in effects:
#         # Create glow effect
#         glow_img = Image.new("RGBA", img_with_text.size, (0, 0, 0, 0))
#         glow_draw = ImageDraw.Draw(glow_img)
        
#         # Draw multiple layers for glow
#         for offset in range(6, 0, -2):
#             alpha = int(255 * (offset / 6) * 0.5)
#             glow_color = text_color + (alpha,)
#             for dx in range(-offset, offset+1):
#                 for dy in range(-offset, offset+1):
#                     glow_draw.text((x + dx, y + dy), text, font=font, fill=glow_color)
        
#         # Blur the glow
#         glow_img = glow_img.filter(ImageFilter.GaussianBlur(4))
#         img_with_text = Image.alpha_composite(img_with_text.convert("RGBA"), glow_img).convert("RGB")
#         draw = ImageDraw.Draw(img_with_text)
    
#     if "shadow" in effects:
#         # Add shadow
#         shadow_color = (0, 0, 0) if sum(text_color) > 384 else (255, 255, 255)
#         shadow_offset = max(2, font_size // 20)
#         draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    
#     if "outline" in effects:
#         # Add outline
#         outline_color = (0, 0, 0) if sum(text_color) > 384 else (255, 255, 255)
#         outline_width = max(2, font_size // 30)
#         for dx in range(-outline_width, outline_width+1):
#             for dy in range(-outline_width, outline_width+1):
#                 if dx != 0 or dy != 0:
#                     draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    
#     # Draw main text
#     draw.text((x, y), text, font=font, fill=text_color)
    
#     return img_with_text


# # -------------------------
# # Image generation: Stable Diffusion 1.5 (Lighter!)
# # -------------------------

# def load_sd_pipeline():
#     """
#     Load SD 1.5 pipeline - much lighter than SDXL.
#     Uses only ~2GB RAM vs SDXL's ~7GB.
#     """
#     global pipe
    
#     if pipe is not None:
#         return pipe
    
#     print("\n🔄 Loading Stable Diffusion 1.5 model...")
#     print("   (Lighter and faster than SDXL - only ~2GB)\n")
    
#     try:
#         # Load SD 1.5
#         pipe = StableDiffusionPipeline.from_pretrained(
#             IMAGE_MODEL,
#             torch_dtype=torch.float32,  # Use float32 for MPS compatibility
#             safety_checker=None,  # Disable for faster loading
#         )
        
#         # Use faster scheduler
#         pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        
#         # Use MPS (Metal) for M1
#         if torch.backends.mps.is_available():
#             pipe.to("mps")
#             print("✅ Using MPS (Metal) acceleration")
#         else:
#             pipe.to("cpu")
#             print("⚠️  Using CPU (MPS not available)")
        
#         # Enable memory optimizations
#         pipe.enable_attention_slicing()
        
#         print("✅ SD 1.5 model loaded successfully!\n")
        
#     except Exception as e:
#         print(f"❌ Error loading model: {e}")
#         raise
    
#     return pipe


# def generate_cover_image_local(
#     image_prompt: str,
#     track_name: str,
#     text_style: dict,
#     out_path: str = "cover.png",
#     num_inference_steps: int = 25,
#     guidance_scale: float = 7.5,
#     add_text: bool = True,
# ) -> str:
#     """
#     Use local Stable Diffusion 1.5 to generate an image,
#     then add styled text overlay.
    
#     Args:
#         image_prompt: Text description of the image
#         track_name: Name of the track to overlay on the image
#         text_style: Dictionary with styling info from Llama
#         out_path: Where to save the generated image
#         num_inference_steps: More steps = better quality but slower
#         guidance_scale: How closely to follow the prompt
#         add_text: Whether to add text overlay
    
#     Returns:
#         Path to the saved image
#     """
    
#     # Load model if not already loaded
#     pipeline = load_sd_pipeline()
    
#     print("\n🖼  Generating image with Stable Diffusion 1.5...")
#     print(f"   Steps: {num_inference_steps}, Guidance: {guidance_scale}\n")
    
#     try:
#         # Generate image (512x512 is SD 1.5's native resolution)
#         result = pipeline(
#             prompt=image_prompt,
#             num_inference_steps=num_inference_steps,
#             guidance_scale=guidance_scale,
#             height=512,
#             width=512,
#         )
        
#         image = result.images[0]
        
#         # Upscale to 1024x1024 for better quality
#         image = image.resize((1024, 1024), Image.LANCZOS)
        
#         # Add text overlay if requested
#         if add_text:
#             print("✍️  Adding styled text overlay...")
#             print(f"   Text: '{track_name}'")
#             print(f"   Style: {text_style.get('font_style', 'default')}")
#             print(f"   Color: {text_style.get('color', 'white')}")
#             print(f"   Position: {text_style.get('position', 'center')}")
#             print(f"   Effects: {text_style.get('effects', 'none')}\n")
            
#             image = add_text_to_image(image, track_name, text_style)
        
#         # Save image
#         out = Path(out_path)
#         out.parent.mkdir(parents=True, exist_ok=True)
#         image.save(out, format="PNG", quality=95)
        
#         # Free up memory
#         gc.collect()
#         if torch.backends.mps.is_available():
#             torch.mps.empty_cache()
        
#         print(f"✅ Image saved to: {out}\n")
#         return str(out)
        
#     except Exception as e:
#         print(f"❌ Error generating image: {e}")
#         raise


# # -------------------------
# # MAIN ENTRY
# # -------------------------

# if __name__ == "__main__":
#     print("\n🎵 Llama 3.2 + Stable Diffusion 1.5 Cover Generator")
#     print("=" * 50)
#     print("💡 Using SD 1.5 - lighter and faster than SDXL!")
    
#     # Check if MPS is available
#     if not torch.backends.mps.is_available():
#         print("\n⚠️  Warning: MPS not available. Using CPU (will be slower)")
#         print("   Make sure you're on macOS 12.3+ with M1/M2 chip\n")
#     else:
#         print("✅ MPS (Metal) acceleration detected\n")
    
#     track_name = input("Enter track name: ").strip()
#     genre = input("Enter genre (e.g. hiphop, lofi, edm): ").strip() or "default"

#     # 1) Get image prompt from Llama 3.2
#     print("\n" + "=" * 50)
#     print("🧠 Generating image prompt from Llama 3.2...")
#     print("=" * 50 + "\n")
    
#     image_prompt, text_style = generate_image_prompt_with_llama(track_name, genre)

#     print("🔎 Generated Image Prompt:")
#     print("-" * 50)
#     print(image_prompt)
#     print("-" * 50)
    
#     print("\n🎨 Text Styling:")
#     print("-" * 50)
#     print(f"Font Style: {text_style.get('font_style', 'N/A')}")
#     print(f"Color: {text_style.get('color', 'N/A')}")
#     print(f"Position: {text_style.get('position', 'N/A')}")
#     print(f"Effects: {text_style.get('effects', 'N/A')}")
#     print("-" * 50)

#     # 2) Generate image with SD 1.5
#     output_file = input("\nEnter output file name (default: cover.png): ").strip() or "cover.png"
    
#     # Optional: ask for quality settings
#     quality = input("\nQuality preset (fast/balanced/high, default: balanced): ").strip().lower()
    
#     if quality == "fast":
#         steps, guidance = 15, 7.0
#     elif quality == "high":
#         steps, guidance = 35, 8.0
#     else:  # balanced
#         steps, guidance = 25, 7.5
    
#     # Ask if user wants text overlay
#     add_text = input("\nAdd track name to cover? (y/n, default: y): ").strip().lower()
#     add_text = add_text != 'n'
    
#     generate_cover_image_local(
#         image_prompt,
#         track_name=track_name,
#         text_style=text_style,
#         out_path=output_file,
#         num_inference_steps=steps,
#         guidance_scale=guidance,
#         add_text=add_text,
#     )
    
#     print("\n" + "=" * 50)
#     print("🎉 Done! Your album cover is ready!")
#     print("=" * 50 + "\n")




import os
import json
from pathlib import Path

import ollama
from dotenv import load_dotenv
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import gc

load_dotenv()  # reads .env file

# -------------------------
# CONFIG
# -------------------------

LLM_MODEL = "llama3.2:latest"   # local via Ollama
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"  # Lighter SD 1.5 model

# Global pipeline instance (loaded once)
pipe = None


# -------------------------
# LLM: prompt generation with Llama 3.2
# -------------------------

def build_llama_prompt(track_name: str, genre: str) -> str:
    """
    Build the instruction for Llama 3.2:
    We want it to output a single JSON object with a 'prompt' string and 'text_style' object.
    """
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
  * Electronic/EDM/Techno → "Arial Bold" or "Helvetica Bold" or "Impact"
  * Lo-fi/Chill → "Times New Roman" or "Georgia" or "Palatino"
  * Hip-hop/Trap → "Impact" or "Arial Black" or "Marker Felt"
  * Jazz/Soul → "Times New Roman" or "Baskerville" or "Palatino"
  * Rock/Metal → "Impact" or "Arial Narrow Bold" or "Helvetica Bold"
  * Synthwave/Vaporwave → "Courier New Bold" or "OCR A" or "Monaco"
  * Ambient/Experimental → "Helvetica" or "Arial" or "Futura"
  * Classical → "Times New Roman" or "Baskerville" or "Garamond"
  
  Choose from these available fonts (pick ONE specific font name):
  - Arial, Arial Bold, Arial Black, Arial Narrow Bold
  - Helvetica, Helvetica Bold
  - Times New Roman, Times New Roman Bold
  - Courier New, Courier New Bold
  - Impact
  - Georgia
  - Palatino
  - Marker Felt
  - Brush Script
  
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
    "font_family": "specific font name like Arial Bold, Times New Roman, Impact, etc.",
    "color": "specific color name or hex code",
    "position": "center",
    "effects": "glow" or "shadow" or "outline" or "glow and shadow" or "none"
  }}
}}
"""


def generate_image_prompt_with_llama(track_name: str, genre: str) -> tuple[str, dict]:
    """
    Call Llama 3.2 via Ollama and get back a prompt string and text styling info.
    Returns: (image_prompt, text_style_dict)
    """

    prompt_text = build_llama_prompt(track_name, genre)

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

    # Try to parse JSON directly
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: extract JSON blob
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
        "font_family": "Arial Bold",
        "color": "white",
        "position": "center",
        "effects": "shadow"
    })

    return data["prompt"], text_style


# -------------------------
# Text overlay with smart styling
# -------------------------

def get_font_path(font_family: str, size: int) -> ImageFont.FreeTypeFont:
    """
    Get the exact font based on font family name.
    Maps font names to macOS system font paths.
    """
    font_family_lower = font_family.lower()
    
    # Direct mapping of font family names to macOS paths
    font_map = {
        # Arial family
        "arial": "/System/Library/Fonts/Supplemental/Arial.ttf",
        "arial bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "arial black": "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "arial narrow bold": "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
        
        # Helvetica family
        "helvetica": "/System/Library/Fonts/Helvetica.ttc",
        "helvetica bold": "/System/Library/Fonts/Helvetica.ttc",
        
        # Times New Roman family
        "times new roman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "times new roman bold": "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "times": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        
        # Courier family
        "courier new": "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "courier new bold": "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "courier": "/System/Library/Fonts/Courier.dfont",
        
        # Other fonts
        "impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
        "georgia": "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "palatino": "/Library/Fonts/Palatino.ttc",
        "marker felt": "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "brush script": "/System/Library/Fonts/Supplemental/Brush Script.ttf",
        "futura": "/System/Library/Fonts/Supplemental/Futura.ttc",
        "baskerville": "/System/Library/Fonts/Supplemental/Baskerville.ttc",
    }
    
    # Try exact match first
    if font_family_lower in font_map:
        path = font_map[font_family_lower]
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    
    # Try partial match
    for font_name, path in font_map.items():
        if font_name in font_family_lower and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    
    # Fallback to Helvetica (always available on macOS)
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        # Ultimate fallback
        return ImageFont.load_default()


def parse_color(color_str: str) -> tuple:
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
    image: Image.Image,
    text: str,
    text_style: dict,
) -> Image.Image:
    """
    Add styled text overlay to the generated image.
    
    Args:
        image: PIL Image to add text to
        text: The text to add (track name)
        text_style: Dictionary with font_style, color, position, effects
    
    Returns:
        PIL Image with text overlay
    """
    img_width, img_height = image.size
    
    # Create a copy to work with
    img_with_text = image.copy()
    
    # Determine font size based on image size and text length
    base_size = img_width // 10  # Adjusted for 512x512
    font_size = max(30, min(base_size, img_width // (len(text) // 2 + 1)))
    
    # Get font based on font family
    font_family = text_style.get("font_family", "Arial Bold")
    font = get_font_path(font_family, font_size)
    
    # Parse color
    text_color = parse_color(text_style.get("color", "white"))
    
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
    
    # Apply effects
    effects = text_style.get("effects", "shadow").lower()
    
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
    
    return img_with_text


# -------------------------
# Image generation: Stable Diffusion 1.5 (Lighter!)
# -------------------------

def load_sd_pipeline():
    """
    Load SD 1.5 pipeline - much lighter than SDXL.
    Uses only ~2GB RAM vs SDXL's ~7GB.
    """
    global pipe
    
    if pipe is not None:
        return pipe
    
    print("\n🔄 Loading Stable Diffusion 1.5 model...")
    print("   (Lighter and faster than SDXL - only ~2GB)\n")
    
    try:
        # Load SD 1.5
        pipe = StableDiffusionPipeline.from_pretrained(
            IMAGE_MODEL,
            torch_dtype=torch.float32,  # Use float32 for MPS compatibility
            safety_checker=None,  # Disable for faster loading
        )
        
        # Use faster scheduler
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        
        # Use MPS (Metal) for M1
        if torch.backends.mps.is_available():
            pipe.to("mps")
            print("✅ Using MPS (Metal) acceleration")
        else:
            pipe.to("cpu")
            print("⚠️  Using CPU (MPS not available)")
        
        # Enable memory optimizations
        pipe.enable_attention_slicing()
        
        print("✅ SD 1.5 model loaded successfully!\n")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise
    
    return pipe


def generate_cover_image_local(
    image_prompt: str,
    track_name: str,
    text_style: dict,
    out_path: str = "cover.png",
    num_inference_steps: int = 25,
    guidance_scale: float = 7.5,
    add_text: bool = True,
) -> str:
    """
    Use local Stable Diffusion 1.5 to generate an image,
    then add styled text overlay.
    
    Args:
        image_prompt: Text description of the image
        track_name: Name of the track to overlay on the image
        text_style: Dictionary with styling info from Llama
        out_path: Where to save the generated image
        num_inference_steps: More steps = better quality but slower
        guidance_scale: How closely to follow the prompt
        add_text: Whether to add text overlay
    
    Returns:
        Path to the saved image
    """
    
    # Load model if not already loaded
    pipeline = load_sd_pipeline()
    
    print("\n🖼  Generating image with Stable Diffusion 1.5...")
    print(f"   Steps: {num_inference_steps}, Guidance: {guidance_scale}\n")
    
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
        
        # Upscale to 1024x1024 for better quality
        image = image.resize((1024, 1024), Image.LANCZOS)
        
        # Add text overlay if requested
        if add_text:
            print("✍️  Adding styled text overlay...")
            print(f"   Text: '{track_name}'")
            print(f"   Font: {text_style.get('font_family', 'default')}")
            print(f"   Color: {text_style.get('color', 'white')}")
            print(f"   Position: center (always)")
            print(f"   Effects: {text_style.get('effects', 'none')}\n")
            
            image = add_text_to_image(image, track_name, text_style)
        
        # Save image
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, format="PNG", quality=95)
        
        # Free up memory
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        
        print(f"✅ Image saved to: {out}\n")
        return str(out)
        
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        raise


# -------------------------
# MAIN ENTRY
# -------------------------

if __name__ == "__main__":
    print("\n🎵 Llama 3.2 + Stable Diffusion 1.5 Cover Generator")
    print("=" * 50)
    print("💡 Using SD 1.5 - lighter and faster than SDXL!")
    
    # Check if MPS is available
    if not torch.backends.mps.is_available():
        print("\n⚠️  Warning: MPS not available. Using CPU (will be slower)")
        print("   Make sure you're on macOS 12.3+ with M1/M2 chip\n")
    else:
        print("✅ MPS (Metal) acceleration detected\n")
    
    track_name = input("Enter track name: ").strip()
    genre = input("Enter genre (e.g. hiphop, lofi, edm): ").strip() or "default"

    # 1) Get image prompt from Llama 3.2
    print("\n" + "=" * 50)
    print("🧠 Generating image prompt from Llama 3.2...")
    print("=" * 50 + "\n")
    
    image_prompt, text_style = generate_image_prompt_with_llama(track_name, genre)

    print("🔎 Generated Image Prompt:")
    print("-" * 50)
    print(image_prompt)
    print("-" * 50)
    
    print("\n🎨 Text Styling:")
    print("-" * 50)
    print(f"Font Family: {text_style.get('font_family', 'N/A')}")
    print(f"Color: {text_style.get('color', 'N/A')}")
    print(f"Position: center (always)")
    print(f"Effects: {text_style.get('effects', 'N/A')}")
    print("-" * 50)

    # 2) Generate image with SD 1.5
    output_file = input("\nEnter output file name (default: cover.png): ").strip() or "cover.png"
    
    # Optional: ask for quality settings
    quality = input("\nQuality preset (fast/balanced/high, default: balanced): ").strip().lower()
    
    if quality == "fast":
        steps, guidance = 15, 7.0
    elif quality == "high":
        steps, guidance = 35, 8.0
    else:  # balanced
        steps, guidance = 25, 7.5
    
    # Ask if user wants text overlay
    add_text = input("\nAdd track name to cover? (y/n, default: y): ").strip().lower()
    add_text = add_text != 'n'
    
    generate_cover_image_local(
        image_prompt,
        track_name=track_name,
        text_style=text_style,
        out_path=output_file,
        num_inference_steps=steps,
        guidance_scale=guidance,
        add_text=add_text,
    )
    
    print("\n" + "=" * 50)
    print("🎉 Done! Your album cover is ready!")
    print("=" * 50 + "\n")