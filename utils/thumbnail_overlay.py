from PIL import Image, ImageDraw, ImageFont
import os
import logging

logger = logging.getLogger(__name__)

class ThumbnailOverlay:
    def __init__(self, font_style: str = "bold"):
        """
        Initialize overlay with selected font style.
        Font size is fixed at 170px, only style changes.
        
        Available styles: bold, regular, serif, serif_bold, mono, mono_bold
        """
        self.font = None
        self.font_size = 170
        
        # Font style mapping
        font_map = {
            "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "serif_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "mono_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        }
        
        # Get font path for selected style, default to bold if invalid
        font_path = font_map.get(font_style, font_map["bold"])
        
        # Try to load the selected font
        if os.path.exists(font_path):
            try:
                self.font = ImageFont.truetype(font_path, self.font_size)
                logger.info(f"Loaded font style '{font_style}': {font_path}")
            except Exception as e:
                logger.warning(f"Failed to load font {font_path}: {e}")
                # Fallback to default
                self.font = ImageFont.load_default()
        else:
            logger.warning(f"Font not found: {font_path}. Using default.")
            self.font = ImageFont.load_default()

    def apply(self, image: Image.Image, title: str):
        draw = ImageDraw.Draw(image)

        W, H = image.size
        text = title.upper()

        # Measure text size
        if hasattr(draw, "textbbox"):
            # Pillow >= 9.2.0
            left, top, right, bottom = draw.textbbox((0, 0), text, font=self.font)
            w = right - left
            h = bottom - top
        else:
            # Older Pillow
            w, h = draw.textsize(text, font=self.font)

        # Position text slightly above center (looks better in thumbnails)
        x = (W - w) / 2
        y = H * 0.38   # 38% from top

        # Draw text (white + slight shadow)
        # Only draw shadow if we have a decent font size, otherwise it looks messy on default font
        if isinstance(self.font, ImageFont.FreeTypeFont):
            draw.text((x + 4, y + 4), text, font=self.font, fill=(0,0,0,160))  # shadow
        
        draw.text((x, y), text, font=self.font, fill=(255,255,255,240))    # main

        return image
