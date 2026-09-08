"""Entrypoint: runs the background scheduler and a minimal FastAPI app.

Usage:
    python main.py            # starts scheduler (blocks, runs in background)

For the review/setup UI, run separately:
    python gradio_app.py
"""

import time

from fastapi import FastAPI

import db
import scheduler

app = FastAPI(title="Digital Journal")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/today")
def today_status():
    from datetime import datetime

    today_str = datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today_str,
        "responses": db.get_responses_for_date(today_str),
        "entry": db.get_entry(today_str),
    }


def run_background():
    # just the scheduler loop, no HTTP server - this is the default way to run it
    db.init_db()
    if not db.get_settings():
        print("No settings found. Run `python gradio_app.py` and complete Setup first.")
        return
    scheduler.start()
    print("Scheduler started. Running in background -- Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
        print("Stopped.")


if __name__ == "__main__":
    run_background()