"""Build the reviewed CoreELEC 22 ARM64 Tailscale package."""
import hashlib
import io
from pathlib import Path
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/service.tailscale'
VERSION = '1.104.7'
SHA256 = 'd6bed2720310b328b861f943d7b4016c5358a9bad60575eb51e8143b79068484'

def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()

def main():
    data = fetch(f'https://pkgs.tailscale.com/stable/tailscale_{VERSION}_arm64.tgz')
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Official archive checksum mismatch')
    files = {}
    for path in SOURCE.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            value = path.read_bytes()
            if path.suffix in ('.py', '.xml', '.po', '.md', '.service') or path.parent.name == 'bin':
                value = value.replace(b'\r\n', b'\n')
            files[path.relative_to(SOURCE).as_posix()] = value
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for name in ('tailscale', 'tailscaled'):
            value = archive.extractfile(f'tailscale_{VERSION}_arm64/{name}').read()
            if value[:5] != b'\x7fELF\x02' or int.from_bytes(value[18:20], 'little') != 183:
                raise ValueError('Expected ARM64 ELF binary')
            files[f'bin/{name}'] = value
    for channel in ('piers', 'avdvplus'):
        channel_files = dict(files)
        if channel == 'avdvplus':
            # Retain the customized service, settings, networking and persistent state.
            # Only substitute the Kodi 21.3 metadata; binaries and service files stay identical.
            xml = files['addon.xml'].decode('utf-8')
            xml = xml.replace('22.0.13.101', '21.3.13.101')
            xml = xml.replace('CoreELEC 22/Piers', 'CoreELEC 21.3/AVDVPlus')
            xml = xml.replace('CoreELEC 22', 'CoreELEC 21.3')
            xml = xml.replace('Kodi 22', 'Kodi 21.3')
            channel_files['addon.xml'] = xml.encode('utf-8')
        version = ET.fromstring(channel_files['addon.xml']).attrib['version']
        destination = ROOT / channel / 'service.tailscale'
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / f'service.tailscale-{version}.zip'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, value in sorted(channel_files.items()):
                info = zipfile.ZipInfo(f'service.tailscale/{name}', (2026, 10, 4, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100755 if name.startswith('bin/') else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, value)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:
                raise ValueError(f'Corrupted ZIP for {channel}')
            if archive.read('service.tailscale/addon.xml') != channel_files['addon.xml']:
                raise ValueError(f'Incorrect Kodi metadata for {channel}')
        for name in ('addon.xml', 'icon.png'):
            (destination / name).write_bytes(channel_files[name])
        (destination / (target.name + '.sha256')).write_text(
            hashlib.sha256(target.read_bytes()).hexdigest() + '  ' + target.name + '\n')
        print(target)

if __name__ == '__main__':
    main()
