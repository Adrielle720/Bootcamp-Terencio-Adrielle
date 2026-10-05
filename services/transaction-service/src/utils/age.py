from datetime import date

ADULT_AGE = 18


def age_in_years(birthdate: date) -> int:
    today = date.today()
    had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
    return today.year - birthdate.year - (0 if had_birthday else 1)


def is_adult(birthdate: date) -> bool:
    return age_in_years(birthdate) >= ADULT_AGE
