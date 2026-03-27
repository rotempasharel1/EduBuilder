from __future__ import annotations

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path

import requests

START_MARKER = "<!-- TRACE_EXCERPT_START -->"
END_MARKER = "<!-- TRACE_EXCERPT_END -->"
DEFAULT_API_URL = os.environ.get("TRACE_API_URL", "http://localhost:8000")


def run_command(command: list[str], timeout: int = 60, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_docker_compose_available() -> None:
    run_command(["docker", "compose", "version"], timeout=20, check=True)


def wait_for_api(base_url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            response.raise_for_status()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"API did not become ready at {base_url!r}. Last error: {last_error}")


def start_redis_monitor() -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["docker", "compose", "exec", "-T", "redis", "redis-cli", "MONITOR"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def trigger_api_activity(base_url: str) -> None:
    requests.get(f"{base_url}/plans", timeout=10).raise_for_status()
    requests.get(f"{base_url}/plans/shared", timeout=10).raise_for_status()


def trigger_worker_activity() -> str:
    result = run_command(["docker", "compose", "run", "--rm", "worker", "python", "scripts/refresh.py"], timeout=120, check=True)
    return result.stdout.strip() or "(worker completed without stdout)"


def stop_monitor(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.poll() is None:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()

    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()

    return stdout, stderr


def tail_lines(text: str, max_lines: int = 30) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "(no lines captured)"
    return "\n".join(lines[-max_lines:])


def build_redis_trace_excerpt(base_url: str) -> str:
    ensure_docker_compose_available()
    wait_for_api(base_url)
    monitor_process = start_redis_monitor()

    try:
        time.sleep(2)
        trigger_api_activity(base_url)
        worker_output = trigger_worker_activity()
        time.sleep(2)
    finally:
        monitor_stdout, monitor_stderr = stop_monitor(monitor_process)

    monitor_block = tail_lines(monitor_stdout, max_lines=40)
    worker_block = tail_lines(worker_output, max_lines=20)
    stderr_block = tail_lines(monitor_stderr, max_lines=20) if monitor_stderr.strip() else "(empty)"

    if monitor_block == "(no lines captured)":
        raise RuntimeError("No Redis MONITOR lines were captured.")

    return (
        "```text\n"
        "# redis-monitor\n"
        f"{monitor_block}\n\n"
        "# worker-trigger\n"
        f"{worker_block}\n\n"
        "# redis-monitor-stderr\n"
        f"{stderr_block}\n"
        "```"
    )


def inject_excerpt(notes_path: Path, excerpt_block: str) -> None:
    content = notes_path.read_text(encoding="utf-8")
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1 or end == -1:
        raise RuntimeError("Trace markers were not found in docs/EX3-notes.md")

    start += len(START_MARKER)
    new_content = content[:start] + "\n\n" + excerpt_block + "\n\n" + content[end:]
    notes_path.write_text(new_content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a real Redis monitor excerpt into docs/EX3-notes.md.")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Base URL for the local API. Defaults to TRACE_API_URL or http://localhost:8000.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    notes_path = project_root / "docs" / "EX3-notes.md"

    excerpt = build_redis_trace_excerpt(args.api_url)
    inject_excerpt(notes_path, excerpt)
    print("Injected a real local Redis trace excerpt into docs/EX3-notes.md")


if __name__ == "__main__":
    main()
