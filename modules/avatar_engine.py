import os
import json
import time
import urllib.parse
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

class AvatarEngine:
    """
    Dynamic Character Engine:
    Maintains a consistent character identity (e.g., dusky Indian man with chevron moustache)
    while dynamically altering his outfit, facial expression, and background environment
    to match each specific video topic, followed by AI lip-syncing to the spoken audio.
    """

    def __init__(self, config_path=None):
        if not config_path:
            config_path = os.path.join(os.getcwd(), "config", "avatar_persona.json")

        self.config_path = config_path
        self.persona = self._load_persona()
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        self.cache_dir = os.path.join(os.getcwd(), "assets", "avatar", "cache")
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _load_persona(self):
        default_persona = {
            "name": "Arjun",
            "enabled": True,
            "avatar_scenes_count": 2,
            "character_dna": "Photorealistic cinematic portrait of a 30-year-old everyday Indian man, warm medium-dark dusky skin tone, defined jawline, kind expressive dark brown eyes, thick well-groomed chevron moustache, short textured black hair parted neatly, realistic skin texture with natural pores, looking directly into the camera, 9:16 vertical composition",
            "camera_framing": "medium close-up portrait, upper chest and face visible, looking directly at viewer, 9:16 vertical ratio",
            "style_modifiers": "cinematic lighting, 8k resolution, photorealistic, sharp focus, master portrait photography, highly detailed",
            "negative_prompt": "cartoon, 3d render, anime, blurry, distorted face, fair skin, light eyes, clean shaven, deformed lips"
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_persona.update(data)
            except Exception as e:
                print(f"⚠️ Error reading avatar persona config: {e}. Using defaults.")

        return default_persona

    def build_avatar_prompt(self, outfit=None, background=None, expression=None):
        """Constructs a prompt fusing permanent character DNA with dynamic context."""
        dna = self.persona.get("character_dna")
        framing = self.persona.get("camera_framing")
        style = self.persona.get("style_modifiers")

        outfit_desc = f"wearing {outfit}" if outfit else "wearing smart casual dark apparel"
        bg_desc = f"in {background}" if background else "in a cinematic studio background with moody rim lighting"
        expr_desc = f"facial expression: {expression}" if expression else "expressive engaged speaking expression"

        full_prompt = f"{dna}, {outfit_desc}, {bg_desc}, {expr_desc}, {framing}, {style}"
        return full_prompt

    def generate_avatar_image(self, scene_id, outfit=None, background=None, expression=None):
        """Generates the contextual avatar frame using Flux."""
        out_image = os.path.join(self.temp_dir, f"avatar_frame_{scene_id}.jpg")
        if os.path.exists(out_image):
            return out_image

        prompt = self.build_avatar_prompt(outfit, background, expression)
        print(f"   👤 Synthesizing Contextual Avatar Image (Scene {scene_id})...")
        print(f"      • Outfit: {outfit or 'Default'}")
        print(f"      • Environment: {background or 'Default'}")

        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&model=flux&nologo=true"

        for attempt in range(3):
            try:
                res = requests.get(url, timeout=35)
                res.raise_for_status()
                with open(out_image, "wb") as f:
                    f.write(res.content)
                return out_image
            except Exception as e:
                print(f"      ⚠️ Image generation retry {attempt+1}/3: {e}")
                time.sleep(2)

        return None

    def lip_sync_video(self, image_path, audio_path, duration, output_path):
        """
        Animates avatar image with spoken audio.
        Attempts cloud Wav2Lip/SadTalker; if unavailable or timing out,
        falls back to dynamic cinematic zoom and subtle head breathing motion.
        """
        if os.path.exists(output_path):
            return output_path

        # 1. Attempt Cloud Wav2Lip / SadTalker via Gradio Client
        try:
            from gradio_client import Client, handle_file
            print(f"   🎙️ Connecting to Cloud Lip-Sync Engine...")
            client = Client("manavisrani07/gradio-lipsync-wav2lip", verbose=False)
            
            # Call wav2lip endpoint with 40s timeout
            result = client.predict(
                video=handle_file(image_path),
                audio=handle_file(audio_path),
                checkpoint="wav2lip",
                no_smooth=0,
                resize_factor=10,
                pad_top=0,
                pad_bottom=0,
                pad_left=1,
                api_name="/generate"
            )
            
            raw_video = result.get("video") if isinstance(result, dict) else result
            if raw_video and os.path.exists(raw_video):
                print("   ✅ Lip-sync successful! Formatting to 1080x1920...")
                # Ensure final aspect ratio is exactly 1080x1920 @ 30fps
                cmd = [
                    "ffmpeg", "-y", "-i", raw_video,
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "30",
                    output_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return output_path

        except Exception as e:
            print(f"   ⚠️ Cloud Lip-Sync unavailable or timed out ({e}). Using resilient motion fallback...")

        # 2. Resilient Motion Fallback (Ken Burns camera movement + audio lock)
        return self._render_motion_fallback(image_path, audio_path, duration, output_path)

    def _render_motion_fallback(self, image_path, audio_path, duration, output_path):
        """
        Creates a high-end cinematic talking head scene:
        Subtle camera push-in on the avatar's face while audio plays.
        """
        frames = int((duration + 0.5) * 30)
        # Slow cinematic zoom-in focused on the upper-body / face
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.12)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2.5-(ih/zoom/2.5)':s=1080x1920:fps=30"

        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
            "-t", str(duration + 0.5), "-shortest",
            output_path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ Contextual Avatar scene rendered: {output_path}")
            return output_path
        except Exception as e:
            print(f"   ❌ Motion fallback render failed: {e}")
            return None

    def render_scene(self, scene):
        """End-to-end generator for one avatar scene."""
        scene_id = scene["id"]
        audio_path = scene.get("audio_path")
        duration = scene.get("duration", 4.0)

        outfit = scene.get("avatar_outfit")
        background = scene.get("avatar_background")
        expression = scene.get("avatar_expression")

        # 1. Generate image
        image_path = self.generate_avatar_image(scene_id, outfit, background, expression)
        if not image_path:
            return None

        # 2. Animate & Lip-Sync
        output_video = os.path.join(self.temp_dir, f"avatar_scene_{scene_id}.mp4")
        return self.lip_sync_video(image_path, audio_path, duration, output_video)
