#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLAlchemy models:
- Project
- Job
- Media
- Config
"""

import os
import datetime
import json

from sqlalchemy import (
    create_engine, Column, Integer, String,
    DateTime, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    return SessionLocal()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    audio_path = Column(Text, nullable=False)
    video_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    medias = relationship("Media", back_populates="project", cascade="all, delete-orphan")


class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    primary_color = Column(String(32), default="#F7F2EB")
    accent_color = Column(String(32), default="#ec4899")
    bg_color = Column(String(32), default="#050510")
    border_color = Column(String(32), default="#FFFFFF")
    font_name = Column(String(128), default="Yekan")

    advanced_json = Column(Text, default="{}")

    created_at = Column(DateTime, default=datetime.datetime.now)

    jobs = relationship("Job", back_populates="config")

    def to_config_dict(self):
        try:
            adv = json.loads(self.advanced_json or "{}")
        except Exception:
            adv = {}
        text_cfg = adv.get("text", {})
        video_cfg = adv.get("video", {})
        return {
            "name": self.name,
            "primary_color": self.primary_color,
            "accent_color": self.accent_color,
            "bg_color": self.bg_color,
            "border_color": self.border_color,
            "font_name": self.font_name,
            "text": text_cfg,
            "video": video_cfg,
        }


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(64), nullable=False, unique=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    audio_path = Column(Text, nullable=False)
    video_path = Column(Text, nullable=False)
    output_path = Column(Text, nullable=True)

    config_id = Column(Integer, ForeignKey("configs.id"), nullable=True)

    title = Column(String(255), nullable=True)
    tags = Column(String(512), nullable=True)

    status = Column(String(32), default="queued")  # queued, running, done, error, cancelled
    progress = Column(Integer, default=0)
    message = Column(Text, default="")
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now)

    project = relationship("Project", back_populates="jobs")
    medias = relationship("Media", back_populates="job")
    config = relationship("Config", back_populates="jobs")

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "project_id": self.project_id,
            "audio_path": self.audio_path,
            "video_path": self.video_path,
            "output_path": self.output_path,
            "config_id": self.config_id,
            "title": self.title,
            "tags": self.tags,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "created_at": self.created_at.isoformat(sep=" ", timespec="seconds") if self.created_at else None,
            "updated_at": self.updated_at.isoformat(sep=" ", timespec="seconds") if self.updated_at else None,
        }


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)

    file_path = Column(Text, nullable=False)
    media_type = Column(String(32), default="video")
    created_at = Column(DateTime, default=datetime.datetime.now)

    project = relationship("Project", back_populates="medias")
    job = relationship("Job", back_populates="medias")


def ensure_default_configs():
    db = get_session()
    try:
        if db.query(Config).first():
            return

        import json as _json

        presets = [
            Config(
                name="تیره کالیگرافی",
                description="پس‌زمینه‌ی تیره و متن روشن با پالس نرم روی ضرب.",
                primary_color="#F9F5FF",
                accent_color="#ec4899",
                bg_color="#020617",
                border_color="#94a3b8",
                font_name="Yekan",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.5,
                        "rotate_deg": -8,
                        "stroke_width": 4.5,
                        "pulse_rt": 0.09
                    },
                    "video": {
                        "filter_chain": "eq=contrast=1.08:saturation=1.1, vignette"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="نوستالژیک قهوه‌ای",
                description="فضای گرم و نوستالژیک برای آهنگ‌های احساسی.",
                primary_color="#fef3c7",
                accent_color="#f97316",
                bg_color="#3b2516",
                border_color="#facc15",
                font_name="Yekan",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.4,
                        "rotate_deg": -12,
                        "stroke_width": 4.0,
                        "pulse_rt": 0.1
                    },
                    "video": {
                        "filter_chain": "curves=vintage, eq=saturation=0.9:gamma=0.95"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="نئونی مدرن",
                description="نئون بنفش/سبز برای تم‌های مدرن.",
                primary_color="#a855f7",
                accent_color="#22c55e",
                bg_color="#020617",
                border_color="#22c55e",
                font_name="Yekan",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.3,
                        "rotate_deg": -4,
                        "stroke_width": 3.5,
                        "pulse_rt": 0.07
                    },
                    "video": {
                        "filter_chain": "eq=saturation=1.2:contrast=1.1, curves=negative"
                    }
                }, ensure_ascii=False),
            ),
        ]
        for p in presets:
            db.add(p)
        db.commit()
    finally:
        db.close()
