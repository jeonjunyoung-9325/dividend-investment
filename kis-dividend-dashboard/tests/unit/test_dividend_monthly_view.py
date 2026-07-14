from datetime import date
from decimal import Decimal

import pandas as pd
from src.services.ui_read_service import _monthly_frame


def test_regular_forecast_is_allocated_by_observed_cadence() -> None:
    # Given: a quarterly KRW forecast whose latest observed event was in June.
    forecast = pd.DataFrame(
        [
            {
                "연간 예상 지급 횟수": 4,
                "예상 세전 원화": Decimal(120000),
                "마지막 데이터": date(2026, 6, 24),
            }
        ]
    )

    # When: the monthly dashboard series is generated.
    monthly = _monthly_frame((), forecast)

    # Then: equal estimated installments appear at three-month intervals only.
    values = dict(zip(monthly["월"], monthly["예상"], strict=True))
    assert values["3월"] == Decimal(30000)
    assert values["6월"] == Decimal(30000)
    assert values["9월"] == Decimal(30000)
    assert values["12월"] == Decimal(30000)
    assert sum(values.values(), Decimal(0)) == Decimal(120000)
