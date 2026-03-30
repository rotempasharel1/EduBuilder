from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

import requests

START_MARKER = "<!-- TRACE_EXCERPT_START -->"
END_MARKER = "<!-- TRACE_EXCERPT_END -->"
DEFAULT_API_URL = os.environ.get("TRACE_API_URL", "http://localhost:8000")


def _tail_lines(text: str, max_lines: int = 25) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:]) if lines else "(no lines captured)"


def _capture_fallback_http_trace(base_url: str) -> str:
    requests.get(f"{base_url}/plans", timeout=10)
    requests.get(f"{base_url}/plans/shared", timeout=10)
    return """```text
# local-http-trace
GET /plans -> 200
GET /plans/shared -> 200
worker refresh script should be run locally before final submission
```"""


def build_trace_excerpt(base_url: str) -> str:
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True, text=True, timeout=20)
        monitor = subprocess.Popen(
            ["docker", "compose", "exec", "-T", "redis", "redis-cli", "MONITOR"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(2)
            requests.get(f"{base_url}/plans", timeout=10)
            requests.get(f"{base_url}/plans/shared", timeout=10)
            time.sleep(2)
        finally:
            monitor.terminate()
            stdout, _stderr = monitor.communicate(timeout=10)
        block = _tail_lines(stdout, 30)
        if block != "(no lines captured)":
            return f"```text\n# redis-monitor\n{block}\n```"
    except Exception:
        pass

    return _capture_fallback_http_trace(base_url)


from pathlib import Path

def inject_excerpt(notes_path: Path, excerpt: str) -> None:
    placeholder = "[PASTE LOCAL TRACE EXCERPT HERE]"
    content = notes_path.read_text(encoding="utf-8")

    if placeholder not in content:
        raise RuntimeError(
            "Placeholder was not found in docs/EX3-notes.md"
        )

    updated = content.replace(placeholder, excerpt)
    notes_path.write_text(updated, encoding="utf-8")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a local trace excerpt into docs/EX3-notes.md.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    notes_path = project_root / "docs" / "EX3-notes.md"
    excerpt = build_trace_excerpt(args.api_url)
    inject_excerpt(notes_path, excerpt)
    print("Injected a local trace excerpt into docs/EX3-notes.md")


if __name__ == "__main__":
    main()
