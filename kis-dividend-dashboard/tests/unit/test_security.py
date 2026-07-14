from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken
from src.security import TokenCipher, app_key_fingerprint, mask_account_number


def test_token_cipher_round_trip_does_not_preserve_plaintext() -> None:
    key = Fernet.generate_key().decode("ascii")
    cipher = TokenCipher(key)

    encrypted = cipher.encrypt("secret-access-token")

    assert encrypted != b"secret-access-token"
    assert cipher.decrypt(encrypted) == "secret-access-token"


def test_token_cipher_rejects_a_different_key() -> None:
    encrypted = TokenCipher(Fernet.generate_key().decode("ascii")).encrypt("token")

    with pytest.raises(InvalidToken):
        TokenCipher(Fernet.generate_key().decode("ascii")).decrypt(encrypted)


def test_app_key_fingerprint_is_stable_and_non_reversible() -> None:
    first = app_key_fingerprint("app-key-value")

    assert first == app_key_fingerprint("app-key-value")
    assert first != app_key_fingerprint("different-app-key")
    assert len(first) == 64
    assert "app-key-value" not in first


def test_account_number_is_masked() -> None:
    assert mask_account_number("12345678-01") == "1234****-**"
