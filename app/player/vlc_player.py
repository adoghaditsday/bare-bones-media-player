from __future__ import annotations

import sys
from pathlib import Path

import vlc
from PySide6.QtWidgets import QWidget


class VlcPlayer:
    def __init__(self) -> None:
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()
        self._current_source: str | None = None
        self._current_display_name: str | None = None
        self._is_network_source = False

    def set_video_widget(self, widget: QWidget) -> None:
        win_id = int(widget.winId())

        if sys.platform.startswith("linux"):
            self.media_player.set_xwindow(win_id)
        elif sys.platform == "win32":
            self.media_player.set_hwnd(win_id)
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(win_id)

    def load(self, file_path: str) -> None:
        resolved = str(Path(file_path).resolve())
        media = self.instance.media_new(resolved)
        self.media_player.set_media(media)
        self._current_source = resolved
        self._current_display_name = Path(resolved).name
        self._is_network_source = False

    def load_url(self, url: str, display_name: str = "Online Video") -> None:
        media = self.instance.media_new(url)
        self.media_player.set_media(media)
        self._current_source = url
        self._current_display_name = display_name
        self._is_network_source = True

    def play(self) -> None:
        self.media_player.play()

    def pause(self) -> None:
        self.media_player.pause()

    def stop(self) -> None:
        self.media_player.stop()

    def set_position(self, value: int, maximum: int) -> None:
        if maximum <= 0:
            return
        self.media_player.set_position(float(value / maximum))

    def set_time(self, ms: int) -> None:
        if ms >= 0:
            self.media_player.set_time(int(ms))

    def set_volume(self, volume: int) -> None:
        self.media_player.audio_set_volume(max(0, min(volume, 100)))

    def get_time(self) -> int:
        return max(self.media_player.get_time(), 0)

    def get_length(self) -> int:
        return max(self.media_player.get_length(), 0)

    def is_playing(self) -> bool:
        return bool(self.media_player.is_playing())

    @property
    def current_source(self) -> str | None:
        return self._current_source

    @property
    def current_display_name(self) -> str | None:
        return self._current_display_name

    @property
    def is_network_source(self) -> bool:
        return self._is_network_source