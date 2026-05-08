"""Python AST analysis helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PythonFacts:
    file_path: str
    classes: dict[str, dict[str, str]] = field(default_factory=dict)
    functions: dict[str, dict[str, Any]] = field(default_factory=dict)
    dict_returns: dict[str, list[set[str]]] = field(default_factory=dict)
    function_calls: dict[str, list[str]] = field(default_factory=dict)


def annotation_to_str(node: ast.AST | None) -> str:
    if node is None:
        return "unknown"
    try:
        return ast.unparse(node)
    except Exception:
        return "unknown"


class PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.facts = PythonFacts(file_path=file_path)
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._class_stack.append(node.name)
        self.facts.classes.setdefault(node.name, {})
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                self.facts.classes[node.name][stmt.target.id] = annotation_to_str(stmt.annotation)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        signature = {
            "params": {
                arg.arg: annotation_to_str(arg.annotation)
                for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                if arg.arg != "self"
            },
            "return": annotation_to_str(node.returns),
            "lineno": node.lineno,
        }
        fullname = ".".join([*self._class_stack, node.name]) if self._class_stack else node.name
        self.facts.functions[fullname] = signature
        self._function_stack.append(fullname)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_Return(self, node: ast.Return) -> Any:
        if self._function_stack and isinstance(node.value, ast.Dict):
            keys: set[str] = set()
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
            if keys:
                self.facts.dict_returns.setdefault(self._function_stack[-1], []).append(keys)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if self._function_stack:
            name = call_name(node.func)
            if name:
                self.facts.function_calls.setdefault(self._function_stack[-1], []).append(name)
        self.generic_visit(node)


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def analyze_python_file(path: Path, root: Path) -> PythonFacts | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    analyzer = PythonAnalyzer(str(path.relative_to(root)))
    analyzer.visit(tree)
    return analyzer.facts
