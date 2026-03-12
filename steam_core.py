import os
import subprocess
import time
import winreg


def get_steam_paths() -> tuple[str, str]:
    """Returns (steam_dir, steam_exe) from the Windows Registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam") as key:
            steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
            steam_exe = winreg.QueryValueEx(key, "SteamExe")[0]
            return os.path.normpath(steam_path), os.path.normpath(steam_exe)
    except FileNotFoundError:
        raise RuntimeError("Steam was not found in the Windows Registry.")


def kill_steam_process() -> None:
    """Forcefully terminates Steam without showing a console window."""
    subprocess.run(
        ["taskkill", "/f", "/im", "steam.exe"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    time.sleep(2)  # let the OS release file handles


def execute_downgrade(steam_exe: str, wayback_date: str) -> None:
    """Launches Steam with flags that force a specific build download."""
    manifest_url = (
        f"http://web.archive.org/web/{wayback_date}if_/media.steampowered.com/client"
    )
    process = subprocess.Popen(
        [
            steam_exe,
            "-forcesteamupdate",
            "-forcepackagedownload",
            f"-overridepackageurl", manifest_url,
            "-exitsteam",
            "-clearbeta",
        ],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    process.wait()
    time.sleep(3)  # safety delay after Steam exits


# Lines written to steam.cfg to prevent automatic updates
_BLOCK_LINES = {
    "BootStrapperInhibitAll=enable",
    "BootStrapperForceSelfUpdate=disable",
}


def _cfg_path(steam_path: str) -> str:
    return os.path.join(steam_path, "steam.cfg")


def apply_block_update(steam_path: str) -> None:
    """Appends missing update-blocking lines to steam.cfg."""
    path = _cfg_path(steam_path)
    existing_lines: list[str] = []
    existing_set: set[str] = set()

    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing_lines = f.readlines()
            existing_set = {line.strip() for line in existing_lines}
        except OSError:
            pass

    if _BLOCK_LINES.issubset(existing_set):
        return

    missing = _BLOCK_LINES - existing_set
    with open(path, "a", encoding="utf-8") as f:
        if existing_lines and not existing_lines[-1].endswith("\n"):
            f.write("\n")
        for line in sorted(missing):
            f.write(line + "\n")


def remove_block_update(steam_path: str) -> None:
    """Removes blocking lines from steam.cfg, or deletes the file if nothing else remains."""
    path = _cfg_path(steam_path)
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as f:
        all_lines = f.readlines()

    kept = [line for line in all_lines if line.strip() not in _BLOCK_LINES]

    if not any(line.strip() for line in kept):
        os.remove(path)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(kept)


def is_update_blocked(steam_path: str) -> bool:
    """Checks whether steam.cfg contains any update-blocking lines."""
    path = _cfg_path(steam_path)
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            content = {line.strip() for line in f}
        return bool(content & _BLOCK_LINES)
    except OSError:
        return False
