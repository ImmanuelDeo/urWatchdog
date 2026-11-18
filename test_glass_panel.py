"""Safe UI smoke test: every mutating service action is mocked."""
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch, Mock
import glass_panel as g
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

app = g.QApplication.instance() or g.QApplication([])
app.setStyle('Fusion')
real_config = g.CONFIG_PATH.read_bytes()
real_pid = g.Backend().status()
class Fake:
    pid = None
    calls = []
    def status(self): return self.pid
    def start(self): self.calls.append('start'); self.pid = 12345
    def stop(self): self.calls.append('stop'); self.pid = None
    def save(self, values): self.calls.append(values)
    def startup(self, enabled): self.calls.append(('startup', enabled))
f = Fake()
p = g.Panel(f)
p.show()
QTest.qWait(1000)
p.start_button.click(); p.refresh()
assert p.stop_button.isEnabled() and not p.start_button.isEnabled()
p.stop_button.click(); p.refresh()
assert p.start_button.isEnabled()
p.idle.setText('0'); p.save_button.click()
assert '1–1440' in p.notice.text()
p.idle.setText('10'); p.countdown.setText('60')
p.vision.click(); p.sound.click(); p.save_button.click()
assert f.calls[-1]['idle_threshold_seconds'] == 600
assert f.calls[-1]['countdown_seconds'] == 60
p.startup.click(); assert f.calls[-1][0] == 'startup'
for a,b in [('x','60'),('-1','60'),('10','0'),('1441','60'),('10','3601')]:
    try: g.validate_settings(a,b)
    except ValueError: pass
    else: raise AssertionError((a,b))
with tempfile.TemporaryDirectory(dir=str(g.BASE_DIR / '.ui-validation')) as directory:
    target = Path(directory) / 'config.json'
    target.write_text(json.dumps({'force_shutdown_after_close': True, 'unknown': 9}))
    with patch.object(g, 'CONFIG_PATH', target):
        g.Backend().save({'countdown_seconds': 60})
        assert json.loads(target.read_text()) == {'force_shutdown_after_close': True, 'unknown': 9, 'countdown_seconds': 60}
with patch.object(g, 'get_daemon_process', return_value=None), patch.object(g.subprocess, 'Popen') as launch:
    g.Backend().start()
    assert launch.call_args.args[0] == [g.PYTHONW_EXE, str(g.DAEMON_PY)]
proc = Mock()
with patch.object(g, 'get_daemon_process', return_value=proc):
    with patch.object(g, 'BASE_DIR', Path(directory)):
        Path(directory).mkdir(exist_ok=True)
        g.Backend().stop(); assert (Path(directory)/'daemon.stop').exists()
        proc.terminate.assert_not_called()
p.sim_button.click()
QTest.qWait(11000)
assert any('Selesai.' in x.text() for x in p.preview.findChildren(QLabel))
p.preview.close()
assert g.CONFIG_PATH.read_bytes() == real_config
assert g.Backend().status() == real_pid
# Capture a real, read-only panel rather than the fake service status.
p.close(); QTest.qWait(100); assert not p.isVisible() and p.tray.isVisible()
p.restore(); QTest.qWait(100); assert p.isVisible()
p.tray.hide(); p.close()
live = g.Panel()
live.show(); live.raise_(); live.activateWindow()
QTest.qWait(1000)
from PIL import ImageGrab
out = g.BASE_DIR / '.ui-validation'
ImageGrab.grab().save(out / 'desktop.png')
rect = live.frameGeometry()
ratio = live.devicePixelRatioF()
live.grab().save(str(out / 'panel.png'))
print(json.dumps({'result':'PASS', 'checks':['start/stop button states','invalid input rejection','vision/sound save payload','startup callback','atomic config preservation','exact launch arguments','targeted stop','safe preview completes','config unchanged','daemon PID unchanged'], 'acrylic_api_success':live.acrylic,'daemon_pid':real_pid,'screenshot':str(out/'panel.png')}))
live.close()
