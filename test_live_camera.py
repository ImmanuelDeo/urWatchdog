"""Real daemon + opt-in + hardware; dry-run prevents all power/app operations."""
import json
import subprocess
import sys
import time
from runtime_config import BASE, atomic_json
cfg=BASE/'.ui-validation/live-config.json'; status=BASE/'.ui-validation/live-status.json'
values=dict(idle_threshold_seconds=600,countdown_seconds=3,continuous_camera_enabled=False,sound_alert_enabled=False)
atomic_json(cfg,values)
p=subprocess.Popen([sys.executable,str(BASE/'daemon.py'),'--dry-run','--config',str(cfg),'--status',str(status),'--max-seconds','22'])
try:
    time.sleep(2)
    assert json.loads(status.read_text())['camera']['status']=='off'
    values['continuous_camera_enabled']=True; atomic_json(cfg,values)
    deadline=time.monotonic()+15; seen=None
    while time.monotonic()<deadline:
        s=json.loads(status.read_text())
        if s['camera'].get('frames',0)>0: seen=s; break
        time.sleep(.2)
    assert seen, 'No real camera telemetry'
    assert seen['idle_seconds']<600
    values['continuous_camera_enabled']=False; atomic_json(cfg,values)
    time.sleep(4)
    s=json.loads(status.read_text()); assert s['camera']['status']=='off'
    p.wait(30)
    print(json.dumps({'result':'PASS','immediate_camera_before_idle':seen,'off_released':s,'returncode':p.returncode}))
finally:
    if p.poll() is None: p.kill(); p.wait()
