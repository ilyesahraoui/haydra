
from flask import Flask, request, render_template_string
from datetime import datetime, timezone
import sqlite3
import os
import requests

app = Flask(__name__)

VIDEO_ID = "QEPCVFLw1i8"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "visitors.db"
)

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">
    <title>Haydra19 | الفيديو</title>
    <style>
        body {
            background: #111827;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 30px 15px;
        }
        .panel {
            max-width: 800px;
            margin: 30px auto;
            padding: 24px;
            background: #1f2937;
            border-radius: 16px;
        }
        iframe {
            width: 100%;
            aspect-ratio: 16 / 9;
            border: 0;
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Haydra19</h1>
        <p>مرحبًا بك في موقعي!</p>

        <iframe
            src="https://www.youtube-nocookie.com/embed/{{ video_id }}"
            title="فيديو يوتيوب"
            allow="accelerometer; autoplay; clipboard-write;
                   encrypted-media; gyroscope; picture-in-picture;
                   web-share"
            allowfullscreen>
        </iframe>

        <p>إجمالي الزيارات: {{ total }}</p>
        <p>
            يجمع الموقع إحصائيات الزيارات ومعلومات عامة عن
            المتصفح ونظام التشغيل لأغراض إحصائية.
        </p>
    </div>
</body>
</html>
"""


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                browser TEXT,
                os_name TEXT,
                visited_at TEXT
            )
        """)


def get_browser(ua):
    if "Edg/" in ua:
        return "Edge"
    if "Firefox/" in ua or "FxiOS/" in ua:
        return "Firefox"
    if "OPR/" in ua:
        return "Opera"
    if "Chrome/" in ua or "CriOS/" in ua:
        return "Chrome"
    if "Safari/" in ua:
        return "Safari"
    return "Other"


def get_os(ua):
    if "Android" in ua:
        return "Android"
    if "iPhone" in ua or "iPad" in ua:
        return "iOS"
    if "Windows" in ua:
        return "Windows"
    if "Mac OS" in ua:
        return "macOS"
    if "Linux" in ua:
        return "Linux"
    return "Other"



def notify_discord(browser, os_name, now, total):
    if not WEBHOOK:
        app.logger.warning("Discord webhook is not configured")
        return

    message = (
        "📊 زيارة جديدة للموقع\n"
        f"المتصفح: {browser}\n"
        f"النظام: {os_name}\n"
        f"الوقت: {now}\n"
        f"إجمالي الزيارات: {total}"
    )

    try:
        response = requests.post(
            WEBHOOK,
            json={"content": message},
            timeout=10
        )

        if response.status_code in (200, 204):
            app.logger.info("Discord notification sent")

        elif response.status_code == 429:
            app.logger.error(
                "Discord returned 429. Retry-After=%s. "
                "Automatic retries are disabled.",
                response.headers.get("Retry-After", "unknown")
            )

        else:
            app.logger.error(
                "Discord returned HTTP %s. Response type: %s",
                response.status_code,
                response.headers.get("Content-Type", "unknown")
            )

    except requests.RequestException:
        app.logger.exception("Discord request failed")

@app.route("/")
def home():
    ua = request.headers.get("User-Agent", "")
    browser = get_browser(ua)
    os_name = get_os(ua)
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """INSERT INTO visits (browser, os_name, visited_at)
               VALUES (?, ?, ?)""",
            (browser, os_name, now)
        )

        total = db.execute(
            "SELECT COUNT(*) FROM visits"
        ).fetchone()[0]

        db.commit()

    app.logger.info(
        "Visit recorded. Browser=%s OS=%s Total=%s",
        browser, os_name, total
    )

    notify_discord(browser, os_name, now, total)

    return render_template_string(
        HTML,
        video_id=VIDEO_ID,
        total=total
    )


init_db()

if __name__ == "__main__":
    app.run(debug=False)
