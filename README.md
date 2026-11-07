# urWatchdog

Autonomous background watchdog daemon for Windows that enforces idle-based power management and graceful application shutdown. Designed for low power consumption (< 15 MB RAM, 0% CPU) with an optional on-demand vision verification stage (face presence vs. hand wave).

---

## Architecture & System State Flow

```
                      [System Boot / Start]
                                │
                                ▼
                    [Daemon Loop (Every 3s)]
                    Query GetLastInputInfo()
             (Mouse, Keyboard, Hardware Fn Keys)
                                │
                    Idle >= Threshold (e.g. 10m)?
                                │
                 ┌──────────────┴──────────────┐
                No                            Yes
                 │                             │
            Sleep 3s                 Camera Enabled in config?
                                               │
                                 ┌─────────────┴─────────────┐
                                Yes                          No
                                 │                           │
                     [Webcam Verification (5s)]              │
                     - Face Detection (Haar)                 │
                     - Hand Wave (Oscillation)               │
                                 │                           │
          ┌──────────────────────┼─────────────────────┐     │
          │                      │                     │     │
          ▼ (Face Detected)      ▼ (Wave Detected)     │     │
     [Keep Awake]           [Fast Shutdown]            │     │
   User is reading/       User intentionally           │     │
   watching screen.       waved at camera.             │     │
   Postpone 5 minutes.    Show 15s confirmation.       │     │
   Camera turns off.             │                     │     │
                                 │                     ▼ (None)
                                 │           [Inactivity Countdown]
                                 │           Show 60s warning dialog
                                 │           Sound chime alert
                                 │           Cancel on mouse/key
                                 │                     │
                                 └──────────┬──────────┘
                                            │
                                  Timeout / Confirmed
                                            │
                                            ▼
                              [Graceful App Closer]
                           Send WM_CLOSE (0x0010) to
                          all visible user window handles
                                            │
                                  Wait 3s for autosave
                                            │
                                            ▼
                               [Windows Shutdown Execution]
                                 shutdown.exe /s /t 0 /f
```

---

## Core Mechanisms

### 1. Zero-Overhead Inactivity Monitoring
Rather than polling hooks or continuously consuming system power, urWatchdog queries Windows Native API `GetLastInputInfo` from `user32.dll`. This API tracks any user hardware interaction—mouse movement, clicks, keyboard events, and hardware multimedia/brightness keys—with zero measurable CPU footprint.

### 2. On-Demand Vision Verification (Two-Tier Hybrid)
The camera is kept completely offline during standard operation. Only when the 10-minute idle threshold is crossed does the daemon open the webcam for up to 5 seconds:
- **Face Presence (`FACE_KEEP_AWAKE`)**: Evaluated via OpenCV Haar cascade (`haarcascade_frontalface_default.xml`). If the user is quietly reading or watching a video, the shutdown is aborted and deferred by 5 minutes.
- **Hand Wave Gesture (`WAVE_SHUTDOWN`)**: Evaluated via optical difference tracking across frames. Rhythmic lateral motion (directional oscillation count >= 2 outside the face boundary) indicates an intentional wave to shut down, immediately opening a 15-second fast countdown.
- **Empty / Inactive (`NONE`)**: If neither is detected (room dark, user asleep or away), the standard 60-second inactivity countdown begins.
- The camera handle is released immediately once a decision is reached so the hardware LED turns off.

### 3. Graceful Application Termination
Before triggering Windows shutdown, the daemon enumerates top-level visible application windows (`EnumWindows`), filters out system processes, and dispatches `WM_CLOSE` messages. This allows text editors, IDEs, and browsers to flush caches and prompt or auto-save work before power off.

---

## Directory Structure

```
D:\urWatchdog\
├── app_closer.py          # Window enumeration and WM_CLOSE dispatcher
├── config.json            # Main configuration parameters
├── control_panel.py       # One-gate graphical management interface
├── daemon.log             # Operational event log
├── daemon.py              # Single-instance core daemon loop
├── manage_startup.py      # Windows Startup & Start Menu shortcut installer
├── open_control_panel.bat # Launcher for GUI control panel
├── run_silent.vbs         # Background VBS launcher for headless execution
├── start_daemon.bat       # Starts daemon in background via pythonw
├── status_daemon.bat      # CLI status reporter
├── status_daemon.py       # Process inspector
├── stop_daemon.bat        # CLI stop trigger
├── stop_daemon.py         # Graceful process terminator
├── test_simulation.py     # Non-destructive test script
├── toggle_vision.bat      # Instant vision toggle
├── toggle_vision.py       # Vision configuration switcher
├── ui_countdown.py        # Topmost dark-mode warning dialog
└── vision_check.py        # OpenCV face and gesture analysis module
```

---

## Configuration Reference (`config.json`)

```json
{
  "idle_threshold_seconds": 600,
  "countdown_seconds": 60,
  "check_interval_seconds": 3,
  "vision_verification_enabled": true,
  "vision_check_duration_seconds": 5,
  "prevent_shutdown_if_audio_playing": false,
  "postpone_after_presence_seconds": 300,
  "graceful_close_wait_seconds": 3,
  "force_shutdown_after_close": true,
  "sound_alert_enabled": true,
  "debug_mode": false
}
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `idle_threshold_seconds` | int | 600 | Inactivity threshold before initiating verification (10 minutes) |
| `countdown_seconds` | int | 60 | Dialog countdown duration for standard inactivity |
| `check_interval_seconds` | int | 3 | Daemon polling sleep interval |
| `vision_verification_enabled` | bool | true | Enables on-demand webcam presence/gesture check |
| `vision_check_duration_seconds` | int | 5 | Maximum camera window duration |
| `postpone_after_presence_seconds` | int | 300 | Deferral window if face is detected (5 minutes) |
| `graceful_close_wait_seconds` | int | 3 | Delay after sending `WM_CLOSE` before initiating shutdown |
| `force_shutdown_after_close` | bool | true | Enforces `/f` on final shutdown command |
| `sound_alert_enabled` | bool | true | Triggers Windows warning chime during countdown |

---

## Usage

### 1. One-Gate Control Panel
Open Start Menu and search `urWatchdog Control Panel`, or execute:
```cmd
open_control_panel.bat
```
The Control Panel allows starting/stopping the daemon, toggling camera verification, adjusting idle timeouts, toggling Windows startup, and viewing live logs.

### 2. Command Line Operations
- Start daemon in background: `start_daemon.bat`
- Stop daemon: `stop_daemon.bat`
- Check runtime status: `status_daemon.bat`
- Toggle camera verification: `toggle_vision.bat`
- Safe test run without shutdown: `python test_simulation.py`

### 3. Windows Search Integration
Run `manage_startup.py` once to register shortcuts in `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\urWatchdog`. Afterwards, `urWatchdog` can be launched directly from Windows Search / Start Menu.
