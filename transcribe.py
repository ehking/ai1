#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from typing import Tuple, List, Dict, Any

try:
    import whisper
except Exception:
    whisper = None


def transcribe_audio(audio_path: str, cache_dir: str, model_name: str = "small") -> Tuple[list, str]:
    os.makedirs(cache_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    out_json = os.path.join(cache_dir, f"segments_{base}.json")

    if os.path.exists(out_json):
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["segments"], out_json

    if whisper is None:
        segments = [{
            "start": 0.0,
            "end": 5.0,
            "text": "برای استفاده از whisper آن را نصب کنید."
        }]
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)
        return segments, out_json

    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, language="fa")

    segments: List[Dict[str, Any]] = []
    for seg in result.get("segments", []):
        segments.append({
            "start": float(seg.get("start", 0.0)),
            "end": float(seg.get("end", 0.0)),
            "text": seg.get("text", "").strip(),
        })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)

    return segments, out_json
