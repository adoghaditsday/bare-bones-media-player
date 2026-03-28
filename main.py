import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.utils.paths import resource_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Bare Bones")
    app.setOrganizationName("GSG3")

    icon_path = resource_path("assets/icons/app.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())