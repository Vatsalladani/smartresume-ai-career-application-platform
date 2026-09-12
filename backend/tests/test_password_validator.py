import pytest

from app.validators.password import validate_password_strength


def test_password_strength_accepts_reasonable_password() -> None:
    assert validate_password_strength("StrongPass1!") == "StrongPass1!"


@pytest.mark.parametrize("password", ["short1!", "lowercase1!", "NOLOWERCASE1!", "NoNumber!", "NoSymbol1"])
def test_password_strength_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValueError):
        validate_password_strength(password)
