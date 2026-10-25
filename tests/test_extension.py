from scrollgauge.extension import parse_factors, starter_app_factors


def test_starter_apps_are_files_and_first_installed_terminal():
    installed = {"org.gnome.Nautilus", "org.gnome.Console", "org.gnome.Terminal", "org.gnome.TextEditor"}
    assert starter_app_factors(installed, 0.3) == {"org.gnome.Nautilus": 0.3, "org.gnome.Console": 0.3}


def test_starter_apps_skip_missing_apps():
    assert starter_app_factors({"org.gnome.Ptyxis"}, 0.5) == {"org.gnome.Ptyxis": 0.5}


def test_parse_factors():
    assert parse_factors("{'firefox': 0.4, 'code': 1.0}") == {"firefox": 0.4, "code": 1.0}


def test_parse_empty_factors():
    assert parse_factors("@a{sd} {}") == {}

