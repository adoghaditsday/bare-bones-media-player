from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
)


class PlaylistDock(QDockWidget):
    open_requested = Signal(str)
    remove_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Playlist", parent)

        self.setObjectName("PlaylistDock")

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self._emit_open_selected)

        remove_btn = QPushButton("Remove")
        clear_btn = QPushButton("Clear")

        remove_btn.clicked.connect(self.remove_requested)
        clear_btn.clicked.connect(self.clear_requested)

        buttons = QHBoxLayout()
        buttons.addWidget(remove_btn)
        buttons.addWidget(clear_btn)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons)

        self.setWidget(root)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

    def add_file(self, path: str) -> None:
        path = str(Path(path).resolve())
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                return

        item = QListWidgetItem(Path(path).name)
        item.setToolTip(path)
        item.setData(Qt.UserRole, path)
        self.list_widget.addItem(item)

    def add_files(self, paths: list[str]) -> None:
        for path in paths:
            if Path(path).exists():
                self.add_file(path)

    def files(self) -> list[str]:
        output: list[str] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            output.append(item.data(Qt.UserRole))
        return output

    def clear_files(self) -> None:
        self.list_widget.clear()

    def remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def current_file(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def select_path(self, path: str) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                self.list_widget.setCurrentRow(i)
                return

    def _emit_open_selected(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.open_requested.emit(path)