from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import obsws_python as obs


@dataclass
class OBSConfig:
    host: str = "127.0.0.1"
    port: int = 4455
    password: str = ""
    scene_name: str = "YouTubeRequests"
    now_playing_source: str = "NowPlayingText"
    requester_source: str = "RequesterText"
    player_window_source: str = "PlayerWindow"


class OBSController:
    def __init__(self, config: OBSConfig) -> None:
        self.config = config
        self.client: Optional[obs.ReqClient] = None
        self.connected = False

    def connect(self) -> bool:
        try:
            self.client = obs.ReqClient(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                timeout=3,
            )
            self.connected = True
            return True
        except Exception as exc:
            print(f"[OBS] Connect failed: {exc}")
            self.client = None
            self.connected = False
            return False

    def ensure_connected(self) -> bool:
        if self.connected and self.client is not None:
            return True
        return self.connect()

    def disconnect(self) -> None:
        self.client = None
        self.connected = False

    def switch_scene(self, scene_name: Optional[str] = None) -> bool:
        if not self.ensure_connected():
            return False

        target_scene = scene_name or self.config.scene_name

        try:
            self.client.set_current_program_scene(target_scene)
            return True
        except Exception as exc:
            print(f"[OBS] switch_scene failed: {exc}")
            self.connected = False
            return False

    def set_text(self, input_name: str, text: str) -> bool:
        if not self.ensure_connected():
            return False

        try:
            self.client.set_input_settings(
                name=input_name,
                settings={"text": text},
                overlay=True,
            )
            return True
        except Exception as exc:
            print(f"[OBS] set_text failed for {input_name}: {exc}")
            self.connected = False
            return False

    def set_source_visibility(
        self,
        scene_name: str,
        source_name: str,
        visible: bool,
    ) -> bool:
        if not self.ensure_connected():
            return False

        try:
            items = self.client.get_scene_item_list(scene_name).scene_items
            for item in items:
                if item["sourceName"] == source_name:
                    self.client.set_scene_item_enabled(
                        scene_name=scene_name,
                        item_id=item["sceneItemId"],
                        enabled=visible,
                    )
                    return True

            print(f"[OBS] Source not found in scene '{scene_name}': {source_name}")
            return False

        except Exception as exc:
            print(f"[OBS] set_source_visibility failed: {exc}")
            self.connected = False
            return False

    def show_request_scene(self, title: str, requested_by: str = "") -> None:
        self.switch_scene(self.config.scene_name)
        self.set_text(self.config.now_playing_source, f"Now Playing: {title}")

        if self.config.requester_source:
            requester_text = f"Requested by: {requested_by}" if requested_by else ""
            self.set_text(self.config.requester_source, requester_text)

        if self.config.player_window_source:
            self.set_source_visibility(
                self.config.scene_name,
                self.config.player_window_source,
                True,
            )

    def clear_request_overlay(self) -> None:
        if self.config.now_playing_source:
            self.set_text(self.config.now_playing_source, "")
        if self.config.requester_source:
            self.set_text(self.config.requester_source, "")