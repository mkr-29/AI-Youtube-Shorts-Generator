import os
import asyncio
import edge_tts
from mutagen.mp3 import MP3
from modules.subtitle_renderer import SubtitleRenderer

class AudioEngine:
    def __init__(self, voice="en-US-AvaNeural"):
        self.voice = voice
        self.output_dir = os.path.join(os.getcwd(), "assets", "audio_clips")
        os.makedirs(self.output_dir, exist_ok=True)
        self.subtitle_renderer = SubtitleRenderer()

    async def generate_audio_and_subtitles(self, text: str, scene_id: int, retries: int = 3):
        """
        Generates high-quality MP3 voiceover and timed subtitle cues with WordBoundary precision.
        """
        audio_filename = f"voice_{scene_id}.mp3"
        sub_filename = f"sub_{scene_id}.ass"
        output_audio_path = os.path.join(self.output_dir, audio_filename)
        output_sub_path = os.path.join(self.output_dir, sub_filename)

        for attempt in range(retries):
            try:
                # Rate +10% for punchy short-form engagement
                communicate = edge_tts.Communicate(
                    text,
                    self.voice,
                    rate="+10%",
                    boundary="WordBoundary"
                )

                word_cues = []
                with open(output_audio_path, "wb") as audio_file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            start_sec = chunk["offset"] / 10_000_000.0
                            duration_sec = chunk["duration"] / 10_000_000.0
                            word_cues.append({
                                "word": chunk["text"],
                                "start": start_sec,
                                "end": start_sec + duration_sec
                            })

                # If no word cues were emitted, fall back to sentence-level timing
                if not word_cues:
                    duration = self.get_audio_duration(output_audio_path)
                    word_cues.append({"word": text, "start": 0.0, "end": max(duration, 1.0)})

                # Generate stylized .ass subtitle file
                self.subtitle_renderer.generate_ass(word_cues, output_sub_path)
                return output_audio_path, output_sub_path, word_cues

            except Exception as e:
                print(f"      ⚠️ Audio Error (Attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    print("      ❌ Failed to generate audio after max retries.")
                    raise e

    def get_audio_duration(self, file_path):
        try:
            audio = MP3(file_path)
            return audio.info.length
        except Exception as e:
            print(f"❌ Error reading audio length: {e}")
            return 0.0

    async def process_script(self, script_data):
        print(f"🎙️ Starting Audio & Subtitle Generation for {len(script_data)} scenes...")
        narrated = []

        for scene in script_data:
            scene_id = scene['id']
            text = scene['text']

            try:
                audio_path, sub_path, word_cues = await self.generate_audio_and_subtitles(text, scene_id)
                duration = self.get_audio_duration(audio_path)
                if duration <= 0:
                    print(f"   ❌ Skipping Scene {scene_id}: unreadable audio duration.")
                    continue

                scene['audio_path'] = audio_path
                scene['sub_path'] = sub_path
                scene['word_cues'] = word_cues
                scene['duration'] = duration
                narrated.append(scene)

                print(f"   ✅ Scene {scene_id}: {duration:.2f}s generated with word-level subtitles.")

                # Polite pause to prevent connection rate-limits
                await asyncio.sleep(1)

            except Exception as e:
                print(f"   ❌ Skipping Scene {scene_id} due to audio error: {e}")
                continue

        if len(narrated) < len(script_data):
            print(f"   ⚠️ {len(script_data) - len(narrated)} scene(s) dropped without audio.")

        return narrated
