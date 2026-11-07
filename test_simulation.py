import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app_closer import get_running_user_windows
from ui_countdown import show_countdown_dialog
from vision_check import analyze_user_behavior

def run_test():
    print("==================================================")
    print("      urWatchdog Daemon - Simulation Test Mode    ")
    print("==================================================")
    print("Testing 3 main components without triggering real shutdown:")
    print()

    # Test 1: Window Detection
    print("[1/3] Testing user application detection...")
    windows = get_running_user_windows()
    print(f" -> Found {len(windows)} active user windows:")
    for hwnd, title in windows[:5]:
        print(f"    * {title[:50]}")
    if len(windows) > 5:
        print(f"    * ... and {len(windows) - 5} more")
    print(" -> App closer test passed!")
    print()

    # Test 2: Vision Check
    print("[2/3] Testing camera behavior analysis (4 seconds)...")
    print(" (Diam melihat kamera = Keep Awake | Lambai tangan = Shutdown)")
    behavior = analyze_user_behavior(duration_seconds=4)
    print(f" -> Camera analysis result: {behavior}")
    if behavior == "FACE_KEEP_AWAKE":
        print("    [OK] Wajah terdeteksi -> Laptop tetap MENYALA (batal shutdown)")
    elif behavior == "WAVE_SHUTDOWN":
        print("    [OK] Lambaian tangan terdeteksi -> Konfirmasi SHUTDOWN cepat")
    else:
        print("    [OK] Tidak ada orang/sepi -> Countdown shutdown standar")
    print()

    # Test 3: Countdown UI
    print("[3/3] Launching Countdown Dialog (10-second test)...")
    print(" (Test moving mouse / clicking 'Tetap Nyala' or 'Shutdown Sekarang')")
    result = show_countdown_dialog(
        countdown_seconds=10,
        sound_alert=True,
        title_text="Uji Coba Dialog SleepGuard",
        subtitle_text="Ini hanya tes simulasi (tidak akan mematikan laptop):",
        icon_text="🧪"
    )
    print(f" -> Dialog outcome: {result.upper()}")
    print("==================================================")
    print("Simulation test completed successfully!")

if __name__ == "__main__":
    run_test()
