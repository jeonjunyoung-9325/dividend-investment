from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from src.database import create_database_engine, create_session_factory
from src.models import Base, DividendPayment, SyncRun
from src.repositories.dividends import (
    UNVERIFIED_ACCOUNT_RIGHTS_SOURCE,
    insert_payments,
    list_payments,
    purge_unverified_account_rights_payments,
)
from src.repositories.positions import list_latest_positions
from src.repositories.snapshots import asset_history, upsert_positions
from src.schemas import DividendPaymentInput, Market, Position


def _factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def _position(instant: datetime) -> Position:
    return Position(
        market=Market.OVERSEAS,
        exchange="NYSE",
        symbol="O",
        name="Realty Income",
        quantity=Decimal(2),
        evaluation_amount=Decimal(100),
        profit_loss=Decimal(10),
        currency="USD",
        krw_exchange_rate=Decimal(1350),
        evaluation_amount_krw=Decimal(135000),
        profit_loss_krw=Decimal(13500),
        queried_at=instant,
        source="test",
    )


def test_snapshot_upsert_is_idempotent_and_readable() -> None:
    factory = _factory()
    instant = datetime(2026, 7, 14, tzinfo=UTC)
    with factory() as session, session.begin():
        session.add(SyncRun(id="run", started_at=instant, status="success"))
    with factory() as session, session.begin():
        assert upsert_positions(session, sync_run_id="run", positions=(_position(instant),)) == (
            1,
            0,
        )
        assert upsert_positions(session, sync_run_id="run", positions=(_position(instant),)) == (
            0,
            1,
        )
    with factory() as session:
        latest = list_latest_positions(session)
        history = asset_history(session)
    assert len(latest) == 1
    assert latest[0].symbol == "O"
    assert history[0][1] == Decimal("135000.00000000")


def test_payment_import_hash_prevents_duplicate_rows() -> None:
    factory = _factory()
    payment = DividendPaymentInput(
        market=Market.OVERSEAS,
        exchange="NYSE",
        symbol="O",
        name="Realty Income",
        payment_date=date(2026, 7, 14),
        gross_amount=Decimal(10),
        tax_amount=Decimal("1.5"),
        net_amount=Decimal("8.5"),
        currency="USD",
        krw_exchange_rate=Decimal(1350),
        import_hash="a" * 64,
    )
    with factory() as session, session.begin():
        assert insert_payments(session, (payment, payment)) == (1, 1)
    with factory() as session:
        assert len(tuple(session.scalars(select(DividendPayment)))) == 1


def test_unverified_account_rights_are_removed_from_actual_payments() -> None:
    factory = _factory()
    with factory() as session, session.begin():
        session.add(
            DividendPayment(
                market="domestic",
                exchange="KRX",
                symbol="475720",
                name="RISE 200위클리커버드콜",
                payment_date=date(2026, 7, 2),
                gross_amount=Decimal(5600),
                tax_amount=Decimal(0),
                net_amount=Decimal(5600),
                currency="KRW",
                source=UNVERIFIED_ACCOUNT_RIGHTS_SOURCE,
            )
        )
    with factory() as session, session.begin():
        assert list_payments(session) == ()
        assert purge_unverified_account_rights_payments(session) == 1
    with factory() as session:
        assert tuple(session.scalars(select(DividendPayment))) == ()
