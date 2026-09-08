"""Journal style presets, chosen once at setup, and check-in prompt templates."""

import json
import random
from pathlib import Path

STYLE_PRESETS = {
    "reflective": {
        "label": "Reflective",
        "description": "Thoughtful, first-person, explores why things happened the way they did.",
        "llm_instruction": (
            "You'll be given the user's own raw notes from today, tagged by time of day. Your job "
            "is light editing, NOT rewriting.\n\n"
            "Rules:\n"
            "- Keep the user's original wording, phrases, and sentences almost exactly as given. "
            "Do not paraphrase them into different words. Do not replace their phrasing with your "
            "own even if it sounds more 'polished' -- their phrasing IS the entry, EXCEPT for fixing "
            "typos/abbreviations and rephrasing a short answer so it reads in context of its question "
            "(see instructions below).\n"
            "- You may add short connecting words/phrases between their notes (e.g. 'by evening,', "
            "'but the thing is,', 'anyway,') to make it flow as one entry instead of separate lines.\n"
            "- Do not add new facts, feelings, or details they didn't mention.\n"
            "- Do not add a conclusion, lesson, or summary sentence at the end that they didn't say.\n"
            "- Match their exact tone and casualness -- if they wrote lowercase and casual, keep it "
            "that way, don't formalize it.\n"
            "- The result should read like their own notes glued together smoothly, not like "
            "someone else describing their day."
        ),
    },
    "gratitude": {
        "label": "Gratitude",
        "description": "Warm, appreciative tone, highlights what went well.",
        "llm_instruction": (
            "You'll be given the user's own raw notes from today. Do light editing, NOT "
            "rewriting: keep their wording and phrases as-is, only add short connecting words "
            "between notes so it reads as one entry (e.g. 'and', 'also', 'on top of that'). "
            "Don't force positivity onto notes that weren't positive -- just keep them as stated. "
            "Do not add facts, feelings, or details they didn't mention, and no closing summary "
            "sentence they didn't say."
        ),
    },
    "concise_bullet": {
        "label": "Concise Bullet",
        "description": "Short bullet-point log, minimal narrative.",
        "llm_instruction": (
            "Turn the notes below into one bullet per note (same number of bullets as notes given "
            "-- don't merge, split, or add any). Just lightly clean up spelling/grammar and phrase "
            "each as a short casual fragment, e.g. 'stuck on X for a while' style phrasing -- but "
            "the CONTENT of each bullet must come only from that note. Do not invent, add, or copy "
            "in any events, details, or bullets that are not in the notes below. Lowercase fine, "
            "fragments fine, no summary bullet like 'Overall, a productive day' at the end."
        ),
    },
    "stream_of_consciousness": {
        "label": "Stream of Consciousness",
        "description": "Free-flowing, unfiltered, minimal structure.",
        "llm_instruction": (
            "You'll be given the user's own raw notes from today. Do light editing, NOT "
            "rewriting: string their notes together in order using their own wording as-is, "
            "loosely connected like one continuous stream of thought (e.g. 'anyway,', 'also,', "
            "'then'). Let it trail off naturally, no neat conclusion. Do not add facts, feelings, "
            "or details they didn't mention."
        ),
    },
}

DEFAULT_STYLE = "reflective"

# add, remove, or reword any of these freely -- one is picked at random
# each time a check-in fires. this is the DEFAULT list; the Customize
# Questions tab lets users override it via custom_prompts.json
DEFAULT_CHECK_IN_PROMPTS = [
    "hey, what's happening today?",
    "how's it going right now?",
    "what's on your mind?",
    "anything good happen yet?",
    "how are you feeling at this exact moment?",
    "what have you been up to?",
    "quick check-in -- what's going on?",
    "anything annoying you today?",
    "what's the highlight so far?",
    "how's your energy right now?",
    "anything you're looking forward to today?",
    "what did you just finish doing?",
    "how's today comparing to yesterday?",
    "what's stressing you out right now, if anything?",
    "anything worth remembering from the last bit?",
    "what are you procrastinating on right now, be honest",
]

_CUSTOM_PROMPTS_PATH = Path(__file__).parent / "custom_prompts.json"


def get_active_prompts():
    if _CUSTOM_PROMPTS_PATH.exists():
        try:
            data = json.loads(_CUSTOM_PROMPTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CHECK_IN_PROMPTS


def save_custom_prompts(prompts):
    cleaned = [p.strip() for p in prompts if p.strip()]
    _CUSTOM_PROMPTS_PATH.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")


def reset_prompts_to_default():
    if _CUSTOM_PROMPTS_PATH.exists():
        _CUSTOM_PROMPTS_PATH.unlink()


def get_style(style_key):
    return STYLE_PRESETS.get(style_key, STYLE_PRESETS[DEFAULT_STYLE])


def random_prompt():
    return random.choice(get_active_prompts())