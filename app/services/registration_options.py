import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference_data import Country, GenderOption, StateProvince

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COUNTRIES = tuple(
    (item["code"], item["name"])
    for item in json.loads((DATA_DIR / "countries.json").read_text())
)
STATES = tuple(
    (item["code"], item["country_code"], item["name"])
    for item in json.loads((DATA_DIR / "states.json").read_text())
)

GENDERS = (
    ("agender", "Agender"),
    ("bigender", "Bigender"),
    ("female", "Female"),
    ("genderfluid", "Genderfluid"),
    ("genderqueer", "Genderqueer"),
    ("intersex", "Intersex"),
    ("male", "Male"),
    ("non_binary", "Non-binary"),
    ("prefer_not_to_say", "Prefer not to say"),
    ("other", "Other"),
    ("transgender", "Transgender"),
    ("two_spirit", "Two-spirit"),
)


def seed_registration_options(db: Session) -> None:
    for order, (code, name) in enumerate(COUNTRIES):
        if not db.get(Country, code):
            db.add(Country(code=code, name=name, sort_order=order))

    for order, (code, country_code, name) in enumerate(STATES):
        if not db.get(StateProvince, code):
            db.add(
                StateProvince(
                    code=code,
                    country_code=country_code,
                    name=name,
                    sort_order=order,
                )
            )

    for order, (code, label) in enumerate(GENDERS):
        if not db.get(GenderOption, code):
            db.add(GenderOption(code=code, label=label, sort_order=order))
    db.commit()


def ensure_registration_options(db: Session) -> None:
    if not db.scalar(select(Country.code).limit(1)):
        seed_registration_options(db)


def registration_options(db: Session) -> dict:
    ensure_registration_options(db)
    countries = db.scalars(
        select(Country).where(Country.active).order_by(Country.sort_order, Country.name)
    ).all()
    genders = db.scalars(
        select(GenderOption)
        .where(GenderOption.active)
        .order_by(GenderOption.sort_order, GenderOption.label)
    ).all()
    return {
        "countries": [{"code": item.code, "name": item.name} for item in countries],
        "genders": [{"code": item.code, "label": item.label} for item in genders],
    }


def states_for_country(db: Session, country_code: str) -> list[dict]:
    ensure_registration_options(db)
    states = db.scalars(
        select(StateProvince)
        .where(StateProvince.country_code == country_code.upper(), StateProvince.active)
        .order_by(StateProvince.sort_order, StateProvince.name)
    ).all()
    return [{"code": item.code, "name": item.name} for item in states]


def validate_registration_options(
    db: Session,
    *,
    country_code: str | None,
    state_code: str | None,
    gender_code: str,
) -> None:
    gender = db.get(GenderOption, gender_code)
    if not gender or not gender.active:
        raise ValueError("Invalid gender")
    if not country_code:
        if state_code:
            raise ValueError("State requires a country")
        return
    country = db.get(Country, country_code.upper())
    if not country or not country.active:
        raise ValueError("Invalid country")
    if state_code:
        state = db.get(StateProvince, state_code.upper())
        if not state or not state.active or state.country_code != country.code:
            raise ValueError("State does not belong to the selected country")
