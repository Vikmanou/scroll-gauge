import subprocess

import pytest

from scrollgauge import wsf


def fake_run(stdout: str = "", returncode: int = 0, calls: list | None = None):
    def run(cmd, **_kwargs):
        if calls is not None:
            calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="boom" if returncode else "")

    return run


@pytest.fixture
def installed(monkeypatch):
    monkeypatch.setattr(wsf.shutil, "which", lambda _: "/usr/bin/wsf")


def test_read_parses_json(installed, monkeypatch):
    out = '{"scroll_vertical_factor":0.2500,"scroll_horizontal_factor":0.5000,"pinch_zoom_factor":1.0}'
    monkeypatch.setattr(wsf.subprocess, "run", fake_run(out))
    assert wsf.read() == wsf.Factors(vertical=0.25, horizontal=0.5)


def test_write_passes_both_axes(installed, monkeypatch):
    calls = []
    monkeypatch.setattr(wsf.subprocess, "run", fake_run(calls=calls))
    wsf.write(wsf.Factors(0.2, 0.3))
    assert calls == [["/usr/bin/wsf", "set", "--scroll-vertical", "0.2000", "--scroll-horizontal", "0.3000"]]


def test_missing_wsf_raises(monkeypatch):
    monkeypatch.setattr(wsf.shutil, "which", lambda _: None)
    with pytest.raises(wsf.WsfError, match="not found"):
        wsf.read()


def test_failed_command_raises(installed, monkeypatch):
    monkeypatch.setattr(wsf.subprocess, "run", fake_run(returncode=1))
    with pytest.raises(wsf.WsfError, match="boom"):
        wsf.read()
