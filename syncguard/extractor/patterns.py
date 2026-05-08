"""Regex and filesystem pattern extraction."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

SUPPORTED_SUFFIXES = {".py", ".js", ".ts", ".go", ".java", ".rb"}


def iter_source_files(root: Path) -> list[Path]:
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".syncguard"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix in SUPPORTED_SUFFIXES:
            files.append(path)
    return sorted(files)


def find_import_patterns(files: list[Path], root: Path) -> dict[str, list[str]]:
    imports: dict[str, list[str]] = defaultdict(list)
    import_re = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+)|require\(['\"]([^'\"]+)['\"]\))")
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(root))
        for line in text.splitlines():
            match = import_re.search(line)
            if match:
                target = next(group for group in match.groups() if group)
                imports[rel].append(target)
    return dict(imports)


def filename_conventions(files: list[Path], root: Path) -> list[dict[str, object]]:
    by_dir: dict[str, Counter[str]] = defaultdict(Counter)
    for path in files:
        rel = path.relative_to(root)
        parent = str(rel.parent)
        name = path.name
        if name.startswith("test_"):
            by_dir[parent]["test_prefix"] += 1
        if name.endswith(f"_test{path.suffix}"):
            by_dir[parent]["test_suffix"] += 1
        if name.endswith(f"_service{path.suffix}"):
            by_dir[parent]["service_suffix"] += 1
    out: list[dict[str, object]] = []
    for parent, counts in by_dir.items():
        total = sum(counts.values())
        if total:
            pattern, count = counts.most_common(1)[0]
            out.append({"scope": parent, "pattern": pattern, "count": count, "total": total})
    return out
