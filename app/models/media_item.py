from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaItem:
    path: Path

    @property
    def title(self) -> str:
        return self.path.name