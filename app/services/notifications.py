import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UserNotification


def create_notification(
    db: Session,
    *,
    user_id: str,
    type: str,
    title: str,
    body: str,
    link: str = "",
) -> UserNotification:
    row = UserNotification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
        read=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_notifications(
    db: Session, user_id: str, *, unread_only: bool = False, limit: int = 50
) -> tuple[list[UserNotification], int]:
    stmt = (
        select(UserNotification)
        .where(UserNotification.user_id == user_id)
        .order_by(UserNotification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(UserNotification.read.is_(False))
    items = list(db.scalars(stmt))
    unread = db.scalar(
        select(func.count())
        .select_from(UserNotification)
        .where(UserNotification.user_id == user_id, UserNotification.read.is_(False))
    )
    return items, unread or 0


def mark_read(db: Session, user_id: str, notification_id: str) -> UserNotification | None:
    row = db.get(UserNotification, notification_id)
    if not row or row.user_id != user_id:
        return None
    row.read = True
    db.commit()
    db.refresh(row)
    return row
