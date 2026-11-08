import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

class SubtitleRenderer:
    """
    Renders high-retention, centered kinetic subtitles for vertical (9:16) videos.
    Supports native FFmpeg libass filter when available, with automatic fallback
    to Pillow-generated transparent frame overlays for platforms without libass.
    """

    def __init__(self, width=1080, height=1920):
        self.width = width
        self.height = height
        self.has_libass = self._check_libass()

    def _check_libass(self) -> bool:
        """Check if current ffmpeg installation supports the subtitles filter."""
        try:
            res = subprocess.run(
                ["ffmpeg", "-filters"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return " subtitles " in res.stdout
        except Exception:
            return False

    def generate_ass(self, word_cues, output_path: str):
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file with viral styling:
        - Uppercase
        - Bold with black outline
        - Yellow / White highlight
        - Centered in the middle-lower 9:16 safe area
        """
        header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,76,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,5,80,80,960,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        # Group into 2-3 word chunks for rapid modern short pacing
        chunk_size = 3
        for i in range(0, len(word_cues), chunk_size):
            chunk = word_cues[i:i + chunk_size]
            start_sec = chunk[0]["start"]
            end_sec = chunk[-1]["end"]
            
            # Format times as H:MM:SS.cs
            start_str = self._format_ass_time(start_sec)
            end_str = self._format_ass_time(end_sec)
            
            # Capitalized words with yellow highlight on first word
            words = [w["word"].upper().strip() for w in chunk]
            if len(words) > 1:
                highlighted_text = f"{{\\c&H0000FFFF&}}{words[0]}{{\\c&H00FFFFFF&}} {' '.join(words[1:])}"
            else:
                highlighted_text = f"{{\\c&H0000FFFF&}}{words[0]}"
                
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{highlighted_text}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))

    def _format_ass_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    def render_overlay_clip(self, word_cues, duration: float, output_video_path: str):
        """
        Creates a transparent overlay video clip using Pillow frames when FFmpeg
        lacks the subtitles filter. Ensures 100% cross-platform compatibility.
        """
        temp_dir = os.path.join(os.path.dirname(output_video_path), "sub_frames")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            font = None
            font_candidates = [
                "/System/Library/Fonts/Supplemental/Arial Black.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "Arial.ttf"
            ]
            for candidate in font_candidates:
                if os.path.exists(candidate):
                    try:
                        font = ImageFont.truetype(candidate, 68)
                        break
                    except Exception:
                        continue
            if not font:
                font = ImageFont.load_default()

            fps = 10
            total_frames = int(duration * fps) + 1
            chunk_size = 3

            for frame_idx in range(total_frames):
                current_time = frame_idx / fps
                active_chunk = None

                for i in range(0, len(word_cues), chunk_size):
                    chunk = word_cues[i:i + chunk_size]
                    if chunk[0]["start"] <= current_time <= chunk[-1]["end"]:
                        active_chunk = chunk
                        break

                img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)

                if active_chunk:
                    text = " ".join([w["word"].upper().strip() for w in active_chunk])
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    x = (self.width - text_w) // 2
                    y = int(self.height * 0.58)

                    # Draw thick black outline
                    for ox in range(-5, 6):
                        for oy in range(-5, 6):
                            draw.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, 255))
                    # Draw vibrant yellow main text
                    draw.text((x, y), text, font=font, fill=(255, 235, 59, 255))

                frame_file = os.path.join(temp_dir, f"frame_{frame_idx:05d}.png")
                img.save(frame_file)

            # Assemble into transparent ProRes/PNG video
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "png",
                "-pix_fmt", "rgba",
                "-t", str(duration),
                output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_video_path

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

