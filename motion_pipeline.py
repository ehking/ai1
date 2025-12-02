#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import uuid
from typing import Callable, Dict, Any

from transcribe import transcribe_audio
from beat_analysis import analyze_beats

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def process_job(
    audio_path: str,
    video_path: str,
    output_dir: str,
    progress_callback: Callable[[int, str], None] | None = None,
    quality: str = "h",
    config: Dict[str, Any] | None = None,
) -> str:
    job_id = str(uuid.uuid4())[:8]
    job_tmp = os.path.join(BASE_DIR, "workdir", f"job_{job_id}")
    _ensure_dir(job_tmp)
    _ensure_dir(output_dir)

    def update(p, m):
        if progress_callback:
            progress_callback(p, m)

    update(10, "در حال تبدیل و تشخیص گفتار (Whisper)...")
    segments, _ = transcribe_audio(audio_path, job_tmp)

    update(25, "تحلیل ضرب آهنگ (Beat Tracking)...")
    _, beats_list = analyze_beats(audio_path, job_tmp)

    update(40, "آماده‌سازی کانفیگ بصری برای Manim...")
    config = config or {}
    meta = {
        "audio_path": audio_path,
        "video_path": video_path,
        "segments": segments,
        "beats": beats_list,
        "visual": config,
    }
    meta_path = os.path.join(job_tmp, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    update(60, "رندر متن با Manim...")
    manim_video = run_manim(meta_path, quality=quality)

    update(80, "ترکیب ویدیو زمینه و متن (ffmpeg)...")
    final_out = os.path.join(output_dir, f"final_job_{job_id}.mp4")
    overlay_with_ffmpeg(video_path, manim_video, audio_path, final_out, (config.get("video") if config else {}) or {})

    update(100, "پایان کار")
    return final_out


def run_manim(meta_path: str, quality: str = "h") -> str:
    env = os.environ.copy()
    env["FARSI_MOTION_META"] = meta_path

    qflag = f"-q{quality}"
    cmd = ["manim", qflag, "-t", "motion.py", "FarsiKinetic"]
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env)

    media_dir = os.path.join(BASE_DIR, "media", "videos", "motion")
    for root, _, files in os.walk(media_dir):
        for fn in files:
            if fn.startswith("FarsiKinetic") and fn.endswith(".mov"):
                return os.path.join(root, fn)
    raise FileNotFoundError("خروجی Manim (FarsiKinetic.mov) پیدا نشد.")


def overlay_with_ffmpeg(base_video: str, overlay_video: str, audio_path: str, output_path: str, video_cfg: Dict[str, Any]):
    filter_chain = video_cfg.get("filter_chain", "")
    if filter_chain:
        vf = f"[0:v]{filter_chain}[b];[b][1:v]overlay=(W-w)/2:(H-h)/2:shortest=1[v]"
    else:
        vf = "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:shortest=1[v]"

    cmd = [
        "ffmpeg", "-y",
        "-i", base_video,
        "-i", overlay_video,
        "-i", audio_path,
        "-filter_complex", vf,
        "-map", "[v]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, check=True)
