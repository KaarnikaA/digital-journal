"""SQLite storage layer for the digital journal.

Tables:
    settings   -- single-row config: style, window start/end, prompts/day
    responses  -- raw check-in responses captured via popup
    entries    -- generated (and possibly edited) journal entries, one per day
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "journal.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),   -- singleton row
    style TEXT NOT NULL,
    window_start TEXT NOT NULL,              -- "HH:MM"
    window_end TEXT NOT NULL,                -- "HH:MM"
    prompts_per_day INTEGER NOT NULL DEFAULT 3,
    llm_backend TEXT NOT NULL DEFAULT 'ollama'
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,                -- "YYYY-MM-DD", groups responses per day
    scheduled_time TEXT NOT NULL,             -- ISO timestamp the prompt was scheduled for
    prompt_text TEXT NOT NULL,
    response_text TEXT,                       -- NULL if skipped
    responded_at TEXT,                        -- ISO timestamp, NULL if skipped
    status TEXT NOT NULL DEFAULT 'pending'    -- pending | answered | skipped
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL UNIQUE,          -- "YYYY-MM-DD"
    style TEXT NOT NULL,
    generated_text TEXT NOT NULL,             -- what the LLM produced
    final_text TEXT NOT NULL,                 -- what the user accepted/edited to
    status TEXT NOT NULL DEFAULT 'draft',     -- draft | accepted | edited
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# settings

def save_settings(style, window_start, window_end, prompts_per_day=3, llm_backend="ollama"):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO settings (id, style, window_start, window_end, prompts_per_day, llm_backend)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                style=excluded.style,
                window_start=excluded.window_start,
                window_end=excluded.window_end,
                prompts_per_day=excluded.prompts_per_day,
                llm_backend=excluded.llm_backend
            """,
            (style, window_start, window_end, prompts_per_day, llm_backend),
        )


def get_settings():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        return dict(row) if row else None


# responses

def add_scheduled_prompt(entry_date, scheduled_time, prompt_text):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO responses (entry_date, scheduled_time, prompt_text, status)
               VALUES (?, ?, ?, 'pending')""",
            (entry_date, scheduled_time, prompt_text),
        )
        return cur.lastrowid


def save_response(response_id, response_text):
    with get_conn() as conn:
        conn.execute(
            """UPDATE responses
               SET response_text = ?, responded_at = ?, status = 'answered'
               WHERE id = ?""",
            (response_text, datetime.now().isoformat(timespec="seconds"), response_id),
        )


def mark_skipped(response_id):
    with get_conn() as conn:
        conn.execute("UPDATE responses SET status = 'skipped' WHERE id = ?", (response_id,))


def get_responses_for_date(entry_date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM responses WHERE entry_date = ? ORDER BY scheduled_time",
            (entry_date,),
        ).fetchall()
        return [dict(r) for r in rows]


# entries

def save_generated_entry(entry_date, style, generated_text):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO entries (entry_date, style, generated_text, final_text, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
                style=excluded.style,
                generated_text=excluded.generated_text,
                final_text=excluded.generated_text,
                status='draft',
                updated_at=excluded.updated_at
            """,
            (entry_date, style, generated_text, generated_text, now, now),
        )
        return cur.lastrowid


LOG_PATH = Path(__file__).parent / "journal_log.md"


def append_to_log(entry_date, final_text):
    block = f"{entry_date}\n{final_text.strip()}\n\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(block)


JOURNAL_DOC_PATH = Path(__file__).parent / "journal_log.md"


def _append_to_doc(entry_date, final_text):
    header = f"## {entry_date}"
    new_section = f"{header}\n\n{final_text.strip()}\n\n"

    if not JOURNAL_DOC_PATH.exists():
        JOURNAL_DOC_PATH.write_text(f"# Journal Log\n\n{new_section}", encoding="utf-8")
        return

    content = JOURNAL_DOC_PATH.read_text(encoding="utf-8")
    if header in content:
        # this date already has a section -- replace it instead of duplicating
        start = content.index(header)
        rest = content[start + len(header):]
        next_marker = rest.find("\n## ")
        end = start + len(header) + (next_marker if next_marker != -1 else len(rest))
        content = content[:start] + new_section.rstrip("\n") + "\n\n" + content[end:].lstrip("\n")
        JOURNAL_DOC_PATH.write_text(content, encoding="utf-8")
    else:
        with open(JOURNAL_DOC_PATH, "a", encoding="utf-8") as f:
            f.write(new_section)


def finalize_entry(entry_date, final_text, edited):
    with get_conn() as conn:
        conn.execute(
            """UPDATE entries
               SET final_text = ?, status = ?, updated_at = ?
               WHERE entry_date = ?""",
            (
                final_text,
                "edited" if edited else "accepted",
                datetime.now().isoformat(timespec="seconds"),
                entry_date,
            ),
        )
    _append_to_doc(entry_date, final_text)
    append_to_log(entry_date, final_text)


def get_entry(entry_date):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM entries WHERE entry_date = ?", (entry_date,)).fetchone()
        return dict(row) if row else None


def get_all_entries():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM entries ORDER BY entry_date DESC").fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {DB_PATH}")