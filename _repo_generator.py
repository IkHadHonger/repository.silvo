#!/usr/bin/env python3
"""
Repository Generator for repository.silvo
Generates addons.xml, addons.xml.md5, and index.html files for each channel
"""

import hashlib
import sys
from pathlib import Path
from xml.dom import minidom


class RepoGenerator:
    """Generate addons.xml, addons.xml.md5, and index.html for repository channels"""

    # Files to exclude from directory listings
    EXCLUDED_FILES = {'.git', '.gitignore', '.github', 'README.md', 'AUTOMATION_SETUP.md',
                      'QUICK_REFERENCE.md', 'TESTING_CHECKLIST.md', '_addon_deploy_workflow.yml',
                      '_package_addon.py', '_repo_generator.py', 'index.html'}

    def __init__(self, channels=None):
        """
        Initialize generator and process channels

        Args:
            channels: List of channel names to process. If None, processes all found channels.
        """
        if channels is None:
            channels = self._find_channels()

        if not channels:
            print("No channels found. Expected directories: piers")
            sys.exit(1)

        print(f"Processing {len(channels)} channel(s): {', '.join(channels)}")
        for channel in channels:
            self._generate_channel(channel)

        self._generate_root_index(channels)

    def _find_channels(self):
        """Find all channel directories in current path"""
        channels = []
        for item in Path('.').iterdir():
            if item.is_dir() and item.name in ['piers', 'stable', 'alpha', 'beta']:
                channels.append(item.name)
        return sorted(channels)

    def _generate_channel(self, channel):
        """
        Generate addons.xml and addons.xml.md5 for a specific channel

        Args:
            channel: Name of the channel directory
        """
        channel_path = Path(channel)
        if not channel_path.exists():
            print(f"  Warning: Channel '{channel}' does not exist, skipping")
            return

        print(f"\n{'='*60}")
        print(f"Generating for channel: {channel}/")
        print(f"{'='*60}")

        addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
        addon_count = 0

        for addon_dir in sorted(channel_path.iterdir()):
            if not addon_dir.is_dir():
                continue

            addon_xml_path = addon_dir / "addon.xml"
            if not addon_xml_path.exists():
                print(f"  Skipping {addon_dir.name}/ - no addon.xml found")
                continue

            try:
                with open(addon_xml_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                dom = minidom.parseString(content)

                addon_element = dom.getElementsByTagName('addon')[0]
                addon_id = addon_element.getAttribute('id')
                addon_version = addon_element.getAttribute('version')

                for line in content.split('\n'):
                    if '<?xml' not in line:
                        addons_xml += line + '\n'

                addon_count += 1
                print(f"  ✓ Added: {addon_id} v{addon_version}")

            except Exception as e:
                print(f"  ✗ Error processing {addon_dir.name}/addon.xml: {e}")
                continue

        addons_xml += '</addons>\n'

        if addon_count == 0:
            print(f"  Warning: No valid addons found in {channel}/")
            return

        addons_xml_path = channel_path / "addons.xml"
        addons_xml_path.write_text(addons_xml, encoding='utf-8')
        print(f"\n  Generated: {addons_xml_path}")

        md5_hash = hashlib.md5(addons_xml.encode('utf-8')).hexdigest()
        md5_path = channel_path / "addons.xml.md5"
        md5_path.write_text(md5_hash, encoding='utf-8')
        print(f"  Generated: {md5_path}")
        print(f"  MD5: {md5_hash}")
        print(f"  Total addons: {addon_count}")

        self._generate_channel_index(channel_path)

    def _generate_index_html(self, directory: Path, entries: list[str]) -> None:
        """
        Generate index.html with hidden links for Kodi file manager browsing.

        Kodi's HTTPDirectory parser looks for <a href="X">X</a> patterns where
        the link text matches the href. CSS styling is ignored.

        Args:
            directory: Path to write index.html
            entries: List of file/folder names (folders should end with /)
        """
        links = '\n'.join(f'<a href="{e}">{e}</a>' for e in sorted(entries))
        html = f'''<!DOCTYPE html>
<html>
<head><title>Index of /{directory}</title></head>
<body>
<!-- Hidden directory listing for Kodi file manager -->
<div style="display:none">
{links}
</div>
</body>
</html>
'''
        index_path = directory / "index.html"
        index_path.write_text(html, encoding='utf-8')
        print(f"  Generated: {index_path} ({len(entries)} entries)")

    def _generate_root_index(self, channels: list[str]) -> None:
        """Inject hidden links into existing root index.html for Kodi file manager."""
        print(f"\n{'='*60}")
        print("Updating root index.html with hidden links")
        print(f"{'='*60}")

        index_path = Path('index.html')
        if not index_path.exists():
            print("  Warning: No root index.html found, skipping")
            return

        entries = []
        for channel in channels:
            entries.append(f"{channel}/")
        if Path('repository.ikhadhonger').is_dir():
            entries.append("repository.ikhadhonger/")

        links = '\n'.join(f'<a href="{e}">{e}</a>' for e in sorted(entries))
        hidden_block = f'''<!-- Hidden directory listing for Kodi file manager -->
<div style="display:none">
{links}
</div>
'''
        content = index_path.read_text(encoding='utf-8')

        # Remove any existing hidden block
        import re
        content = re.sub(
            r'<!-- Hidden directory listing for Kodi file manager -->.*?</div>\s*',
            '',
            content,
            flags=re.DOTALL
        )

        # Inject hidden block after <body> tag
        if '<body>' in content:
            content = content.replace('<body>', f'<body>\n{hidden_block}', 1)
        elif '<body' in content:
            content = re.sub(r'(<body[^>]*>)', rf'\1\n{hidden_block}', content, count=1)

        index_path.write_text(content, encoding='utf-8')
        print(f"  Updated: {index_path} (injected {len(entries)} hidden links)")

        # Also generate index for repository.ikhadhonger folder
        repo_path = Path('repository.ikhadhonger')
        if repo_path.is_dir():
            self._generate_addon_index(repo_path)

    def _generate_channel_index(self, channel_path: Path) -> None:
        """Generate index.html for a channel directory and its addon subdirectories."""
        entries = []

        for item in sorted(channel_path.iterdir()):
            if item.name in self.EXCLUDED_FILES:
                continue
            if item.is_dir():
                entries.append(f"{item.name}/")
                self._generate_addon_index(item)
            elif item.is_file():
                entries.append(item.name)

        self._generate_index_html(channel_path, entries)

    def _generate_addon_index(self, addon_path: Path) -> None:
        """Generate index.html for an addon directory."""
        entries = []

        for item in sorted(addon_path.iterdir()):
            if item.name == 'index.html':
                continue
            if item.is_dir():
                entries.append(f"{item.name}/")
            elif item.is_file():
                entries.append(item.name)

        self._generate_index_html(addon_path, entries)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║          SiLVO Repository Generator v1.0.0                   ║
╚══════════════════════════════════════════════════════════════╝
""")

    channels_arg = sys.argv[1:] if len(sys.argv) > 1 else None

    try:
        RepoGenerator(channels=channels_arg)
        print(f"\n{'='*60}")
        print("✓ Repository generation completed successfully!")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
