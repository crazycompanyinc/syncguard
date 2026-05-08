from __future__ import annotations

from syncguard.extractor.python_ast import analyze_python_file


def test_python_analyzer_extracts_class_fields(tmp_path) -> None:
    path = tmp_path / "model.py"
    path.write_text("class User:\n    user_id: str\n", encoding="utf-8")
    facts = analyze_python_file(path, tmp_path)
    assert facts is not None
    assert facts.classes["User"]["user_id"] == "str"


def test_python_analyzer_extracts_return_shape_and_calls(tmp_path) -> None:
    path = tmp_path / "handlers.py"
    path.write_text("def get_handler():\n    auth_check()\n    return {'data': {}, 'meta': {}}\n", encoding="utf-8")
    facts = analyze_python_file(path, tmp_path)
    assert facts is not None
    assert facts.dict_returns["get_handler"] == [{"data", "meta"}]
    assert facts.function_calls["get_handler"] == ["auth_check"]
