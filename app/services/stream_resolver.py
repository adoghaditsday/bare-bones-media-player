from __future__ import annotations

from dataclasses import dataclass

import yt_dlp


@dataclass
class ResolvedStream:
    original_url: str
    playback_url: str
    title: str
    webpage_url: str


class StreamResolver:
    def resolve_youtube(self, url: str) -> ResolvedStream:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": False,
            "format": "best[ext=mp4]/best",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        playback_url = info.get("url")
        if not playback_url:
            raise RuntimeError("Could not resolve a playable stream URL.")

        title = info.get("title") or "Online Video"
        webpage_url = info.get("webpage_url") or url

        return ResolvedStream(
            original_url=url,
            playback_url=playback_url,
            title=title,
            webpage_url=webpage_url,
        )