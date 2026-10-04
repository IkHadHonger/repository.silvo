import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/service.tailscale'

class TailscaleTests(unittest.TestCase):
    def test_defaults_and_start(self):
        defaults = {s.attrib['id']: s.text for s in ET.parse(SOURCE / 'settings-default.xml').getroot()}
        self.assertEqual(defaults['ts_accept_dns'], 'false')
        start = (SOURCE / 'bin/tailscale.start').read_text()
        self.assertIn('--accept-dns=$ts_accept_dns', start)
        self.assertIn('-statedir "$STATE_DIR"', start)
        self.assertIn('ts_read_settings "$ADDON_HOME/settings.xml"', start)
        self.assertNotIn('/storage/.config/tailscale-settings-compat.sh', start)
        self.assertEqual(ET.parse(SOURCE / 'addon.xml').getroot().attrib['id'], 'service.tailscale')

    @unittest.skipUnless(shutil.which('xmlstarlet') and shutil.which('sh'), 'Requires Linux xmlstarlet (CI)')
    def test_settings_formats_and_literal_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.xml'
            helper = SOURCE / 'bin/tailscale.settings'
            for version in range(1, 5):
                dangerous = '$(touch SHOULD_NOT_EXIST); --exit-node=evil'
                setting = f'<setting id="ts_hostname" value="{dangerous}"/>' if version == 1 else f'<setting id="ts_hostname">{dangerous}</setting>'
                connect = '<setting id="ts_connect" value="true"/>' if version == 1 else '<setting id="ts_connect">true</setting>'
                path.write_text(f'<settings version="{version}">{setting}{connect}</settings>')
                result = subprocess.run(['sh', '-c', '. "$1"; ts_read_settings "$2" || exit 1; printf "%s\\n%s" "$ts_connect" "$ts_hostname"', 'test', str(helper), str(path)], cwd=directory, capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout, 'true\n' + dangerous)
                self.assertFalse((Path(directory) / 'SHOULD_NOT_EXIST').exists())
            for xml in ('<broken', '<settings version="99"/>'):
                path.write_text(xml)
                result = subprocess.run(['sh', '-c', '. "$1"; ts_read_settings "$2"', 'test', str(helper), str(path)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)

            path.write_text('<settings version="4"><setting id="ts_connect">true</setting></settings>')
            result = subprocess.run(['sh', '-c', '. "$1"; ts_read_settings "$2" && ts_read_settings "$3" || exit 1; printf "%s/%s" "$ts_connect" "$ts_accept_dns"', 'test', str(helper), str(SOURCE / 'settings-default.xml'), str(path)], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, 'true/false')

    def test_package(self):
        package = ROOT / 'avdvplus/service.tailscale/service.tailscale-21.0.12.100.zip'
        self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), package.with_suffix('.zip.sha256').read_text().split()[0])
        with zipfile.ZipFile(package) as archive:
            self.assertIsNone(archive.testzip())
            for name in ('tailscale', 'tailscaled'):
                info = archive.getinfo('service.tailscale/bin/' + name)
                binary = archive.read(info)
                self.assertEqual(binary[:5], b'\x7fELF\x02')
                self.assertEqual(int.from_bytes(binary[18:20], 'little'), 183)
                self.assertTrue(info.external_attr >> 16 & 0o111)
            self.assertIn('service.tailscale/LICENSE.Tailscale', archive.namelist())
            self.assertIn('service.tailscale/LICENSE.GPL-2.0', archive.namelist())
            for name in ('addon.xml', 'bin/tailscale.start', 'bin/tailscale.settings', 'settings-default.xml'):
                self.assertEqual(archive.read('service.tailscale/' + name), (SOURCE / name).read_bytes().replace(b'\r\n', b'\n'))
            self.assertFalse(any('tailscaled.state' in n or 'addon_data' in n for n in archive.namelist()))

    def test_catalog(self):
        catalog = ROOT / 'avdvplus/addons.xml'
        self.assertEqual(hashlib.md5(catalog.read_bytes()).hexdigest(), catalog.with_suffix('.xml.md5').read_text().strip())
        entries = [a for a in ET.parse(catalog).getroot() if a.attrib['id'] == 'service.tailscale']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].attrib['version'], '21.0.12.100')

    def test_version_matches_channel(self):
        version = ET.parse(SOURCE / 'addon.xml').getroot().attrib['version']
        self.assertEqual(version, '21.0.12.100')
        repository = ET.parse(ROOT / 'repository.ikhadhonger/addon.xml').getroot()
        dirs = repository.find('extension').findall('dir')
        omega = [d for d in dirs if d.attrib.get('minversion') == '21.0.0']
        self.assertEqual(len(omega), 1)
        self.assertTrue(omega[0].findtext('info').endswith('/avdvplus/addons.xml'))

if __name__ == '__main__':
    unittest.main()
