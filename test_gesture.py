"""Safe regression tests: no camera or power calls."""
import unittest
import vision_check as v

class GestureTests(unittest.TestCase):
    def test_slow_landmark_wave(self):
        self.assertTrue(hasattr(v, 'WaveTracker'), 'Missing real hand landmark tracker')
        tracker = v.WaveTracker()
        xs = [.3 + i*.01 for i in range(21)] + [.5-i*.01 for i in range(21)] + [.3+i*.01 for i in range(21)]
        self.assertTrue(any(tracker.update(x, i*.04) for i,x in enumerate(xs)))

    def test_jitter_and_one_way_do_not_wave(self):
        for xs in ([.5,.51,.49,.5]*30, [i*.005 for i in range(100)]):
            tracker = v.WaveTracker()
            self.assertFalse(any(tracker.update(x,i*.03) for i,x in enumerate(xs)))

    def test_missing_hand_resets(self):
        tracker = v.WaveTracker()
        for i,x in enumerate([.3,.4,.5,.4,.3]): tracker.update(x,i*.1)
        tracker.update(None,.5)
        self.assertEqual(tracker.turns,0)

    def test_worker_missing_fails_safe(self):
        from unittest.mock import patch
        with patch.object(v.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertEqual(v.analyze_user_behavior(), 'ERROR')

    def test_wave_timeout_cancels_real_dialog(self):
        from unittest.mock import patch
        import ui_countdown as ui
        with patch.object(ui, 'get_idle_seconds', return_value=900):
            self.assertEqual(ui.show_countdown_dialog(1, sound_alert=False, require_explicit_confirmation=True), 'cancelled')

    def test_camera_signals_use_configured_countdown(self):
        import sys, time
        from unittest.mock import patch
        import daemon_runtime as d
        from runtime_config import atomic_json, BASE
        cfg=BASE/'.ui-validation/signal-config.json'
        atomic_json(cfg,dict(continuous_camera_enabled=True,countdown_seconds=1,sound_alert_enabled=False))
        for signal in ['WAVE','EYES_CLOSED','HEAD_TURNED','FACE_AWAY']:
            status=BASE/'.ui-validation/signal-status.json'
            begun=time.monotonic()
            with patch.object(sys,'argv',['daemon.py','--dry-run','--once','--config',str(cfg),'--status',str(status)]), patch.object(d.Camera,'start'), patch.object(d.Camera,'poll',return_value=signal), patch.object(d.Camera,'stop'), patch.object(d,'get_idle_seconds',side_effect=lambda:time.monotonic()-begun+10), patch.object(d,'close_all_user_apps') as close, patch.object(d,'execute_shutdown') as shutdown:
                d.main()
                import json
                result=json.loads(status.read_text())
                self.assertEqual(result['mode'],'dry-run-complete')
                self.assertEqual(result['reason'],signal)
                self.assertEqual(result['countdown_seconds'],1)
                close.assert_not_called(); shutdown.assert_not_called()

if __name__ == '__main__': unittest.main()
