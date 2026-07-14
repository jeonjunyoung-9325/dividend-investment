from src.config import Settings


def test_blank_usd_krw_rate_uses_safe_fallback() -> None:
    # Given
    configured_rate = ""

    # When
    settings = Settings(_env_file=None, DEFAULT_USD_KRW_RATE=configured_rate)

    # Then
    assert settings.DEFAULT_USD_KRW_RATE == "1350"
