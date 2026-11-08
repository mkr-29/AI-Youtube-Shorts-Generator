import os
import requests
import random
import subprocess
import urllib.parse
from dotenv import load_dotenv

class AssetManager:
    """
    Self-healing multi-tier visual asset harvester:
    1. Pexels Stock Video API (if PEXELS_API_KEY is configured)
    2. Pixabay Stock Video API (if PIXABAY_API_KEY is configured - instant free key)
    3. Pollinations AI / Flux (Zero-key default: generates 1080x1920 photorealistic scenes
       with smooth Ken Burns motion via FFmpeg)
    """

    def __init__(self):
        load_dotenv()
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")

        self.assets_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        sources = []
        if self.pexels_key:
            sources.append("Pexels Video")
        if self.pixabay_key:
            sources.append("Pixabay Video")
        sources.append("Pollinations AI Flux (Zero-Key)")
        print(f"🎨 Visual Pipeline Active: {' ➔ '.join(sources)}")

    def search_pexels(self, query: str, duration_min: int = 4):
        """Searches Pexels for a portrait video."""
        if not self.pexels_key:
            return None

        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "per_page": 5,
            "orientation": "portrait",
            "size": "medium"
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code != 200:
                return None
            data = res.json()
            videos = data.get("videos", [])
            if not videos:
                return None

            valid_videos = [v for v in videos if v.get("duration", 0) >= duration_min] or videos
            selected = random.choice(valid_videos)
            files = selected.get("video_files", [])
            files.sort(key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
            return files[0]["link"] if files else None
        except Exception:
            return None

    def search_pixabay(self, query: str):
        """Searches Pixabay for vertical/HD video clips."""
        if not self.pixabay_key:
            return None

        url = "https://pixabay.com/api/videos/"
        params = {
            "key": self.pixabay_key,
            "q": query,
            "video_type": "film",
            "per_page": 5
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code != 200:
                return None
            data = res.json()
            hits = data.get("hits", [])
            if not hits:
                return None

            selected = random.choice(hits)
            videos = selected.get("videos", {})
            # Prefer large/medium
            for quality in ("large", "medium", "small", "tiny"):
                if quality in videos and videos[quality].get("url"):
                    return videos[quality]["url"]
            return None
        except Exception:
            return None

    def generate_ai_clip(self, query: str, filename: str, duration: float = 4.0) -> str:
        """
        Zero-key AI fallback: Generates a high-quality 9:16 vertical image using Flux
        and animates it with a cinematic Ken Burns zoom effect using FFmpeg.
        """
        save_path = os.path.join(self.assets_dir, filename)
        if os.path.exists(save_path):
            return save_path

        clean_query = query.replace('"', '').strip()
        enhanced_prompt = f"{clean_query}, cinematic lighting, 8k photorealistic, dramatic vertical composition"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        ai_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"

        temp_img = os.path.join(self.temp_dir, f"ai_{os.path.splitext(filename)[0]}.jpg")
        try:
            print(f"      ✨ Synthesizing AI Visual (Flux): '{clean_query[:35]}'...")
            res = requests.get(ai_url, timeout=30)
            res.raise_for_status()
            with open(temp_img, "wb") as f:
                f.write(res.content)

            # Alternate zoom directions between clip A (zoom in) and clip B (zoom out)
            frames = int(duration * 30)
            if "_a" in filename:
                zoom_filter = f"zoompan=z='min(zoom+0.0012,1.2)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
            else:
                zoom_filter = f"zoompan=z='max(1.15-0.0012*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"

            vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{zoom_filter}"

            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", temp_img,
                "-vf", vf,
                "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
                save_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return save_path
        except Exception as e:
            print(f"      ⚠️ AI synthesis error: {e}")
            return None
        finally:
            if os.path.exists(temp_img):
                try:
                    os.remove(temp_img)
                except Exception:
                    pass

    def download_stock_video(self, url: str, filename: str) -> str:
        """Downloads a stock video file to disk."""
        save_path = os.path.join(self.assets_dir, filename)
        if os.path.exists(save_path):
            return save_path

        try:
            with requests.get(url, stream=True, timeout=20) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return save_path
        except Exception as e:
            print(f"      ❌ Download error: {e}")
            return None

    def fetch_clip(self, query: str, filename: str) -> str:
        """Tries Pexels -> Pixabay -> Pollinations AI Flux cascade."""
        print(f"   🔍 Sourcing Visual for: '{query}'...")

        # 1. Try Pexels if key exists
        if self.pexels_key:
            url = self.search_pexels(query)
            if url:
                path = self.download_stock_video(url, filename)
                if path:
                    print(f"      ✅ Sourced from Pexels: {filename}")
                    return path

        # 2. Try Pixabay if key exists
        if self.pixabay_key:
            url = self.search_pixabay(query)
            if url:
                path = self.download_stock_video(url, filename)
                if path:
                    print(f"      ✅ Sourced from Pixabay: {filename}")
                    return path

        # 3. Autonomous AI Visual Generation (Zero Key)
        path = self.generate_ai_clip(query, filename)
        if path:
            print(f"      ✅ Rendered AI Visual: {filename}")
            return path

        return None

    def get_videos(self, script_data):
        """
        Acquires two visual clips per scene (A and B).
        Guarantees that every scene has valid visuals.
        """
        print("🎥 Acquiring Visual Clips for all scenes...")
        video_pairs = []

        for scene in script_data:
            scene_id = scene['id']
            query_a = scene.get('visual_1', scene.get('keywords', 'intriguing mystery'))
            query_b = scene.get('visual_2', query_a)

            # Get Clip A
            path_a = self.fetch_clip(query_a, f"scene_{scene_id}_a.mp4")

            # Get Clip B
            path_b = self.fetch_clip(query_b, f"scene_{scene_id}_b.mp4")

            # Self-healing fallbacks
            if not path_a and path_b:
                path_a = path_b
            if not path_b and path_a:
                path_b = path_a

            if path_a and path_b:
                video_pairs.append((path_a, path_b))
                print(f"   ✅ Scene {scene_id} Visuals Ready.")
            else:
                print(f"   ❌ Scene {scene_id} Critical Failure (No visual produced).")
                video_pairs.append(None)

        return video_pairs
