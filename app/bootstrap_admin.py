"""One-shot platform superuser bootstrap: python -m app.bootstrap_admin."""

from app.config import settings
from app.db.session import SessionLocal
from app.services.admin import bootstrap_superuser


def main() -> None:
    credentials = (
        settings.bootstrap_admin_username,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    if not all(credentials):
        raise SystemExit(
            "Set BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_EMAIL, "
            "and BOOTSTRAP_ADMIN_PASSWORD"
        )

    db = SessionLocal()
    try:
        admin = bootstrap_superuser(
            db,
            username=credentials[0],
            email=credentials[1],
            password=credentials[2],
        )
        print(f"Platform superuser ready: {admin.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
