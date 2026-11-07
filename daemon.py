import ctypes
import json
import logging
import os
import sys
import time

# Ensure local imports work regardless of CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app_closer import close_all_user_apps, execute_shutdown
from ui_countdown import get_idle_seconds, show_countdown_dialog
from vision_check import analyze_user_behavior

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "daemon.log")

# Setup logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("urWatchdog")

def log(msg: str):
    print(msg)
    logger.info(msg)

def load_config() -> dict:
    default_config = {
        "idle_threshold_seconds": 600,
        "countdown_seconds": 60,
        "check_interval_seconds": 3,
        "vision_verification_enabled": True,
        "vision_check_duration_seconds": 5,
        "prevent_shutdown_if_audio_playing": False,
        "postpone_after_presence_seconds": 300,
        "graceful_close_wait_seconds": 3,
        "force_shutdown_after_close": True,
        "sound_alert_enabled": True,
        "debug_mode": False
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception as e:
            logger.error(f"Failed loading config: {e}")
    return default_config

def acquire_single_instance_lock():
    """
    Ensures only one instance of urWatchdog daemon runs at a time.
    """
    kernel32 = ctypes.windll.kernel32
    mutex_name = "Global\\urWatchdogDaemonMutex_Deo"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        log("Another instance of urWatchdog is already running. Exiting.")
        sys.exit(0)
    return mutex

def run_daemon():
    mutex = acquire_single_instance_lock()
    log("urWatchdog Daemon started successfully.")

    # Track presence cooldown
    presence_postpone_until = 0

    while True:
        try:
            cfg = load_config()
            interval = cfg.get("check_interval_seconds", 3)
            time.sleep(interval)

            now = time.time()
            if now < presence_postpone_until:
                continue

            idle_sec = get_idle_seconds()
            threshold = cfg.get("idle_threshold_seconds", 600)

            if cfg.get("debug_mode", False):
                log(f"Idle: {idle_sec:.1f}s / {threshold}s")

            if idle_sec >= threshold:
                log(f"Idle threshold reached ({idle_sec:.1f}s >= {threshold}s).")

                # Step 1: Vision check (if enabled)
                vision_enabled = cfg.get("vision_verification_enabled", True)
                behavior = "NONE"

                if vision_enabled:
                    duration = cfg.get("vision_check_duration_seconds", 5)
                    log(f"Initiating camera behavior check for {duration} seconds (Face: keep-on / Wave: shutdown)...")
                    behavior = analyze_user_behavior(duration)
                    log(f"Camera analysis outcome: {behavior}")

                    if behavior == "FACE_KEEP_AWAKE":
                        postpone_sec = cfg.get("postpone_after_presence_seconds", 300)
                        log(f"Face detected! User is awake watching/reading screen. Postponing shutdown for {postpone_sec}s.")
                        presence_postpone_until = time.time() + postpone_sec
                        continue

                # Step 2: Show Countdown Dialog based on behavior
                sound_alert = cfg.get("sound_alert_enabled", True)

                if behavior == "WAVE_SHUTDOWN":
                    # Wave detected: fast confirmation countdown (15s)
                    log("Hand wave detected! User requested shutdown. Displaying quick confirmation dialog...")
                    action = show_countdown_dialog(
                        countdown_seconds=15,
                        config_path=CONFIG_PATH,
                        sound_alert=sound_alert,
                        title_text="Lambaian Tangan Terdeteksi",
                        subtitle_text="Sinyal shutdown dikonfirmasi! Menutup aplikasi & mati dalam:",
                        icon_text="👋"
                    )
                else:
                    # Inactivity (NONE or vision disabled): standard countdown (60s)
                    countdown_sec = cfg.get("countdown_seconds", 60)
                    log(f"Displaying {countdown_sec}s inactivity countdown dialog...")
                    action = show_countdown_dialog(
                        countdown_seconds=countdown_sec,
                        config_path=CONFIG_PATH,
                        sound_alert=sound_alert,
                        title_text="Tidak Ada Aktivitas Terdeteksi",
                        subtitle_text="Laptop idle selama 10 menit. Sistem akan menutup aplikasi & shutdown dalam:",
                        icon_text="💤"
                    )

                if action == "shutdown":
                    log("Shutdown confirmed. Closing user applications...")
                    wait_sec = cfg.get("graceful_close_wait_seconds", 3)
                    close_all_user_apps(wait_seconds=wait_sec, logger=log)

                    force = cfg.get("force_shutdown_after_close", True)
                    execute_shutdown(force=force, logger=log)
                    break
                else:
                    log("Shutdown cancelled by user interaction. Resuming idle monitoring.")
                    # Give a small 5-second buffer after cancel
                    time.sleep(5)

        except KeyboardInterrupt:
            log("SleepGuard Daemon stopped by user.")
            break
        except Exception as e:
            logger.exception(f"Unexpected error in daemon loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_daemon()
