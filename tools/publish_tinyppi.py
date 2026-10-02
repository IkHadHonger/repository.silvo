"""Publish tested public fork snapshots into both existing Kodi branches."""
from pathlib import Path
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile


def command(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)


def version(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Manual version review required: ' + value)
    return tuple(map(int, value.split('.')))


def publish(source, repository, branch, channel):
    metadata = (source / 'addon.xml').read_bytes()
    addon = ET.fromstring(metadata)
    assert addon.attrib['id'] == 'script.tinyppi'
    release = addon.attrib['version']
    catalog = repository / channel / 'addons.xml'
    before = {a.attrib['id']: ET.tostring(a) for a in ET.parse(catalog).getroot()}
    deployed = ET.fromstring(before['script.tinyppi']).attrib['version']
    if version(release) <= version(deployed):
        print(f'{branch}: already current ({deployed})')
        return
    folder = repository / channel / 'script.tinyppi'
    archive = folder / f'script.tinyppi-{release}.zip'
    command('git', 'archive', '--format=zip', '--prefix=script.tinyppi/', '-o', str(archive), 'HEAD', cwd=source)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert package.read('script.tinyppi/addon.xml') == metadata
        for asset in addon.findall('extension/assets/*'):
            destination = folder / asset.text
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package.read('script.tinyppi/' + asset.text))
    (folder / 'addon.xml').write_bytes(metadata)
    spec = importlib.util.spec_from_file_location('generator', repository / '_repo_generator.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = Path.cwd()
    try:
        os.chdir(repository)
        module.RepoGenerator.__new__(module.RepoGenerator)._generate_channel(channel)
    finally:
        os.chdir(original)
    for index in (repository / channel).rglob('index.html'):
        index.write_bytes(index.read_bytes().replace(b'\\', b'/').replace(b'\r\n', b'\n'))
    catalog.write_bytes(catalog.read_bytes().replace(b'\r\n', b'\n'))
    checksum = hashlib.md5(catalog.read_bytes()).hexdigest()
    (catalog.parent / 'addons.xml.md5').write_bytes(checksum.encode())
    after = {a.attrib['id']: ET.tostring(a) for a in ET.parse(catalog).getroot()}
    assert before.keys() == after.keys()
    for key in before:
        if key != 'script.tinyppi':
            assert before[key] == after[key], f'Unexpected addon change: {key}'
    command('git', 'add', channel, cwd=repository)
    command('git', 'commit', '-m', f'Publish tested TinyPPI {release}', cwd=repository)
    command('git', 'push', 'origin', f'HEAD:{branch}', cwd=repository)
    remote = command('git', 'ls-remote', 'origin', f'refs/heads/{branch}', cwd=repository).stdout.split()[0]
    assert remote == command('git', 'rev-parse', 'HEAD', cwd=repository).stdout.strip()
    print(f'Published and verified {branch}: TinyPPI {release}, catalog MD5 {checksum}')


def main():
    repository = Path.cwd().resolve()
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / 'tinyppi'
        command('git', 'clone', '--branch', 'main', '--single-branch', 'https://github.com/IkHadHonger/script.tinyppi.git', str(source), cwd=repository)
        # Test public source without adding credentials to its checkout.
        command(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', cwd=source)
        command(sys.executable, '-m', 'pytest', 'tests/unit', '-q', cwd=source)
        command(sys.executable, '-m', 'compileall', '-q', 'main.py', 'resources/lib', cwd=source)
        for test in (source / 'tests').glob('test_*.js'):
            command('node', str(test), cwd=source)
        for script in (source / 'resources/web/js').glob('*.js'):
            command('node', '--check', str(script), cwd=source)
        command('git', 'config', 'user.name', 'github-actions[bot]', cwd=repository)
        command('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com', cwd=repository)
        publish(source, repository, 'cube-custom', 'piers')
        command('git', 'fetch', 'origin', 'avdvplus-custom', cwd=repository)
        participant = Path(temporary) / 'participant'
        command('git', 'worktree', 'add', '--detach', str(participant), 'FETCH_HEAD', cwd=repository)
        try:
            publish(source, participant, 'avdvplus-custom', 'avdvplus')
        finally:
            command('git', 'worktree', 'remove', str(participant), cwd=repository)


if __name__ == '__main__':
    main()
