from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QMenu,
    QTabWidget,
    QSystemTrayIcon,
)

from app.constants import (
    AUTO_NEXT_POLL_MS,
    DEFAULT_VOLUME,
    RESUME_MINIMUM_MS,
    RESUME_SAVE_INTERVAL_MS,
    SEEK_STEP_MS,
    UPDATE_INTERVAL_MS,
    VOLUME_STEP,
)
from app.player.vlc_player import VlcPlayer
from app.services.recent_files_service import RecentFilesService
from app.services.settings_service import SettingsService
from app.services.stream_resolver import StreamResolver
from app.ui.controls_bar import ControlsBar
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.online_tab import OnlineTab
from app.ui.playlist_dock import PlaylistDock
from app.ui.video_frame import VideoFrame
from app.utils.paths import resource_path
from app.utils.time_format import format_ms


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Bare Bones")
        self.resize(1200, 760)
        self.setAcceptDrops(True)

        self.settings_service = SettingsService()
        self.player = VlcPlayer()
        self.recent_files = RecentFilesService(self.settings_service)
        self.stream_resolver = StreamResolver()
        self.resume_positions = self.settings_service.load_resume_positions()
        self.hotkeys = self.settings_service.load_hotkeys()

        self._resume_pending_ms: int | None = None
        self._resume_attempts = 0
        self._resume_active = False
        self._last_known_time = 0
        self._end_guard_counter = 0
        self._last_auto_advanced_source: str | None = None
        self._allow_real_close = False

        self.shuffle_enabled = False
        self.loop_playlist_enabled = False
        self.minimal_view_enabled = False

        self.video_frame = VideoFrame()
        self.controls = ControlsBar()
        self.controls.set_loop_enabled(self.loop_playlist_enabled)
        self.status_label = QLabel("Ready")

        self.player_tab = QWidget()
        self.player_layout = QVBoxLayout(self.player_tab)
        self.player_layout.addWidget(self.video_frame, 1)
        self.player_layout.addWidget(self.controls)
        self.player_layout.addWidget(self.status_label)

        self.online_tab = OnlineTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.player_tab, "Player")
        self.tabs.addTab(self.online_tab, "Online")
        self.setCentralWidget(self.tabs)

        self.playlist_dock = PlaylistDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.playlist_dock)

        self.recent_menu: QMenu | None = None
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None

        self.toggle_playlist_action: QAction | None = None
        self.shuffle_action: QAction | None = None
        self.loop_action: QAction | None = None
        self.minimal_view_action: QAction | None = None

        self._normal_geometry = None
        self.shortcuts: list[QShortcut] = []

        self._create_menu()
        self._connect_signals()
        self._rebuild_shortcuts()
        self._setup_tray()

        self.player.set_video_widget(self.video_frame)

        saved_volume = self.settings_service.load_volume(DEFAULT_VOLUME)
        self.controls.volume_slider.setValue(saved_volume)
        self.player.set_volume(saved_volume)

        self._restore_settings()
        self._load_saved_playlist()
        self._rebuild_recent_menu()

        self.timer = QTimer(self)
        self.timer.setInterval(UPDATE_INTERVAL_MS)
        self.timer.timeout.connect(self._refresh_ui)
        self.timer.start()

        self.resume_timer = QTimer(self)
        self.resume_timer.setInterval(RESUME_SAVE_INTERVAL_MS)
        self.resume_timer.timeout.connect(self._save_current_resume_position)
        self.resume_timer.start()

        self.auto_next_timer = QTimer(self)
        self.auto_next_timer.setInterval(AUTO_NEXT_POLL_MS)
        self.auto_next_timer.timeout.connect(self._check_auto_next)
        self.auto_next_timer.start()

    def _icon_path(self) -> str:
        png_path = resource_path("assets/icons/app.png")
        if png_path.exists():
            return str(png_path)
        return ""

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = self._icon_path()
        if not icon_path:
            return

        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Bare Bones")

        self.tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_from_tray)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._quit_from_tray)

        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(hide_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._allow_real_close = True
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.close()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self._show_from_tray()

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open File", self)
        open_action.triggered.connect(self.open_file)

        open_many_action = QAction("Open &Files", self)
        open_many_action.triggered.connect(self.open_files)

        self.recent_menu = file_menu.addMenu("Open &Recent")

        clear_recent_action = QAction("Clear Recent Files", self)
        clear_recent_action.triggered.connect(self._clear_recent_files)

        settings_action = QAction("&Settings / Hotkeys", self)
        settings_action.triggered.connect(self._open_settings_dialog)

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self._quit_from_tray)

        file_menu.addAction(open_action)
        file_menu.addAction(open_many_action)
        file_menu.addMenu(self.recent_menu)
        file_menu.addAction(clear_recent_action)
        file_menu.addSeparator()
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        playlist_menu = self.menuBar().addMenu("&Playlist")

        add_to_playlist_action = QAction("&Add Files to Playlist", self)
        add_to_playlist_action.triggered.connect(self.open_files)

        remove_selected_action = QAction("&Remove Selected", self)
        remove_selected_action.triggered.connect(self._remove_selected_playlist_item)

        clear_playlist_action = QAction("&Clear Playlist", self)
        clear_playlist_action.triggered.connect(self._clear_playlist)

        next_action = QAction("&Next", self)
        next_action.triggered.connect(self._next_track)

        previous_action = QAction("&Previous", self)
        previous_action.triggered.connect(self._previous_track)

        self.shuffle_action = QAction("&Shuffle", self)
        self.shuffle_action.setCheckable(True)
        self.shuffle_action.setChecked(False)
        self.shuffle_action.triggered.connect(self._toggle_shuffle)

        self.loop_action = QAction("&Loop Playlist", self)
        self.loop_action.setCheckable(True)
        self.loop_action.setChecked(False)
        self.loop_action.triggered.connect(self._toggle_loop_playlist)

        playlist_menu.addAction(add_to_playlist_action)
        playlist_menu.addAction(remove_selected_action)
        playlist_menu.addAction(clear_playlist_action)
        playlist_menu.addSeparator()
        playlist_menu.addAction(previous_action)
        playlist_menu.addAction(next_action)
        playlist_menu.addAction(self.shuffle_action)
        playlist_menu.addAction(self.loop_action)

        view_menu = self.menuBar().addMenu("&View")

        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)

        self.toggle_playlist_action = QAction("Show &Playlist", self)
        self.toggle_playlist_action.setCheckable(True)
        self.toggle_playlist_action.setChecked(True)
        self.toggle_playlist_action.triggered.connect(self._toggle_playlist_dock)

        self.minimal_view_action = QAction("&Minimal View", self)
        self.minimal_view_action.setCheckable(True)
        self.minimal_view_action.setChecked(False)
        self.minimal_view_action.triggered.connect(self._toggle_minimal_view)

        view_menu.addAction(fullscreen_action)
        view_menu.addAction(self.toggle_playlist_action)
        view_menu.addAction(self.minimal_view_action)

        playback_menu = self.menuBar().addMenu("&Playback")

        replay_action = QAction("&Replay", self)
        replay_action.triggered.connect(self._replay_current)

        playback_menu.addAction(replay_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self) -> None:
        self.controls.previous_clicked.connect(self._previous_track)
        self.controls.play_clicked.connect(self.player.play)
        self.controls.pause_clicked.connect(self.player.pause)
        self.controls.stop_clicked.connect(self.player.stop)
        self.controls.replay_clicked.connect(self._replay_current)
        self.controls.next_clicked.connect(self._next_track)
        self.controls.loop_clicked.connect(self._toggle_loop_playlist)
        self.controls.volume_changed.connect(self._set_volume)
        self.controls.seek_changed.connect(self._seek_from_slider)

        self.playlist_dock.open_requested.connect(self.load_media)
        self.playlist_dock.remove_requested.connect(self._remove_selected_playlist_item)
        self.playlist_dock.clear_requested.connect(self._clear_playlist)

        self.online_tab.play_youtube_requested.connect(self._play_youtube_url)

        self.playlist_dock.visibilityChanged.connect(self._sync_playlist_toggle_state)

    def _bind_shortcut(self, key_text: str, callback) -> None:
        shortcut = QShortcut(QKeySequence(key_text), self)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)

    def _rebuild_shortcuts(self) -> None:
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts.clear()

        self._bind_shortcut(self.hotkeys["toggle_play_pause"], self._toggle_play_pause)
        self._bind_shortcut(self.hotkeys["fullscreen"], self.toggle_fullscreen)
        self._bind_shortcut(self.hotkeys["toggle_playlist"], self._toggle_playlist_dock)
        self._bind_shortcut(self.hotkeys["toggle_minimal_view"], self._toggle_minimal_view)
        self._bind_shortcut(self.hotkeys["replay"], self._replay_current)
        self._bind_shortcut(self.hotkeys["seek_forward"], lambda: self._seek_relative(SEEK_STEP_MS))
        self._bind_shortcut(self.hotkeys["seek_backward"], lambda: self._seek_relative(-SEEK_STEP_MS))
        self._bind_shortcut(self.hotkeys["volume_up"], lambda: self._change_volume(VOLUME_STEP))
        self._bind_shortcut(self.hotkeys["volume_down"], lambda: self._change_volume(-VOLUME_STEP))

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.hotkeys, self)
        if dialog.exec():
            self.hotkeys = dialog.get_hotkeys()
            self.settings_service.save_hotkeys(self.hotkeys)
            self._rebuild_shortcuts()
            self.status_label.setText("Hotkeys updated")

    def _media_filter(self) -> str:
        return "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.flac);;All Files (*)"

    def _toggle_shuffle(self) -> None:
        self.shuffle_enabled = bool(self.shuffle_action.isChecked()) if self.shuffle_action else False
        self.status_label.setText(f"Shuffle {'enabled' if self.shuffle_enabled else 'disabled'}")

    def _toggle_loop_playlist(self) -> None:
        self.loop_playlist_enabled = not self.loop_playlist_enabled

        if self.loop_action is not None:
            self.loop_action.blockSignals(True)
            self.loop_action.setChecked(self.loop_playlist_enabled)
            self.loop_action.blockSignals(False)

        self.controls.set_loop_enabled(self.loop_playlist_enabled)
        self.status_label.setText(
            f"Playlist loop {'enabled' if self.loop_playlist_enabled else 'disabled'}"
        )

    def _toggle_playlist_dock(self) -> None:
        visible = not self.playlist_dock.isVisible()
        self.playlist_dock.setVisible(visible)
        self._sync_playlist_toggle_state(visible)

    def _sync_playlist_toggle_state(self, visible: bool) -> None:
        if self.toggle_playlist_action is not None:
            self.toggle_playlist_action.blockSignals(True)
            self.toggle_playlist_action.setChecked(visible)
            self.toggle_playlist_action.blockSignals(False)

    def _toggle_minimal_view(self) -> None:
        self.minimal_view_enabled = not self.minimal_view_enabled

        if self.minimal_view_action is not None:
            self.minimal_view_action.blockSignals(True)
            self.minimal_view_action.setChecked(self.minimal_view_enabled)
            self.minimal_view_action.blockSignals(False)

        if self.minimal_view_enabled:
            if not self.isFullScreen():
                self._normal_geometry = self.saveGeometry()

            self.menuBar().hide()
            self.status_label.hide()
            self.controls.hide()
            self.tabs.tabBar().hide()
            self.playlist_dock.hide()

            self.resize(640, 390)
            self.status_label.setText("Minimal view enabled")
        else:
            self.menuBar().show()
            self.controls.show()
            self.status_label.show()
            self.tabs.tabBar().show()

            if self.toggle_playlist_action is not None and self.toggle_playlist_action.isChecked():
                self.playlist_dock.show()

            if self._normal_geometry is not None and not self.isFullScreen():
                self.restoreGeometry(self._normal_geometry)

            self.status_label.setText("Minimal view disabled")

    def _replay_current(self) -> None:
        current_source = self.player.current_source
        if not current_source:
            return

        self._save_current_resume_position()

        try:
            if self.player.is_network_source:
                display_name = self.player.current_display_name or "Online Video"
                self.player.stop()
                self.player.load_url(current_source, display_name)
                self.player.play()
            else:
                self.player.stop()
                self.player.load(current_source)
                self.player.play()

            self._resume_pending_ms = None
            self._resume_active = False
            self.status_label.setText("Replay started")
        except Exception as exc:
            QMessageBox.warning(self, "Replay error", f"Could not replay media.\n\n{exc}")

    def _playlist_index_of_current(self) -> int:
        files = self.playlist_dock.files()
        current = self.player.current_source
        if not current or current not in files:
            return -1
        return files.index(current)

    def _next_track(self) -> None:
        files = self.playlist_dock.files()
        if not files:
            return

        current_index = self._playlist_index_of_current()

        if self.shuffle_enabled:
            candidates = [f for f in files if f != self.player.current_source]
            if not candidates:
                return
            self.load_media(random.choice(candidates))
            return

        if current_index == -1:
            self.load_media(files[0])
            return

        next_index = current_index + 1
        if next_index >= len(files):
            if self.loop_playlist_enabled:
                self.load_media(files[0])
            return

        self.load_media(files[next_index])

    def _previous_track(self) -> None:
        files = self.playlist_dock.files()
        if not files:
            return

        current_index = self._playlist_index_of_current()
        if current_index == -1:
            self.load_media(files[0])
            return

        previous_index = current_index - 1
        if previous_index < 0:
            if self.loop_playlist_enabled:
                self.load_media(files[-1])
            else:
                self._replay_current()
            return

        self.load_media(files[previous_index])

    def open_file(self) -> None:
        start_dir = self.settings_service.load_last_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Media", start_dir, self._media_filter())
        if file_path:
            self.load_media(file_path)
            self.playlist_dock.add_file(file_path)
            self._save_playlist()

    def open_files(self) -> None:
        start_dir = self.settings_service.load_last_dir()
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Open Media Files", start_dir, self._media_filter())
        if not file_paths:
            return

        for path in file_paths:
            self.playlist_dock.add_file(path)

        self._save_playlist()
        self.load_media(file_paths[0])

    def load_media(self, file_path: str) -> None:
        if not Path(file_path).exists():
            QMessageBox.warning(self, "Missing file", "That file could not be found.")
            return

        self._save_current_resume_position()

        self.player.load(file_path)
        self.player.play()

        self.recent_files.add(file_path)
        self.settings_service.save_last_dir(file_path)
        self.settings_service.save_last_played(file_path)

        self.playlist_dock.add_file(file_path)
        self.playlist_dock.select_path(file_path)
        self._save_playlist()
        self._rebuild_recent_menu()

        self.tabs.setCurrentIndex(0)
        self.status_label.setText(f"Loaded: {Path(file_path).name}")

        self._prepare_resume_for_source(file_path)
        self._last_auto_advanced_source = None

    def _play_youtube_url(self, url: str) -> None:
        self.online_tab.set_status("Resolving stream...")

        try:
            resolved = self.stream_resolver.resolve_youtube(url)
            self._save_current_resume_position()

            self.player.load_url(resolved.playback_url, resolved.title)
            self.player.play()

            self.tabs.setCurrentIndex(0)
            self.status_label.setText(f"Streaming: {resolved.title}")
            self.online_tab.set_status(
                f"Title: {resolved.title}\n"
                f"Original URL: {resolved.original_url}\n\n"
                f"Resolved and sent to VLC."
            )

            self._clear_resume_for_current_network_source()
            self._last_auto_advanced_source = None

        except Exception as exc:
            self.online_tab.set_status(f"Failed to play URL.\n\n{exc}")
            QMessageBox.warning(self, "Playback error", f"Could not play that URL.\n\n{exc}")

    def _refresh_ui(self) -> None:
        current_ms = self.player.get_time()
        total_ms = self.player.get_length()

        self.controls.position_slider.blockSignals(True)
        self.controls.position_slider.setRange(0, max(total_ms, 0))
        self.controls.position_slider.setValue(min(current_ms, total_ms) if total_ms else 0)
        self.controls.position_slider.blockSignals(False)

        self.controls.time_label.setText(f"{format_ms(current_ms)} / {format_ms(total_ms)}")

        if current_ms > 0:
            self._last_known_time = current_ms

        self._apply_pending_resume_if_ready()

    def _apply_pending_resume_if_ready(self) -> None:
        if not self._resume_active or self._resume_pending_ms is None:
            return

        total_ms = self.player.get_length()
        if total_ms <= 0:
            self._resume_attempts += 1
            if self._resume_attempts > 20:
                self._resume_active = False
            return

        target_ms = min(self._resume_pending_ms, max(total_ms - 1500, 0))
        if target_ms >= RESUME_MINIMUM_MS:
            self.player.set_time(target_ms)
            self.status_label.setText(f"Resumed at {format_ms(target_ms)}")
        self._resume_active = False
        self._resume_pending_ms = None

    def _prepare_resume_for_source(self, source: str) -> None:
        try:
            normalized = str(Path(source).resolve())
        except Exception:
            normalized = source

        saved_ms = int(self.resume_positions.get(normalized, 0))
        if saved_ms >= RESUME_MINIMUM_MS:
            self._resume_pending_ms = saved_ms
            self._resume_attempts = 0
            self._resume_active = True
        else:
            self._resume_pending_ms = None
            self._resume_attempts = 0
            self._resume_active = False

    def _save_current_resume_position(self) -> None:
        current_source = self.player.current_source
        if not current_source or self.player.is_network_source:
            return

        current_ms = self.player.get_time()
        total_ms = self.player.get_length()

        if current_ms < RESUME_MINIMUM_MS:
            return

        if total_ms > 0 and current_ms >= total_ms - 2000:
            self.resume_positions.pop(current_source, None)
            self.settings_service.save_resume_positions(self.resume_positions)
            return

        self.resume_positions[current_source] = int(current_ms)
        self.settings_service.save_resume_positions(self.resume_positions)

    def _clear_resume_for_current_network_source(self) -> None:
        self._resume_pending_ms = None
        self._resume_attempts = 0
        self._resume_active = False

    def _check_auto_next(self) -> None:
        if self.player.is_network_source:
            return

        current_source = self.player.current_source
        if not current_source:
            return

        total_ms = self.player.get_length()
        current_ms = self.player.get_time()
        is_playing = self.player.is_playing()

        if total_ms > 0 and current_ms >= max(total_ms - 1200, 0) and not is_playing:
            self._end_guard_counter += 1
        else:
            self._end_guard_counter = 0

        if self._end_guard_counter < 2:
            return

        if self._last_auto_advanced_source == current_source:
            return

        self.resume_positions.pop(current_source, None)
        self.settings_service.save_resume_positions(self.resume_positions)

        self._last_auto_advanced_source = current_source
        self._end_guard_counter = 0
        self._next_track()

    def _seek_from_slider(self, value: int) -> None:
        maximum = self.controls.position_slider.maximum()
        self.player.set_position(value, maximum)

    def _seek_relative(self, delta_ms: int) -> None:
        current = self.player.get_time()
        total = self.player.get_length()

        if total <= 0:
            return

        new_time = max(0, min(current + delta_ms, total))
        self.controls.position_slider.setValue(new_time)
        self.player.set_position(new_time, total)

    def _set_volume(self, volume: int) -> None:
        self.player.set_volume(volume)
        self.settings_service.save_volume(volume)

    def _change_volume(self, delta: int) -> None:
        value = max(0, min(self.controls.volume_slider.value() + delta, 100))
        self.controls.volume_slider.setValue(value)

    def _toggle_play_pause(self) -> None:
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def toggle_fullscreen(self) -> None:
        if not self.isActiveWindow():
            return

        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "My Video Player\n\nPlaylist loop added.",
        )

    def _remove_selected_playlist_item(self) -> None:
        self.playlist_dock.remove_selected()
        self._save_playlist()

    def _clear_playlist(self) -> None:
        self.playlist_dock.clear_files()
        self._save_playlist()

    def _save_playlist(self) -> None:
        self.settings_service.save_playlist(self.playlist_dock.files())

    def _load_saved_playlist(self) -> None:
        files = [p for p in self.settings_service.load_playlist() if Path(p).exists()]
        self.playlist_dock.add_files(files)

        last_played = self.settings_service.load_last_played()
        if last_played and Path(last_played).exists():
            self.playlist_dock.select_path(last_played)

    def _clear_recent_files(self) -> None:
        self.recent_files.clear()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        if self.recent_menu is None:
            return

        self.recent_files.remove_missing()
        self.recent_menu.clear()

        files = self.recent_files.list()
        if not files:
            empty_action = QAction("(No recent files)", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return

        for path in files:
            action = QAction(Path(path).name, self)
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, p=path: self.load_media(p))
            self.recent_menu.addAction(action)

    def _restore_settings(self) -> None:
        geometry = self.settings_service.load_geometry()
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings_service.load_window_state()
        if state:
            self.restoreState(state)

    def closeEvent(self, event) -> None:
        self._save_current_resume_position()
        self.settings_service.save_geometry(self.saveGeometry())
        self.settings_service.save_window_state(self.saveState())
        self.settings_service.save_volume(self.controls.volume_slider.value())
        self._save_playlist()

        if not self._allow_real_close and self.tray_icon is not None and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            return

        if self.tray_icon is not None:
            self.tray_icon.hide()

        super().closeEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return

        added = []
        for url in urls:
            local_path = url.toLocalFile()
            if local_path and Path(local_path).exists():
                self.playlist_dock.add_file(local_path)
                added.append(local_path)

        if added:
            self._save_playlist()
            self.load_media(added[0])