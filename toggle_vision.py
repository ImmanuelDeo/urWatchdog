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

    current = cfg.get("vision_verification_enabled", True)
    new_val = not current
    cfg["vision_verification_enabled"] = new_val

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    status_str = "AKTIF (ON)" if new_val else "NONAKTIF (OFF)"
    print(f"\n[SleepGuard] Status Verifikasi Kamera: {status_str}\n")

if __name__ == "__main__":
    toggle()
