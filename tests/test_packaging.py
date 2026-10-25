import re
from pathlib import Path

import pytest

import scrollgauge

SPEC = Path(__file__).resolve().parent.parent / "packaging/scrollgauge.spec"


@pytest.mark.skipif(not SPEC.exists(), reason="packaging/ is not part of the PyPI source archive")
def test_rpm_spec_version_matches_package():
    version = re.search(r"^Version:\s*(\S+)$", SPEC.read_text(), re.M).group(1)
    assert version == scrollgauge.__version__
