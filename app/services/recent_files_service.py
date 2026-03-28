from __future__ import annotations

from pathlib import Path

from app.config import MAX_RECENT_FILES
from app.services.settings_service import SettingsService


class RecentFilesService:
    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service
        self._items: list[str] = []
        self._load()

    def _normalize(self, path: str) -> str:
        return str(Path(path).resolve())

    def _load(self) -> None:
        items = self.settings_service.load_recent_files()
        self._items = [self._normalize(p) for p in items if Path(p).exists()]

    def _save(self) -> None:
        self.settings_service.save_recent_files(self._items)

    def add(self, path: str) -> None:
        normalized = self._normalize(path)
        if normalized in self._items:
            self._items.remove(normalized)
        self._items.insert(0, normalized)
        self._items = self._items[:MAX_RECENT_FILES]
        self._save()

    def remove_missing(self) -> None:
        self._items = [p for p in self._items if Path(p).exists()]
        self._save()

    def list(self) -> list[str]:
        return list(self._items)

    def clear(self) -> None:
        self._items = []
        self._save()