@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Steam Anchor - PyInstaller Build
echo ============================================
echo.

:: 1. Create and activate a clean virtual environment to avoid trash in the .exe
echo [*] Creating clean virtual environment...
if exist "build_venv" rd /s /q "build_venv"
python -m venv build_venv
call build_venv\Scripts\activate

:: 2. Install PyInstaller in the clean environment
echo [*] Installing PyInstaller and dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller zstandard imageio >nul 2>&1

:: 3. UPX Handling
echo [*] Checking for UPX...
where upx.exe >nul 2>&1
if not errorlevel 1 (
    echo [*] UPX found in PATH.
    set UPX_CMD=
) else (
    if not exist "upx.exe" (
        echo [*] UPX not found. Downloading UPX 5.1.1...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v5.1.1/upx-5.1.1-win64.zip' -OutFile 'upx.zip'; Expand-Archive -Path 'upx.zip' -DestinationPath 'upx_temp' -Force; Copy-Item 'upx_temp\upx-5.1.1-win64\upx.exe' -Destination '.'; Remove-Item 'upx.zip'; Remove-Item 'upx_temp' -Recurse -Force" >nul 2>&1
        if exist "upx.exe" (
            echo [*] UPX successfully downloaded.
            set UPX_CMD=--upx-dir="."
        ) else (
            echo [!] Failed to download UPX. Compression will be skipped.
            set UPX_CMD=--noupx
        )
    ) else (
        echo [*] UPX found in project root.
        set UPX_CMD=--upx-dir="."
    )
)

:build
echo.
echo [*] Compiling Steam Anchor with PyInstaller...
echo [*] This will take a few minutes.
echo.

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --version-file="version.txt" ^
    --icon="assets\icon.ico" ^
    --name="SteamAnchor" ^
    --distpath="dist" ^
    --add-data="assets;assets" ^
    !UPX_CMD! ^
    main.py

if errorlevel 1 (
    echo.
    echo [!] Build failed.
    call build_venv\Scripts\deactivate
    pause
    exit /b 1
)

:: 4. Cleanup and finalization
if exist "build" rd /s /q "build"
if exist "SteamAnchor.spec" del /f /q "SteamAnchor.spec"

call build_venv\Scripts\deactivate
rd /s /q "build_venv"

echo.
echo ============================================
if exist "dist\SteamAnchor.exe" (
    echo   Build complete! Output: dist\SteamAnchor.exe
    for %%I in ("dist\SteamAnchor.exe") do set "size=%%~zI"
    set /a "sizeMB=size/1048576"
    echo   Final Size: !sizeMB! MB (!size! bytes)
) else (
    echo   Build complete but could not locate dist\SteamAnchor.exe
)
echo ============================================
pause
