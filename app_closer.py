import ctypes
import os
import time

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
# Explicit pointer-sized HWND signatures avoid truncation on 64-bit Windows.
from ctypes import wintypes
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]

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

def close_all_user_apps(wait_seconds: int = 20, logger=None, windows=None, api=None):
    """Sequential WM_CLOSE; abort on refusal/unsaved prompt. Never kill processes."""
    api = api or user32
    windows = get_running_user_windows() if windows is None else windows
    for hwnd, title in windows:
        if title.startswith('urWatchdog'): continue
        if not api.IsWindow(hwnd): continue
        if logger: logger(f'Closing application: {title[:80]}')
        if not api.PostMessageW(hwnd, 0x0010, 0, 0):
            if logger: logger('WM_CLOSE refused; shutdown aborted')
            return False
        deadline = time.monotonic() + wait_seconds
        while api.IsWindow(hwnd):
            if time.monotonic() >= deadline:
                if logger: logger('Window still open (possibly unsaved work); shutdown aborted')
                return False
            time.sleep(.1)
    # A save prompt may survive after its original window disappears.
    if api is user32:
        remaining = [(h,t) for h,t in get_running_user_windows() if not t.startswith('urWatchdog')]
        if remaining:
            if logger: logger('New or remaining application windows; shutdown aborted')
            return False
    return True

def execute_shutdown(force: bool = False, logger=None):
    """Normal Windows shutdown only; the force argument cannot enable /f."""
    import subprocess
    if force: raise ValueError('Forced shutdown is forbidden')
    if logger: logger('Requesting normal Windows shutdown (no /f)')
    subprocess.run(['shutdown.exe', '/s', '/t', '0'], check=True)

if __name__ == "__main__":
    print("Detected user windows:")
    for hwnd, title in get_running_user_windows():
        print(f" - [0x{hwnd:x}] {title}")
