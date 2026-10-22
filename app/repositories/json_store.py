"""JSON file repository with locking, atomic writes and corruption recovery.

Design refs: DATA-01 (lock + atomic write), ERR-30 (recovery), ERR-31 (write failure).
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from app.errors import AppError, ErrorCode
from app.repositories.models import DataFile

logger = logging.getLogger("budget_tracker")


@dataclass(frozen=True)
class RecoveryInfo:
    """[ERR-30] Set when a corrupted file was moved aside."""

    backup_file: str


class Transaction:
    """Mutable view of the data inside a locked section. Call discard() to skip saving."""

    def __init__(self, data: DataFile) -> None:
        self.data = data
        self.save = True

    def discard(self) -> None:
        self.save = False


class JsonStore:
    """Single JSON file store. One instance per app process (MOD-20)."""

    def __init__(self, path: Path, now_fn: Callable[[], datetime] | None = None) -> None:
        self.path = path
        self._tmp_path = path.with_name(path.name + ".tmp")
        self._lock = threading.Lock()
        self._now_fn = now_fn or datetime.now
        self.recovery: RecoveryInfo | None = None

    # ---- public API -------------------------------------------------

    def initialize(self) -> None:
        """[ERR-30] Called at startup: drop a leftover .tmp, then load or recover."""
        with self._lock:
            if self._tmp_path.exists():
                logger.warning("Removing leftover temp file %s", self._tmp_path.name)
                self._tmp_path.unlink()
            self._load_or_recover()
        logger.info("Data file: %s", self.path)

    def read(self) -> DataFile:
        """Fresh copy of the data (callers may not write it back)."""
        with self._lock:
            return self._load_or_recover()

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """[DATA-01] Load, modify and save under one lock to prevent lost updates.

        Nothing is saved when the block raises or calls Transaction.discard().
        """
        with self._lock:
            tx = Transaction(self._load_or_recover())
            yield tx
            if tx.save:
                self._write(tx.data)

    # ---- internals --------------------------------------------------

    def _load_or_recover(self) -> DataFile:
        if not self.path.exists():
            data = DataFile.initial()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write(data)
            return data
        try:
            return DataFile.model_validate_json(self.path.read_bytes())
        except ValidationError as exc:
            backup = self._move_aside()
            logger.warning(
                "Data file is corrupted (%d errors); moved to %s", exc.error_count(), backup.name
            )
            data = DataFile.initial()
            self._write(data)
            self.recovery = RecoveryInfo(backup_file=backup.name)
            return data

    def _move_aside(self) -> Path:
        """[ERR-30] Rename to budget.json.corrupt-YYYYMMDDHHMMSS[-n]. Failure is fatal."""
        stamp = self._now_fn().strftime("%Y%m%d%H%M%S")
        candidate = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        suffix = 1
        while candidate.exists():
            candidate = self.path.with_name(f"{self.path.name}.corrupt-{stamp}-{suffix}")
            suffix += 1
        try:
            os.replace(self.path, candidate)
        except OSError:
            logger.critical("Cannot move corrupted data file %s aside", self.path)
            raise
        return candidate

    def _write(self, data: DataFile) -> None:
        """[DATA-01][ERR-31] Write a temp file, fsync, then os.replace (atomic)."""
        payload = data.model_dump_json(indent=2)
        try:
            with open(self._tmp_path, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(self._tmp_path, self.path)
        except OSError as exc:
            self._tmp_path.unlink(missing_ok=True)
            raise AppError(ErrorCode.STORAGE_WRITE_FAILED, 500, f"Failed to save data: {exc}") from exc
