import os
import io
import time
import random
import urllib.parse
import subprocess
import requests
from dotenv import load_dotenv
import resvg_py

from modules.brain import _generate

load_dotenv()

class StickmanEngine:
    """
    Production-Grade 2D Stickman Motion Graphics Engine.
    Emulates the viral aesthetics of @stickylife3, @lowkeyexplains, and @saysstickman:
    1. Generates 100% custom, expressive 2D cartoon vector SVG artwork via Google Gemini.
    2. Renders pixel-perfect 1080x1920 9:16 vertical images via high-speed Rust resvg.
    3. Transforms vector panels into lively motion graphics using dynamic camera choreography
       (punch snaps, wide reveals, horizontal narrative pans, and comedic bobbing).
    4. Includes multi-tier fallbacks (Pixabay vector, Pollinations turbo, and Pillow).
    """

    SVG_DIRECTOR_PROMPT = """
You are an expert 2D stickman animator and vector illustrator creating viral Instagram Reels and YouTube Shorts in the exact style of @stickylife3 and @lowkeyexplains.

Generate complete, valid, standalone SVG code (viewBox="0 0 1080 1920") for this story beat:
"{description}"

STRICT DESIGN REQUIREMENTS:
1. Output ONLY the raw <svg viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">...</svg> markup.
   NO markdown code blocks, NO explanation.
2. Character Style:
   - Solid, clean off-white background (#F9F9F7).
   - Cute stick figure with round white head (circle stroke="black" stroke-width="12" fill="white", r=75 to 80).
   - Highly expressive face: big lively cartoon eyes (white ovals with black pupils and expressive black eyebrows), cute open/smiling mouth or reaction mouth.
   - Distinctive stick torso, arms, and legs with black hands/shoes (stroke="black" stroke-width="12" to "14").
   - Character should wear relevant hats/accessories when mentioned (e.g. beekeeper hat, police cap, chef hat, sunglasses, top hat, tie).
3. Props and Environment:
   - When cats, dogs, honey jars, bees, money, cars, or pyramids are mentioned, DRAW THEM clearly in cute cartoon line art!
   - Animals must look charming (e.g. cute cat with pointy ears, whiskers, curled tail, purr sound waves).
   - Props should have thick black outlines and cheerful flat accent colors (e.g. golden honey, orange cat, green money, blue hats).
4. Visual Balance:
   - Center the main character and action in the upper-middle vertical safe zone (y: 400 to 1400) so bottom subtitles won't obstruct the art.
   - Clean, charming, high-retention viral quality.
"""

    def __init__(self):
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        self.clips_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.clips_dir, exist_ok=True)

    def generate_svg_scene(self, scene_id: int, description: str) -> str:
        """
        Authors a custom 2D stickman vector illustration using Gemini and resvg.
        """
        output_image = os.path.join(self.temp_dir, f"stickman_{scene_id}.png")
        if os.path.exists(output_image):
            return output_image

        prompt = self.SVG_DIRECTOR_PROMPT.format(description=description)
        print(f"   ✏️ Drawing Custom Vector Stickman Scene {scene_id}: '{description[:42]}...'")

        try:
            resp = _generate(prompt)
            svg_text = resp.text.strip()
            if "```xml" in svg_text:
                svg_text = svg_text.split("```xml")[1].split("```")[0].strip()
            elif "```svg" in svg_text:
                svg_text = svg_text.split("```svg")[1].split("```")[0].strip()
            elif "```" in svg_text:
                svg_text = svg_text.split("```")[1].split("```")[0].strip()

            if "<svg" in svg_text and "</svg>" in svg_text:
                # Clean up any prefix/suffix around svg tags
                start_idx = svg_text.find("<svg")
                end_idx = svg_text.rfind("</svg>") + 6
                clean_svg = svg_text[start_idx:end_idx]

                # Render with high-speed Rust resvg
                png_bytes = resvg_py.svg_to_bytes(clean_svg, width=1080, height=1920)
                with open(output_image, "wb") as f:
                    f.write(png_bytes)
                print(f"      ✨ Vector scene {scene_id} rendered ({len(png_bytes)} bytes)")
                return output_image
        except Exception as e:
            print(f"      ⚠️ Gemini vector generation error ({e}). Trying fallbacks...")

        return None

    def fetch_pixabay_cartoon(self, scene_id: int, query: str) -> str:
        """Fallback: Fetches a cartoon illustration from Pixabay and composites onto a 9:16 canvas."""
        if not self.pixabay_key or not query:
            return None

        output_image = os.path.join(self.temp_dir, f"stickman_{scene_id}.png")
        if os.path.exists(output_image):
            return output_image

        clean_query = query.strip()
        search_terms = [clean_query]
        if "cartoon" not in clean_query and "illustration" not in clean_query:
            search_terms.append(f"{clean_query} cartoon")

        for q in search_terms:
            try:
                encoded = urllib.parse.quote(q)
                url = f"https://pixabay.com/api/?key={self.pixabay_key}&q={encoded}&image_type=illustration&per_page=5"
                res = requests.get(url, timeout=10)
                data = res.json()
                hits = data.get("hits", [])
                if hits:
                    img_url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
                    img_res = requests.get(img_url, timeout=12)
                    from PIL import Image

                    img = Image.open(io.BytesIO(img_res.content)).convert("RGBA")
                    canvas = Image.new("RGB", (1080, 1920), color="#F9F9F7")
                    img.thumbnail((980, 1200), Image.Resampling.LANCZOS)
                    x = (1080 - img.width) // 2
                    y = (1920 - img.height) // 2 - 80

                    mask = img.split()[3] if len(img.split()) > 3 else None
                    canvas.paste(img, (x, y), mask=mask)
                    canvas.save(output_image, "PNG")
                    print(f"   🎨 Matched Pixabay Cartoon for Scene {scene_id}: '{q}'")
                    return output_image
            except Exception:
                continue

        return None

    def _generate_procedural_stickman(self, output_image: str, description: str, mood: str = "funny") -> str:
        """Ultimate offline fallback using Pillow."""
        try:
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (1080, 1920), color="#F9F9F7")
            d = ImageDraw.Draw(img)

            # Head
            d.ellipse((440, 580, 640, 780), outline="black", width=14, fill="white")
            # Eyes with pupils
            d.ellipse((485, 650, 515, 680), fill="black")
            d.ellipse((565, 650, 595, 680), fill="black")
            d.arc((505, 690, 575, 740), start=0, end=180, fill="black", width=8)

            # Body
            d.line((540, 780, 540, 1280), fill="black", width=14)
            # Legs with shoes
            d.line((540, 1280, 420, 1580), fill="black", width=14)
            d.ellipse((390, 1560, 440, 1600), fill="black")
            d.line((540, 1280, 660, 1580), fill="black", width=14)
            d.ellipse((640, 1560, 690, 1600), fill="black")

            # Expressive Arms based on mood
            if mood in ("shocking", "shocked"):
                d.line((540, 930, 400, 830), fill="black", width=14)
                d.line((400, 830, 440, 630), fill="black", width=14)
                d.line((540, 930, 680, 830), fill="black", width=14)
                d.line((680, 830, 640, 630), fill="black", width=14)
                d.text((680, 520), "?!", fill="black")
            elif mood in ("pointing", "educational", "scientific"):
                d.rectangle((660, 480, 1020, 920), outline="black", width=10, fill="white")
                d.line((700, 560, 980, 560), fill="black", width=6)
                d.line((700, 640, 940, 640), fill="black", width=6)
                d.line((540, 930, 750, 750), fill="black", width=14)
                d.line((540, 930, 420, 1080), fill="black", width=14)
            else:
                d.line((540, 930, 360, 1080), fill="black", width=14)
                d.line((540, 930, 720, 830), fill="black", width=14)

            # Ground line
            d.line((150, 1600, 930, 1600), fill="black", width=8)

            img.save(output_image, "PNG")
            return output_image
        except Exception as e:
            print(f"      ❌ Procedural draw failed: {e}")
            return None

    def generate_scene_art(self, scene_id: int, description: str, keywords: str = None, mood: str = "funny") -> str:
        """Acquires the highest quality stickman cartoon artwork."""
        output_image = os.path.join(self.temp_dir, f"stickman_{scene_id}.png")
        if os.path.exists(output_image):
            return output_image

        # Tier 1: Dedicated Custom Vector Art (Gemini + resvg)
        art = self.generate_svg_scene(scene_id, description)
        if art:
            return art

        # Tier 2: Pixabay Cartoon Graphic
        if keywords:
            art = self.fetch_pixabay_cartoon(scene_id, keywords)
            if art:
                return art

        # Tier 3: Procedural Expressive Stickman
        return self._generate_procedural_stickman(output_image, description, mood=mood)

    def animate_stickman_clip(self, image_path: str, duration: float, motion_type: str = "zoom_in", output_path: str = None) -> str:
        """
        Converts the stickman image into an animated video clip with dynamic comic camera movement.
        Supports: zoom_in, zoom_out, pan_right, pan_left, bounce/drift.
        """
        if not output_path:
            filename = os.path.basename(image_path).replace(".png", ".mp4").replace(".jpg", ".mp4")
            output_path = os.path.join(self.clips_dir, filename)

        if os.path.exists(output_path):
            return output_path

        frames = int(max(duration, 1.0) * 30)

        # Dynamic camera choreography for high-retention viral pacing
        if motion_type == "zoom_in":
            # Dramatic punch snap: zoom into the character and action
            zoom_expr = f"zoompan=z='min(1.04+0.003*on,1.26)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2.3-(ih/zoom/2.3)':s=1080x1920:fps=30"
        elif motion_type == "zoom_out":
            # Pull-back reveal: starts close and reveals full scene
            zoom_expr = f"zoompan=z='max(1.25-0.003*on,1.02)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2.3-(ih/zoom/2.3)':s=1080x1920:fps=30"
        elif motion_type == "pan_right":
            # Horizontal sweep across the scene
            zoom_expr = f"zoompan=z=1.18:d={frames}:x='(iw-iw/zoom)*(on/{frames})':y='ih/2.3-(ih/zoom/2.3)':s=1080x1920:fps=30"
        elif motion_type == "pan_left":
            zoom_expr = f"zoompan=z=1.18:d={frames}:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2.3-(ih/zoom/2.3)':s=1080x1920:fps=30"
        else:
            # Comedic bobbing floating drift
            zoom_expr = f"zoompan=z='1.10+0.025*sin(on/8)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2.3-(ih/zoom/2.3)':s=1080x1920:fps=30"

        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{zoom_expr}"

        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", vf,
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
            output_path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
        except Exception as e:
            print(f"      ❌ FFmpeg animation error: {e}")
            return None

    def render_scene(self, scene: dict) -> str:
        """Renders one complete stickman video scene matching the narration."""
        scene_id = scene["id"]
        description = scene.get("stickman_prompt") or scene.get("text", "Stickman cartoon")
        keywords = scene.get("cartoon_keywords") or scene.get("keywords")
        duration = scene.get("duration", 4.0)
        motion = scene.get("motion_type", "zoom_in")
        mood = scene.get("mood", "funny")

        image_path = self.generate_scene_art(scene_id, description, keywords=keywords, mood=mood)
        if not image_path:
            return None

        output_clip = os.path.join(self.clips_dir, f"stickman_clip_{scene_id}.mp4")
        return self.animate_stickman_clip(image_path, duration, motion_type=motion, output_path=output_clip)
