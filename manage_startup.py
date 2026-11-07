import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_PY = os.path.join(BASE_DIR, "daemon.py")
CONTROL_PANEL_PY = os.path.join(BASE_DIR, "control_panel.py")
STOP_PY = os.path.join(BASE_DIR, "stop_daemon.py")
PYTHONW_EXE = r"C:\Users\deoim\miniconda3\envs\yolo11-ablation\pythonw.exe"
PYTHON_EXE = r"C:\Users\deoim\miniconda3\envs\yolo11-ablation\python.exe"
VBS_PATH = os.path.join(BASE_DIR, "run_silent.vbs")

ICO_PATH = os.path.join(BASE_DIR, "assets", "urwatchdog.ico")

def get_appdata_dirs():
    appdata = os.environ.get("APPDATA")
    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    programs_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\urWatchdog")
    return startup_dir, programs_dir

def create_shortcut(target, args, shortcut_path, desc, workdir=BASE_DIR, icon_path=None):
    icon_line = f"$s.IconLocation = '{icon_path},0'; " if icon_path and os.path.exists(icon_path) else ""
    ps_cmd = (
        f"$wsh = New-Object -ComObject WScript.Shell; "
        f"$s = $wsh.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Arguments = '{args}'; "
        f"$s.WorkingDirectory = '{workdir}'; "
        f"$s.Description = '{desc}'; "
        f"{icon_line}"
        f"$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)

def install():
    startup_dir, programs_dir = get_appdata_dirs()
    os.makedirs(startup_dir, exist_ok=True)
    os.makedirs(programs_dir, exist_ok=True)

    # 1. Silent VBS for daemon
    vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\n' \
                  f'WshShell.Run """{PYTHONW_EXE}"" ""{DAEMON_PY}""", 0, False\n'
    with open(VBS_PATH, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    # 2. Startup folder shortcut
    startup_shortcut = os.path.join(startup_dir, "urWatchdog.lnk")
    create_shortcut('wscript.exe', f'"{VBS_PATH}"', startup_shortcut, 'urWatchdog Auto-Start Daemon', icon_path=ICO_PATH)

    # 3. Start Menu Shortcuts (Searchable in Windows Search)
    cp_shortcut = os.path.join(programs_dir, "urWatchdog Control Panel.lnk")
    create_shortcut(PYTHONW_EXE, f'"{CONTROL_PANEL_PY}"', cp_shortcut, 'urWatchdog One-Gate Control Panel', icon_path=ICO_PATH)

    start_shortcut = os.path.join(programs_dir, "Start urWatchdog.lnk")
    create_shortcut('wscript.exe', f'"{VBS_PATH}"', start_shortcut, 'Start urWatchdog Background Daemon', icon_path=ICO_PATH)

    stop_shortcut = os.path.join(programs_dir, "Stop urWatchdog.lnk")
    create_shortcut(PYTHON_EXE, f'"{STOP_PY}"', stop_shortcut, 'Stop urWatchdog Daemon', icon_path=ICO_PATH)

    print(f"[urWatchdog] Terpasang di Windows Startup & Start Menu:")
    print(f" - Start Menu Folder: {programs_dir}")
    print(f" - Startup Shortcut: {startup_shortcut}")

def uninstall():
    startup_dir, programs_dir = get_appdata_dirs()
    startup_shortcut = os.path.join(startup_dir, "urWatchdog.lnk")
    if os.path.exists(startup_shortcut):
        os.remove(startup_shortcut)
        print("[urWatchdog] Shortcut dihapus dari Startup.")
    else:
        print("[urWatchdog] Shortcut tidak ada di Startup.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall()
    else:
        install()
