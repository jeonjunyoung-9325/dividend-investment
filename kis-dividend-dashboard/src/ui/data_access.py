"""Lazy UI data-provider boundary that preserves the pre-login access gate."""

from src.ui.viewmodels import (
    CalendarView,
    DashboardView,
    DividendView,
    EditableSettingView,
    HistoryView,
    ImportColumnMapping,
    ImportPreviewView,
    ImportResultView,
    PortfolioView,
    SyncView,
)


def dashboard_view(*, is_demo: bool) -> DashboardView:
    """Load dashboard data from the isolated demo or production provider."""
    if is_demo:
        from src.demo_data import get_dashboard_view  # noqa: PLC0415

        return get_dashboard_view()
    from src.services.ui_read_service import get_dashboard_view  # noqa: PLC0415

    return get_dashboard_view()


def portfolio_view(*, is_demo: bool) -> PortfolioView:
    """Load portfolio data without importing providers before authentication."""
    if is_demo:
        from src.demo_data import get_portfolio_view  # noqa: PLC0415

        return get_portfolio_view()
    from src.services.ui_read_service import get_portfolio_view  # noqa: PLC0415

    return get_portfolio_view()


def dividend_view(*, is_demo: bool) -> DividendView:
    """Load dividend data from the selected isolated provider."""
    if is_demo:
        from src.demo_data import get_dividend_view  # noqa: PLC0415

        return get_dividend_view()
    from src.services.ui_read_service import get_dividend_view  # noqa: PLC0415

    return get_dividend_view()


def calendar_view(*, is_demo: bool) -> CalendarView:
    """Load dividend calendar events from the selected provider."""
    if is_demo:
        from src.demo_data import get_calendar_view  # noqa: PLC0415

        return get_calendar_view()
    from src.services.ui_read_service import get_calendar_view  # noqa: PLC0415

    return get_calendar_view()


def history_view(*, is_demo: bool) -> HistoryView:
    """Load asset history from the selected provider."""
    if is_demo:
        from src.demo_data import get_history_view  # noqa: PLC0415

        return get_history_view()
    from src.services.ui_read_service import get_history_view  # noqa: PLC0415

    return get_history_view()


def editable_settings(*, is_demo: bool) -> EditableSettingView:
    """Load only non-secret settings exposed by the selected provider."""
    if is_demo:
        from src.demo_data import get_editable_settings  # noqa: PLC0415

        return get_editable_settings()
    from src.services.ui_read_service import get_editable_settings  # noqa: PLC0415

    return get_editable_settings()


def save_editable_settings(settings: EditableSettingView, *, is_demo: bool) -> None:
    """Persist only the explicitly editable non-secret settings."""
    if is_demo:
        from src.demo_data import save_editable_settings  # noqa: PLC0415

        save_editable_settings(settings)
        return
    from src.services.ui_read_service import save_editable_settings  # noqa: PLC0415

    save_editable_settings(settings)


def synchronize(*, is_demo: bool) -> SyncView:
    """Run the demo or production synchronization service."""
    if is_demo:
        from src.demo_data import synchronize_demo  # noqa: PLC0415

        return synchronize_demo()
    from src.services.sync_service import synchronize_for_ui  # noqa: PLC0415

    return synchronize_for_ui()


def preview_dividend_import(filename: str, content: bytes) -> ImportPreviewView:
    """Validate an uploaded dividend file in memory without persistence."""
    from src.services.import_service import preview_dividend_import  # noqa: PLC0415

    return preview_dividend_import(filename, content)


def commit_dividend_import(
    filename: str,
    content: bytes,
    mappings: tuple[ImportColumnMapping, ...],
    *,
    source: str = "user_upload",
) -> ImportResultView:
    """Commit a confirmed dividend import through the service boundary."""
    from src.services.import_service import commit_dividend_import  # noqa: PLC0415

    return commit_dividend_import(filename, content, mappings, source=source)
