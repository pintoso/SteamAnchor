@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Steam Anchor - Nuitka Build
echo ============================================
echo.

:: 1. Create and activate a clean virtual environment to avoid trash in the .exe
echo [*] Creating clean virtual environment...
if exist "build_venv" rd /s /q "build_venv"
python -m venv build_venv
call build_venv\Scripts\activate

:: 2. Install Nuitka in the clean environment
echo [*] Installing Nuitka...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install nuitka zstandard imageio >nul 2>&1

:: 3. UPX Handling
echo [*] Checking for UPX...
where upx.exe >nul 2>&1
if not errorlevel 1 (
    echo [*] UPX found in PATH.
    set UPX_CMD=--enable-plugin=upx --upx-binary="upx.exe"
) else (
    if not exist "upx.exe" (
        echo [*] UPX not found. Downloading UPX 5.1.1...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v5.1.1/upx-5.1.1-win64.zip' -OutFile 'upx.zip'; Expand-Archive -Path 'upx.zip' -DestinationPath 'upx_temp' -Force; Copy-Item 'upx_temp\upx-4.2.2-win64\upx.exe' -Destination '.'; Remove-Item 'upx.zip'; Remove-Item 'upx_temp' -Recurse -Force" >nul 2>&1
        if exist "upx.exe" (
            echo [*] UPX successfully downloaded.
            set UPX_CMD=--enable-plugin=upx --upx-binary="upx.exe"
        ) else (
            echo [!] Failed to download UPX. Compression will be skipped.
            set UPX_CMD=
        )
    ) else (
        echo [*] UPX found in project root.
        set UPX_CMD=--enable-plugin=upx --upx-binary="upx.exe"
    )
)

:build
echo.
echo [*] Compiling Steam Anchor with Nuitka...
echo [*] This will take a few minutes as it translates Python to C/C++.
echo.

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --enable-plugin=tk-inter ^
    --windows-icon-from-ico="assets\icon.ico" ^
    --output-filename="SteamAnchor.exe" ^
    --output-dir="dist" ^
    --include-data-dir="assets=assets" ^
    --remove-output ^
    --lto=yes ^
    --disable-console ^
    --nofollow-import-to=urllib ^
    --nofollow-import-to=ssl ^
    --nofollow-import-to=_ssl ^
    --nofollow-import-to=hashlib ^
    --nofollow-import-to=http ^
    --nofollow-import-to=_socket ^
    --nofollow-import-to=select ^
    --nofollow-import-to=lzma ^
    --nofollow-import-to=pyexpat ^
    --nofollow-import-to=ctypes ^
    --nofollow-import-to=email ^
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