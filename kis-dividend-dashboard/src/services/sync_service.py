from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

from sqlalchemy.exc import SQLAlchemyError

from src.config import Settings, get_settings
from src.database import create_database_engine, create_session_factory
from src.kis.auth import HttpTokenIssuer, InMemoryTokenStore, SystemClock, TokenManager
from src.kis.client import DEMO_BASE_URL, REAL_BASE_URL, KisClient, KisClientConfig, KisEnvironment
from src.kis.domestic import DomesticBalanceRequest, fetch_domestic_balance
from src.kis.exceptions import KisError
from src.kis.token_io import TokenAcquisitionSource, TokenPolicyError
from src.models import SyncRun
from src.repositories.sync_runs import SyncLockTimeoutError, start_run, synchronization_lock
from src.repositories.tokens import TokenIdentity, TokenRepository
from src.security import TokenCipher, app_key_fingerprint
from src.services.dividend_sync_service import DividendSyncRequest, synchronize_dividend_events
from src.services.overseas_sync_service import (
    CURRENCY_BY_EXCHANGE,
    OverseasSyncRequest,
    enabled_exchanges,
    fetch_overseas_positions,
    rates_for_exchanges,
)
from src.services.portfolio_service import normalize_domestic
from src.services.snapshot_service import save_snapshot
from src.ui.viewmodels import SyncView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

    from src.schemas import Position


@dataclass(slots=True)
class _AccessTokenProvider:
    manager: TokenManager
    identity: TokenIdentity
    access_action: Literal["reused", "issued", "not_used"] = "not_used"

    def get_access_token(self) -> str:
        acquisition = self.manager.get_access_token(self.identity)
        self.access_action = (
            "issued" if acquisition.source is TokenAcquisitionSource.ISSUED else "reused"
        )
        return acquisition.access_token


@dataclass(frozen=True, slots=True)
class _Runtime:
    settings: Settings
    session_factory: sessionmaker[Session]
    client: KisClient
    token_provider: _AccessTokenProvider


@lru_cache(maxsize=1)
def _runtime() -> _Runtime:
    settings = get_settings()
    settings.validate_runtime()
    engine = create_database_engine(settings.SUPABASE_DB_URL.get_secret_value())
    factory = create_session_factory(engine)
    environment = KisEnvironment(settings.KIS_MODE)
    app_key = settings.KIS_APP_KEY.get_secret_value()
    token_manager = TokenManager(
        repository=TokenRepository(factory),
        cipher=TokenCipher(settings.TOKEN_ENCRYPTION_KEY.get_secret_value()),
        issuer=HttpTokenIssuer(
            base_url=REAL_BASE_URL if environment is KisEnvironment.REAL else DEMO_BASE_URL,
            app_key=app_key,
            app_secret=settings.KIS_APP_SECRET.get_secret_value(),
        ),
        clock=SystemClock(),
        memory=InMemoryTokenStore(),
        expiry_buffer=timedelta(minutes=settings.TOKEN_EXPIRY_BUFFER_MINUTES),
        demo_mode=False,
        lock_timeout_seconds=settings.TOKEN_LOCK_TIMEOUT_SECONDS,
    )
    identity = TokenIdentity(settings.KIS_MODE, app_key_fingerprint(app_key))
    provider = _AccessTokenProvider(token_manager, identity)
    client = KisClient(
        KisClientConfig(
            environment=environment,
            app_key=settings.KIS_APP_KEY,
            app_secret=settings.KIS_APP_SECRET,
        ),
        provider,
    )
    return _Runtime(settings, factory, client, provider)


def synchronize_for_ui() -> SyncView:
    if get_settings().DEMO_MODE:
        return SyncView(
            "failed", "DEMO_MODE에서는 실제 동기화를 실행하지 않습니다.", None, "not_used"
        )
    try:
        runtime = _runtime()
        with synchronization_lock(
            runtime.session_factory,
            timeout_seconds=runtime.settings.TOKEN_LOCK_TIMEOUT_SECONDS,
        ):
            return _synchronize(runtime)
    except SyncLockTimeoutError:
        return SyncView(
            "failed",
            "다른 동기화가 실행 중입니다. 완료 후 다시 시도해 주세요.",
            None,
            "not_used",
            failures=("동기화 잠금 대기 시간 초과",),
        )
    except SQLAlchemyError:
        return SyncView(
            "failed",
            "데이터베이스에 연결하지 못했습니다. 마지막 정상 데이터를 표시합니다.",
            None,
            "not_used",
            failures=("데이터베이스 연결 실패",),
        )
    except (RuntimeError, ValueError):
        return SyncView(
            "failed",
            "서버 Secret 설정을 확인해 주세요. 민감정보는 화면에 표시하지 않습니다.",
            None,
            "not_used",
            failures=("서버 설정 검증 실패",),
        )


def _synchronize(runtime: _Runtime) -> SyncView:
    runtime.token_provider.access_action = "not_used"
    now = datetime.now(UTC)
    with runtime.session_factory() as session, session.begin():
        run = start_run(session, started_at=now)
        run_id = run.id

    default_rate = _default_usd_rate(runtime.settings)
    account = runtime.settings.KIS_ACCOUNT_NO.get_secret_value().replace("-", "")
    domestic_status, domestic_positions, domestic_failures = _fetch_domestic(runtime, account, now)

    with runtime.session_factory() as session:
        exchanges = enabled_exchanges(session)
        rates = rates_for_exchanges(session, exchanges, default_rate, now)
        session.commit()
    exchange_status = (
        "success" if all(CURRENCY_BY_EXCHANGE[item] in rates for item in exchanges) else "partial"
    )
    overseas_status, overseas_positions, overseas_failures = fetch_overseas_positions(
        runtime.client,
        OverseasSyncRequest(
            account=account,
            product_code=runtime.settings.KIS_ACCOUNT_PRODUCT_CODE,
            exchanges=exchanges,
            rates=rates,
            now=now,
        ),
    )
    positions = domestic_positions + overseas_positions
    dividend_status, event_inserted, event_updated, dividend_failures = synchronize_dividend_events(
        runtime.client,
        runtime.session_factory,
        DividendSyncRequest(positions, now),
    )
    failures = domestic_failures + overseas_failures + dividend_failures

    inserted = event_inserted
    updated = event_updated
    if positions:
        with runtime.session_factory() as session, session.begin():
            snapshot_inserted, snapshot_updated = save_snapshot(
                session, sync_run_id=run_id, positions=tuple(positions)
            )
            inserted += snapshot_inserted
            updated += snapshot_updated

    essential_success = domestic_status == "success" or overseas_status in {"success", "partial"}
    status = (
        "success"
        if essential_success and not failures
        else "partial"
        if essential_success
        else "failed"
    )
    message = {
        "success": "동기화를 완료했습니다.",
        "partial": "일부 조회에 실패해 성공한 데이터와 마지막 정상 데이터를 표시합니다.",
        "failed": "동기화하지 못했습니다. 마지막 정상 데이터를 표시합니다.",
    }[status]
    finished = datetime.now(UTC)
    with runtime.session_factory() as session, session.begin():
        run = session.get(SyncRun, run_id)
        if run is not None:
            run.finished_at = finished
            run.status = status
            run.domestic_status = domestic_status
            run.overseas_status = overseas_status
            run.dividend_status = dividend_status
            run.exchange_rate_status = exchange_status
            run.message = message
            run.records_inserted = inserted
            run.records_updated = updated
    return SyncView(
        status,
        message,
        finished if status in {"success", "partial"} else None,
        runtime.token_provider.access_action,
        inserted,
        updated,
        tuple(failures),
    )


def _fetch_domestic(
    runtime: _Runtime, account: str, now: datetime
) -> tuple[str, tuple[Position, ...], list[str]]:
    try:
        result = fetch_domestic_balance(
            runtime.client,
            DomesticBalanceRequest(
                account_no=account,
                product_code=runtime.settings.KIS_ACCOUNT_PRODUCT_CODE,
            ),
        )
    except (KisError, TokenPolicyError, ValueError):
        return "failed", (), ["국내주식 잔고 조회 실패"]
    return "success", normalize_domestic(result, now), []


def _default_usd_rate(settings: Settings) -> Decimal:
    try:
        rate = Decimal(settings.DEFAULT_USD_KRW_RATE)
    except InvalidOperation:
        return Decimal(0)
    return rate if rate > 0 else Decimal(0)
