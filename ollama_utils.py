"""Check whether Ollama is reachable, and start it if not.

Used by the Setup tab so the user doesn't need a separate terminal running
`ollama serve` at all times.
"""

import subprocess
import time

import requests

OLLAMA_URL = "http://localhost:11434"


def is_ollama_running():
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def start_ollama(wait_seconds=10):
    if is_ollama_running():
        return True, "Ollama is already running."

    try:
        # keeps a console window from popping up on Windows, ignored elsewhere
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except FileNotFoundError:
        return False, "Couldn't find the `ollama` command. Is Ollama installed and on your PATH?"
    except Exception as exc:
        return False, f"Failed to launch Ollama: {exc}"

    for _ in range(wait_seconds):
        time.sleep(1)
        if is_ollama_running():
            return True, "Ollama started successfully."

    return False, "Ollama was launched but isn't responding yet -- give it a few more seconds and check again."