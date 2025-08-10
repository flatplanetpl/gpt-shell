import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    # Ustaw WORKDIR na katalog testowy i przeładuj moduł, by podchwycił env
    monkeypatch.setenv("WORKDIR", str(tmp_path))
    # Upewnij się, że ścieżka projektu jest na PYTHONPATH
    proj_root = Path(__file__).resolve().parents[1]
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))
    # Przeładuj moduł, aby wczytał nowe zmienne środowiskowe
    m = importlib.reload(importlib.import_module("cli_assistant_fs"))
    return m
