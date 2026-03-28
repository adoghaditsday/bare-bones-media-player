from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parents[2] / relative_path