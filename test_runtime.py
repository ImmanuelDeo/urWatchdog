"""Safe runtime tests: no real app closure or shutdown, real dialog/daemon."""
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from face_signals import FaceSignals
from runtime_config import BASE, atomic_json, load
import app_closer

class Tests(unittest.TestCase):
    def test_face_debounce(self):
        d=FaceSignals()
        self.assertIsNone(d.update(0,True,.1,0))
        self.assertIsNone(d.update(.2,True,.3,0))
        self.assertIsNone(d.update(1,True,.1,0))
        self.assertEqual(d.update(4.1,True,.1,0),'EYES_CLOSED')
        self.assertIsNone(d.update(5,True,.1,0))
        d.update(6,True,.3,.5)
        self.assertEqual(d.update(9.1,True,.3,.5),'HEAD_TURNED')
        d.update(10,False)
        self.assertEqual(d.update(15.1,False),'FACE_AWAY')
    def test_close_sequential_and_refusal(self):
        class API:
            def __init__(self,refuse=False): self.open={1,2}; self.sent=[]; self.refuse=refuse
            def IsWindow(self,h): return h in self.open
            def PostMessageW(self,h,*args):
                self.sent.append(h)
                if not self.refuse:self.open.remove(h)
                return True
        api=API()
        self.assertTrue(app_closer.close_all_user_apps(.1,windows=[(1,'test1'),(2,'test2')],api=api))
        self.assertEqual(api.sent,[1,2])
        api=API(True)
        self.assertFalse(app_closer.close_all_user_apps(.1,windows=[(1,'test1'),(2,'test2')],api=api))
        self.assertEqual(api.sent,[1])
        with self.assertRaises(ValueError): app_closer.execute_shutdown(True)
        with patch('subprocess.run') as run:
            app_closer.execute_shutdown(); self.assertEqual(run.call_args.args[0],['shutdown.exe','/s','/t','0'])
    def test_dialog_cancel_on_new_input(self):
        from ui_countdown import show_countdown_dialog
        began=time.monotonic()
        result=show_countdown_dialog(3,sound_alert=False,idle_provider=lambda:60 if time.monotonic()-began<.3 else 0)
        self.assertEqual(result,'cancelled')
    def test_config(self):
        target=BASE/'.ui-validation/test-config.json'
        atomic_json(target,{'vision_verification_enabled':True})
        self.assertFalse(load(target)['continuous_camera_enabled'])
        atomic_json(target,{'idle_threshold_seconds':1})
        with self.assertRaises(ValueError):load(target)
    def test_real_60_second_daemon_dialog_dryrun(self):
        target=BASE/'.ui-validation/e2e-config.json'; status=BASE/'.ui-validation/e2e-status.json'
        atomic_json(target,dict(idle_threshold_seconds=60,countdown_seconds=3,check_interval_seconds=.2,sound_alert_enabled=False))
        began=time.monotonic()
        proc=subprocess.Popen([sys.executable,str(BASE/'daemon.py'),'--dry-run','--test-idle-clock','--once','--config',str(target),'--status',str(status),'--max-seconds','75'])
        modes=set(); screenshot=False
        while proc.poll() is None and time.monotonic()-began<85:
            if status.exists():
                data=json.loads(status.read_text()); modes.add(data['mode'])
                if data['mode']=='countdown' and not screenshot:
                    from PIL import ImageGrab
                    time.sleep(.3); ImageGrab.grab().save(BASE/'.ui-validation/countdown-runtime.png'); screenshot=True
            time.sleep(.15)
        if proc.poll() is None: proc.kill(); self.fail('daemon timeout')
        data=json.loads(status.read_text())
        self.assertEqual(proc.returncode,0)
        self.assertIn('countdown',modes)
        self.assertEqual(data['mode'],'dry-run-complete')
        self.assertEqual(data['apps_closed'],0)
        self.assertGreaterEqual(time.monotonic()-began,63)
        print('E2E',json.dumps(data),'elapsed',time.monotonic()-began,flush=True)

if __name__=='__main__': unittest.main(verbosity=2)
