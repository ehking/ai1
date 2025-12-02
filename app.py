#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
import queue
import uuid
import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, send_from_directory, flash, jsonify
)
from sqlalchemy.orm import Session

from models import (
    engine, Base, Project, Job, Media, Config,
    get_session, ensure_default_configs
)
import motion_pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-secret"

Base.metadata.create_all(bind=engine)
ensure_default_configs()

JOB_QUEUE: "queue.Queue[int]" = queue.Queue()
ALLOWED_MUSIC_TYPES = {"iranian", "foreign"}


def enqueue_job(project_id: int, audio_path: str, video_path: str,
                title: str = "", tags: str = "", config_id: int | None = None) -> int:
    db: Session = get_session()
    try:
        job = Job(
            uuid=str(uuid.uuid4())[:8],
            project_id=project_id,
            audio_path=audio_path,
            video_path=video_path,
            status="queued",
            progress=0,
            message="در صف انتظار...",
            title=title or "Job",
            tags=tags or "",
            config_id=config_id,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        JOB_QUEUE.put(job.id)
        return job.id
    finally:
        db.close()


def worker_loop():
    while True:
        job_id = JOB_QUEUE.get()
        db: Session = get_session()
        try:
            job = db.get(Job, job_id)
            if not job:
                JOB_QUEUE.task_done()
                db.close()
                continue

            if job.status == "cancelled":
                JOB_QUEUE.task_done()
                db.close()
                continue

            job.status = "running"
            job.progress = 5
            job.message = "شروع پردازش..."
            job.updated_at = datetime.datetime.now()
            db.commit()

            conf_dict = None
            if job.config_id:
                cfg = db.get(Config, job.config_id)
                if cfg:
                    conf_dict = cfg.to_config_dict()

            def progress_cb(percent, msg):
                j = db.get(Job, job_id)
                if not j:
                    return
                if j.status == "cancelled":
                    return
                j.progress = max(0, min(100, int(percent)))
                j.message = msg
                j.updated_at = datetime.datetime.now()
                db.commit()

            try:
                output_path = motion_pipeline.process_job(
                    audio_path=job.audio_path,
                    video_path=job.video_path,
                    output_dir=OUTPUT_DIR,
                    progress_callback=progress_cb,
                    quality="h",
                    config=conf_dict,
                )

                if job.status != "cancelled":
                    media = Media(
                        project_id=job.project_id,
                        job_id=job.id,
                        file_path=output_path,
                        media_type="video",
                        created_at=datetime.datetime.now(),
                    )
                    db.add(media)

                    job.status = "done"
                    job.progress = 100
                    job.message = "تمام شد ✅"
                    job.output_path = output_path
                    job.updated_at = datetime.datetime.now()
                    db.commit()

            except Exception as e:
                job.status = "error"
                job.progress = 0
                job.message = "خطا در اجرای جاب"
                job.error = str(e)
                job.updated_at = datetime.datetime.now()
                db.commit()

        finally:
            JOB_QUEUE.task_done()
            db.close()


worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()


def _save_upload(file_obj, subdir: str) -> str:
    if not file_obj or not file_obj.filename:
        return ""
    folder = os.path.join(UPLOAD_DIR, subdir)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, file_obj.filename)
    file_obj.save(path)
    return path


def _normalize_music_type(value: str | None, default: str = "iranian") -> str:
    if value in ALLOWED_MUSIC_TYPES:
        return value
    return default


def _filter_configs_for_project(configs, music_type: str | None):
    if not music_type:
        return configs
    return [c for c in configs if (c.music_type is None or c.music_type == music_type)]


def _render_projects_page(db: Session, music_filter: str | None = None, default_music_type: str = "iranian"):
    configs = db.query(Config).order_by(Config.created_at.desc()).all()
    query = db.query(Project)
    if music_filter in ALLOWED_MUSIC_TYPES:
        query = query.filter(Project.music_type == music_filter)
    projects = query.order_by(Project.created_at.desc()).all()
    create_music_type = _normalize_music_type(default_music_type, default="iranian")
    return render_template(
        "projects.html",
        projects=projects,
        configs=configs,
        create_music_type=create_music_type,
        active_music_filter=music_filter,
    )


@app.route("/")
def root():
    return redirect(url_for("projects_list"))


# ------------- Configs -------------
@app.route("/configs", methods=["GET", "POST"])
def configs_list():
    db: Session = get_session()
    try:
        if request.method == "POST":
            import json
            name = request.form.get("name") or "Config"
            description = request.form.get("description") or ""
            primary_color = request.form.get("primary_color") or "#F7F2EB"
            accent_color = request.form.get("accent_color") or "#ec4899"
            bg_color = request.form.get("bg_color") or "#050510"
            border_color = request.form.get("border_color") or "#FFFFFF"
            font_name = request.form.get("font_name") or "Yekan"
            music_type_val = request.form.get("music_type") or None
            if music_type_val not in ("iranian", "foreign"):
                music_type_val = None

            text_json_raw = request.form.get("advanced_json_text") or "{}"
            video_json_raw = request.form.get("advanced_json_video") or "{}"
            try:
                text_cfg = json.loads(text_json_raw)
                video_cfg = json.loads(video_json_raw)
            except Exception:
                flash("فرمت JSON نادرست است.", "error")
                return redirect(url_for("configs_list"))

            advanced_json = json.dumps({
                "text": text_cfg,
                "video": video_cfg,
            }, ensure_ascii=False)

            cfg = Config(
                name=name,
                description=description,
                primary_color=primary_color,
                accent_color=accent_color,
                bg_color=bg_color,
                border_color=border_color,
                font_name=font_name,
                music_type=music_type_val,
                advanced_json=advanced_json,
                created_at=datetime.datetime.now(),
            )
            db.add(cfg)
            db.commit()
            flash("کانفیگ جدید ساخته شد.", "success")
            return redirect(url_for("configs_list"))

        configs = db.query(Config).order_by(Config.created_at.desc()).all()
        return render_template("configs.html", configs=configs)
    finally:
        db.close()


@app.route("/configs/<int:config_id>", methods=["GET", "POST"])
def configs_edit(config_id: int):
    db: Session = get_session()
    try:
        cfg = db.get(Config, config_id)
        if not cfg:
            flash("کانفیگ پیدا نشد.", "error")
            return redirect(url_for("configs_list"))

        if request.method == "POST":
            import json
            cfg.name = request.form.get("name") or cfg.name
            cfg.description = request.form.get("description") or ""
            cfg.primary_color = request.form.get("primary_color") or cfg.primary_color
            cfg.accent_color = request.form.get("accent_color") or cfg.accent_color
            cfg.bg_color = request.form.get("bg_color") or cfg.bg_color
            cfg.border_color = request.form.get("border_color") or cfg.border_color
            cfg.font_name = request.form.get("font_name") or cfg.font_name
            music_type_val = request.form.get("music_type") or None
            if music_type_val not in ("iranian", "foreign"):
                music_type_val = None
            cfg.music_type = music_type_val

            text_json_raw = request.form.get("advanced_json_text") or "{}"
            video_json_raw = request.form.get("advanced_json_video") or "{}"
            try:
                text_cfg = json.loads(text_json_raw)
                video_cfg = json.loads(video_json_raw)
            except Exception:
                flash("فرمت JSON نادرست است.", "error")
                return redirect(url_for("configs_edit", config_id=config_id))

            cfg.advanced_json = json.dumps({
                "text": text_cfg,
                "video": video_cfg,
            }, ensure_ascii=False)
            db.commit()
            flash("کانفیگ به‌روزرسانی شد.", "success")
            return redirect(url_for("configs_list"))

        try:
            import json
            adv = json.loads(cfg.advanced_json or "{}")
        except Exception:
            adv = {}
        text_raw = json.dumps(adv.get("text", {}), ensure_ascii=False, indent=2)
        video_raw = json.dumps(adv.get("video", {}), ensure_ascii=False, indent=2)

        return render_template("configs_edit.html", cfg=cfg, text_raw=text_raw, video_raw=video_raw)
    finally:
        db.close()


# ------------- Projects -------------
@app.route("/projects", methods=["GET", "POST"])
def projects_list():
    db: Session = get_session()
    try:
        if request.method == "POST":
            name = request.form.get("name") or "پروژه بدون نام"
            job_title = request.form.get("job_title") or "Job"
            job_tags = request.form.get("job_tags") or ""
            config_id_val = request.form.get("config_id")
            config_id = int(config_id_val) if config_id_val else None
            music_type_val = _normalize_music_type(request.form.get("music_type"), default="iranian")

            existing = db.query(Project).filter(Project.name == name).first()
            audio_file = request.files.get("audio")
            video_file = request.files.get("video")

            if existing:
                # اگر فایل جدید آپلود شده باشد، جایگزین می‌کنیم
                if audio_file and audio_file.filename:
                    subdir = f"project_{existing.id}"
                    existing.audio_path = _save_upload(audio_file, subdir)
                if video_file and video_file.filename:
                    subdir = f"project_{existing.id}"
                    existing.video_path = _save_upload(video_file, subdir)
                db.commit()

                job_id = enqueue_job(
                    project_id=existing.id,
                    audio_path=existing.audio_path,
                    video_path=existing.video_path,
                    title=job_title,
                    tags=job_tags,
                    config_id=config_id,
                )
                flash(f"پروژه از قبل وجود داشت؛ جاب جدید #{job_id} ساخته شد.", "success")
                return redirect(url_for("project_detail", project_id=existing.id))

            if not audio_file or not audio_file.filename:
                flash("فایل صوتی را انتخاب کنید.", "error")
                return redirect(url_for("projects_list"))
            if not video_file or not video_file.filename:
                flash("فایل ویدیویی را انتخاب کنید.", "error")
                return redirect(url_for("projects_list"))

            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            subdir = f"project_{stamp}"
            audio_path = _save_upload(audio_file, subdir)
            video_path = _save_upload(video_file, subdir)

            project = Project(
                name=name,
                audio_path=audio_path,
                video_path=video_path,
                music_type=music_type_val,
                created_at=datetime.datetime.now(),
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            job_id = enqueue_job(
                project_id=project.id,
                audio_path=audio_path,
                video_path=video_path,
                title=job_title,
                tags=job_tags,
                config_id=config_id,
            )
            flash(f"پروژه '{project.name}' ساخته شد و جاب #{job_id} به صف اضافه شد.", "success")
            return redirect(url_for("project_detail", project_id=project.id))

        return _render_projects_page(db, music_filter=None, default_music_type="iranian")
    finally:
        db.close()


@app.route("/projects/iranian")
def projects_iranian():
    db: Session = get_session()
    try:
        return _render_projects_page(db, music_filter="iranian", default_music_type="iranian")
    finally:
        db.close()


@app.route("/projects/foreign")
def projects_foreign():
    db: Session = get_session()
    try:
        return _render_projects_page(db, music_filter="foreign", default_music_type="foreign")
    finally:
        db.close()


@app.route("/projects/<int:project_id>")
def project_detail(project_id: int):
    db: Session = get_session()
    try:
        project = db.get(Project, project_id)
        if not project:
            flash("پروژه پیدا نشد.", "error")
            return redirect(url_for("projects_list"))
        jobs = db.query(Job).filter(Job.project_id == project_id).order_by(Job.created_at.desc()).all()
        medias = db.query(Media).filter(Media.project_id == project_id).order_by(Media.created_at.desc()).all()
        configs = db.query(Config).order_by(Config.created_at.desc()).all()
        filtered_configs = _filter_configs_for_project(configs, project.music_type)
        return render_template(
            "project_detail.html",
            project=project,
            jobs=jobs,
            medias=medias,
            configs=configs,
            filtered_configs=filtered_configs,
        )
    finally:
        db.close()


@app.route("/projects/<int:project_id>/new-job", methods=["POST"])
def project_new_job(project_id: int):
    db: Session = get_session()
    try:
        project = db.get(Project, project_id)
        if not project:
            flash("پروژه پیدا نشد.", "error")
            return redirect(url_for("projects_list"))

        job_title = request.form.get("job_title") or "Job"
        job_tags = request.form.get("job_tags") or ""
        config_id_val = request.form.get("config_id")
        config_id = int(config_id_val) if config_id_val else None

        job_id = enqueue_job(
            project_id=project.id,
            audio_path=project.audio_path,
            video_path=project.video_path,
            title=job_title,
            tags=job_tags,
            config_id=config_id,
        )
        flash(f"جاب جدید #{job_id} ساخته شد.", "success")
        return redirect(url_for("jobs_detail", job_id=job_id))
    finally:
        db.close()


# ------------- Job control (cancel / requeue) -------------
@app.route("/jobs/<int:job_id>/cancel", methods=["POST"])
def jobs_cancel(job_id: int):
    db: Session = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            flash("جاب پیدا نشد.", "error")
            return redirect(url_for("jobs_list"))

        if job.status in ("queued", "running"):
            job.status = "cancelled"
            job.message = "توسط کاربر کنسل شد."
            job.updated_at = datetime.datetime.now()
            db.commit()
            flash("جاب کنسل شد.", "success")
        else:
            flash("این جاب در حال اجرا یا صف نیست.", "error")

        return redirect(url_for("jobs_detail", job_id=job_id))
    finally:
        db.close()


@app.route("/jobs/<int:job_id>/requeue", methods=["POST"])
def jobs_requeue(job_id: int):
    db: Session = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            flash("جاب پیدا نشد.", "error")
            return redirect(url_for("jobs_list"))

        new_id = enqueue_job(
            project_id=job.project_id,
            audio_path=job.audio_path,
            video_path=job.video_path,
            title=job.title,
            tags=job.tags,
            config_id=job.config_id,
        )
        flash(f"جاب جدید #{new_id} از روی این جاب ساخته شد.", "success")
        return redirect(url_for("jobs_detail", job_id=new_id))
    finally:
        db.close()


# ------------- Jobs -------------
@app.route("/jobs")
def jobs_list():
    db: Session = get_session()
    try:
        filter_type = request.args.get("type")
        if filter_type not in ALLOWED_MUSIC_TYPES:
            filter_type = None

        projects_query = db.query(Project)
        if filter_type:
            projects_query = projects_query.filter(Project.music_type == filter_type)
        projects = projects_query.order_by(Project.created_at.desc()).all()
        proj_jobs = []
        for p in projects:
            jobs = db.query(Job).filter(Job.project_id == p.id).order_by(Job.created_at.desc()).all()
            if jobs:
                proj_jobs.append((p, jobs))
        return render_template("jobs.html", proj_jobs=proj_jobs, filter_type=filter_type)
    finally:
        db.close()


@app.route("/jobs/<int:job_id>")
def jobs_detail(job_id: int):
    db: Session = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            flash("جاب پیدا نشد.", "error")
            return redirect(url_for("jobs_list"))
        return render_template("job_detail.html", job=job)
    finally:
        db.close()


@app.route("/jobs/<int:job_id>/json")
def jobs_status_json(job_id: int):
    db: Session = get_session()
    try:
        job = db.get(Job, job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        return jsonify(job.to_dict())
    finally:
        db.close()


# ------------- Media -------------
@app.route("/media")
def media_list():
    db: Session = get_session()
    try:
        medias = db.query(Media).order_by(Media.created_at.desc()).all()
        return render_template("media.html", medias=medias)
    finally:
        db.close()


@app.route("/media/file/<int:media_id>")
def media_file(media_id: int):
    db: Session = get_session()
    try:
        media = db.get(Media, media_id)
        if not media:
            flash("مدیا پیدا نشد.", "error")
            return redirect(url_for("media_list"))
        directory = os.path.dirname(media.file_path)
        fname = os.path.basename(media.file_path)
        return send_from_directory(directory, fname, as_attachment=False)
    finally:
        db.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)