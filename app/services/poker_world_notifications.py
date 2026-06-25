from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import UserNotification
from app.services.notifications import create_notification

NOTIFICATION_TYPE = "poker_world.tournament_reminder"


def _tournament_link(venue_id: str, tournament_id: str) -> str:
    base = settings.poker_world_launch_url.rstrip("/")
    return f"{base}/venues/{venue_id}/tournaments/{tournament_id}"


def _reminder_title(tournament_name: str) -> str:
    return f"{tournament_name} starts soon"


def _reminder_body(venue_name: str | None, hours_until_start: float | None) -> str:
    venue_part = f" at {venue_name}" if venue_name else ""
    if hours_until_start is None:
        return f"Your favorited tournament{venue_part} is starting soon."
    hours = int(hours_until_start) if hours_until_start == int(hours_until_start) else hours_until_start
    unit = "hour" if hours == 1 else "hours"
    return f"Your favorited tournament{venue_part} starts in {hours} {unit}."


def find_tournament_reminder(
    db: Session, user_id: str, tournament_id: str, venue_id: str
) -> UserNotification | None:
    link = _tournament_link(venue_id, tournament_id)
    return db.scalar(
        select(UserNotification).where(
            UserNotification.user_id == user_id,
            UserNotification.type == NOTIFICATION_TYPE,
            UserNotification.link == link,
        )
    )


def process_tournament_starting_soon(db: Session, data: dict) -> UserNotification | None:
    user_id = data.get("userId")
    tournament_id = data.get("tournamentId")
    venue_id = data.get("venueId")
    if not user_id or not tournament_id or not venue_id:
        return None

    if find_tournament_reminder(db, user_id, tournament_id, venue_id):
        return None

    tournament_name = data.get("tournamentName") or "Tournament"
    return create_notification(
        db,
        user_id=user_id,
        type=NOTIFICATION_TYPE,
        title=_reminder_title(tournament_name),
        body=_reminder_body(data.get("venueName"), data.get("hoursUntilStart")),
        link=_tournament_link(venue_id, tournament_id),
    )
