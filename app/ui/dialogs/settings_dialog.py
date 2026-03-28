from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from app.constants import DEFAULT_HOTKEYS


class SettingsDialog(QDialog):
    def __init__(self, hotkeys: dict[str, str], parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Settings / Hotkeys")
        self.resize(420, 320)

        self.inputs: dict[str, QLineEdit] = {}

        layout = QVBoxLayout(self)

        info = QLabel(
            "Enter Qt-style key names such as F10, Space, R, Left, Right, Up, Down.\n"
            "Changes apply after clicking Save."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        layout.addLayout(form)

        labels = {
            "toggle_play_pause": "Play / Pause",
            "fullscreen": "Fullscreen",
            "toggle_playlist": "Toggle Playlist",
            "toggle_minimal_view": "Toggle Minimal View",
            "replay": "Replay",
            "seek_forward": "Seek Forward",
            "seek_backward": "Seek Backward",
            "volume_up": "Volume Up",
            "volume_down": "Volume Down",
        }

        for key, label in labels.items():
            edit = QLineEdit(hotkeys.get(key, DEFAULT_HOTKEYS[key]))
            self.inputs[key] = edit
            form.addRow(label, edit)

        buttons = QHBoxLayout()
        layout.addLayout(buttons)

        self.reset_button = QPushButton("Reset Defaults")
        self.cancel_button = QPushButton("Cancel")
        self.save_button = QPushButton("Save")

        buttons.addWidget(self.reset_button)
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        self.reset_button.clicked.connect(self._reset_defaults)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)

    def _reset_defaults(self) -> None:
        for key, edit in self.inputs.items():
            edit.setText(DEFAULT_HOTKEYS[key])

    def get_hotkeys(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, edit in self.inputs.items():
            value = edit.text().strip()
            result[key] = value if value else DEFAULT_HOTKEYS[key]
        return result