from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    (tmp_path / "api").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "migrations").mkdir()
    (tmp_path / "api" / "models.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    user_id: str\n    name: str\n",
        encoding="utf-8",
    )
    (tmp_path / "api" / "handlers.py").write_text(
        "def get_user_handler():\n    return {'data': {}, 'meta': {}, 'links': {}}\n\n"
        "def list_user_handler():\n    return {'data': [], 'meta': {}, 'links': {}}\n",
        encoding="utf-8",
    )
    (tmp_path / "services" / "payment.py").write_text(
        "def consume_payment(user_id: str) -> None:\n    assert isinstance(user_id, str)\n",
        encoding="utf-8",
    )
    (tmp_path / "services" / "notification.py").write_text(
        "def consume_notification(user_id: str) -> None:\n    assert isinstance(user_id, str)\n",
        encoding="utf-8",
    )
    (tmp_path / "migrations" / "001_create_users.py").write_text(
        "def up():\n    pass\n\n\ndef down():\n    pass\n",
        encoding="utf-8",
    )
    return tmp_path
