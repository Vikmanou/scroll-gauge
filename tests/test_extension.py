from scrollgauge.extension import parse_factors


def test_parse_factors():
    assert parse_factors("{'firefox': 0.4, 'code': 1.0}") == {"firefox": 0.4, "code": 1.0}


def test_parse_empty_factors():
    assert parse_factors("@a{sd} {}") == {}

