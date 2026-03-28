from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
)


class OnlineTab(QWidget):
    play_youtube_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.info_label = QLabel("Paste a YouTube link and click Play.")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.play_button = QPushButton("Play YouTube")
        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setMinimumHeight(120)

        top_row = QHBoxLayout()
        top_row.addWidget(self.url_input, 1)
        top_row.addWidget(self.play_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addLayout(top_row)
        layout.addWidget(self.status_box)

        self.play_button.clicked.connect(self._emit_request)
        self.url_input.returnPressed.connect(self._emit_request)

    def _emit_request(self) -> None:
        text = self.url_input.text().strip()
        if text:
            self.play_youtube_requested.emit(text)

    def set_status(self, text: str) -> None:
        self.status_box.setPlainText(text)