@echo off
set PYTHON_EXE=C:\Users\deoim\miniconda3\envs\yolo11-ablation\pythonw.exe
set SCRIPT_DIR=%~dp0

echo Menjalankan urWatchdog Daemon di background...
start "" "%PYTHON_EXE%" "%SCRIPT_DIR%daemon.py"

ping 127.0.0.1 -n 2 >nul
echo Selesai. urWatchdog aktif memantau aktivitas laptop.
echo Gunakan status_daemon.bat untuk mengecek log dan status.
pause
