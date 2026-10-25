from scrollgauge.calibrate import MAX_FACTOR, MIN_FACTOR, balanced_factors


def test_reference_keeps_its_factor():
    assert balanced_factors({"ref": 120}, "ref", 0.25) == {"ref": 0.25}


def test_faster_app_gets_lower_factor():
    factors = balanced_factors({"ref": 100, "fast": 200, "slow": 50}, "ref", 0.4)
    assert factors == {"ref": 0.4, "fast": 0.2, "slow": 0.8}


def test_factors_are_clamped():
    factors = balanced_factors({"ref": 100, "huge": 100_000, "tiny": 1}, "ref", 1.0)
    assert factors["huge"] == MIN_FACTOR
    assert factors["tiny"] == MAX_FACTOR
