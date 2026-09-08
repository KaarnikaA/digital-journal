"""Small always-on-top Tkinter popup used to capture a check-in response.

Runs in its own process so Tkinter's mainloop doesn't block the scheduler.
If the user ignores it, it auto-closes after a timeout and the response
gets marked as skipped.
"""

import tkinter as tk
from tkinter import ttk

AUTO_CLOSE_MS = 5 * 60 * 1000  # give up after 5 min


def show_prompt_popup(prompt_text, on_submit, on_skip):
    root = tk.Tk()
    root.title("Journal check-in")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    # stick it near the top-right of the screen
    width, height = 320, 160
    screen_w = root.winfo_screenwidth()
    x = screen_w - width - 40
    y = 60
    root.geometry(f"{width}x{height}+{x}+{y}")

    submitted = {"done": False}

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)

    label = ttk.Label(frame, text=prompt_text, wraplength=290, font=("Helvetica", 11))
    label.pack(anchor="w", pady=(0, 8))

    text_box = tk.Text(frame, height=4, width=34, wrap="word")
    text_box.pack(fill="both", expand=True)
    text_box.focus_set()

    def submit():
        response = text_box.get("1.0", "end").strip()
        submitted["done"] = True
        root.destroy()
        if response:
            on_submit(response)
        else:
            on_skip()

    def skip_and_close():
        if not submitted["done"]:
            submitted["done"] = True
            root.destroy()
            on_skip()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill="x", pady=(8, 0))
    ttk.Button(btn_frame, text="Skip", command=skip_and_close).pack(side="left")
    ttk.Button(btn_frame, text="Submit", command=submit).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", skip_and_close)
    root.after(AUTO_CLOSE_MS, skip_and_close)

    root.mainloop()


if __name__ == "__main__":
    show_prompt_popup(
        "What's on your mind?",
        on_submit=lambda text: print(f"Got response: {text}"),
        on_skip=lambda: print("Skipped."),
    )