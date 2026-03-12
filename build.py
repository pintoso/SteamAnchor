"""
Steam Anchor build script.
"""
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from api import __version__

ROOT = Path(__file__).parent


def generate_version_file() -> Path:
    t = tuple(int(x) for x in (__version__ + ".0.0.0").split(".")[:4])
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={t},
    prodvers={t},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'PINTOSO'),
        StringStruct(u'FileDescription', u'Steam Anchor'),
        StringStruct(u'FileVersion', u'{__version__}'),
        StringStruct(u'InternalName', u'SteamAnchor'),
        StringStruct(u'LegalCopyright', u'Copyright (c) PINTOSO 2026'),
        StringStruct(u'OriginalFilename', u'SteamAnchor.exe'),
        StringStruct(u'ProductName', u'Steam Anchor'),
        StringStruct(u'ProductVersion', u'{__version__}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    path = ROOT / "version.txt"
    path.write_text(content, encoding="utf-8")
    print(f"[*] version.txt generated for v{__version__}")
    return path


def find_or_download_upx() -> list[str]:
    if shutil.which("upx"):
        print("[*] UPX found in PATH.")
        return []
    if (ROOT / "upx.exe").exists():
        print("[*] UPX found in project root.")
        return [f"--upx-dir={ROOT}"]

    print("[*] UPX not found. Downloading UPX 5.1.1...")
    url = "https://github.com/upx/upx/releases/download/v5.1.1/upx-5.1.1-win64.zip"
    zip_path = ROOT / "upx.zip"
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            for member in z.namelist():
                if member.endswith("upx.exe"):
                    source = z.extract(member, ROOT / "upx_temp")
                    shutil.move(source, ROOT / "upx.exe")
                    break
        shutil.rmtree(ROOT / "upx_temp", ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        print("[*] UPX downloaded successfully.")
        return [f"--upx-dir={ROOT}"]
    except Exception as e:
        print(f"[!] Failed to download UPX: {e}. Compression will be skipped.")
        return ["--noupx"]


def main():
    print("============================================")
    print(f"  Steam Anchor v{__version__} - PyInstaller Build")
    print("============================================\n")

    version_file = generate_version_file()
    upx_args = find_or_download_upx()

    print("\n[*] Compiling Steam Anchor with PyInstaller...")
    print("[*] This will take a few minutes.\n")

    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--version-file={version_file}",
        "--icon=assets/icon.ico",
        "--name=SteamAnchor",
        "--distpath=dist",
        "--add-data=assets;assets",
        *upx_args,
        "main.py",
    ])

    if result.returncode != 0:
        print("\n[!] Build failed.")
        sys.exit(1)

    shutil.rmtree(ROOT / "build", ignore_errors=True)
    (ROOT / "SteamAnchor.spec").unlink(missing_ok=True)
    (ROOT / "version.txt").unlink(missing_ok=True)

    exe = ROOT / "dist" / "SteamAnchor.exe"
    print("\n============================================")
    if exe.exists():
        size = exe.stat().st_size
        print(f"  Build complete! Output: dist/SteamAnchor.exe")
        print(f"  Final Size: {size // 1_048_576} MB ({size:,} bytes)")
    else:
        print("  Build complete but could not locate dist/SteamAnchor.exe")
    print("============================================\n")


if __name__ == "__main__":
    main()
