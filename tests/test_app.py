import pytest

pytest.importorskip("gi")
app = pytest.importorskip("scrollgauge.app", exc_type=ImportError)


def test_demo_text_has_numbered_lines():
    lines = app.demo_text().splitlines()
    assert len(lines) == app.DEMO_LINES
    assert lines[0].split()[:2] == ["1", "Lorem"]
    assert lines[-1].lstrip().startswith(str(app.DEMO_LINES))


def test_demo_lines_fit_the_demo_box():
    assert max(len(line) for line in app.demo_text().splitlines()) <= 50
