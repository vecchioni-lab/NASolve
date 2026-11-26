"""Look up the latest published NARestraints release for the explicit environment check."""
import json
from http.client import HTTPException
from urllib.error import URLError
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version

RELEASE_API = "https://api.github.com/repos/vecchioni-lab/NARestraints/releases/latest"
LATEST_SOURCE = "https://github.com/vecchioni-lab/NARestraints/releases/latest/download/narestraints.tar.gz"
_MAX_BYTES = 256 * 1024


def release_status(installed: str) -> str:
    request = Request(RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "NASolve"})
    try:
        with urlopen(request, timeout=3) as response:
            data = response.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            raise ValueError("oversized release response")
        item = json.loads(data)
        if (not isinstance(item, dict) or item.get("draft") is not False
                or item.get("prerelease") is not False or not isinstance(item.get("tag_name"), str)):
            raise ValueError("invalid stable release")
        latest = Version(item["tag_name"])
        if latest.is_prerelease or latest.local:
            raise ValueError("expected a published stable version")
    except (OSError, URLError, HTTPException, ValueError, RecursionError):
        return "Latest NARestraints release unavailable from GitHub."
    if installed == "not installed":
        state = "install"
    else:
        try:
            local = Version(installed)
        except InvalidVersion:
            return f"Latest NARestraints release {latest}. Could not compare installed version {installed}."
        if local == latest:
            return f"Latest NARestraints release {latest}. Installed version is up to date."
        if local > latest:
            return f"Latest NARestraints release {latest}. Installed version {installed} is ahead."
        state = "update available"
    return f'Latest NARestraints release {latest} ({state}). Run python -m pip install --upgrade --no-cache-dir "NARestraints @ {LATEST_SOURCE}"'
