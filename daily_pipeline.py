#!/usr/bin/env python3
"""
AutoShorts AI — Pipeline Diário de Automação Total.
1. Gerar novos vídeos com IA (IA escolhe tópicos em alta e cria roteiro, narração e edição)
2. Criar metadados virais (título, descrição e 20 tags virais com Gemini)
3. Fazer upload automático para o YouTube Shorts

Uso:
    python daily_pipeline.py --count 2          # Gerar e publicar 2 vídeos agora
    python daily_pipeline.py --generate-only    # Apenas gerar sem subir
    python daily_pipeline.py --upload-only      # Apenas subir pendentes
"""

import os
import sys
import argparse
import asyncio
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from main import main_async, parse_args as parse_main_args
from upload_scheduled import upload_batch, show_status, log


async def run_daily_pipeline(count=2, generate_only=False, upload_only=False, lang="en"):
    log("\n" + "═" * 60)
    log(f"🚀 STARTING AUTONOMOUS DAILY PIPELINE [{lang}] — AUTOSHORTS AI")
    log("═" * 60)

    # 1. VIDEO GENERATION WITH AI
    if not upload_only:
        log(f"\n🎬 [STAGE 1/3] Generating {count} new video(s) [{lang}] with AI...")
        log("   • AI selecting high-retention trending topics")
        log("   • Crafting edutainment beat table script (Gemini Pro)")
        log(f"   • Synthesizing neural voiceover & word-level subtitles ({lang})")
        log("   • Harvesting HD vertical clips on Pexels")
        log("   • Rendering final video with dynamic transitions & kinetic captions (FFmpeg)...")

        main_args = parse_main_args(["--runs", str(count), "--lang", lang])
        try:
            exit_code = await main_async(main_args)
            if exit_code == 0:
                log("✅ [STAGE 1/3] Video generation completed successfully!")
            else:
                log("⚠️ [STAGE 1/3] Some videos might not have completed rendering.")
        except Exception as e:
            log(f"❌ [STAGE 1/3] Error during video generation: {e}")
            if generate_only:
                return 1

    if generate_only:
        log("✨ Generation stage completed (--generate-only active).")
        return 0

    # 2. UPLOAD TO YOUTUBE AND INSTAGRAM
    log(f"\n📤 [STAGE 2/3 & 3/3] Generating viral metadata & publishing to YouTube Shorts and Instagram Reels...")
    res = upload_batch(count=count)

    log("\n" + "═" * 60)
    log("🎉 DAILY PIPELINE COMPLETED!")
    log("═" * 60 + "\n")
    return res


def main():
    parser = argparse.ArgumentParser(description="Autonomous Daily Pipeline (Generation + Multi-Platform Upload)")
    parser.add_argument("--count", type=int, default=1, help="Number of videos to generate and publish per day (default: 1)")
    parser.add_argument("--lang", choices=["pt-BR", "en"], default="en", help="Language for generated videos (default: en)")
    parser.add_argument("--generate-only", action="store_true", help="Generate videos only, without uploading")
    parser.add_argument("--upload-only", action="store_true", help="Upload pending videos only")
    parser.add_argument("--status", action="store_true", help="Show upload status and history")

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    return asyncio.run(run_daily_pipeline(
        count=args.count,
        generate_only=args.generate_only,
        upload_only=args.upload_only,
        lang=args.lang
    ))


if __name__ == "__main__":
    sys.exit(main())
