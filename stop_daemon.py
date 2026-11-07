import os
import psutil

def stop():
    current_pid = os.getpid()
    stopped = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            name = (proc.info.get('name') or '').lower()
            if not ('python' in name or 'pythonw' in name):
                continue
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()
            if "daemon.py" in cmd_str and ("urwatchdog" in cmd_str or "sleepguard" in cmd_str):
                pid = proc.info['pid']
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                print(f"[urWatchdog] Berhasil menghentikan proses PID: {pid}")
                stopped += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if stopped == 0:
        print("[urWatchdog] Tidak ada proses urWatchdog yang sedang berjalan.")

if __name__ == "__main__":
    stop()
