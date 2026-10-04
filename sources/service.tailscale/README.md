# Tailscale for CoreELEC 22/Piers ARM64

An addon fork, not a CoreELEC firmware fork. Upstream shell/Python/GUI code:
CoreELEC/CoreELEC `75626f5a6e955cdee0aa1a4c97b0d8660e1ea1af`,
`packages/addons/service/tailscale/source` (GPL-2.0-only, Team LibreELEC).
Icon retained from the same upstream package. Changes by IkHadHonger.

Bundled binaries: official Tailscale 1.102.4 ARM64, BSD-3-Clause.
SHA-256 of the upstream archive:
`9dd1e6a592a014bbaea0103167ffe299adeda4ba14e078ce9c2895364f6c4c3f`.

Addon version 22.0.12.100 is independent of the bundled Tailscale version.
It follows the official 22.0.12 base and exceeds official revision 9.
The original 22.0.0.100 was lower than 22.0.12.9; this release corrects that.
The existing ID `service.tailscale`, settings, socket, systemd unit and
`/storage/.cache/tailscale/tailscaled.state` are retained. Do not uninstall
or remove state files to migrate. Select this repository as update source;
an official repository switch/reinstall can replace this fork.

Settings are loaded without evaluating their values, supporting legacy
attribute format and text formats 2, 3 and 4. DNS acceptance defaults to
false and is a GUI setting. Existing hostname, exit-node and subnet options
are retained. No external compatibility hook is needed.

Build using `python tools/package_tailscale.py`. Tests:
`python -m unittest discover -s tools -p test_tailscale.py`.
The archive is only published in the Piers channel. Do not install on
CoreELEC 21/ARM32 or other platforms. This release does not automatically
download future binaries; upgrades require a reviewed, checksummed build.
