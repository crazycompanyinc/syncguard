from __future__ import annotations

from click.testing import CliRunner

from syncguard.cli import main


def test_cli_init(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".syncguard" / "syncguard.db").exists()


def test_cli_extract_and_patterns(sample_project, monkeypatch) -> None:
    monkeypatch.chdir(sample_project)
    result = CliRunner().invoke(main, ["extract", "--path", str(sample_project)])
    assert result.exit_code == 0, result.output
    patterns = CliRunner().invoke(main, ["patterns", "--type", "data_shape"])
    assert patterns.exit_code == 0
    assert "data_shape" in patterns.output


def test_cli_predict_without_drifts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["predict"])
    assert result.exit_code == 0
    assert result.output == ""
