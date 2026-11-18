"""Validated live settings and atomic runtime telemetry."""
import json
import os
import tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent
DEFAULTS = dict(idle_threshold_seconds=600, countdown_seconds=30, check_interval_seconds=1,
    continuous_camera_enabled=False, sound_alert_enabled=True, graceful_close_wait_seconds=20,
    paused_until=0, camera_closed_seconds=3, camera_away_seconds=5, camera_turn_seconds=3)

def atomic_json(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def load(path=BASE/'config.json'):
    data = DEFAULTS.copy()
    if Path(path).exists(): data.update(json.loads(Path(path).read_text(encoding='utf-8')))
    for key, low, high in [('idle_threshold_seconds',60,86400),('countdown_seconds',1,3600),
            ('check_interval_seconds',.2,10),('graceful_close_wait_seconds',1,120),
            ('camera_closed_seconds',1,30),('camera_away_seconds',2,60),('camera_turn_seconds',1,30)]:
        if isinstance(data[key], bool) or not low <= float(data[key]) <= high: raise ValueError('Invalid '+key)
        data[key] = float(data[key])
    if not isinstance(data['continuous_camera_enabled'], bool): raise ValueError('Camera preference must be boolean')
    data['force_shutdown_after_close'] = False
    return data
