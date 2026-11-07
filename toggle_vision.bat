@echo off
set PYTHON_EXE=C:\Users\deoim\miniconda3\envs\yolo11-ablation\python.exe
set SCRIPT_DIR=%~dp0
"%PYTHON_EXE%" "%SCRIPT_DIR%toggle_vision.py"
pause
