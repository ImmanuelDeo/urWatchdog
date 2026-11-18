"""Independent idle monitor; continuous vision requires explicit opt-in."""
import argparse
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import subprocess
import sys
import threading
import time
from runtime_config import BASE, load, atomic_json
from ui_countdown import get_idle_seconds, show_countdown_dialog
from app_closer import close_all_user_apps, execute_shutdown
from vision_check import VISION_PYTHON
logger=logging.getLogger('urWatchdogRuntime')

class Camera:
    def __init__(self):
        self.proc=None; self.events=queue.Queue(); self.last={}; self.last_update=0
    def start(self,cfg):
        self.events=queue.Queue()
        self.proc=subprocess.Popen([str(VISION_PYTHON),str(BASE/'vision_worker.py'),'--continuous',
            '--closed',str(cfg['camera_closed_seconds']),'--away',str(cfg['camera_away_seconds']),
            '--turn',str(cfg['camera_turn_seconds'])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.last_update=time.monotonic(); self.last={'status':'starting'}
        proc,events=self.proc,self.events
        def reader():
            for line in proc.stdout:
                try: events.put(json.loads(line))
                except ValueError: pass
        threading.Thread(target=reader,daemon=True).start()
    def poll(self):
        signal=None
        while not self.events.empty():
            self.last=self.events.get_nowait(); self.last_update=time.monotonic()
            signal=self.last.get('signal') or signal
        if self.proc and (self.proc.poll() is not None or time.monotonic()-self.last_update>20):
            self.last={'error':self.last.get('error','Camera worker exited or stalled')}; self.stop(); signal=None
        return signal
    def stop(self):
        if self.proc:
            try:
                self.proc.stdin.write('stop\n'); self.proc.stdin.flush(); self.proc.wait(3)
            except (OSError,subprocess.TimeoutExpired):
                self.proc.kill(); self.proc.wait(3)
            self.proc=None

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default=str(BASE/'config.json')); p.add_argument('--status',default=str(BASE/'runtime_status.json'))
    p.add_argument('--dry-run',action='store_true'); p.add_argument('--test-idle-clock',action='store_true')
    p.add_argument('--once',action='store_true'); p.add_argument('--max-seconds',type=float,default=0)
    args=p.parse_args()
    if args.test_idle_clock and not args.dry_run: p.error('test clock requires dry-run')
    k=ctypes.windll.kernel32; k.CreateMutexW.restype=ctypes.c_void_p
    mutex=k.CreateMutexW(None,False,'Local\\urWatchdogRuntime'+(str(os.getpid()) if args.dry_run else ''))
    if not mutex: raise ctypes.WinError()
    if k.GetLastError()==183: return
    handler=RotatingFileHandler(BASE/'daemon.log',maxBytes=512000,backupCount=2,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler); logger.setLevel(logging.INFO); logger.propagate=False
    stop_path=BASE/'daemon.stop'
    if not args.dry_run: stop_path.unlink(missing_ok=True)
    camera=Camera(); start=time.monotonic(); rearm=start; camera_retry=0
    state=dict(pid=os.getpid(),mode='starting',camera={'status':'off'},dry_run=args.dry_run)
    def status(**values):
        state.update(values,updated=time.time()); atomic_json(args.status,state)
    def stopped(): return not args.dry_run and stop_path.exists()
    logger.info('Daemon started pid=%s dry_run=%s',os.getpid(),args.dry_run)
    if not args.dry_run:
        subprocess.Popen([str(__import__('pathlib').Path(sys.executable).with_name('pythonw.exe')), str(BASE/'control_panel.py'), '--tray'], creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        while not stopped():
            cfg=load(args.config); now=time.monotonic()
            idle=now-start if args.test_idle_clock else get_idle_seconds()
            paused=time.time()<cfg.get('paused_until',0)
            wanted=cfg['continuous_camera_enabled'] and not paused
            if wanted and not camera.proc and now>=camera_retry:
                try: camera.start(cfg)
                except OSError as exc: camera.last={'error':str(exc)}
                camera_retry=now+30
            if not wanted and camera.proc: camera.stop()
            signal=camera.poll() if wanted else None
            status(mode='paused' if paused else ('cooldown' if now<rearm else 'monitoring'),idle_seconds=round(idle,1),
                threshold_seconds=cfg['idle_threshold_seconds'],countdown_seconds=cfg['countdown_seconds'],
                camera=camera.last if wanted else {'status':'off'},reason=None)
            reason='IDLE' if idle>=cfg['idle_threshold_seconds'] else signal
            if reason and not paused and now>=rearm:
                if reason=='IDLE' and not args.test_idle_clock and get_idle_seconds()<cfg['idle_threshold_seconds']: continue
                camera.stop()
                logger.info('Countdown reason=%s idle=%.1f duration=%s',reason,idle,cfg['countdown_seconds'])
                status(mode='countdown',reason=reason,camera={'status':'off'})
                def abort():
                    live=load(args.config)
                    return stopped() or time.time()<live.get('paused_until',0) or (reason!='IDLE' and not live['continuous_camera_enabled'])
                action=show_countdown_dialog(int(cfg['countdown_seconds']),args.config,cfg['sound_alert_enabled'],
                    title_text='Konfirmasi shutdown · '+reason,
                    subtitle_text='Aplikasi ditutup satu per satu setelah hitung mundur.',
                    abort_check=abort,progress=lambda remaining:status(remaining_seconds=remaining),
                    idle_provider=(lambda:time.monotonic()-start) if args.test_idle_clock else get_idle_seconds)
                logger.info('Countdown outcome=%s reason=%s',action,reason)
                if action=='shutdown' and not abort():
                    status(mode='closing',reason=reason)
                    if args.dry_run:
                        status(mode='dry-run-complete',action='shutdown',apps_closed=0); return
                    if close_all_user_apps(cfg['graceful_close_wait_seconds'],logger.info):
                        execute_shutdown(logger=logger.info); status(mode='shutdown-requested'); return
                    status(mode='blocked',error='Application refused closure or unsaved prompt; shutdown aborted')
                    logger.warning('Shutdown aborted: application refused closure')
                rearm=time.monotonic()+max(60,cfg['idle_threshold_seconds'])
                status(mode='cooldown',action=action,cooldown_until=time.time()+max(60,cfg['idle_threshold_seconds']))
                if args.once: return
            if args.max_seconds and time.monotonic()-start>args.max_seconds: return
            time.sleep(cfg['check_interval_seconds'])
    except Exception as exc:
        logger.exception('Monitor failed'); status(mode='error',error=str(exc)); raise
    finally:
        camera.stop()
        if state.get('mode') not in ('dry-run-complete','error','shutdown-requested'): status(mode='stopped',camera={'status':'off'})
        k.CloseHandle(ctypes.c_void_p(mutex))
