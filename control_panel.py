import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "daemon.log")
ICO_PATH = os.path.join(BASE_DIR, "assets", "urwatchdog.ico")
PYTHONW_EXE = r"C:\Users\deoim\miniconda3\envs\yolo11-ablation\pythonw.exe"
PYTHON_EXE = r"C:\Users\deoim\miniconda3\envs\yolo11-ablation\python.exe"
DAEMON_PY = os.path.join(BASE_DIR, "daemon.py")

def get_daemon_process():
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
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def is_startup_enabled():
    appdata = os.environ.get("APPDATA", "")
    shortcut = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup\urWatchdog.lnk")
    return os.path.exists(shortcut)

def set_startup(enable: bool):
    import subprocess
    cmd = [PYTHON_EXE, os.path.join(BASE_DIR, "manage_startup.py")]
    if not enable:
        cmd.append("uninstall")
    subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

class UrWatchdogApp:
    def __init__(self, root):
        self.root = root
        self.root.title("urWatchdog — Control Panel")
        self.root.geometry("640x720")
        self.root.configure(bg="#121214")
        self.root.resizable(False, False)

        if os.path.exists(ICO_PATH):
            try:
                self.root.iconbitmap(ICO_PATH)
            except Exception:
                pass

        # Style definitions
        self.bg_color = "#121214"
        self.card_bg = "#1a1a1e"
        self.border_color = "#2a2a30"
        self.text_primary = "#f4f4f5"
        self.text_secondary = "#a1a1aa"
        self.accent_blue = "#2563eb"
        self.accent_red = "#dc2626"
        self.accent_green = "#16a34a"

        self.load_config()
        self.build_ui()
        self.refresh_status()
        self.refresh_log()

        # Background status refresh loop
        self.update_loop()

    def load_config(self):
        default = {
            "idle_threshold_seconds": 600,
            "countdown_seconds": 60,
            "check_interval_seconds": 3,
            "vision_verification_enabled": True,
            "vision_check_duration_seconds": 5,
            "postpone_after_presence_seconds": 300,
            "graceful_close_wait_seconds": 3,
            "force_shutdown_after_close": True,
            "sound_alert_enabled": True
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    default.update(json.load(f))
            except Exception:
                pass
        self.config = default

    def save_config(self):
        try:
            self.config["idle_threshold_seconds"] = int(self.idle_minutes_var.get()) * 60
            self.config["countdown_seconds"] = int(self.countdown_sec_var.get())
            self.config["vision_verification_enabled"] = self.vision_var.get()
            self.config["sound_alert_enabled"] = self.sound_var.get()

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            messagebox.showinfo("Tersimpan", "Pengaturan urWatchdog berhasil disimpan.")
        except ValueError:
            messagebox.showerror("Error", "Batas waktu harus berupa angka bulat.")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan konfigurasi: {e}")

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=16)
        main_frame.pack(fill="both", expand=True)

        # Header
        header_frame = tk.Frame(main_frame, bg=self.bg_color)
        header_frame.pack(fill="x", pady=(0, 14))

        lbl_title = tk.Label(
            header_frame,
            text="urWatchdog Control Panel",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg=self.text_primary
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header_frame,
            text="One-Gate Autonomous System Watchdog & Graceful Power Management",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_secondary
        )
        lbl_sub.pack(anchor="w")

        # Status Card
        status_card = tk.LabelFrame(
            main_frame,
            text=" Status Layanan ",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.text_primary,
            bd=1,
            relief="solid",
            padx=14,
            pady=10
        )
        status_card.pack(fill="x", pady=(0, 12))

        status_row = tk.Frame(status_card, bg=self.card_bg)
        status_row.pack(fill="x", pady=4)

        tk.Label(status_row, text="Status Daemon:", font=("Segoe UI", 10), bg=self.card_bg, fg=self.text_secondary).pack(side="left")
        self.lbl_status = tk.Label(status_row, text="Memeriksa...", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.text_primary)
        self.lbl_status.pack(side="left", padx=8)

        btn_row = tk.Frame(status_card, bg=self.card_bg)
        btn_row.pack(fill="x", pady=(8, 2))

        self.btn_start = tk.Button(
            btn_row,
            text="Nyalakan Watchdog",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_green,
            fg="#ffffff",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.start_daemon
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = tk.Button(
            btn_row,
            text="Hentikan Watchdog",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_red,
            fg="#ffffff",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.stop_daemon
        )
        self.btn_stop.pack(side="left", padx=8)

        self.btn_test = tk.Button(
            btn_row,
            text="Uji Simulasi Aman",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg=self.text_primary,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.run_simulation
        )
        self.btn_test.pack(side="right")

        # Configuration Card
        config_card = tk.LabelFrame(
            main_frame,
            text=" Pengaturan & Kebijakan ",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.text_primary,
            bd=1,
            relief="solid",
            padx=14,
            pady=10
        )
        config_card.pack(fill="x", pady=(0, 12))

        # Vision checkbox
        self.vision_var = tk.BooleanVar(value=self.config.get("vision_verification_enabled", True))
        chk_vision = tk.Checkbutton(
            config_card,
            text="Aktifkan Verifikasi Kamera (Wajah: Tetap Nyala | Lambaian: Shutdown)",
            variable=self.vision_var,
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.text_primary,
            selectcolor="#27272a",
            activebackground=self.card_bg,
            activeforeground="#ffffff"
        )
        chk_vision.pack(anchor="w", pady=(2, 6))

        # Timeouts row
        row_params = tk.Frame(config_card, bg=self.card_bg)
        row_params.pack(fill="x", pady=4)

        tk.Label(row_params, text="Batas Idle (Menit):", font=("Segoe UI", 9), bg=self.card_bg, fg=self.text_secondary).grid(row=0, column=0, sticky="w", pady=4)
        self.idle_minutes_var = tk.StringVar(value=str(self.config.get("idle_threshold_seconds", 600) // 60))
        entry_idle = tk.Entry(row_params, textvariable=self.idle_minutes_var, width=6, bg="#27272a", fg="#ffffff", insertbackground="#ffffff", bd=1)
        entry_idle.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        tk.Label(row_params, text="Countdown Shutdown (Detik):", font=("Segoe UI", 9), bg=self.card_bg, fg=self.text_secondary).grid(row=0, column=2, sticky="w", padx=(16, 4), pady=4)
        self.countdown_sec_var = tk.StringVar(value=str(self.config.get("countdown_seconds", 60)))
        entry_cd = tk.Entry(row_params, textvariable=self.countdown_sec_var, width=6, bg="#27272a", fg="#ffffff", insertbackground="#ffffff", bd=1)
        entry_cd.grid(row=0, column=3, sticky="w", padx=8, pady=4)

        # Startup and Sound options
        row_opts = tk.Frame(config_card, bg=self.card_bg)
        row_opts.pack(fill="x", pady=4)

        self.sound_var = tk.BooleanVar(value=self.config.get("sound_alert_enabled", True))
        chk_sound = tk.Checkbutton(
            row_opts,
            text="Suara Peringatan (Chime)",
            variable=self.sound_var,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.text_secondary,
            selectcolor="#27272a",
            activebackground=self.card_bg,
            activeforeground="#ffffff"
        )
        chk_sound.pack(side="left")

        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        def on_toggle_startup():
            set_startup(self.startup_var.get())
        chk_startup = tk.Checkbutton(
            row_opts,
            text="Auto-Start saat Windows Login",
            variable=self.startup_var,
            command=on_toggle_startup,
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.text_secondary,
            selectcolor="#27272a",
            activebackground=self.card_bg,
            activeforeground="#ffffff"
        )
        chk_startup.pack(side="left", padx=16)

        btn_save = tk.Button(
            config_card,
            text="Simpan Konfigurasi",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_blue,
            fg="#ffffff",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.save_config
        )
        btn_save.pack(anchor="e", pady=(6, 2))

        # Live Log Card
        log_card = tk.LabelFrame(
            main_frame,
            text=" Live Log urWatchdog ",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_bg,
            fg=self.text_primary,
            bd=1,
            relief="solid",
            padx=10,
            pady=8
        )
        log_card.pack(fill="both", expand=True)

        self.txt_log = tk.Text(
            log_card,
            bg="#09090b",
            fg="#a1a1aa",
            font=("Consolas", 8),
            bd=0,
            height=12,
            wrap="word"
        )
        self.txt_log.pack(fill="both", expand=True)

        log_actions = tk.Frame(log_card, bg=self.card_bg)
        log_actions.pack(fill="x", pady=(6, 0))

        tk.Button(
            log_actions,
            text="Refresh Log",
            font=("Segoe UI", 8),
            bg="#27272a",
            fg=self.text_primary,
            bd=0,
            padx=8,
            pady=2,
            command=self.refresh_log
        ).pack(side="right")

    def refresh_status(self):
        proc = get_daemon_process()
        if proc:
            self.lbl_status.config(text=f"AKTIF (PID: {proc.pid})", fg=self.accent_green)
            self.btn_start.config(state="disabled", bg="#27272a")
            self.btn_stop.config(state="normal", bg=self.accent_red)
        else:
            self.lbl_status.config(text="NONAKTIF (STOPPED)", fg="#eab308")
            self.btn_start.config(state="normal", bg=self.accent_green)
            self.btn_stop.config(state="disabled", bg="#27272a")

    def refresh_log(self):
        if os.path.exists(LOG_PATH):
            try:
                with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                self.txt_log.delete("1.0", tk.END)
                for line in lines[-40:]:
                    self.txt_log.insert(tk.END, line)
                self.txt_log.see(tk.END)
            except Exception:
                pass

    def start_daemon(self):
        proc = get_daemon_process()
        if not proc:
            subprocess.Popen([PYTHONW_EXE, DAEMON_PY], cwd=BASE_DIR)
            time.sleep(1)
        self.refresh_status()
        self.refresh_log()

    def stop_daemon(self):
        proc = get_daemon_process()
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        time.sleep(0.5)
        self.refresh_status()
        self.refresh_log()

    def run_simulation(self):
        subprocess.Popen([PYTHON_EXE, os.path.join(BASE_DIR, "test_simulation.py")], cwd=BASE_DIR)

    def update_loop(self):
        self.refresh_status()
        self.root.after(3000, self.update_loop)

def main():
    root = tk.Tk()
    app = UrWatchdogApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
