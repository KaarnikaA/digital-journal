"""Scheduling logic.

Each morning (at app start or via the daily cron job) we generate N random
prompt times within the user's active window and schedule a popup for each.
Shortly after the window closes, we schedule entry generation for the day.
"""

import multiprocessing
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

import db
import llm
from popup import show_prompt_popup
from styles import random_prompt

scheduler = BackgroundScheduler()


def _parse_hhmm(value, on_date):
    hh, mm = map(int, value.split(":"))
    return on_date.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _random_times_in_window(window_start, window_end, count, today):
    start = _parse_hhmm(window_start, today)
    end = _parse_hhmm(window_end, today)
    span_seconds = int((end - start).total_seconds())
    if span_seconds <= 0:
        raise ValueError("window_end must be after window_start")
    offsets = sorted(random.sample(range(span_seconds), k=min(count, span_seconds)))
    return [start + timedelta(seconds=o) for o in offsets]


def _run_popup_process(response_id, prompt_text):
    # runs in its own process so tkinter's mainloop doesn't block apscheduler
    def on_submit(text):
        db.save_response(response_id, text)

    def on_skip():
        db.mark_skipped(response_id)

    show_prompt_popup(prompt_text, on_submit, on_skip)


def fire_prompt(response_id, prompt_text):
    p = multiprocessing.Process(target=_run_popup_process, args=(response_id, prompt_text))
    p.start()


def schedule_today():
    settings = db.get_settings()
    if not settings:
        raise RuntimeError("No settings found -- run setup first.")

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    times = _random_times_in_window(
        settings["window_start"], settings["window_end"], settings["prompts_per_day"], today
    )

    for t in times:
        prompt_text = random_prompt()
        response_id = db.add_scheduled_prompt(today_str, t.isoformat(), prompt_text)
        if t > datetime.now():
            scheduler.add_job(
                fire_prompt,
                "date",
                run_date=t,
                args=[response_id, prompt_text],
                id=f"prompt_{response_id}",
                misfire_grace_time=300,
            )

    # generate the entry a few minutes after the window closes
    end_time = _parse_hhmm(settings["window_end"], today) + timedelta(minutes=5)
    scheduler.add_job(
        llm.generate_entry_for_date,
        "date",
        run_date=end_time,
        args=[today_str],
        id=f"generate_{today_str}",
        misfire_grace_time=3600,
        replace_existing=True,
    )


def start():
    db.init_db()
    schedule_today()
    scheduler.add_job(schedule_today, "cron", hour=0, minute=5, id="daily_replan", replace_existing=True)
    scheduler.start()


def stop():
    scheduler.shutdown(wait=False)