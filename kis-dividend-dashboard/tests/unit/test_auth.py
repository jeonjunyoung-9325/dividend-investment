from __future__ import annotations

from typing import TYPE_CHECKING

from src.ui.auth import secret_value

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_secret_value_reads_local_dotenv_when_process_environment_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    expected_hash = "$argon2id$local-development-hash"
    (tmp_path / ".env").write_text(
        f"APP_PASSWORD_HASH={expected_hash}\nDEMO_MODE=true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)

    # When
    actual_hash = secret_value("APP_PASSWORD_HASH")

    # Then
    assert actual_hash == expected_hash
