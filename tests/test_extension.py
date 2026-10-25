from scrollgauge.extension import parse_factors, visible_app_name


def test_parse_factors():
    assert parse_factors("{'firefox': 0.4, 'code': 1.0}") == {"firefox": 0.4, "code": 1.0}


def test_parse_empty_factors():
    assert parse_factors("@a{sd} {}") == {}


def write_desktop(tmp_path, body):
    path = tmp_path / "app.desktop"
    path.write_text("[Desktop Entry]\n" + body)
    return path


def test_visible_app_name(tmp_path):
    assert visible_app_name(write_desktop(tmp_path, "Type=Application\nName=Files\n")) == "Files"


def test_hidden_apps_are_skipped(tmp_path):
    assert visible_app_name(write_desktop(tmp_path, "Type=Application\nName=X\nNoDisplay=true\n")) is None


def test_non_applications_are_skipped(tmp_path):
    assert visible_app_name(write_desktop(tmp_path, "Type=Link\nName=X\n")) is None
