from PySide6.QtWidgets import QFrame


class VideoFrame(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("videoFrame")
        self.setStyleSheet(
            """
            QFrame#videoFrame {
                background-color: black;
                border: 1px solid #222;
            }
            """
        )