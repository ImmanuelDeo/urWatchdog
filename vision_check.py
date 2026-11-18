"""Short, isolated MediaPipe hand scans. Importing never opens a camera."""
import json
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
VISION_PYTHON = BASE / '.vision-venv/Scripts/python.exe'

class WaveTracker:
    """Accumulate travel, not per-frame speed; require two real reversals."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.anchor = self.extreme = self.last_x = None
        self.direction = self.turns = 0
        self.started = self.last_time = None

    def update(self, x, now):
        if x is None:
            self.reset()
            return False
        if self.last_time is not None and (now-self.last_time > .4 or now-self.started > 4 or abs(x-self.last_x) > .25):
            self.reset()
        if self.anchor is None:
            self.anchor = self.extreme = x
            self.started = now
        self.last_time, self.last_x = now, x
        if not self.direction:
            if abs(x-self.anchor) >= .08:
                self.direction = 1 if x > self.anchor else -1
                self.extreme = x
        elif (x-self.extreme)*self.direction >= 0:
            self.extreme = x
        elif abs(x-self.extreme) >= .08:
            self.turns += 1
            self.direction *= -1
            self.extreme = x
        return self.turns >= 2 and now-self.started >= .6


def analyze_user_behavior(duration_seconds=5):
    """Worker failures are ERROR, never absence. Caller must fail safe."""
    duration = max(1, min(10, float(duration_seconds)))
    try:
        result = subprocess.run([str(VISION_PYTHON), str(BASE/'vision_worker.py'), '--seconds', str(duration)],
            capture_output=True, text=True, timeout=duration+15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return 'ERROR'
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        return next((item['result'] for item in reversed(lines) if 'result' in item), 'ERROR')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 'ERROR'

check_user_presence = analyze_user_behavior

if __name__ == '__main__':
    print(analyze_user_behavior())
