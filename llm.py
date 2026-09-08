"""LLM-backed journal entry generation.

Swappable backend: local Ollama (default, free, private) or a free-tier
hosted API. Swap by changing `llm_backend` in settings.
"""

import os

import db
from styles import get_style

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# hosted fallback -- e.g. a free-tier Groq/Together/Gemini endpoint
# set HOSTED_API_KEY and HOSTED_API_URL as env vars to enable
HOSTED_API_KEY = os.environ.get("HOSTED_API_KEY")
HOSTED_API_URL = os.environ.get("HOSTED_API_URL")


def _time_bucket(iso_timestamp):
    hour = int(iso_timestamp[11:13])
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _build_prompt(responses, style_key):
    style = get_style(style_key)
    answered = [r for r in responses if r["status"] == "answered" and r["response_text"]]

    if not answered:
        raw = "(nothing was logged today)"
    else:
        lines = [
            f"[{_time_bucket(r['scheduled_time'])}] asked: \"{r['prompt_text']}\" -> answered: \"{r['response_text']}\""
            for r in answered
        ]
        raw = "\n".join(lines)

    return (
        f"{style['llm_instruction']}\n\n"
        f"Here's what the user actually wrote today, tagged by rough time of day, with the "
        f"question they were answering:\n{raw}\n\n"
        f"Stitch these into one entry using their own words as-is. Only add minimal connective "
        f"phrasing between them -- do not rewrite or rephrase their sentences.\n\n"
        f"Two exceptions where light cleanup IS okay:\n"
        f"- Fix obvious typos and expand abbreviations (e.g. 'nthing spcl' -> 'nothing special', "
        f"'idk' -> 'i don't know') so it reads clean, but don't change word choice otherwise.\n"
        f"- Make sure each answer reads as a natural statement in context of what it was answering "
        f"-- e.g. if asked 'what's happening today?' and the answer was 'nothing spcl', write it as "
        f"something like 'nothing much happening today' rather than just repeating 'nothing spcl' "
        f"out of context.\n\n"
        f"CRITICAL: use ONLY the notes listed above. There are exactly {len(answered)} note(s) "
        f"listed. Do not add any event, detail, task, or feeling that isn't in one of those "
        f"{len(answered)} note(s) above, even if it seems like a plausible or common thing to "
        f"mention. If you're unsure whether something was said, leave it out.\n\n"
        f"Output ONLY the diary entry text itself. Do not add any preamble like \"Here's the "
        f"entry:\", do not add any note/explanation afterward about what you did or changed, and "
        f"do not wrap it in quotes. Your entire response should be the entry and nothing else."
    )


_PREAMBLE_PATTERNS = [
    "here's the stitched-together entry:",
    "here's the entry:",
    "here is the entry:",
    "here's the diary entry:",
    "here is the diary entry:",
]

_POSTAMBLE_MARKERS = [
    "\ni made minimal adjustments",
    "\ni made only minimal",
    "\nnote:",
    "\n(note:",
]


def _strip_wrapper_text(text):
    cleaned = text.strip()

    lower = cleaned.lower()
    for pattern in _PREAMBLE_PATTERNS:
        if lower.startswith(pattern):
            cleaned = cleaned[len(pattern):].strip()
            lower = cleaned.lower()
            break

    lower = cleaned.lower()
    for marker in _POSTAMBLE_MARKERS:
        idx = lower.find(marker)
        if idx != -1:
            cleaned = cleaned[:idx].strip()
            break

    # got wrapped in quotes entirely, strip them off
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 1:
        cleaned = cleaned[1:-1].strip()

    return cleaned


def _call_ollama(prompt):
    import requests

    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _call_hosted(prompt):
    import requests

    if not (HOSTED_API_KEY and HOSTED_API_URL):
        raise RuntimeError("Hosted API not configured (HOSTED_API_KEY / HOSTED_API_URL).")

    resp = requests.post(
        HOSTED_API_URL,
        headers={"Authorization": f"Bearer {HOSTED_API_KEY}"},
        json={"prompt": prompt},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["text"].strip()


def generate_entry_for_date(entry_date):
    settings = db.get_settings()
    responses = db.get_responses_for_date(entry_date)
    prompt = _build_prompt(responses, settings["style"])

    backend = settings.get("llm_backend", "ollama")
    try:
        if backend == "hosted":
            text = _call_hosted(prompt)
        else:
            text = _call_ollama(prompt)
        text = _strip_wrapper_text(text)
    except Exception as exc:
        print(f"[llm] generation failed for {entry_date} via backend={backend}: {exc}")
        text = (
            "(Entry generation failed -- LLM backend unreachable. "
            f"Raw error: {exc}. Raw responses are still saved and you can retry "
            "generation from the Gradio app.)"
        )

    db.save_generated_entry(entry_date, settings["style"], text)
    return text