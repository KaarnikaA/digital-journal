"""Gradio UI: setup screen + entry review (accept/edit) + browse past entries."""

from datetime import datetime

import gradio as gr

import db
import llm
import ollama_utils
import styles
from styles import STYLE_PRESETS

db.init_db()


def do_setup(style_label, window_start, window_end, prompts_per_day, llm_backend):
    style_key = next(k for k, v in STYLE_PRESETS.items() if v["label"] == style_label)
    db.save_settings(style_key, window_start, window_end, int(prompts_per_day), llm_backend)
    return f"Saved. Style: {style_label}, window {window_start}-{window_end}, {prompts_per_day} prompts/day."


def check_ollama_status():
    return "🟢 Ollama is running" if ollama_utils.is_ollama_running() else "🔴 Ollama is not running"


def start_ollama_clicked():
    success, message = ollama_utils.start_ollama()
    prefix = "🟢" if success else "🔴"
    return f"{prefix} {message}"


def load_today_entry():
    today_str = datetime.now().strftime("%Y-%m-%d")
    entry = db.get_entry(today_str)
    if not entry:
        return today_str, "(No entry generated yet for today.)", gr.update(interactive=False)
    return today_str, entry["final_text"], gr.update(interactive=True)


def regenerate_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    text = llm.generate_entry_for_date(today_str)
    return text


def accept_entry(edited_text):
    today_str = datetime.now().strftime("%Y-%m-%d")
    entry = db.get_entry(today_str)
    edited = entry is not None and edited_text.strip() != entry["generated_text"].strip()
    db.finalize_entry(today_str, edited_text, edited)
    note = "Saved as accepted." if not edited else "Saved with your edits."
    return f"{note} Also written to journal_log.md."


def browse_entries():
    entries = db.get_all_entries()
    return [[e["entry_date"], e["style"], e["status"], e["final_text"][:120] + "..."] for e in entries]


def load_questions_text():
    return "\n".join(styles.get_active_prompts())


def save_questions_text(text):
    prompts = [line.strip() for line in text.split("\n") if line.strip()]
    if not prompts:
        return "No questions to save -- enter at least one, one per line."
    styles.save_custom_prompts(prompts)
    return f"Saved {len(prompts)} question(s). New prompts will be used starting tomorrow's schedule (or restart main.py to apply today)."


def reset_questions():
    styles.reset_prompts_to_default()
    return "\n".join(styles.DEFAULT_CHECK_IN_PROMPTS), "Reset to default questions."


with gr.Blocks(title="Digital Journal") as app:
    gr.Markdown("# Digital Journal")

    with gr.Tab("Setup"):
        gr.Markdown("Pick your style and active window once. Re-run this any time to change settings.")

        gr.Markdown("**LLM backend status**")
        with gr.Row():
            ollama_status = gr.Textbox(label="Ollama status", value="Click Check to test", interactive=False, scale=3)
            check_btn = gr.Button("Check", scale=1)
            start_btn = gr.Button("Start Ollama", scale=1)
        check_btn.click(check_ollama_status, outputs=ollama_status)
        start_btn.click(start_ollama_clicked, outputs=ollama_status)

        style_dd = gr.Dropdown(
            choices=[v["label"] for v in STYLE_PRESETS.values()],
            value=list(STYLE_PRESETS.values())[0]["label"],
            label="Journal style",
        )
        start_tb = gr.Textbox(value="09:00", label="Active window start (HH:MM)")
        end_tb = gr.Textbox(value="22:00", label="Active window end (HH:MM)")
        count_num = gr.Number(value=3, precision=0, label="Prompts per day")
        backend_dd = gr.Dropdown(choices=["ollama", "hosted"], value="ollama", label="LLM backend")
        setup_btn = gr.Button("Save settings")
        setup_out = gr.Textbox(label="Status", interactive=False)
        setup_btn.click(do_setup, [style_dd, start_tb, end_tb, count_num, backend_dd], setup_out)

    with gr.Tab("Today's Entry"):
        gr.Markdown("Review, edit, and accept today's generated entry.")
        date_out = gr.Textbox(label="Date", interactive=False)
        entry_box = gr.Textbox(label="Entry", lines=12, interactive=True)
        with gr.Row():
            load_btn = gr.Button("Load saved entry")
            regen_btn = gr.Button("Generate / Regenerate (calls LLM)")
            accept_btn = gr.Button("Accept / Save edits", variant="primary")
        accept_out = gr.Textbox(label="Status", interactive=False)

        load_btn.click(load_today_entry, outputs=[date_out, entry_box, entry_box])
        regen_btn.click(regenerate_today, outputs=entry_box)
        accept_btn.click(accept_entry, inputs=entry_box, outputs=accept_out)

    with gr.Tab("Customize Questions"):
        gr.Markdown(
            "One question per line. A random one from this list is used each time a "
            "check-in fires. Leave blank and click Reset to go back to the defaults."
        )
        questions_box = gr.Textbox(
            value=load_questions_text(), lines=14, label="Check-in questions", interactive=True
        )
        with gr.Row():
            save_q_btn = gr.Button("Save questions", variant="primary")
            reset_q_btn = gr.Button("Reset to defaults")
        questions_status = gr.Textbox(label="Status", interactive=False)

        save_q_btn.click(save_questions_text, inputs=questions_box, outputs=questions_status)
        reset_q_btn.click(reset_questions, outputs=[questions_box, questions_status])

    with gr.Tab("Past Entries"):
        browse_btn = gr.Button("Refresh")
        table = gr.Dataframe(
            headers=["Date", "Style", "Status", "Preview"],
            interactive=False,
        )
        browse_btn.click(browse_entries, outputs=table)

if __name__ == "__main__":
    app.launch()
