import logging

from src.logging_config import SecretRedactionFilter


def test_filter_redacts_configured_and_structured_secrets() -> None:
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "token-value Authorization: Bearer-value account=12345678 "
        "postgresql://user:db-password@host/db",
        (),
        None,
    )

    allowed = SecretRedactionFilter(["token-value", "Bearer-value"]).filter(record)

    message = record.getMessage()
    assert allowed
    assert "token-value" not in message
    assert "Bearer-value" not in message
    assert "db-password" not in message
    assert "1234****-**" in message
