# Tailscale for CoreELEC 21.3 / ARM64-capable kernels

An addon fork, not a CoreELEC firmware fork. Upstream shell/Python/GUI code:
CoreELEC/CoreELEC `75626f5a6e955cdee0aa1a4c97b0d8660e1ea1af`,
`packages/addons/service/tailscale/source` (GPL-2.0-only, Team LibreELEC).
Icon retained from the same upstream package. Changes by IkHadHonger.

Bundled binaries: official Tailscale 1.102.4 ARM64, BSD-3-Clause.
SHA-256 of the upstream archive:
`9dd1e6a592a014bbaea0103167ffe299adeda4ba14e078ce9c2895364f6c4c3f`.

Addon version 21.0.12.100 is independent of the bundled Tailscale version.
Prepared for future fresh installations; not an automatic Entware migration.
Compatibility was inspected against avdvplus/CoreELEC commit
`55282781e6cfd4886208efc0681ffe593be7d254` (21.3 avdvplus R10).
That build supports systemd service addons. The same static ARM64 Tailscale
1.102.4 binaries already work on the user's AM6B+ through Entware.
Actual startup of this addon on CoreELEC 21.3 has not yet been tested.
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
The archive is published in the 21.3/avdvplus channel. An ARM64-capable
kernel is required, including on AM6B+ builds with ARM32 userspace.
Do not install on 32-bit-only kernels, x86, or unverified other platforms.
Do not run alongside Entware tailscaled. Entware state/login is not copied
from /opt; fresh installations must authenticate to their tailnet.
No changes are made to currently installed Entware services.
This release does not automatically
download future binaries; upgrades require a reviewed, checksummed build.
