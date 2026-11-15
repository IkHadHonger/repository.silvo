#!/usr/bin/env python3
"""Build an ARM64 Kodi Tailscale 1.104.7 service add-on for CoreELEC 22 and 21.3."""
import hashlib
import io
import os
import platform
import subprocess
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

VERSION = "1.104.7"
REVISION = "13"
ADDON_ID = "service.tailscale"
ADDON_VERSION = f"{VERSION}.{REVISION}"
ARCHIVE_URL = f"https://pkgs.tailscale.com/stable/tailscale_{VERSION}_arm64.tgz"
EXPECTED_SHA256 = "d6bed2720310b328b861f943d7b4016c5358a9bad60575eb51e8143b79068484"
UPSTREAM = "https://raw.githubusercontent.com/CoreELEC/CoreELEC/eba4ee592a212ce4d8117f905d2e37e982a916bf/packages/addons/service/tailscale/source"
SOURCE_FILES = [
    "default.py",
    "bin/tailscale.start",
    "bin/tailscale.stop",
    "resources/settings.xml",
    "resources/language/resource.language.en_gb/strings.po",
]

ADDON_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{ADDON_ID}" name="Tailscale (CoreELEC ARM64)" version="{ADDON_VERSION}" provider-name="Team LibreELEC / IkHadHonger">
  <requires><import addon="xbmc.python" version="3.0.0" /></requires>
  <extension point="xbmc.service" library="service.py" start="startup" />
  <extension point="xbmc.python.script" library="default.py" />
  <extension point="xbmc.addon.metadata">
    <summary lang="en_GB">Private WireGuard mesh VPN for CoreELEC ARM64</summary>
    <description lang="en_GB">Official Tailscale {VERSION} static ARM64 binaries, packaged with the CoreELEC service controls for Kodi 21 Omega and Kodi 22 Piers. Requires CoreELEC and ARM64.</description>
    <platform>linux</platform>
    <license>BSD-3-Clause</license>
  </extension>
</addon>
'''

SERVICE_PY = r'''# Kodi Python service supervising the CoreELEC Tailscale service shell scripts.
import os
import platform
import signal
import subprocess
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
BASE = ADDON.getAddonInfo("path")
START = os.path.join(BASE, "bin", "tailscale.start")
STOP = os.path.join(BASE, "bin", "tailscale.stop")

def log(message, level=xbmc.LOGINFO):
    xbmc.log("[service.tailscale] " + message, level)

def stop(process):
    if process is None:
        return
    try:
        subprocess.run(["/bin/sh", STOP], timeout=15, check=False)
    except Exception as exc:
        log("Stop script: " + str(exc), xbmc.LOGWARNING)
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except Exception as exc:
        log("Stopping daemon: " + str(exc), xbmc.LOGWARNING)

class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.changed = False
    def onSettingsChanged(self):
        self.changed = True

def main():
    if platform.machine().lower() not in ("aarch64", "arm64"):
        log("This ZIP contains only ARM64 binaries", xbmc.LOGERROR)
        return
    monitor = Monitor()
    process = None
    try:
        while not monitor.abortRequested():
            if process is None or monitor.changed:
                monitor.changed = False
                stop(process)
                process = None
                try:
                    process = subprocess.Popen(["/bin/sh", START], start_new_session=True)
                except Exception as exc:
                    log("Cannot start Tailscale: " + str(exc), xbmc.LOGERROR)
            if monitor.waitForAbort(2):
                break
            if process is not None and process.poll() is not None:
                log("Tailscale startup script exited with code " + str(process.returncode), xbmc.LOGERROR)
                break
    finally:
        stop(process)

if __name__ == "__main__":
    main()
'''

def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()

def make_package():
    archive_bytes = download(ARCHIVE_URL)
    actual = hashlib.sha256(archive_bytes).hexdigest()
    if actual != EXPECTED_SHA256:
        raise ValueError(f"Official Tailscale archive SHA256 mismatch: {actual}")
    files = {
        "addon.xml": ADDON_XML.encode("utf-8"),
        "service.py": SERVICE_PY.encode("utf-8"),
    }
    ET.fromstring(files["addon.xml"])
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as source:
        for binary in ("tailscale", "tailscaled"):
            members = [m for m in source.getmembers()
                       if m.isfile() and m.name.endswith("/" + binary)]
            if len(members) != 1:
                raise ValueError(f"Missing/ambiguous ARM64 binary: {binary}")
            files[f"bin/{binary}"] = source.extractfile(members[0]).read()
            if not files[f"bin/{binary}"].startswith(b"\x7fELF"):
                raise ValueError(f"Not an ELF binary: {binary}")
            if files[f"bin/{binary}"][18:20] != (183).to_bytes(2, "little"):
                raise ValueError(f"Not ARM64: {binary}")
    for relative in SOURCE_FILES:
        files[relative] = download(f"{UPSTREAM}/{relative}")
    ET.fromstring(files["resources/settings.xml"])
    for channel in ("piers", "avdvplus"):
        destination = Path(channel) / ADDON_ID
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "addon.xml").write_bytes(files["addon.xml"])
        zip_path = destination / f"{ADDON_ID}-{ADDON_VERSION}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
            for name, content in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{ADDON_ID}/{name}")
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (0o755 if name in ("bin/tailscale", "bin/tailscaled", "bin/tailscale.start", "bin/tailscale.stop")
                                       else 0o644) << 16
                zipped.writestr(entry, content)
        with zipfile.ZipFile(zip_path) as zipped:
            assert zipped.testzip() is None
            xml = ET.fromstring(zipped.read(f"{ADDON_ID}/addon.xml"))
            assert xml.attrib["id"] == ADDON_ID
            assert xml.attrib["version"] == ADDON_VERSION
        print(f"Validated {channel} installable ZIP: {zip_path}, {zip_path.stat().st_size} bytes")

if __name__ == "__main__":
    make_package()
