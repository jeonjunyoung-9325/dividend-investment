from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

SENSITIVE_ASSIGNMENT: Final = re.compile(
    r"(?i)(authorization|app[_-]?key|app[_-]?secret|access[_-]?token|"
    r"password|encryption[_-]?key|session[_-]?secret)\s*[:=]\s*([^\s,;]+)"
)
ACCOUNT_NUMBER: Final = re.compile(r"(?<!\d)(\d{4})\d{4}(?:-?\d{2})?(?!\d)")
DATABASE_CREDENTIALS: Final = re.compile(
    r"(?i)(postgres(?:ql)?(?:\+psycopg)?://[^:\s]+:)[^@\s]+(@)"
)


class SecretRedactionFilter(logging.Filter):
    """Remove configured secrets and common credential shapes before emission."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = tuple(value for value in secrets if value)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self._secrets:
            message = message.replace(secret, "<redacted>")
        message = SENSITIVE_ASSIGNMENT.sub(r"\1=<redacted>", message)
        message = DATABASE_CREDENTIALS.sub(r"\1<redacted>\2", message)
        message = ACCOUNT_NUMBER.sub(r"\1****-**", message)
        record.msg = message
        record.args = ()
        return True


def configure_logging(*, secrets: Iterable[str] = (), level: int = logging.INFO) -> None:
    """Configure a concise root handler shared by Streamlit and CLI entry points."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S%z")
    )
    handler.addFilter(SecretRedactionFilter(secrets))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
