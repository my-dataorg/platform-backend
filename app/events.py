import logging

from app.config import settings

logger = logging.getLogger(__name__)

_nats_client = None
_nats_disabled = False


async def get_nats():
    global _nats_client, _nats_disabled
    if _nats_disabled or not settings.nats_url:
        return None
    if _nats_client is not None:
        return _nats_client
    try:
        import nats

        _nats_client = await nats.connect(settings.nats_url, connect_timeout=2)
        return _nats_client
    except Exception as exc:
        logger.warning("NATS unavailable, consumers disabled: %s", exc)
        _nats_disabled = True
        return None


async def close_nats() -> None:
    global _nats_client
    if _nats_client is None:
        return
    try:
        await _nats_client.drain()
        await _nats_client.close()
    except Exception as exc:
        logger.warning("Error closing NATS: %s", exc)
    finally:
        _nats_client = None
