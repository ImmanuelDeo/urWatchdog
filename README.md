# urWatchdog

Windows idle shutdown monitor with optional explicitly enabled continuous Camera Watch. Existing `control_panel.py`, Start Menu shortcuts and batch launchers remain valid. The PySide6 Acrylic panel now lives in the system tray; closing its window hides it, not the daemon.

## Use
1. Open `open_control_panel.bat`. Set **Batas idle** in minutes (1–1440), **Hitung mundur** in seconds (1–3600), then **Simpan pengaturan**.
2. **Nyalakan** starts independent Windows idle monitoring. At the threshold it always opens the cancellable countdown, regardless of camera presence/errors. Current saved values: 10 minutes / 30 seconds; the reported 1-minute value was not present in the actual config inspected.
3. Enable **Camera Watch** only when wanted. The toggle saves immediately, starts the daemon if needed, and opens the camera without waiting for idle. OFF releases it. Legacy `vision_verification_enabled=true` does NOT migrate to continuous consent; the new key defaults false.
4. Close the panel to hide to tray. Tray actions: show, start/stop daemon, camera toggle, pause 15 minutes, resume, exit panel only, or stop service and exit. A daemon started via existing shortcuts also starts the tray UI. Reopening the shortcut restores the existing single-instance panel.
5. Mouse/keyboard input cancels a countdown. Stop/pause also cancels it; camera OFF cancels camera-origin countdowns. Countdown timeout authorizes normal shutdown, not instant shutdown on a blink.

## Runtime
`daemon.py` launches `daemon_runtime.py`. Idle uses session-local `GetLastInputInfo` with DWORD rollover-safe subtraction. No face-present postponement or camera error can suppress primary idle. Monitor telemetry in `runtime_status.json` includes mode, seconds idle, threshold, reason, remaining countdown, camera data and errors. Logs rotate at 512 KB with two backups. After cancellation/refusal there is a cooldown of at least one idle threshold (minimum 60 seconds).

`vision_worker.py` launches isolated `camera_runtime.py` using `.vision-venv`. MediaPipe Hands requires an open palm and two meaningful horizontal reversals. Face Mesh uses aspect-corrected eye aspect ratio (EAR < .20 for 3 seconds), relative nose/cheek geometry for head turning (3 seconds), and sustained missing face (5 seconds). `face_signals.py` debounces ordinary blinks and latches each sustained condition. Profile faces may become FACE_AWAY. These are heuristic landmarks, not segmentation, identity recognition, or a diagnosis of sleep. Landmarks suit eyelids/orientation; accuracy varies with glasses, lighting, pose and individual anatomy. Hardware recognition of deliberate closed eyes/head turns/waves still requires personal preview validation.

Camera defaults to OFF, max 10 FPS, no frames/video saved. A named mutex prevents preview and daemon from owning it together. Stop requests release normally, with a bounded kill fallback for a stuck worker. A failed/stalled worker reports an error and retries after 30 seconds; idle continues. Safe preview runs eight seconds and cannot shut down. Camera and idle use the same configured countdown duration.

`app_closer.py` sends WM_CLOSE to visible application windows sequentially, waits up to `graceful_close_wait_seconds` (20 default) for each, and aborts if any refuses or an unsaved/new window remains. It does not save files or promise all apps are covered. Only after success is `shutdown.exe /s /t 0` requested; `/f` is forbidden. Windows/app prompts may still block shutdown. Never rely on this as a backup for unsaved work.

## Environment and tests
- Runtime: `C:/Users/deoim/miniconda3/envs/yolo11-ablation/python.exe`
- UI dependencies: `.ui-deps`, `requirements-ui.txt`; camera: `.vision-venv`, `requirements-vision.txt`.
- `python -m unittest test_runtime test_gesture -v`: 11 passing tests, including a real daemon child waiting 60 real seconds using an explicitly injected idle clock, a real countdown, and a dry-run executor with zero apps closed. Physical input was active; this is not evidence of 60 seconds actual user inactivity.
- `python test_glass_panel.py`: real Qt controls, validation, tray hide/restore, fake service mutations, unchanged real config/PID; passed. Widget-rendered screenshot `.ui-validation/panel.png` is readable. Desktop screen capture was obscured by other foreground apps, so countdown visual evidence is limited; real Tk dialog creation and result were exercised.
- `python test_live_camera.py`: real daemon child, temporary config opt-in before idle, actual camera Face Mesh frames, OFF release, no shutdown; passed.
- Synthetic gesture/eye/turn/away tests are distinguished from actual inference: actual face landmarks were observed, not a deliberate human wave/closed-eye test.

## Diagnosis
Actual config was 600 seconds, not 60. Old code ran camera only after idle and suppressed countdown for five minutes on either face presence or camera error. Therefore face-visible users could postpone indefinitely. Current tick sample was positive; signed tick overflow was a latent bug fixed, not established as the incident cause. OEM media/Fn keys and separate Windows sessions are not guaranteed to share LASTINPUTINFO; run in the interactive user's session, not Session 0.

No real shutdown or application closing was performed during verification. No commit/push requested or performed.
