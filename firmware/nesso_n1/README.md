# Nesso N1 prebuilt firmware

**Hardware-tested on a physical Arduino Nesso N1.** This is an experimental
port, not a production release. See the main
[`README.md`](../../README.md) for validated features and
remaining limitations.

## Contents

| File | Flash offset | Size | Purpose |
|------|--------------|------|---------|
| `firmware.factory.bin` | `0x0` | 1043664 | Complete factory image |
| `firmware.bin` | `0x10000` | 978128 | Application image |
| `bootloader.bin` | `0x0` | 20720 | ESP32-C6 bootloader |
| `partitions.bin` | `0x8000` | 3072 | Partition table |
| `boot_app0.bin` | `0xe000` | 8192 | OTA selector |
| `SHA256SUMS` | — | — | SHA-256 checksums |

## Version

- RNode firmware: `1.56` (`0x0156`)
- Board model: `0x43`
- App image SHA-256: `d952dc9a19f38227f9ea64acaf822d9c9b1960c0835f949a25ec4bd99c420589`
- Embedded firmware hash: `127d0a5026b57f2913bbec5a975646f5036788058a04244e17a152c89aa13dfb`

## Flash

Full factory image:

```bash
esptool --chip esp32c6 -p /dev/ttyACM0 -b 460800 \
  write_flash 0x0 firmware/nesso_n1/firmware.factory.bin
```

Application update only:

```bash
esptool --chip esp32c6 -p /dev/ttyACM0 -b 460800 \
  write_flash 0x10000 firmware/nesso_n1/firmware.bin
```

Then provision the device:

```bash
python3 tools/provision_nesso.py \
  --port /dev/ttyACM0 \
  --firmware firmware/nesso_n1/firmware.bin \
  --yes
```

Verify the result:

```bash
python3 tools/provision_nesso.py --port /dev/ttyACM0 --dump
```

## Verify checksums

From the repository root:

```bash
cd firmware/nesso_n1
sha256sum -c SHA256SUMS
```
