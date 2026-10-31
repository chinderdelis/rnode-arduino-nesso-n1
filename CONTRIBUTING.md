# Contributing

Thanks for helping improve the Arduino Nesso N1 port. This repository is an
experimental fork of the upstream RNode Firmware, so contributions should keep
the Nesso-specific work clearly separated from generic RNode behavior.

## Before opening an issue

1. Read [`README.md`](./README.md), especially the verified and not-verified
   sections.
2. Check whether the problem is already listed as unimplemented or untested.
3. Search the existing issues.
4. Confirm that the problem is specific to this fork. Generic RNode Firmware
   issues belong in the [upstream issue tracker](https://github.com/markqvist/RNode_Firmware/issues).

Use the bug report template for reproducible firmware problems. Use the hardware
test report template for successful or failed validation of radio, display, BLE,
power management or other hardware features.

## What to include

Please include enough information to reproduce the result:

- Nesso N1 hardware revision, if known.
- Firmware version and embedded firmware hash.
- Git commit or release tag.
- PlatformIO and esptool versions.
- Exact build and flash commands.
- Radio configuration, including frequency and region.
- Steps to reproduce.
- Expected and actual behavior.
- Relevant serial logs or screenshots.
- Whether a second LoRa node or BLE host was involved.

Do not include Wi-Fi passwords, private keys, API tokens, full flash dumps,
device-specific calibration data, MAC addresses or other sensitive material in
issues, pull requests or logs.

## Pull requests

- Keep changes focused and explain the hardware or protocol behavior they affect.
- Build with `pio run -e nesso_n1` before submitting.
- Test on a physical Nesso N1 when possible, and state exactly what was tested.
- Update the verified and not-verified sections in [`README.md`](./README.md)
  when behavior changes.
- Update checksums and release notes if prebuilt binaries are replaced.
- Do not commit local build output, full flash dumps or personal paths.
- Preserve upstream copyright notices and keep the project under GPLv3.

## Security

Do not report security vulnerabilities in a public issue. Follow
[`SECURITY.md`](./SECURITY.md) instead.

## Upstream

This port is possible because of the upstream RNode Firmware project by Mark
Qvist. Generic RNode protocol, tooling and documentation changes should be
discussed upstream first:

- <https://github.com/markqvist/RNode_Firmware>
- <https://reticulum.network>
