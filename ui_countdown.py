import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk
import winsound
import ctypes

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('dwTime', ctypes.c_uint)
    ]

def get_idle_seconds() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        raise ctypes.WinError()
    millis = (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
    return millis / 1000.0

def show_countdown_dialog(
    countdown_seconds: int = 60,
    config_path: str = "config.json",
    sound_alert: bool = True,
    title_text: str = "Tidak Ada Aktivitas Terdeteksi",
    subtitle_text: str = "Laptop akan otomatis menutup aplikasi & shutdown dalam:",
    icon_text: str = "💤",
    require_explicit_confirmation: bool = False,
    abort_check=lambda: False, progress=lambda remaining: None, idle_provider=get_idle_seconds
) -> str:
    """
    Shows a fullscreen-dim or centered topmost dark-mode dialog.
    Returns: 'shutdown' or 'cancelled'.
    """
    # Load config to get vision_enabled state
    vision_enabled = True
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                vision_enabled = cfg.get("vision_verification_enabled", True)
        except Exception:
            pass

    result = {"action": "cancelled"}
    initial_idle_time = idle_provider()
    opened_at = time.monotonic()

    root = tk.Tk()
    root.title("urWatchdog - Konfirmasi Shutdown")
    root.configure(bg="#18181b")  # Modern dark background
    root.attributes("-topmost", True)
    root.resizable(False, False)

    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "urwatchdog.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass

    # Window geometry centered
    width, height = 480, 360
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Remove title bar standard or keep borderless
    root.overrideredirect(True)

    # Frame border for stylish look
    border_frame = tk.Frame(root, bg="#3f3f46", bd=2)
    border_frame.pack(fill="both", expand=True, padx=2, pady=2)

    inner_frame = tk.Frame(border_frame, bg="#18181b")
    inner_frame.pack(fill="both", expand=True, padx=16, pady=16)

    # Header icon & title
    lbl_icon = tk.Label(inner_frame, text=icon_text, font=("Segoe UI Emoji", 32), bg="#18181b", fg="#fbbf24")
    lbl_icon.pack(pady=(4, 0))

    lbl_title = tk.Label(
        inner_frame,
        text=title_text,
        font=("Segoe UI", 16, "bold"),
        bg="#18181b",
        fg="#f4f4f5"
    )
    lbl_title.pack(pady=(4, 2))

    lbl_sub = tk.Label(
        inner_frame,
        text=subtitle_text,
        font=("Segoe UI", 10),
        bg="#18181b",
        fg="#a1a1aa"
    )
    lbl_sub.pack()

    # Countdown digits
    countdown_var = tk.StringVar(value=str(countdown_seconds))
    lbl_timer = tk.Label(
        inner_frame,
        textvariable=countdown_var,
        font=("Segoe UI", 44, "bold"),
        bg="#18181b",
        fg="#ef4444"
    )
    lbl_timer.pack(pady=4)

    # Info hint
    lbl_hint = tk.Label(
        inner_frame,
        text="Gerakkan mouse atau tekan tombol apa saja untuk membatalkan",
        font=("Segoe UI", 9, "italic"),
        bg="#18181b",
        fg="#71717a"
    )
    lbl_hint.pack(pady=(0, 10))

    # Vision Checkbox toggle
    vision_var = tk.BooleanVar(value=vision_enabled)
    def on_toggle_vision():
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["vision_verification_enabled"] = vision_var.get()
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
        except Exception:
            pass

    chk_vision = tk.Checkbutton(
        inner_frame,
        text="Gunakan verifikasi kamera (Face & Gesture)",
        variable=vision_var,
        command=on_toggle_vision,
        bg="#18181b",
        fg="#d4d4d8",
        selectcolor="#27272a",
        activebackground="#18181b",
        activeforeground="#ffffff",
        font=("Segoe UI", 9)
    )
    # Camera consent is managed only from the control panel.

    # Action buttons
    btn_frame = tk.Frame(inner_frame, bg="#18181b")
    btn_frame.pack(fill="x", pady=4)

    def cancel_action(event=None):
        result["action"] = "cancelled"
        root.destroy()

    def confirm_shutdown():
        result["action"] = "shutdown"
        root.destroy()

    btn_cancel = tk.Button(
        btn_frame,
        text="Tetap Nyala (Batal)",
        font=("Segoe UI", 11, "bold"),
        bg="#2563eb",
        fg="#ffffff",
        activebackground="#1d4ed8",
        activeforeground="#ffffff",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
        command=cancel_action
    )
    btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 6))

    btn_shutdown = tk.Button(
        btn_frame,
        text="Shutdown Sekarang",
        font=("Segoe UI", 11, "bold"),
        bg="#dc2626",
        fg="#ffffff",
        activebackground="#b91c1c",
        activeforeground="#ffffff",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
        command=confirm_shutdown
    )
    btn_shutdown.pack(side="right", expand=True, fill="x", padx=(6, 0))

    # Cancel on user input anywhere in dialog
    root.bind("<Key>", cancel_action)
    root.bind("<Button-1>", lambda e: None)  # Handled by buttons

    # Countdown loop
    time_left = [countdown_seconds]

    def play_chime():
        if sound_alert:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    play_chime()

    def tick():
        # Check if user interacted with Windows globally
        current_idle = idle_provider()
        if abort_check() or current_idle + 0.15 < initial_idle_time + time.monotonic() - opened_at:
            result["action"] = "cancelled"
            root.destroy()
            return

        import math
        time_left[0] = max(0, math.ceil(countdown_seconds - (time.monotonic()-opened_at)))
        progress(time_left[0])
        countdown_var.set(str(time_left[0]))

        # Alert beep every 20 seconds
        if time_left[0] > 0 and time_left[0] % 20 == 0:
            play_chime()

        if time_left[0] <= 0:
            result["action"] = "cancelled" if require_explicit_confirmation else "shutdown"
            root.destroy()
            return

        root.after(200, tick)

    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.after(200, tick)
    root.mainloop()

    return result["action"]

if __name__ == "__main__":
    action = show_countdown_dialog(countdown_seconds=10)
    print("Dialog result:", action)
