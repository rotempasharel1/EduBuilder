from __future__ import annotations

import subprocess
from pathlib import Path

START_MARKER = "<!-- TRACE_EXCERPT_START -->"
END_MARKER = "<!-- TRACE_EXCERPT_END -->"


def run_command(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def build_service_log_excerpt() -> str:
    worker_logs = run_command(["docker", "compose", "logs", "worker", "--tail=20"])
    api_logs = run_command(["docker", "compose", "logs", "api", "--tail=20"])
    return (
        "```text\n"
        "# worker\n"
        f"{worker_logs}\n\n"
        "# api\n"
        f"{api_logs}\n"
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


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    notes_path = project_root / "docs" / "EX3-notes.md"
    excerpt = build_service_log_excerpt()
    inject_excerpt(notes_path, excerpt)
    print("Injected a real local service log excerpt into docs/EX3-notes.md")


if __name__ == "__main__":
    main()
