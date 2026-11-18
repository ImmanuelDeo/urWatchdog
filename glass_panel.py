"""Liquid Glass-inspired native Qt panel with Windows DWM Acrylic."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / '.ui-deps'))
import psutil
from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtGui import QColor, QIcon, QPainter, QLinearGradient, QPen
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit, QCheckBox, QPlainTextEdit, QSystemTrayIcon, QMenu
from PySide6.QtNetwork import QLocalServer, QLocalSocket
import time
from runtime_config import atomic_json
CONFIG_PATH = BASE_DIR / 'config.json'
LOG_PATH = BASE_DIR / 'daemon.log'
DAEMON_PY = BASE_DIR / 'daemon.py'
PYTHON_EXE = r'C:\Users\deoim\miniconda3\envs\yolo11-ablation\python.exe'
PYTHONW_EXE = str(Path(PYTHON_EXE).with_name('pythonw.exe'))
STARTUP_PATH = Path(os.environ.get('APPDATA', '')) / 'Microsoft/Windows/Start Menu/Programs/Startup/urWatchdog.lnk'


def get_daemon_process():
    target = os.path.normcase(os.path.realpath(DAEMON_PY))
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == os.getpid() or not (proc.info['name'] or '').lower().startswith('python'):
                continue
            for arg in (proc.info['cmdline'] or [])[1:]:
                if not arg.lower().endswith('.py'):
                    continue
                candidate = Path(arg)
                if not candidate.is_absolute():
                    candidate = Path(proc.cwd()) / candidate
                if os.path.normcase(os.path.realpath(candidate)) == target:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    return None


def load_config():
    if CONFIG_PATH.exists():
        result = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        if not isinstance(result, dict):
            raise ValueError('Konfigurasi harus berupa objek JSON.')
        return result
    return {}


def validate_settings(idle, countdown):
    try:
        idle, countdown = int(idle), int(countdown)
    except ValueError:
        raise ValueError('Gunakan angka bulat untuk kedua batas waktu.') from None
    if not 1 <= idle <= 1440 or not 1 <= countdown <= 3600:
        raise ValueError('Idle: 1–1440 menit. Hitung mundur: 1–3600 detik.')
    return idle * 60, countdown


class Backend:
    def status(self):
        proc = get_daemon_process()
        return proc.pid if proc else None

    def start(self):
        if not get_daemon_process():
            subprocess.Popen([PYTHONW_EXE, str(DAEMON_PY)], cwd=str(BASE_DIR))

    def stop(self):
        proc = get_daemon_process()
        if proc:
            (BASE_DIR/'daemon.stop').write_text('stop', encoding='utf-8')

    def startup(self, enabled):
        cmd = [PYTHON_EXE, str(BASE_DIR / 'manage_startup.py')]
        if not enabled:
            cmd.append('uninstall')
        subprocess.run(cmd, check=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        if STARTUP_PATH.exists() != enabled:
            raise RuntimeError('Status shortcut startup tidak sesuai. Periksa izin Windows.')

    def save(self, values):
        cfg = load_config()
        cfg.update(values)
        temp = CONFIG_PATH.with_suffix('.json.ui-tmp')
        try:
            temp.write_text(json.dumps(cfg, indent=2) + '\n', encoding='utf-8')
            os.replace(temp, CONFIG_PATH)
        finally:
            temp.unlink(missing_ok=True)


def apply_acrylic(widget):
    if os.name != 'nt':
        return False
    hwnd = int(widget.winId())
    dwm = ctypes.windll.dwmapi
    dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwm.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.c_void_p]
    margins = (ctypes.c_int * 4)(-1, -1, -1, -1)
    dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    for attribute, value in [(20, 0), (33, 2)]:
        data = ctypes.c_int(value)
        dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), 4)
    backdrop = ctypes.c_int(3)
    return dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), 4) == 0


STYLE = '''
/* Hallmark: Workbench / custom Liquid Glass / typography-led */
QWidget { color: #20314b; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { background: transparent; }
QLabel#title { font-size: 29px; font-weight: 650; }
QLabel#section { font-size: 16px; font-weight: 600; }
QLabel#muted { color: #51627a; font-size: 12px; }
QLabel#status { font-size: 25px; font-weight: 600; }
QFrame#glass { background: rgba(255,255,255,145); border: 1px solid rgba(255,255,255,220); border-radius: 22px; }
QPushButton { background: rgba(255,255,255,185); border: 1px solid #c0cddd; border-radius: 16px; padding: 10px 18px; font-weight: 600; }
QPushButton:hover { background: #ffffff; border-color: #8ca6c9; }
QPushButton:focus { border: 2px solid #286ed8; }
QPushButton:pressed { background: #dce8fa; }
QPushButton:disabled { color: #8290a2; background: rgba(226,233,242,120); border-color: transparent; }
QPushButton#primary { background: #2467d9; color: white; border: 1px solid #6095ea; }
QPushButton#primary:hover { background: #1858c4; }
QPushButton#primary:disabled { background: #dae3f0; color: #7e8da3; }
QLineEdit { background: rgba(255,255,255,210); border: 1px solid #bfccdd; border-radius: 12px; padding: 10px 14px; font-size: 22px; font-weight: 600; selection-background-color: #2467d9; }
QLineEdit:focus { border: 2px solid #2467d9; }
QCheckBox { spacing: 12px; padding: 7px 0; }
QCheckBox::indicator { width: 36px; height: 21px; border-radius: 10px; border: 1px solid #a6b5c9; background: #d4ddea; image: url(__OFF__); }
QCheckBox::indicator:checked { background: #2467d9; border-color: #2467d9; image: url(__ON__); }
QCheckBox::indicator:focus { border: 2px solid #154aa0; }
QPlainTextEdit { background: rgba(236,242,250,170); border: 1px solid #d2deed; border-radius: 12px; padding: 10px; font-family: 'Cascadia Mono', 'Consolas'; font-size: 11px; color: #435570; }
'''
STYLE = STYLE.replace('__ON__', (BASE_DIR / 'assets/toggle-on.svg').as_posix()).replace('__OFF__', (BASE_DIR / 'assets/toggle-off.svg').as_posix())


def label(text, name=None):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(True)
    return w


def card():
    w = QFrame()
    w.setObjectName('glass')
    layout = QVBoxLayout(w)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)
    return w, layout


class Panel(QWidget):
    def __init__(self, backend=None):
        super().__init__()
        self.backend = backend or Backend()
        self.acrylic = False
        self.setWindowTitle('urWatchdog — Control Panel')
        self.setWindowIcon(QIcon(str(BASE_DIR / 'assets/urwatchdog.ico')))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(960, 820)
        self.setMinimumSize(900, 790)
        self.setStyleSheet(STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 24)
        root.setSpacing(18)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(label('urWatchdog', 'title'))
        heading.addWidget(label('Kendali daya, tanpa mengganggu pekerjaan.', 'muted'))
        header.addLayout(heading)
        header.addStretch()
        self.material = label('WINDOWS · ACRYLIC', 'muted')
        header.addWidget(self.material)
        root.addLayout(header)
        status_card, status_layout = card()
        status_line = QHBoxLayout()
        status_text = QVBoxLayout()
        status_text.addWidget(label('Layanan pemantauan', 'muted'))
        self.status_label = label('Memeriksa layanan…', 'status')
        status_text.addWidget(self.status_label)
        self.pid_label = label('', 'muted')
        status_text.addWidget(self.pid_label)
        status_line.addLayout(status_text, 1)
        self.start_button = QPushButton('Nyalakan')
        self.start_button.setObjectName('primary')
        self.stop_button = QPushButton('Hentikan')
        self.start_button.clicked.connect(lambda: self.action(self.backend.start, 'Permintaan mulai dikirim.'))
        self.stop_button.clicked.connect(lambda: self.action(self.backend.stop, 'Permintaan berhenti dikirim.'))
        status_line.addWidget(self.start_button)
        status_line.addWidget(self.stop_button)
        status_layout.addLayout(status_line)
        root.addWidget(status_card)
        body = QHBoxLayout()
        body.setSpacing(18)
        settings_card, settings = card()
        settings.addWidget(label('Waktu & verifikasi', 'section'))
        settings.addWidget(label('Atur kapan pemeriksaan tidak aktif dimulai.', 'muted'))
        fields = QHBoxLayout()
        self.idle = QLineEdit()
        self.countdown = QLineEdit()
        for title, field, unit in [('Batas idle', self.idle, 'menit · 1–1440'), ('Hitung mundur', self.countdown, 'detik · 1–3600')]:
            col = QVBoxLayout()
            col.addWidget(label(title))
            field.setAccessibleName(title)
            field.setFixedHeight(58)
            col.setSpacing(8)
            col.addWidget(field)
            col.addWidget(label(unit, 'muted'))
            fields.addLayout(col)
        settings.addLayout(fields)
        self.vision = QCheckBox('Camera Watch · aktif terus saat ON')
        self.sound = QCheckBox('Suara peringatan')
        self.startup = QCheckBox('Mulai saat masuk Windows')
        for control in (self.vision, self.sound, self.startup):
            settings.addWidget(control)
        settings.addWidget(label('Idle selalu mandiri. Kamera opsional: lambaian, mata tertutup lama, kepala menoleh atau wajah hilang memulai hitung mundur.', 'muted'))
        settings.addStretch()
        self.save_button = QPushButton('Simpan pengaturan')
        self.save_button.setObjectName('primary')
        self.save_button.clicked.connect(self.save)
        settings.addWidget(self.save_button)
        self.startup.clicked.connect(self.toggle_startup)
        body.addWidget(settings_card, 1)
        activity_card, activity = card()
        activity_heading = QHBoxLayout()
        activity_heading.addWidget(label('Aktivitas terbaru', 'section'), 1)
        self.refresh_button = QPushButton('Perbarui')
        self.refresh_button.clicked.connect(self.refresh)
        activity_heading.addWidget(self.refresh_button)
        activity.addLayout(activity_heading)
        activity.addWidget(label('Log lokal · diperbarui setiap 3 detik', 'muted'))
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setAccessibleName('Log daemon')
        activity.addWidget(self.logs, 1)
        self.sim_button = QPushButton('Pratinjau hitung mundur')
        self.sim_button.clicked.connect(self.simulate)
        activity.addWidget(self.sim_button)
        self.gesture_button = QPushButton('Uji lambaian sekarang · aman')
        self.gesture_button.clicked.connect(self.scan_gesture)
        activity.addWidget(self.gesture_button)
        self.gesture_status = label('Kamera mati. Uji 8 detik, tanpa shutdown.', 'muted')
        activity.addWidget(self.gesture_status)
        activity.addWidget(label('Pratinjau hitung mundur tanpa kamera. Uji lambaian membuka kamera sebentar; keduanya tanpa shutdown.', 'muted'))
        body.addWidget(activity_card, 1)
        root.addLayout(body, 1)
        self.notice = label('Menutup panel tidak menghentikan layanan.', 'muted')
        root.addWidget(self.notice)
        try:
            cfg = load_config()
            self.idle.setText(str(cfg.get('idle_threshold_seconds', 600) // 60))
            self.countdown.setText(str(cfg.get('countdown_seconds', 60)))
            self.vision.setChecked(cfg.get('continuous_camera_enabled', False))
            self.sound.setChecked(cfg.get('sound_alert_enabled', True))
        except Exception as exc:
            self.idle.setText('10')
            self.countdown.setText('60')
            self.notice.setText(f'Konfigurasi gagal dibaca: {exc}')
        self.startup.setChecked(STARTUP_PATH.exists())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)
        self.vision.clicked.connect(self.toggle_camera)
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu(self)
        menu.addAction('Buka panel', self.restore)
        menu.addAction('Nyalakan watchdog', self.backend.start)
        menu.addAction('Hentikan watchdog', self.backend.stop)
        self.tray_camera = menu.addAction('Camera Watch ON/OFF', self.vision.click)
        menu.addAction('Jeda 15 menit', lambda: self.backend.save({'paused_until':time.time()+900}))
        menu.addAction('Lanjutkan', lambda: self.backend.save({'paused_until':0}))
        menu.addSeparator()
        menu.addAction('Keluar panel (layanan tetap berjalan)', QApplication.instance().quit)
        menu.addAction('Hentikan layanan dan keluar', self.stop_exit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.setToolTip('urWatchdog — buka kendali')
        self.tray.show()
        self.refresh()

    def restore(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def stop_exit(self):
        self.backend.stop(); QApplication.instance().quit()

    def toggle_camera(self):
        try:
            if hasattr(self,'camera_process') and self.camera_process.state()!=QProcess.ProcessState.NotRunning:
                raise RuntimeError('Tutup pratinjau kamera dahulu')
            self.backend.save({'continuous_camera_enabled':self.vision.isChecked()})
            if self.vision.isChecked(): self.backend.start()
            self.notice.setText('Camera Watch diperbarui langsung. Idle tetap mandiri.')
        except Exception as exc:
            self.vision.setChecked(not self.vision.isChecked()); self.notice.setText(str(exc))

    def showEvent(self, event):
        super().showEvent(event)
        self.acrylic = apply_acrylic(self)
        self.material.setText('WINDOWS · ACRYLIC' if self.acrylic else 'WINDOWS · SOLID')
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(236, 245, 255, 55 if self.acrylic else 255))
        gradient.setColorAt(1, QColor(221, 231, 248, 80 if self.acrylic else 255))
        p.setBrush(gradient)
        p.setPen(QPen(QColor(255, 255, 255, 160), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    def action(self, fn, message):
        try:
            fn()
            self.notice.setText(message)
            QTimer.singleShot(500, self.refresh)
        except Exception as exc:
            self.notice.setText(f'Tidak berhasil: {exc}')

    def save(self):
        try:
            idle, countdown = validate_settings(self.idle.text(), self.countdown.text())
            self.backend.save(dict(idle_threshold_seconds=idle, countdown_seconds=countdown,
                continuous_camera_enabled=self.vision.isChecked(), sound_alert_enabled=self.sound.isChecked()))
            self.notice.setText('Tersimpan. Layanan membaca pengaturan pada siklus berikutnya.')
        except Exception as exc:
            self.notice.setText(str(exc))

    def toggle_startup(self):
        previous = not self.startup.isChecked()
        try:
            self.backend.startup(self.startup.isChecked())
            self.notice.setText('Pengaturan startup diperbarui.')
        except Exception as exc:
            self.startup.setChecked(previous)
            self.notice.setText(f'Startup gagal: {exc}')

    def refresh(self):
        try:
            pid = self.backend.status()
            self.status_label.setText('Watchdog aktif' if pid else 'Watchdog nonaktif')
            self.pid_label.setText(f'PID {pid} · Memantau aktivitas Windows' if pid else 'Pemantauan tidak berjalan')
            status_file = BASE_DIR/'runtime_status.json'
            if pid and status_file.exists():
                live = json.loads(status_file.read_text(encoding='utf-8'))
                stale = time.time()-live.get('updated',0)>10
                self.pid_label.setText(f"PID {pid} · {live.get('mode')} · idle {live.get('idle_seconds',0)} / {live.get('threshold_seconds')} s · alasan {live.get('reason') or '-'} · sisa {live.get('remaining_seconds','-')} s" + (' · TELEMETRI LAMA' if stale else ''))
                self.gesture_status.setText('Camera: '+json.dumps(live.get('camera',{}),ensure_ascii=False)+' '+live.get('error',''))
            self.start_button.setEnabled(not bool(pid))
            self.stop_button.setEnabled(bool(pid))
            if LOG_PATH.exists():
                with LOG_PATH.open('rb') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 32768))
                    data = f.read().decode('utf-8', errors='replace')
                text = '\n'.join(data.splitlines()[-60:])
            else:
                text = 'Belum ada aktivitas tercatat.'
            if self.logs.toPlainText() != text:
                self.logs.setPlainText(text)
                self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())
        except Exception as exc:
            self.notice.setText(f'Pembaruan gagal: {exc}')

    def scan_gesture(self):
        if load_config().get('continuous_camera_enabled',False):
            self.notice.setText('Matikan Camera Watch sebelum pratinjau aman.'); return
        from vision_check import VISION_PYTHON
        if hasattr(self, 'camera_process') and self.camera_process.state() != QProcess.ProcessState.NotRunning:
            return
        self.camera_process = QProcess(self)
        self.camera_buffer = ''
        self.camera_process.setWorkingDirectory(str(BASE_DIR))
        self.camera_process.readyReadStandardOutput.connect(self.camera_feedback)
        self.camera_process.finished.connect(self.camera_finished)
        self.camera_process.errorOccurred.connect(self.camera_error)
        self.gesture_button.setEnabled(False)
        self.gesture_status.setText('Memuat model. Kamera hanya aktif selama uji.')
        self.camera_process.start(str(VISION_PYTHON), [str(BASE_DIR / 'vision_worker.py'), '--seconds', '8', '--preview'])
        self.camera_timeout = QTimer(self)
        self.camera_timeout.setSingleShot(True)
        self.camera_timeout.timeout.connect(self.camera_process.kill)
        self.camera_timeout.start(23000)

    def camera_error(self, error):
        self.gesture_status.setText('Kamera gagal dimulai. Periksa .vision-venv.')
        self.gesture_button.setEnabled(True)
        if hasattr(self, 'camera_timeout'):
            self.camera_timeout.stop()

    def camera_feedback(self):
        self.camera_buffer += bytes(self.camera_process.readAllStandardOutput()).decode('utf-8', errors='replace')
        while '\n' in self.camera_buffer:
            line, self.camera_buffer = self.camera_buffer.split('\n', 1)
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if 'result' in data:
                self.gesture_status.setText(f"Hasil: {data['result']}. Kamera mati. Tidak ada shutdown.")
            elif 'error' in data:
                self.gesture_status.setText(data['error'])
            elif 'hand' in data:
                self.gesture_status.setText(f"Tangan: {data['hand']} · terbuka: {data['open_hand']} · balik arah: {data['reversals']}/2 · wajah: {data['face']}")
            else:
                self.gesture_status.setText(data.get('status', 'Memeriksa…'))

    def camera_finished(self, code, status):
        self.camera_feedback()
        self.camera_timeout.stop()
        self.gesture_button.setEnabled(True)
        if code != 0:
            self.gesture_status.setText('Uji berhenti/gagal. Kamera dilepas oleh proses. Tidak ada shutdown.')

    def closeEvent(self, event):
        if hasattr(self, 'camera_process') and self.camera_process.state() != QProcess.ProcessState.NotRunning:
            self.camera_process.kill()
            self.camera_process.waitForFinished(3000)
        if self.tray.isVisible():
            self.hide(); event.ignore()
        else:
            super().closeEvent(event)

    def simulate(self):
        # Pure local preview. No daemon imports, subprocesses or power APIs.
        self.preview = QWidget(self, Qt.WindowType.Window)
        self.preview.setWindowTitle('urWatchdog — Simulasi aman')
        self.preview.setStyleSheet(STYLE)
        self.preview.resize(400, 230)
        layout = QVBoxLayout(self.preview)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(label('Simulasi aman', 'section'))
        layout.addWidget(label('Tidak ada aplikasi yang ditutup. Laptop tetap menyala.', 'muted'))
        remaining = label('10 detik', 'status')
        layout.addWidget(remaining)
        cancel = QPushButton('Batalkan simulasi')
        layout.addWidget(cancel)
        cancel.clicked.connect(self.preview.close)
        timer = QTimer(self.preview)
        state = [10]
        def tick():
            state[0] -= 1
            remaining.setText(f'{state[0]} detik' if state[0] else 'Selesai. Tidak ada shutdown.')
            if not state[0]:
                timer.stop()
        timer.timeout.connect(tick)
        timer.start(1000)
        self.preview.show()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    socket = QLocalSocket()
    socket.connectToServer('urWatchdogPanelV2')
    if socket.waitForConnected(500):
        socket.write(b'show'); socket.flush(); socket.waitForBytesWritten(500); return
    QLocalServer.removeServer('urWatchdogPanelV2')
    server = QLocalServer()
    if not server.listen('urWatchdogPanelV2'): raise RuntimeError(server.errorString())
    app.setStyle('Fusion')
    panel = Panel()
    def activate():
        connection = server.nextPendingConnection()
        if connection: connection.close()
        panel.restore()
    server.newConnection.connect(activate)
    if '--tray' not in sys.argv: panel.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
