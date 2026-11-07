"""Default configuration (decision S6, 7 Nov 2026). Changing a value here changes what the live reviewer does,
so every value names the evidence it came from."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SEARCH = False                                   # S6: code search off by default (rung 3/4: noise > gain)
CALIBRATION = ROOT / "eval/results/rung4n.json"  # the calibration the threshold belongs to


def threshold() -> float | None:
    """The posting threshold from the calibration file; None (everything to the queue) if it is missing."""
    try:
        return json.loads(CALIBRATION.read_text(encoding="utf-8"))["threshold_for_demo"]
    except (OSError, KeyError, ValueError):
        return None
