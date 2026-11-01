import os
import sys
import time as _zeit
from pathlib import Path

import pytest

# Feste Zeitzone, damit die Tests überall dasselbe Ergebnis liefern -
# und damit die Umrechnung aus UTC tatsächlich geprüft wird.
os.environ["TZ"] = "Europe/Berlin"
if hasattr(_zeit, "tzset"):
    _zeit.tzset()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture
def heim(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / ".local" / "state"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path
