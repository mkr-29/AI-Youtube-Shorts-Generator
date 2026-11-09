import os
import glob
import random
import ffmpeg
from modules.subtitle_renderer import SubtitleRenderer
from modules.avatar_engine import AvatarEngine

class Composer:
    def __init__(self):
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        self.final_dir = os.path.join(os.getcwd(), "assets", "final")
        self.avatar_path = os.path.join(os.getcwd(), "assets", "avatar", "avatars.mp4")
        self.music_dir = os.path.join(os.getcwd(), "assets", "music")
        
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.final_dir, exist_ok=True)
        os.makedirs(self.music_dir, exist_ok=True)
        
        self.transitions = ['fade', 'diagbr', 'diagtl']
        self.subtitle_renderer = SubtitleRenderer()
        self.avatar_engine = AvatarEngine()

    def get_duration(self, filepath):
        try:
            probe = ffmpeg.probe(filepath)
            return float(probe['format']['duration'])
        except Exception:
            return 0.0

    def process_scene(self, scene, video_pair, is_avatar=False, is_dynamic_avatar=False):
        """
        Combines Audio with Visuals, injecting dual stock clips or contextual avatar,
        and burning kinetic subtitles.
        """
        scene_id = scene['id']
        audio_path = scene['audio_path']
        sub_path = scene.get('sub_path')
        word_cues = scene.get('word_cues', [])
        total_duration = scene['duration']
        output_path = os.path.join(self.temp_dir, f"scene_{scene_id}.mp4")

        try:
            input_audio = ffmpeg.input(audio_path)

            if is_avatar:
                if is_dynamic_avatar and video_pair[0]:
                    print(f"   👤 Processing Scene {scene_id}: 🌟 Dynamic Character Avatar Mode")
                    video_stream = (
                        ffmpeg.input(video_pair[0])
                        .trim(duration=total_duration + 0.5)
                        .setpts('PTS-STARTPTS')
                        .filter('scale', 1080, 1920, force_original_aspect_ratio='increase')
                        .filter('crop', 1080, 1920)
                        .filter('fps', fps=30, round='up')
                    )
                else:
                    print(f"   ⚙️ Processing Scene {scene_id}: 🤖 Legacy Avatar Mode (Cropped)")
                    video_stream = (
                        ffmpeg.input(video_pair[0], stream_loop=-1)
                        .trim(duration=total_duration + 0.5)
                        .setpts('PTS-STARTPTS')
                        .filter('crop', 'iw', 'ih-150', 0, 0)
                        .filter('scale', 1080, 1920, force_original_aspect_ratio='increase')
                        .filter('crop', 1080, 1920)
                        .filter('fps', fps=30, round='up')
                    )
            else:
                print(f"   ⚙️ Processing Scene {scene_id}: 🎞️ A/B Split Mode")
                path_a, path_b = video_pair
                duration_a = total_duration / 2
                duration_b = (total_duration / 2) + 0.5

                stream_a = (
                    ffmpeg.input(path_a, stream_loop=-1)
                    .trim(duration=duration_a)
                    .setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase')
                    .filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                )

                stream_b = (
                    ffmpeg.input(path_b, stream_loop=-1)
                    .trim(duration=duration_b)
                    .setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase')
                    .filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                )

                video_stream = ffmpeg.concat(stream_a, stream_b, v=1, a=0)

            # --- SUBTITLE BURNING LAYER ---
            if sub_path and os.path.exists(sub_path):
                if self.subtitle_renderer.has_libass:
                    print(f"   💬 Burning Subtitles (libass): Scene {scene_id}")
                    video_stream = video_stream.filter('subtitles', sub_path)
                elif word_cues:
                    print(f"   💬 Burning Subtitles (Pillow overlay fallback): Scene {scene_id}")
                    overlay_mov = os.path.join(self.temp_dir, f"sub_overlay_{scene_id}.mov")
                    self.subtitle_renderer.render_overlay_clip(word_cues, total_duration + 0.5, overlay_mov)
                    if os.path.exists(overlay_mov):
                        sub_stream = ffmpeg.input(overlay_mov)
                        video_stream = ffmpeg.overlay(video_stream, sub_stream)

            # Combine Video + Audio
            runner = ffmpeg.output(
                video_stream, 
                input_audio, 
                output_path, 
                vcodec='libx264', 
                acodec='aac', 
                pix_fmt='yuv420p',
                shortest=None
            )
            
            runner.run(overwrite_output=True, quiet=True)
            return output_path

        except ffmpeg.Error as e:
            err = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"❌ Render Fail Scene {scene_id}: {err}")
            return None

    def render_all_scenes(self, script_data, video_pairs):
        rendered_paths = []
        avatar_indices = []
        use_dynamic_avatar = self.avatar_engine.persona.get("enabled", True)

        # 1. Identify which scenes should be Avatar scenes
        # First check if script explicitly flagged avatar scenes
        flagged_indices = [i for i, s in enumerate(script_data) if s.get("is_avatar")]
        if flagged_indices:
            avatar_indices = flagged_indices
        elif use_dynamic_avatar and len(script_data) >= 4:
            # Auto-assign 1 or 2 middle scenes if none explicitly flagged
            valid_range = list(range(1, len(script_data) - 1))
            count_to_pick = min(self.avatar_engine.persona.get("avatar_scenes_count", 2), len(valid_range))
            avatar_indices = sorted(random.sample(valid_range, count_to_pick))

        if avatar_indices:
            human_readable = [i + 1 for i in avatar_indices]
            print(f"👤 Character Avatar scheduled for Scenes: {human_readable}")

        for i, scene in enumerate(script_data):
            current_pair = video_pairs[i] if i < len(video_pairs) else None
            is_avatar = False
            is_dynamic_avatar = False

            if i in avatar_indices:
                is_avatar = True
                # Generate dynamic contextual avatar video
                if use_dynamic_avatar:
                    avatar_video = self.avatar_engine.render_scene(scene)
                    if avatar_video:
                        current_pair = (avatar_video, None)
                        is_dynamic_avatar = True
                
                # Fallback to legacy avatar if dynamic generation was unavailable
                if not is_dynamic_avatar and os.path.exists(self.avatar_path):
                    current_pair = (self.avatar_path, None)

            if current_pair is None:
                continue 

            output_path = self.process_scene(scene, current_pair, is_avatar, is_dynamic_avatar)
            if output_path:
                rendered_paths.append(output_path)
        
        return rendered_paths

    def concatenate_with_transitions(self, video_paths, output_filename="final_short.mp4"):
        print("🎬 Stitching final video with transitions & audio...")
        output_path = os.path.join(self.final_dir, output_filename)
        
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        if not video_paths:
            return None

        input1 = ffmpeg.input(video_paths[0])
        v_stream = input1.video
        a_stream = input1.audio
        current_dur = self.get_duration(video_paths[0])

        for i in range(1, len(video_paths)):
            next_clip = ffmpeg.input(video_paths[i])
            next_dur = self.get_duration(video_paths[i])
            
            trans_dur = 0.5
            offset = max(current_dur - trans_dur, 0)
            effect = random.choice(self.transitions)
            print(f"   ✨ Transition {i}: '{effect}' at {offset:.2f}s")

            v_stream = ffmpeg.filter(
                [v_stream, next_clip.video], 
                'xfade', 
                transition=effect, 
                duration=trans_dur, 
                offset=offset
            )
            
            a_stream = ffmpeg.filter(
                [a_stream, next_clip.audio], 
                'acrossfade', 
                d=trans_dur
            )
            
            current_dur = (current_dur + next_dur) - trans_dur

        # --- BACKGROUND MUSIC DUCKING LAYER ---
        music_tracks = glob.glob(os.path.join(self.music_dir, "*.mp3")) + glob.glob(os.path.join(self.music_dir, "*.wav"))
        final_a_stream = a_stream

        if music_tracks:
            selected_music = random.choice(music_tracks)
            print(f"🎵 Adding background music (ducked at 8% volume): {os.path.basename(selected_music)}")
            bgm_input = (
                ffmpeg.input(selected_music, stream_loop=-1)
                .filter('volume', 0.08)
            )
            final_a_stream = ffmpeg.filter([a_stream, bgm_input], 'amix', inputs=2, duration='first')

        try:
            runner = ffmpeg.output(
                v_stream, 
                final_a_stream, 
                output_path, 
                vcodec='libx264',
                acodec='aac',
                pix_fmt='yuv420p',
                movflags='faststart',
                preset='medium' 
            )
            
            runner.run(overwrite_output=True, quiet=False)
            print(f"✅ FINAL VIDEO SAVED: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            error_log = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"❌ Stitching Error: {error_log}")
            return None
