import asyncio
import json
from sqlalchemy import select

from app.models import UserNotification
from app.services.poker_world_notifications import (
    NOTIFICATION_TYPE,
    process_tournament_starting_soon,
)

TOURNAMENT_ID = "770e8400-e29b-41d4-a716-446655440002"
VENUE_ID = "550e8400-e29b-41d4-a716-446655440000"
USER_ID = "player-reminder-1"


def _event_data(**overrides):
    data = {
        "userId": USER_ID,
        "tournamentId": TOURNAMENT_ID,
        "venueId": VENUE_ID,
        "venueName": "Bellagio Poker Room",
        "tournamentName": "Daily Deepstack",
        "startTime": "2026-06-23T23:00:00Z",
        "hoursUntilStart": 1,
    }
    data.update(overrides)
    return data


def test_process_tournament_starting_soon_creates_notification(db):
    row = process_tournament_starting_soon(db, _event_data())
    assert row is not None
    assert row.user_id == USER_ID
    assert row.type == NOTIFICATION_TYPE
    assert row.title == "Daily Deepstack starts soon"
    assert "Bellagio Poker Room" in row.body
    assert row.link.endswith(f"/venues/{VENUE_ID}/tournaments/{TOURNAMENT_ID}")


def test_process_tournament_starting_soon_idempotent(db):
    first = process_tournament_starting_soon(db, _event_data())
    second = process_tournament_starting_soon(db, _event_data())
    assert first is not None
    assert second is None
    rows = db.scalars(
        select(UserNotification).where(
            UserNotification.user_id == USER_ID,
            UserNotification.type == NOTIFICATION_TYPE,
        )
    ).all()
    assert len(rows) == 1


def test_process_tournament_starting_soon_missing_fields_noop(db):
    assert process_tournament_starting_soon(db, {"tournamentName": "X"}) is None


def test_start_poker_world_consumer_noops_without_nats(monkeypatch):
    from app.consumers import poker_world as consumer_mod

    monkeypatch.setattr("app.events.settings.nats_url", "")
    sub = asyncio.run(consumer_mod.start_poker_world_consumer())
    assert sub is None


def test_consumer_handles_envelope(db, monkeypatch):
    from app.consumers.poker_world import _on_tournament_starting_soon

    class FakeMsg:
        data = json.dumps(
            {
                "id": "evt_test",
                "type": "poker_world.tournament.starting_soon",
                "version": "1.0",
                "timestamp": "2026-06-23T22:00:00Z",
                "producer": "pokerworld-backend",
                "data": _event_data(),
            }
        ).encode()

    asyncio.run(_on_tournament_starting_soon(FakeMsg()))
    rows = db.scalars(
        select(UserNotification).where(
            UserNotification.user_id == USER_ID,
            UserNotification.type == NOTIFICATION_TYPE,
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].title == "Daily Deepstack starts soon"


def test_consumer_ignores_invalid_json(db):
    from app.consumers.poker_world import _on_tournament_starting_soon

    class FakeMsg:
        data = b"not-json"

    asyncio.run(_on_tournament_starting_soon(FakeMsg()))
    assert db.scalars(select(UserNotification)).all() == []


def test_get_nats_noops_when_unset(monkeypatch):
    from app.events import get_nats

    monkeypatch.setattr("app.events.settings.nats_url", "")
    assert asyncio.run(get_nats()) is None
