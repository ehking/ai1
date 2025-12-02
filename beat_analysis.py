#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from typing import Tuple, List

try:
    import librosa
except Exception:
    librosa = None


def analyze_beats(audio_path: str, cache_dir: str) -> Tuple[str, List[float]]:
    os.makedirs(cache_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    out_json = os.path.join(cache_dir, f"beats_{base}.json")

    if os.path.exists(out_json):
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return out_json, data.get("beats", [])

    if librosa is None:
        beats: List[float] = []
    else:
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = (beat_frames / float(sr)).tolist()

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"beats": beats}, f, ensure_ascii=False, indent=2)

    return out_json, beats
