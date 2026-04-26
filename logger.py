"""
Logging utilities.

Provides a configured Python logger (file + console) and a structured
session logger that appends JSONL entries to a daily log file.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List


_LOG_DIR = Path("logs")


def get_logger(name: str) -> logging.Logger:
    """Return a logger with console (INFO) and file (DEBUG) handlers."""
    lg = logging.getLogger(name)
    if lg.handlers:
        return lg

    lg.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    lg.addHandler(console)

    _LOG_DIR.mkdir(exist_ok=True)
    log_file = _LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    lg.addHandler(fh)

    return lg


class GameSessionLogger:
    """Appends structured JSONL entries to a daily session log file."""

    def __init__(self) -> None:
        _LOG_DIR.mkdir(exist_ok=True)
        self._path = _LOG_DIR / f"sessions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self._log = get_logger("session")

    def _write(self, event: str, data: dict) -> None:
        entry = {"ts": datetime.now().isoformat(), "event": event, **data}
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        self._log.debug("event=%s data=%s", event, data)

    def log_game_start(self, difficulty: str, range_low: int, range_high: int) -> None:
        self._write("game_start", {
            "difficulty": difficulty,
            "range_low": range_low,
            "range_high": range_high,
        })

    def log_guess(self, guess: int, outcome: str, attempts_used: int) -> None:
        self._write("guess", {
            "guess": guess,
            "outcome": outcome,
            "attempts_used": attempts_used,
        })

    def log_ai_hint(
        self,
        confidence: float,
        quality: float,
        retrieved_docs: List[str],
        success: bool,
    ) -> None:
        self._write("ai_hint", {
            "confidence": round(confidence, 3),
            "quality": round(quality, 3),
            "retrieved_docs": retrieved_docs,
            "success": success,
        })

    def log_game_end(self, won: bool, attempts_used: int, score: int) -> None:
        self._write("game_end", {
            "won": won,
            "attempts_used": attempts_used,
            "final_score": score,
        })
