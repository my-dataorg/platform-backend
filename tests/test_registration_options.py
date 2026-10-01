from app.services.registration_options import (
    registration_options,
    seed_registration_options,
    states_for_country,
    validate_registration_options,
)


def test_registration_options_are_seeded(db):
    seed_registration_options(db)

    options = registration_options(db)

    assert len(options["countries"]) >= 200
    assert {item["code"] for item in options["genders"]} >= {
        "female",
        "male",
        "prefer_not_to_say",
    }
    assert any(item["code"] == "US-CA" for item in states_for_country(db, "US"))


def test_state_must_belong_to_country(db):
    seed_registration_options(db)

    validate_registration_options(
        db,
        country_code="US",
        state_code="US-CA",
        gender_code="female",
    )

    try:
        validate_registration_options(
            db,
            country_code="IN",
            state_code="US-CA",
            gender_code="female",
        )
    except ValueError as error:
        assert str(error) == "State does not belong to the selected country"
    else:
        raise AssertionError("Expected a mismatched state to be rejected")
