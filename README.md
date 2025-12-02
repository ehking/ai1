# Farsi Motion Studio – Advanced UI + Configs

این نسخه‌ی پیشرفته شامل:

- **Projects (پروژه‌ها)**:
  - هر پروژه شامل فایل صوتی و ویدیوی خام است.
- **Jobs (جاب‌ها)**:
  - جاب‌ها به ازای هر پروژه ساخته می‌شوند و در UI
    به صورت گروه‌بندی شده بر اساس پروژه نمایش داده می‌شوند.
  - هر جاب:
    - نام (title)
    - تگ‌ها (tags)
    - لینک به یک Config ظاهری
- **Media (مدیاها)**:
  - خروجی‌های ویدیویی نهایی.
- **Configs (کانفیگ‌ها)**:
  - تنظیمات ظاهری پیشرفته برای Manim:
    - رنگ متن، رنگ Accent، پس‌زمینه، رنگ Border
    - نام فونت (مثلاً Yekan, IranNastaliq)
    - advanced_json: تنظیمات دلخواه مثل:
      - base_scale, rotate_deg, shadow_offset_x, shadow_offset_y
      - stroke_width, pulse_rt, border_pulse_opacity, border_pulse_width
  - هر Config در دیتابیس ذخیره می‌شود و می‌توانید آن را روی چندین جاب اعمال کنید.

UI:

- منوها در سمت راست (sidebar)
- حالت تیره / روشن با toggle (ذخیره در localStorage)
- فونت پیش‌فرض "Yekan" (در صورت نصب روی سیستم)

Manim:

- `motion.py` از `config.json` می‌خواند که توسط `motion_pipeline.py`
  بر اساس Config انتخاب شده برای Job ساخته می‌شود.
- استایل تایپوگرافی فارسی با سایه و استروک و Beat Pulse
  قابل شخصی‌سازی از طریق advanced JSON است.

برای اجرا:

```bash
pip install flask sqlalchemy manim openai-whisper torch librosa
python app.py
```

و سپس:

```text
http://localhost:5000
```

از بخش "کانفیگ‌ها" چند استایل مختلف بسازید و سپس موقع ساخت پروژه یا جاب جدید،
یکی از آن‌ها را انتخاب کنید تا خروجی براساس همان کانفیگ ساخته شود.
