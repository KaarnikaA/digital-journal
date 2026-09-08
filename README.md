# Digital Journal

A journal for people who want to journal but don't stick with it. It prompts
you at random moments during your active hours, captures short check-in
responses via a small popup, and writes up a full journal entry for you at
the end of the day — which you can accept as-is or edit before saving.

## How it works

1. **Setup (once):** pick a journal style and your active window (e.g. 9am-10pm).
2. **During the day:** a fixed number of random-time prompts fire. Each opens
   a small always-on-top popup with a short check-in question and a text box.
   Answer or skip — it closes either way in seconds.
3. **End of day:** the raw responses are sent to an LLM along with your
   chosen style, which writes one cohesive entry.
4. **Review:** open the Gradio app, read the generated entry, edit if you
   want, and accept it to save. Accepted entries are also appended to
   `journal_log.md` (date, then entry, one file for your whole history).

## Styles

- **Reflective** — introspective, explores the "why"
- **Gratitude** — warm, highlights what went well
- **Concise Bullet** — short bullet-point log
- **Stream of Consciousness** — loose, unfiltered

## Stack

- FastAPI + APScheduler — background scheduling
- Tkinter — lightweight native popup for capturing responses in the moment
- SQLite — storage
- Gradio — setup and entry review UI
- LLM backend — local Ollama by default, swappable to a free hosted API tier

## Running it

```bash
pip install -r requirements.txt

# one-time setup + entry review UI
python gradio_app.py

# background scheduler (run after setup; leave running)
python main.py
```

Ollama must be running locally (`ollama serve`) with a model pulled
(default `llama3.1`) for the default backend. To use a hosted API instead,
set `HOSTED_API_KEY` and `HOSTED_API_URL` and pick "hosted" in Setup.

## Customizing check-in questions

Go to the **Customize Questions** tab in Gradio -- edit the list (one per line)
and save. New questions apply starting the next scheduling cycle (restart
`main.py` to apply them same-day). Click Reset to go back to the built-in
defaults, which are written to sound like a friend checking in, not a form.

## Journal log file

Every time you accept (or edit-and-save) an entry, it's also written to
`journal_log.md` in the project folder -- one `## YYYY-MM-DD` section per day,
in order, so you end up with a single running document of your journal
alongside the SQLite database. Re-saving the same day updates its section
instead of duplicating it.

## Known limitations (MVP)

- If you change settings in the Setup tab while `main.py` is already running,
  restart `main.py` for the change to take effect same-day (it reads settings
  once at startup; it only re-reads automatically at its daily 00:05 replan).
- The FastAPI app in `main.py` defines `/health` and `/today` routes but they
  aren't served yet -- `python main.py` currently runs the scheduler loop
  only, not the HTTP server. Planned for a follow-up.

## MVP scope

- Fixed active window, no real activity detection (see note below)
- Style is chosen once at setup, not per-entry
- Fixed number of prompts per day
- Single-user, local-only, no auth

### Why not real activity detection?

True activity detection (mouse/keyboard hooks, foreground app tracking)
needs OS-level permissions and different APIs per platform, and is fragile
to get right. A fixed active window covers most of the value for a fraction
of the effort — worth revisiting for v2, not the MVP.

## Roadmap ideas (not in MVP)

- Real activity-aware prompting
- System tray icon / launch on startup
- Voice-to-text response capture
- Weekly/monthly retrospective entries
