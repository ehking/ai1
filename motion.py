from __future__ import annotations
# -*- coding: utf-8 -*-

import os
import json
import math
from typing import Dict, Any, List

from manim import *


def load_meta() -> Dict[str, Any]:
    meta_path = os.environ.get("FARSI_MOTION_META")
    if not meta_path or not os.path.exists(meta_path):
        return {"segments": [], "beats": [], "visual": {}}
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


class FarsiKinetic(Scene):
    def construct(self):
        meta = load_meta()
        visual = meta.get("visual", {})
        text_cfg = visual.get("text", {})

        font_name = visual.get("font_name", "Yekan")
        primary_color = visual.get("primary_color", "#F9F5FF")
        accent_color = visual.get("accent_color", "#ec4899")

        base_scale = text_cfg.get("base_scale", 1.4)
        rotate_deg = text_cfg.get("rotate_deg", -10)
        stroke_width = text_cfg.get("stroke_width", 4.0)
        pulse_rt = text_cfg.get("pulse_rt", 0.09)

        segments: List[Dict[str, Any]] = meta.get("segments", [])
        if not segments:
            segments = [{"start": 0.0, "end": 4.0, "text": "نمونه موشن فارسی"}]

        current_time = 0.0
        for seg in segments:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start + 3.0))
            duration = max(0.5, end - start)
            text = seg.get("text", "").strip() or "..."

            gap = max(0.0, start - current_time)
            if gap > 0:
                self.wait(gap)
                current_time += gap

            line = Text(
                text,
                font=font_name,
                color=primary_color,
                slant=ITALIC,
                weight=BOLD,
            )
            line.scale(base_scale)
            line.rotate(math.radians(rotate_deg))
            line.move_to(ORIGIN)

            stroke = line.copy().set_stroke(color=accent_color, width=stroke_width, opacity=0.4)
            stroke.set_fill(opacity=0)

            group = VGroup(stroke, line)
            group.move_to(ORIGIN)

            self.play(
                FadeIn(stroke, shift=0.2 * DOWN),
                FadeIn(line, shift=0.2 * UP),
                run_time=0.5,
            )

            pulses = max(1, int(duration / max(pulse_rt, 0.4)))
            for _ in range(pulses):
                self.play(
                    line.animate.scale(1.04),
                    stroke.animate.set_stroke(width=stroke_width + 1.0),
                    run_time=pulse_rt,
                    rate_func=there_and_back,
                )

            self.wait(max(0.2, duration - pulses * pulse_rt))
            self.play(
                FadeOut(group, shift=0.3 * DOWN),
                run_time=0.5,
            )
            current_time = end
