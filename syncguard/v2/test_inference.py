"""Infer invariants from existing tests."""

from __future__ import annotations

import ast
from pathlib import Path

from syncguard.core.models import Invariant


class TestInvariantMiner:
    """Mine assertions and dictionary access patterns from tests."""

    def mine(self, root: str | Path) -> list[Invariant]:
        base = Path(root)
        invariants: list[Invariant] = []
        for path in sorted(base.rglob("test_*.py")):
            invariants.extend(self._mine_file(path, base))
        return invariants

    def _mine_file(self, path: Path, root: Path) -> list[Invariant]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return []
        miner = _TestVisitor(str(path.relative_to(root)))
        miner.visit(tree)
        return [
            Invariant(
                name=f"Tests assume `{field}` is present",
                description=f"`{miner.file_path}` contains assertions or subscripts requiring `{field}`.",
                invariant_type="test_inferred",
                scope=field,
                source_files=[miner.file_path],
                confidence=0.9,
                evidence={"field": field, "assertions": count},
            )
            for field, count in sorted(miner.fields.items())
        ]


class _TestVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.fields: dict[str, int] = {}

    def visit_Subscript(self, node: ast.Subscript) -> None:
        field = _constant_string(node.slice)
        if field:
            self.fields[field] = self.fields.get(field, 0) + 1
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        for item in [node.left, *node.comparators]:
            field = _constant_string(item)
            if field:
                self.fields[field] = self.fields.get(field, 0) + 1
        self.generic_visit(node)


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None
