"""Git diff parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess


@dataclass(slots=True)
class ChangedFile:
    path: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    hunks: list[str] = field(default_factory=list)

    @property
    def excerpt(self) -> str:
        lines = self.hunks[:12]
        return "\n".join(lines)


def git_diff(root: str | Path = ".", staged: bool = False) -> str:
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    return subprocess.check_output(cmd, cwd=Path(root), text=True)


def parse_diff(diff_text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current:
                files.append(current)
            current = None
            parts = line.split()
            if len(parts) >= 4:
                path = parts[3][2:] if parts[3].startswith("b/") else parts[3]
                current = ChangedFile(path=path)
            continue
        if current is None:
            continue
        if line.startswith("+++ b/"):
            current.path = line[6:]
        if line.startswith("@@") or line.startswith("+") or line.startswith("-"):
            current.hunks.append(line)
        if line.startswith("+") and not line.startswith("+++"):
            current.added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            current.removed_lines.append(line[1:])
    if current:
        files.append(current)
    return files
