import os
import io
import time
import random
import urllib.parse
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

class StickmanEngine:
    """
    Generates 100% custom Stickman Cartoon Explainer visuals (MinutePhysics / Casually Explained style).
    Every scene gets a custom-drawn doodle comic panel matching the exact story sentence,
    animated with dynamic camera pans, snap-zooms, and comic timing.
    Multi-tier zero-failure engine:
    1. Pixabay Illustration / Vector Engine (instant high-res cartoon art matching beat keywords)
    2. Pollinations AI (Zero-key Flux/Turbo stick figure generator)
    3. Expressive Procedural Stickman Doodle Engine (Dynamic poses & comic props via Pillow)
    """

    STYLE_PREFIX = (
        "Minimalist stick figure comic illustration, simple cute black ink line art stickman, "
        "witty funny cartoon doodle on clean solid white paper background, high contrast 9:16 vertical comic panel, "
        "humorous cartoon style, clean vector lines, simple hand-drawn props, flat minimal comic coloring, "
        "expressive stick figure character: "
    )

    def __init__(self):
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        self.clips_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.clips_dir, exist_ok=True)

    def fetch_pixabay_cartoon(self, scene_id: int, query: str) -> str:
        """Fetches a high-quality cartoon/illustration from Pixabay and composites onto a 9:16 canvas."""
        if not self.pixabay_key or not query:
            return None

        output_image = os.path.join(self.temp_dir, f"stickman_{scene_id}.jpg")
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
                res = requests.get(url, timeout=12)
                data = res.json()
                hits = data.get("hits", [])
                if hits:
                    img_url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
                    img_res = requests.get(img_url, timeout=15)
                    from PIL import Image

                    img = Image.open(io.BytesIO(img_res.content)).convert("RGBA")
                    # Composite onto 1080x1920 solid white canvas
                    canvas = Image.new("RGB", (1080, 1920), color="white")
                    # Fit nicely within safe margins
                    img.thumbnail((980, 1300), Image.Resampling.LANCZOS)
                    x = (1080 - img.width) // 2
                    y = (1920 - img.height) // 2 - 60

                    mask = img.split()[3] if len(img.split()) > 3 else None
                    canvas.paste(img, (x, y), mask=mask)
                    canvas.save(output_image, "JPEG", quality=92)
                    print(f"   🎨 Matched Cartoon Illustration for Scene {scene_id}: '{q}'")
                    return output_image
            except Exception as e:
                continue

        return None

    def _generate_procedural_stickman(self, output_image: str, description: str, mood: str = "funny") -> str:
        """Procedural 100% offline fallback: draws an expressive stick figure with Pillow."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (1080, 1920), color="white")
            d = ImageDraw.Draw(img)

            # Head
            d.ellipse((440, 600, 640, 800), outline="black", width=14)
            # Body
            d.line((540, 800, 540, 1300), fill="black", width=14)
            # Legs
            d.line((540, 1300, 420, 1600), fill="black", width=14)
            d.line((540, 1300, 660, 1600), fill="black", width=14)

            # Dynamic Poses based on mood
            if mood in ("shocking", "shocked"):
                # Hands on head in shock
                d.line((540, 950, 400, 850), fill="black", width=14)
                d.line((400, 850, 440, 650), fill="black", width=14)
                d.line((540, 950, 680, 850), fill="black", width=14)
                d.line((680, 850, 640, 650), fill="black", width=14)
                # Big shocked eyes
                d.ellipse((480, 670, 510, 700), fill="black")
                d.ellipse((570, 670, 600, 700), fill="black")
                # Open mouth O
                d.ellipse((525, 730, 555, 760), outline="black", width=6)
                # Shock symbols ?!
                d.text((680, 520), "?!", fill="black")
            elif mood in ("pointing", "educational", "scientific"):
                # Pointing to chalkboard
                d.rectangle((660, 480, 1020, 950), outline="black", width=10)
                d.line((700, 560, 980, 560), fill="black", width=6)
                d.line((700, 640, 940, 640), fill="black", width=6)
                d.line((700, 720, 960, 720), fill="black", width=6)
                # Pointer arm
                d.line((540, 950, 750, 750), fill="black", width=14)
                d.line((540, 950, 420, 1100), fill="black", width=14)
                # Concentrated eyes & glasses
                d.ellipse((480, 670, 510, 700), outline="black", width=4)
                d.ellipse((570, 670, 600, 700), outline="black", width=4)
                d.line((510, 685, 570, 685), fill="black", width=4)
            elif mood in ("celebrating", "happy", "success"):
                # Arms raised high in victory
                d.line((540, 950, 360, 700), fill="black", width=14)
                d.line((540, 950, 720, 700), fill="black", width=14)
                # Smiling face
                d.ellipse((480, 670, 510, 690), fill="black")
                d.ellipse((570, 670, 600, 690), fill="black")
                d.arc((500, 700, 580, 750), start=0, end=180, fill="black", width=8)
            else:
                # Conversational gesture
                d.line((540, 950, 360, 1100), fill="black", width=14)
                d.line((540, 950, 720, 850), fill="black", width=14)
                d.ellipse((490, 670, 510, 690), fill="black")
                d.ellipse((570, 670, 590, 690), fill="black")
                d.arc((510, 710, 570, 750), start=0, end=180, fill="black", width=6)

            # Ground line
            d.line((150, 1600, 930, 1600), fill="black", width=8)

            img.save(output_image, "JPEG", quality=90)
            return output_image
        except Exception as e:
            print(f"      ❌ Procedural stickman draw failed: {e}")
            return None

    def generate_scene_art(self, scene_id: int, description: str, keywords: str = None, mood: str = "funny") -> str:
        """Acquires the best cartoon art for this beat using multi-tier harvesting."""
        output_image = os.path.join(self.temp_dir, f"stickman_{scene_id}.jpg")
        if os.path.exists(output_image):
            return output_image

        # Tier 1: Pixabay Illustration match
        if keywords:
            img = self.fetch_pixabay_cartoon(scene_id, keywords)
            if img:
                return img

        # Tier 2: Pollinations AI (Zero-key Flux/Turbo)
        clean_desc = (description or "").replace('"', '').strip()
        full_prompt = f"{self.STYLE_PREFIX}{clean_desc}"
        encoded_prompt = urllib.parse.quote(full_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=turbo&nologo=true"

        print(f"   ✏️ Drawing Stickman Scene {scene_id}: '{clean_desc[:45]}...'")
        try:
            res = requests.get(url, timeout=20)
            if res.status_code == 200:
                with open(output_image, "wb") as f:
                    f.write(res.content)
                return output_image
            else:
                print(f"      ℹ️ Pollinations status {res.status_code}. Using expressive doodle engine...")
        except Exception as e:
            print(f"      ℹ️ Pollinations ({e}). Using expressive doodle engine...")

        # Tier 3: Expressive Procedural Stickman
        return self._generate_procedural_stickman(output_image, clean_desc, mood=mood)

    def animate_stickman_clip(self, image_path: str, duration: float, motion_type: str = "zoom_in", output_path: str = None) -> str:
        """
        Converts the stickman image into an animated video clip with comic camera movement.
        Supports: zoom_in, zoom_out, pan_right, pan_left, snap_zoom.
        """
        if not output_path:
            filename = os.path.basename(image_path).replace(".jpg", ".mp4")
            output_path = os.path.join(self.clips_dir, filename)

        if os.path.exists(output_path):
            return output_path

        frames = int(max(duration, 1.0) * 30)

        # Select dynamic camera movement for comic engagement
        if motion_type == "zoom_in":
            # Dramatic push-in on the stick figure's reaction
            zoom_expr = f"zoompan=z='min(zoom+0.002,1.22)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_type == "zoom_out":
            # Reveal the wider funny context
            zoom_expr = f"zoompan=z='max(1.22-0.002*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_type == "pan_right":
            # Pan across a funny diagram or progression
            zoom_expr = f"zoompan=z=1.15:d={frames}:x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_type == "pan_left":
            zoom_expr = f"zoompan=z=1.15:d={frames}:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        else:
            # Subtle comedic drift
            zoom_expr = f"zoompan=z='min(zoom+0.0012,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"

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
        description = scene.get("stickman_prompt") or scene.get("visual_1") or scene.get("text")
        keywords = scene.get("cartoon_keywords") or scene.get("keywords")
        duration = scene.get("duration", 4.0)
        motion = scene.get("motion_type", "zoom_in")
        mood = scene.get("mood", "funny")

        image_path = self.generate_scene_art(scene_id, description, keywords=keywords, mood=mood)
        if not image_path:
            return None

        output_clip = os.path.join(self.clips_dir, f"stickman_clip_{scene_id}.mp4")
        return self.animate_stickman_clip(image_path, duration, motion_type=motion, output_path=output_clip)
