import json
import os
import re
import sys
import subprocess

BLOG_URL = "https://blog.lightwo.net/steam-client-downgrades-survival-kit.html"

if "__compiled__" in globals():
    _BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
elif getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = os.path.join(_BASE_DIR, "versions_cache.json")

# Matches <tr> rows containing a wayback date, manifest ID, and notes
_ROW_RE = re.compile(
    r'<tr>\s*<td>(\d{14}|N/A)</td>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*</tr>',
    re.DOTALL,
)


def _parse_versions(html: str) -> list[dict]:
    """Extracts version entries from 'The Downgrade Table', excluding the SteamCMD variant."""
    start = html.find('id="the-downgrade-table_1"')
    end = html.find('id="the-downgrade-table-steamcmd_1"')

    if start == -1:
        section = html
    elif end == -1:
        section = html[start:]
    else:
        section = html[start:end]

    versions = []
    for wayback_date, manifest, raw_notes in _ROW_RE.findall(section):
        if wayback_date.strip() == "N/A":
            continue
        notes = re.sub(r"<[^>]+>", "", raw_notes).strip()
        versions.append({
            "date": wayback_date.strip(),
            "manifest": manifest.strip(),
            "notes": notes,
        })
    return versions


def load_cache() -> list | None:
    """Returns the cached version list, or None if unavailable."""
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def fetch_versions() -> list[dict]:
    """Scrapes the blog for Steam versions using native curl, caches the result, and returns it."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0", BLOG_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Curl failed with return code {result.returncode}")
        html_text = result.stdout
    except Exception as exc:
        raise RuntimeError(f"Connection failure: {exc}") from exc

    versions = _parse_versions(html_text)
    if not versions:
        raise RuntimeError(
            "No versions found, the page structure may have changed.")

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(versions, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # non-fatal

    return versions
