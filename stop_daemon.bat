@echo off
set PYTHON_EXE=C:\Users\deoim\miniconda3\envs\yolo11-ablation\python.exe
set SCRIPT_DIR=%~dp0
echo Menghentikan SleepGuard Daemon...
"%PYTHON_EXE%" "%SCRIPT_DIR%stop_daemon.py"
pause
