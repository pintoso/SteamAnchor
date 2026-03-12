@echo off

if exist "build_venv" rd /s /q "build_venv"
python -m venv build_venv
call build_venv\Scripts\activate

python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller zstandard imageio >nul 2>&1

python build.py
if errorlevel 1 (
    call build_venv\Scripts\deactivate
    pause
    exit /b 1
)

call build_venv\Scripts\deactivate
rd /s /q "build_venv"
pause