import ctypes
import os
import time

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

# System and background windows to ignore
IGNORED_WINDOW_TITLES = {
    "", "Program Manager", "Windows Input Experience", "Taskbar",
    "Settings", "Setup", "Default IME", "MSCTFIME UI"
}

IGNORED_WINDOW_CLASSES = {
    "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW",
    "Windows.UI.Core.CoreWindow", "ApplicationFrameWindow"
}

def get_window_title(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def get_window_class(hwnd) -> str:
    buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buff, 256)
    return buff.value

def is_user_window(hwnd) -> bool:
    if not user32.IsWindowVisible(hwnd):
        return False

    title = get_window_title(hwnd)
    if not title or title in IGNORED_WINDOW_TITLES:
        return False

    cls_name = get_window_class(hwnd)
    if cls_name in IGNORED_WINDOW_CLASSES:
        return False

    style = user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE
    WS_VISIBLE = 0x10000000
    WS_CHILD = 0x40000000
    if not (style & WS_VISIBLE) or (style & WS_CHILD):
        return False

    # Skip invisible / zero-sized windows
    rect = (ctypes.c_long * 4)()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    if w <= 10 or h <= 10:
        return False

    return True

def get_running_user_windows():
    windows = []
    def enum_cb(hwnd, lparam):
        if is_user_window(hwnd):
            windows.append((hwnd, get_window_title(hwnd)))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return windows

def close_all_user_apps(wait_seconds: int = 3, logger=None):
    """
    Sends WM_CLOSE (0x0010) to all visible user windows, then waits.
    """
    windows = get_running_user_windows()
    if logger:
        logger(f"Closing {len(windows)} user applications...")

    WM_CLOSE = 0x0010
    for hwnd, title in windows:
        try:
            if logger:
                logger(f"  Sending WM_CLOSE -> '{title[:40]}'")
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        except Exception as e:
            if logger:
                logger(f"  Failed closing {title}: {e}")

    time.sleep(wait_seconds)

def execute_shutdown(force: bool = True, logger=None):
    """
    Initiates standard Windows shutdown.
    """
    if logger:
        logger("Triggering Windows shutdown...")
    cmd = "shutdown.exe /s /t 0" + (" /f" if force else "")
    os.system(cmd)

if __name__ == "__main__":
    print("Detected user windows:")
    for hwnd, title in get_running_user_windows():
        print(f" - [0x{hwnd:x}] {title}")
