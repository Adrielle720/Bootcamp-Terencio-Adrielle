FEE_BANDS = [
    (1000, 50),
    (10000, 200),
    (30000, 500),
    (100000, 900),
    (500000, 1200),
]
EXTRA_FEE_PER_ADULT_OVER_TWO = 50
FREE_ADULTS = 2


def calcular_tarifa(amount_cents: int, adult_count: int) -> int:
    base = [fee for minimum, fee in FEE_BANDS if amount_cents >= minimum][-1]
    extra_adults = max(0, adult_count - FREE_ADULTS)

    return base + extra_adults * EXTRA_FEE_PER_ADULT_OVER_TWO
