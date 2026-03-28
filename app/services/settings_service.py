from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from app.config import APP_NAME, ORG_NAME
from app.constants import (
    DEFAULT_HOTKEYS,
    SETTINGS_GEOMETRY_KEY,
    SETTINGS_HOTKEYS_KEY,
    SETTINGS_LAST_DIR_KEY,
    SETTINGS_LAST_PLAYED_KEY,
    SETTINGS_PLAYLIST_KEY,
    SETTINGS_RECENT_FILES_KEY,
    SETTINGS_RESUME_POSITIONS_KEY,
    SETTINGS_STATE_KEY,
    SETTINGS_VOLUME_KEY,
)


class SettingsService:
    def __init__(self) -> None:
        self.settings = QSettings(ORG_NAME, APP_NAME)

    def set_value(self, key: str, value: Any) -> None:
        self.settings.setValue(key, value)

    def get_value(self, key: str, default: Any = None) -> Any:
        return self.settings.value(key, default)

    def save_geometry(self, geometry) -> None:
        self.settings.setValue(SETTINGS_GEOMETRY_KEY, geometry)

    def load_geometry(self):
        return self.settings.value(SETTINGS_GEOMETRY_KEY)

    def save_window_state(self, state) -> None:
        self.settings.setValue(SETTINGS_STATE_KEY, state)

    def load_window_state(self):
        return self.settings.value(SETTINGS_STATE_KEY)

    def save_volume(self, volume: int) -> None:
        self.settings.setValue(SETTINGS_VOLUME_KEY, int(volume))

    def load_volume(self, default: int = 80) -> int:
        value = self.settings.value(SETTINGS_VOLUME_KEY, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def save_last_dir(self, path: str) -> None:
        from pathlib import Path
        p = Path(path)
        directory = str(p.parent if p.is_file() else p)
        self.settings.setValue(SETTINGS_LAST_DIR_KEY, directory)

    def load_last_dir(self) -> str:
        return str(self.settings.value(SETTINGS_LAST_DIR_KEY, ""))

    def save_recent_files(self, files: list[str]) -> None:
        self.settings.setValue(SETTINGS_RECENT_FILES_KEY, files)

    def load_recent_files(self) -> list[str]:
        value = self.settings.value(SETTINGS_RECENT_FILES_KEY, [])
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def save_playlist(self, files: list[str]) -> None:
        self.settings.setValue(SETTINGS_PLAYLIST_KEY, files)

    def load_playlist(self) -> list[str]:
        value = self.settings.value(SETTINGS_PLAYLIST_KEY, [])
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def save_last_played(self, path: str) -> None:
        self.settings.setValue(SETTINGS_LAST_PLAYED_KEY, path)

    def load_last_played(self) -> str:
        return str(self.settings.value(SETTINGS_LAST_PLAYED_KEY, ""))

    def load_resume_positions(self) -> dict[str, int]:
        value = self.settings.value(SETTINGS_RESUME_POSITIONS_KEY, {})
        if value is None:
            return {}
        if isinstance(value, dict):
            output: dict[str, int] = {}
            for key, item in value.items():
                try:
                    output[str(key)] = int(item)
                except (TypeError, ValueError):
                    continue
            return output
        return {}

    def save_resume_positions(self, positions: dict[str, int]) -> None:
        serializable = {str(k): int(v) for k, v in positions.items()}
        self.settings.setValue(SETTINGS_RESUME_POSITIONS_KEY, serializable)

    def load_hotkeys(self) -> dict[str, str]:
        value = self.settings.value(SETTINGS_HOTKEYS_KEY, {})
        if not isinstance(value, dict):
            return dict(DEFAULT_HOTKEYS)

        merged = dict(DEFAULT_HOTKEYS)
        for key, default_value in DEFAULT_HOTKEYS.items():
            loaded_value = value.get(key, default_value)
            if isinstance(loaded_value, str) and loaded_value.strip():
                merged[key] = loaded_value.strip()
        return merged

    def save_hotkeys(self, hotkeys: dict[str, str]) -> None:
        cleaned = {}
        for key, default_value in DEFAULT_HOTKEYS.items():
            value = hotkeys.get(key, default_value)
            cleaned[key] = value.strip() if isinstance(value, str) and value.strip() else default_value
        self.settings.setValue(SETTINGS_HOTKEYS_KEY, cleaned)

    def reset_hotkeys(self) -> dict[str, str]:
        self.save_hotkeys(DEFAULT_HOTKEYS)
        return dict(DEFAULT_HOTKEYS)