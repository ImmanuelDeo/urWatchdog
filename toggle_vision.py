import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def toggle():
    if not os.path.exists(CONFIG_PATH):
        print("config.json tidak ditemukan.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    current = cfg.get("continuous_camera_enabled", False)
    new_val = not current
    cfg["continuous_camera_enabled"] = new_val

    from runtime_config import atomic_json
    atomic_json(CONFIG_PATH,cfg)
    if new_val:
        from glass_panel import Backend
        Backend().start()

    status_str = "AKTIF (ON)" if new_val else "NONAKTIF (OFF)"
    print(f"\n[SleepGuard] Status Verifikasi Kamera: {status_str}\n")

if __name__ == "__main__":
    toggle()
