from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QSlider,
    QLabel,
    QHBoxLayout,
)


class ControlsBar(QWidget):
    previous_clicked = Signal()
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    replay_clicked = Signal()
    next_clicked = Signal()
    loop_clicked = Signal()
    seek_changed = Signal(int)
    volume_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.previous_button = QPushButton("Prev")
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.replay_button = QPushButton("Replay")
        self.next_button = QPushButton("Next")
        self.loop_button = QPushButton("Loop: Off")
        self.loop_button.setCheckable(True)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00")

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(140)

        layout = QHBoxLayout(self)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.replay_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.loop_button)
        layout.addWidget(self.position_slider, 1)
        layout.addWidget(self.time_label)
        layout.addWidget(QLabel("Vol"))
        layout.addWidget(self.volume_slider)

        self.previous_button.clicked.connect(self.previous_clicked)
        self.play_button.clicked.connect(self.play_clicked)
        self.pause_button.clicked.connect(self.pause_clicked)
        self.stop_button.clicked.connect(self.stop_clicked)
        self.replay_button.clicked.connect(self.replay_clicked)
        self.next_button.clicked.connect(self.next_clicked)
        self.loop_button.clicked.connect(self.loop_clicked)
        self.position_slider.sliderMoved.connect(self.seek_changed)
        self.volume_slider.valueChanged.connect(self.volume_changed)

    def set_loop_enabled(self, enabled: bool) -> None:
        self.loop_button.blockSignals(True)
        self.loop_button.setChecked(enabled)
        self.loop_button.setText("Loop: On" if enabled else "Loop: Off")
        self.loop_button.blockSignals(False)