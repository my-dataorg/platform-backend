import json
import logging

from app.db.session import SessionLocal
from app.events import get_nats
from app.services.poker_world_notifications import process_tournament_starting_soon

logger = logging.getLogger(__name__)

SUBJECT = "poker_world.tournament.starting_soon"
_subscription = None


async def _on_tournament_starting_soon(msg) -> None:
    try:
        envelope = json.loads(msg.data.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Invalid tournament.starting_soon payload: %s", exc)
        return

    if envelope.get("type") != SUBJECT:
        return

    data = envelope.get("data") or {}
    db = SessionLocal()
    try:
        process_tournament_starting_soon(db, data)
    except Exception as exc:
        logger.warning("Failed to process tournament.starting_soon: %s", exc)
        db.rollback()
    finally:
        db.close()


async def start_poker_world_consumer():
    global _subscription
    nc = await get_nats()
    if not nc:
        return None
    _subscription = await nc.subscribe(SUBJECT, cb=_on_tournament_starting_soon)
    logger.info("Subscribed to %s", SUBJECT)
    return _subscription


async def stop_poker_world_consumer() -> None:
    global _subscription
    if _subscription is None:
        return
    try:
        await _subscription.unsubscribe()
    except Exception as exc:
        logger.warning("Error unsubscribing from %s: %s", SUBJECT, exc)
    finally:
        _subscription = None
