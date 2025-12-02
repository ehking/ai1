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
from sqlalchemy import inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
# NOTE: For SQLite, add/remove columns by deleting app.db once to recreate tables or
# write a migration script; keep backups of your media/output paths if you do that.
# After refactors (like moving audio/video paths off Project), drop the old app.db
# or migrate manually so the new schema takes effect.

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    return SessionLocal()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True, default="")
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

    music_type = Column(String(16), nullable=True)  # None: عمومی

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

    job_type = Column(String(64), default="standard")
    wizard_data = Column(Text, nullable=True)

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
            "job_type": self.job_type,
            "wizard_data": self.wizard_data,
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
                name="تیره کالیگرافی ایرانی",
                description="پس‌زمینه‌ی تیره و متن روشن با پالس نرم روی ضرب.",
                primary_color="#F9F5FF",
                accent_color="#ec4899",
                bg_color="#0b1220",
                border_color="#94a3b8",
                font_name="Yekan",
                music_type="iranian",
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
                music_type="iranian",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.35,
                        "rotate_deg": -12,
                        "stroke_width": 4.0,
                        "pulse_rt": 0.11
                    },
                    "video": {
                        "filter_chain": "curves=vintage, eq=saturation=0.92:gamma=0.96"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="نئونی مدرن خارجی",
                description="نئون بنفش/سبز برای تم‌های مدرن خارجی.",
                primary_color="#a855f7",
                accent_color="#22c55e",
                bg_color="#0f172a",
                border_color="#22c55e",
                font_name="Yekan",
                music_type="foreign",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.3,
                        "rotate_deg": -4,
                        "stroke_width": 3.5,
                        "pulse_rt": 0.07
                    },
                    "video": {
                        "filter_chain": "eq=saturation=1.2:contrast=1.12, curves=negative"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="نوستالژیک خارجی",
                description="تم سینماتیک با کنتراست بالا برای قطعات خارجی.",
                primary_color="#e2e8f0",
                accent_color="#22d3ee",
                bg_color="#0b1220",
                border_color="#475569",
                font_name="Yekan",
                music_type="foreign",
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.25,
                        "rotate_deg": -6,
                        "stroke_width": 3.8,
                        "pulse_rt": 0.08
                    },
                    "video": {
                        "filter_chain": "eq=brightness=1.02:contrast=1.15:saturation=1.05, vignette"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="موج رنگی عمومی",
                description="کانفیگ عمومی با موج رنگی ویدیو.",
                primary_color="#f8fafc",
                accent_color="#fb7185",
                bg_color="#1f2937",
                border_color="#e5e7eb",
                font_name="Yekan",
                music_type=None,
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.4,
                        "rotate_deg": -10,
                        "stroke_width": 4.2,
                        "pulse_rt": 0.1
                    },
                    "video": {
                        "filter_chain": "colorbalance=rs=.2:gs=-.05:bs=-.05, curves=strong_contrast"
                    }
                }, ensure_ascii=False),
            ),
            Config(
                name="مینیمال روشن",
                description="متن مینیمال با پس‌زمینه‌ی روشن و کنتراست نرم.",
                primary_color="#0f172a",
                accent_color="#f59e0b",
                bg_color="#f8fafc",
                border_color="#cbd5e1",
                font_name="Yekan",
                music_type=None,
                advanced_json=_json.dumps({
                    "text": {
                        "base_scale": 1.15,
                        "rotate_deg": -3,
                        "stroke_width": 2.8,
                        "pulse_rt": 0.12
                    },
                    "video": {
                        "filter_chain": "eq=contrast=1.03:saturation=1.08"
                    }
                }, ensure_ascii=False),
            ),
        ]
        for p in presets:
            db.add(p)
        db.commit()
    finally:
        db.close()


def ensure_job_columns():
    """Ensure new Job columns exist even on older SQLite files."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('jobs')}

    alter_sql = []
    if "job_type" not in columns:
        alter_sql.append("ALTER TABLE jobs ADD COLUMN job_type VARCHAR(64) DEFAULT 'standard'")
    if "wizard_data" not in columns:
        alter_sql.append("ALTER TABLE jobs ADD COLUMN wizard_data TEXT")

    if not alter_sql:
        return

    with engine.begin() as conn:
        for stmt in alter_sql:
            conn.exec_driver_sql(stmt)
