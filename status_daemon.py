import os
import psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "daemon.log")

def show_status():
    print("==================================================")
    print("              STATUS URWATCHDOG DAEMON            ")
    print("==================================================")

    found = []
    current_pid = os.getpid()
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
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if found:
        print("[STATUS] AKTIF BERJALAN (RUNNING)")
        for p in found:
            print(f" - PID: {p.pid} ({p.name()})")
    else:
        print("[STATUS] TIDAK AKTIF (STOPPED)")

    print("\nLog Terakhir (daemon.log):")
    print("--------------------------------------------------")
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in lines[-15:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"Gagal membaca log: {e}")
    else:
        print("Belum ada log tercatat.")
    print("==================================================")

if __name__ == "__main__":
    show_status()
