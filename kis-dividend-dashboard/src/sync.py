from __future__ import annotations

import logging

from src.logging_config import configure_logging
from src.services.sync_service import synchronize_for_ui


def main() -> int:
    configure_logging()
    result = synchronize_for_ui()
    logging.getLogger(__name__).info(
        "sync status=%s inserted=%d updated=%d token=%s",
        result.state,
        result.inserted,
        result.updated,
        result.token_action,
    )
    return 0 if result.state in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
