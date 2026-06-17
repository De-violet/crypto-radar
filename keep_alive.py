"""
Keep-alive HTTP server untuk platform yang butuh port listening (Render, HF Spaces).
Selain itu, /health endpoint untuk monitoring sederhana.
"""
import os
import threading
import time

from flask import Flask, jsonify

app = Flask('')

# Track bot startup time + last scan timestamp (di-update oleh radar.py via env)
_START_TIME = time.time()
_LAST_SCAN_EPOCH = float(os.environ.get("LAST_SCAN_EPOCH", 0))


@app.route('/')
def home():
    return "Bot is alive and running! 🎯"


@app.route('/health')
def health():
    uptime_sec = time.time() - _START_TIME
    return jsonify({
        "status": "ok",
        "uptime_seconds": round(uptime_sec, 0),
        "uptime_human": f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m",
        "last_scan_epoch": _LAST_SCAN_EPOCH,
        "last_scan_human": (
            time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(_LAST_SCAN_EPOCH))
            if _LAST_SCAN_EPOCH > 0 else "never"
        ),
    })


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()
