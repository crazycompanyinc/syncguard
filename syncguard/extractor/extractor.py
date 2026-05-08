"""High-level invariant extraction."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from syncguard.core.models import Invariant
from syncguard.extractor.patterns import filename_conventions, find_import_patterns, iter_source_files
from syncguard.extractor.python_ast import PythonFacts, analyze_python_file


class InvariantExtractor:
    """Extract implicit invariants from a codebase."""

    def __init__(self, min_confidence: float = 0.6) -> None:
        self.min_confidence = min_confidence

    def extract(self, path: str | Path = ".") -> list[Invariant]:
        root = Path(path).resolve()
        files = iter_source_files(root)
        py_facts = [fact for file in files if file.suffix == ".py" if (fact := analyze_python_file(file, root))]
        invariants: list[Invariant] = []
        invariants.extend(self._type_contracts(py_facts))
        invariants.extend(self._response_shapes(py_facts))
        invariants.extend(self._behavioral_migrations(py_facts))
        invariants.extend(self._call_patterns(py_facts))
        invariants.extend(self._cross_module_user_id(py_facts))
        invariants.extend(self._conventions(files, root))
        invariants.extend(self._import_couplings(files, root))
        return [inv for inv in invariants if inv.confidence >= self.min_confidence]

    def _type_contracts(self, facts: list[PythonFacts]) -> list[Invariant]:
        field_types: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for fact in facts:
            for class_name, fields in fact.classes.items():
                for field, annotation in fields.items():
                    field_types[field].append((fact.file_path, class_name, annotation))
            for func, sig in fact.functions.items():
                for param, annotation in sig["params"].items():
                    if annotation != "unknown":
                        field_types[param].append((fact.file_path, func, annotation))
        invariants: list[Invariant] = []
        for field, examples in field_types.items():
            if len(examples) < 2:
                continue
            counts = Counter(annotation for _, _, annotation in examples)
            annotation, count = counts.most_common(1)[0]
            confidence = count / len(examples)
            source_files = sorted({file for file, _, _ in examples})
            invariants.append(
                Invariant(
                    name=f"{field} is consistently {annotation}",
                    description=f"The field or parameter `{field}` is usually annotated as `{annotation}`.",
                    invariant_type="type_contract",
                    scope=field,
                    source_files=source_files,
                    confidence=confidence,
                    evidence={
                        "field": field,
                        "expected_type": annotation,
                        "examples": [
                            {"file": file, "symbol": symbol, "type": typ}
                            for file, symbol, typ in examples
                            if typ == annotation
                        ],
                        "observed_total": len(examples),
                        "matching": count,
                    },
                )
            )
        return invariants

    def _response_shapes(self, facts: list[PythonFacts]) -> list[Invariant]:
        by_file: dict[str, list[tuple[str, tuple[str, ...]]]] = defaultdict(list)
        for fact in facts:
            for func, returns in fact.dict_returns.items():
                for keys in returns:
                    by_file[fact.file_path].append((func, tuple(sorted(keys))))
        invariants: list[Invariant] = []
        for file_path, shapes in by_file.items():
            endpointish = [item for item in shapes if any(word in item[0] for word in ("handler", "route", "endpoint", "get_", "post_", "list_"))]
            candidates = endpointish or shapes
            if len(candidates) < 2:
                continue
            counts = Counter(shape for _, shape in candidates)
            shape, count = counts.most_common(1)[0]
            confidence = count / len(candidates)
            invariants.append(
                Invariant(
                    name=f"{file_path} returns {{{', '.join(shape)}}}",
                    description=f"Dictionary returns in `{file_path}` usually expose keys {list(shape)}.",
                    invariant_type="data_shape",
                    scope=file_path,
                    source_files=[file_path],
                    confidence=confidence,
                    evidence={
                        "shape": list(shape),
                        "examples": [{"function": func, "keys": list(keys)} for func, keys in candidates],
                    },
                )
            )
        return invariants

    def _behavioral_migrations(self, facts: list[PythonFacts]) -> list[Invariant]:
        migration_files = [fact for fact in facts if "migration" in fact.file_path.lower()]
        if not migration_files:
            return []
        matches = [fact for fact in migration_files if "up" in fact.functions and "down" in fact.functions]
        confidence = len(matches) / len(migration_files)
        return [
            Invariant(
                name="Migrations define reversible down()",
                description="Migration files are expected to define both up() and down().",
                invariant_type="behavioral",
                scope="migrations",
                source_files=[fact.file_path for fact in migration_files],
                confidence=confidence,
                evidence={
                    "required_functions": ["up", "down"],
                    "matching_files": [fact.file_path for fact in matches],
                    "observed_total": len(migration_files),
                },
            )
        ]

    def _call_patterns(self, facts: list[PythonFacts]) -> list[Invariant]:
        invariants: list[Invariant] = []
        for fact in facts:
            functions = list(fact.functions)
            if len(functions) < 2:
                continue
            call_counts = Counter(call for calls in fact.function_calls.values() for call in set(calls))
            for call, count in call_counts.items():
                confidence = count / len(functions)
                if confidence >= self.min_confidence and call.endswith(("auth_check", "validate", "close")):
                    invariants.append(
                        Invariant(
                            name=f"{fact.file_path} functions call {call}",
                            description=f"Most functions in `{fact.file_path}` call `{call}`.",
                            invariant_type="behavioral",
                            scope=fact.file_path,
                            source_files=[fact.file_path],
                            confidence=confidence,
                            evidence={"call": call, "matching_functions": count, "total_functions": len(functions)},
                        )
                    )
        return invariants

    def _cross_module_user_id(self, facts: list[PythonFacts]) -> list[Invariant]:
        examples: list[dict[str, str]] = []
        for fact in facts:
            for func, sig in fact.functions.items():
                typ = sig["params"].get("user_id")
                if typ and typ != "unknown":
                    examples.append({"file": fact.file_path, "symbol": func, "type": typ})
        if len(examples) < 2:
            return []
        counts = Counter(example["type"] for example in examples)
        typ, count = counts.most_common(1)[0]
        return [
            Invariant(
                name=f"Cross-module user_id contract is {typ}",
                description=f"Modules that exchange `user_id` consistently expect `{typ}`.",
                invariant_type="cross_module",
                scope="user_id",
                source_files=sorted({example["file"] for example in examples}),
                confidence=count / len(examples),
                evidence={"field": "user_id", "expected_type": typ, "examples": examples, "matching": count},
            )
        ]

    def _conventions(self, files: list[Path], root: Path) -> list[Invariant]:
        invariants: list[Invariant] = []
        for item in filename_conventions(files, root):
            total = int(item["total"])
            confidence = int(item["count"]) / total if total else 0.0
            invariants.append(
                Invariant(
                    name=f"{item['scope']} follows {item['pattern']} naming",
                    description=f"Files in `{item['scope']}` commonly follow `{item['pattern']}`.",
                    invariant_type="convention",
                    scope=str(item["scope"]),
                    source_files=[str(path.relative_to(root)) for path in files if str(path.relative_to(root).parent) == item["scope"]],
                    confidence=confidence,
                    evidence=item,
                )
            )
        return invariants

    def _import_couplings(self, files: list[Path], root: Path) -> list[Invariant]:
        imports = find_import_patterns(files, root)
        invariants: list[Invariant] = []
        for file_path, targets in imports.items():
            if len(targets) >= 2:
                invariants.append(
                    Invariant(
                        name=f"{file_path} import coupling",
                        description=f"`{file_path}` has stable module dependencies.",
                        invariant_type="cross_module",
                        scope=file_path,
                        source_files=[file_path],
                        confidence=1.0,
                        evidence={"imports": targets},
                    )
                )
        return invariants
