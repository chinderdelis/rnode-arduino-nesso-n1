# RNode Firmware for Arduino Nesso N1

> [!NOTE]
> This is the main README for the Arduino Nesso N1 port. The original upstream
> RNode Firmware README is preserved in
> [`README_UPSTREAM.md`](./README_UPSTREAM.md).

> [!IMPORTANT]
> **This port has been built, flashed, provisioned and tested on a physical
> Arduino Nesso N1.** The firmware is not only a successful compile; it has
> been exercised on real hardware.
>
> The port is still **experimental**. "Tested on hardware" does not mean that
> every feature has been validated, and it does not mean that this is a
> production-ready release. The exact test coverage and the remaining gaps are
> listed in this document.

This is an unofficial port of the [RNode Firmware](https://github.com/markqvist/RNode_Firmware)
to the **Arduino Nesso N1** (ESP32-C6 + SX1262). It is based on the upstream
RNode Firmware by Mark Qvist and is distributed under the same **GPLv3** license.
All original copyrights remain with their respective authors.

**Current status:** the board boots, provisions, renders the RNode UI and accepts
TX commands, but end-to-end LoRa communication is not yet demonstrated. Treat it
as an experimental port, not a working Reticulum modem.

---

## Hardware

| Item | Details |
|------|---------|
| Board | Arduino Nesso N1 |
| MCU | ESP32-C6 (RISC-V, Wi-Fi 6 / BLE 5) |
| Radio | Semtech SX1262 (LoRa) |
| Display | ST7789 240x135 IPS (SPI) |
| Power | BQ27220 fuel gauge + AW32001 charger |
| GPIO expansion | 2x PI4IOE5V6408 I2C expanders |
| Buttons | KEY1 / KEY2 on the GPIO expander |

## Current firmware

### Identity

| Field | Value | Meaning |
|-------|-------|---------|
| RNode firmware | `1.56` (`0x0156`) | Firmware/protocol version reported by the firmware. |
| Compile-time board ID | `0x43` (`BOARD_MODEL`) | Selects the Nesso pin/peripheral map at build time. It is **not** the EEPROM product or model value. |
| EEPROM product ID | `0xEC` (`PRODUCT_NESSO_N1`) | Identifies the Nesso N1 product family in the provisioning info block. |
| EEPROM model ID | `0xEF` (`MODEL_EF`) | 868/915 MHz SX1262 variant; the 433 MHz variant is `0xF1`. |
| Provisioning tool | `tools/provision_nesso.py` | Required because upstream `rnodeconf` does not know these IDs. |

### Resource usage and image sizes

| Metric | Value | Meaning |
|--------|-------|---------|
| RAM usage | `120152 / 327680` bytes (`36.7%`) | Static RAM reported by PlatformIO for this build. |
| Flash usage | `930566 / 1310720` bytes (`71.0%`) | Program storage reported by PlatformIO inside the application partition. |
| Application image | `978128` bytes | Size of the final `firmware.bin` file. It includes the ESP32 image/segment headers, alignment padding and the 32-byte appended digest. |
| Factory image | `1043664` bytes | Merged image: bootloader + partition table + OTA selector + application. |

The PlatformIO flash figure and the `.bin` file size are different
measurements. Use the percentage for partition headroom and the file size for
storage or transfer.

### Firmware hashes

| Hash | Value | What it covers |
|------|-------|----------------|
| Application file SHA-256 | `d952dc9a19f38227f9ea64acaf822d9c9b1960c0835f949a25ec4bd99c420589` | The whole `firmware.bin`, including the final 32 bytes. This is what `SHA256SUMS` verifies. |
| Embedded firmware hash | `127d0a5026b57f2913bbec5a975646f5036788058a04244e17a152c89aa13dfb` | The application image **excluding** the final 32 bytes. Those last 32 bytes contain this digest and it is the value used as the RNode firmware-hash target. |

The two values differ by design: one hashes the file including the appended
digest, the other is that appended digest itself.

Prebuilt binaries, flashing instructions and checksums are in
[`firmware/nesso_n1/`](./firmware/nesso_n1/), and attached to the
[`nesso-n1-fw-1.56` release](https://github.com/chinderdelis/rnode-arduino-nesso-n1/releases/tag/nesso-n1-fw-1.56).

## Verified on physical hardware

The following items were checked on a physical Nesso N1 running this build:

| Area | Result |
|------|--------|
| Boot | Firmware boots and enumerates over USB. |
| USB serial | RNode KISS/HDLC communication works for configuration and status commands. |
| Provisioning | EEPROM info block, configuration, lock byte and firmware hash are written and verified. |
| Display | Full RNode UI is rendered correctly in landscape on the 240x135 panel. |
| Button | `KEY1` blanks and unblanks the display; `CMD_DISP_INT` also unblanks it. |
| Radio initialization | SX1262 starts successfully with the expected EU868 configuration. |
| TX command handling | A KISS transmit command was accepted and processed without a firmware error. This confirms command handling only, not RF output or reception. |
| BLE | BLE starts, stops and advertises as an RNode device. |
| Battery | The fuel gauge reports battery state `3`, charge `100%` while connected to USB. |
| Persistence | Radio configuration and provisioning survive reboots. |

The tested radio configuration was:

- Frequency: `869.525 MHz`
- Bandwidth: `125 kHz`
- Spreading factor: `8`
- Coding rate: `5`
- TX power: `14 dBm`

These are the defaults written by the provisioning helper. They are not a
requirement and can be changed through the normal RNode KISS commands.

## Not yet verified or not implemented

These items must not be assumed to work just because the board boots:

- **End-to-end LoRa link:** no second LoRa node was available. Neither actual
  over-the-air transmission nor reception has been confirmed by a receiver. The
  verified TX item above only proves that the command was accepted.
- **BLE data transport:** pairing, connection stability and KISS data transfer
  over BLE were not completed.
- **Display modes:** portrait orientation, recondition mode, automatic display
  blanking and the console/update screens were not validated.
- **Firmware update flow:** the RNode firmware-update display path was not
  validated.
- **Wi-Fi / RNode Remote:** RNode's Wi-Fi Remote transport (TCP KISS on port
  `7633`, AP/STA mode) is disabled for this board (`HAS_WIFI=false`); it is not
  implemented or tested.
- **Deep sleep / power-off:** not implemented for this board.
- **KEY2, Grove and other expansion features:** not mapped or implemented.
- **Battery details:** voltage, charge current and charging behavior were not
  validated under different power conditions. The 100% reading was observed on
  USB.
- **ESP32-C6 temperature:** not exposed by this port.
- **Long-term stability:** a single interrupt-watchdog panic was observed once
  after a USB/RTS-triggered reset while the board was attached to USB. It did
  not reproduce in later boot, provisioning, display or command tests. A useful
  reproduction attempt would repeat USB/RTS resets and capture the serial log;
  behavior under battery-only power or other reset sources is unknown.

## Reticulum compatibility

Status: **not yet verified**.

- Upstream `rnodeconf` does not know the Nesso N1 product/model IDs
  (`0xEC`/`0xEF`), so auto-install, detection and firmware update through
  `rnodeconf` are not expected to work.
- The firmware exposes RNode KISS/HDLC over USB serial. The intended integration
  path is Reticulum's `RNodeInterface` pointed at the Nesso serial port, but no
  end-to-end test with Reticulum or Sideband has been performed.
- BLE data transport has not been validated, so Sideband over BLE is not claimed.
- Do not assume that Reticulum or Sideband will detect the device as an official
  RNode; manual serial configuration may be required.

If you test the integration, please open a
[hardware test report](https://github.com/chinderdelis/rnode-arduino-nesso-n1/issues/new?template=hardware_test_report.yml).

## Display implementation

The Nesso N1 display path is intentionally different from the small OLED boards:

- The standard 128x64 RNode UI is composed into a static `240x135` RGB565 frame
  buffer.
- Landscape: the 128x64 logical UI is upscaled 1.875x with nearest-neighbor
  sampling to `240x120`, then centered. The remaining 15 rows are split 7 px
  above and 8 px below.
- Portrait: the 64x128 logical UI is upscaled 1.875x to `120x240`, centered with
  7 px on the left and 8 px on the right. The code exists but has not been
  visually tested.
- No bilinear filtering is applied; each output pixel takes the nearest source
  pixel and the background stays black.
- The panel is updated with one full-frame `drawRGBBitmap()` call per refresh,
  which avoids partial-region tearing and flicker.
- The LCD reset and backlight are controlled through the I2C GPIO expander.

## Build

The port is built with [PlatformIO](https://platformio.org/):

```bash
pio run -e nesso_n1
pio run -e nesso_n1 -t upload
```

Build output is written to `.pio/build/nesso_n1/`:

| File | Purpose |
|------|---------|
| `bootloader.bin` | ESP32-C6 bootloader, offset `0x0` |
| `partitions.bin` | partition table, offset `0x8000` |
| `boot_app0.bin` | OTA selector, offset `0xe000` |
| `firmware.bin` | application image, offset `0x10000` |
| `firmware.factory.bin` | complete merged image, offset `0x0` |

The build maps the local home directory to `/home/user` in embedded debug
strings, so local usernames and source paths are not included in the firmware
images.

## Flash prebuilt binaries

The repository includes ready-to-flash images in
[`firmware/nesso_n1/`](./firmware/nesso_n1/).

### Recommended: full factory image

This writes the bootloader, partition table, OTA selector and application:

```bash
esptool --chip esp32c6 -p /dev/ttyACM0 -b 460800 \
  write_flash 0x0 firmware/nesso_n1/firmware.factory.bin
```

Replace `/dev/ttyACM0` with the correct port.

### Application update only

This preserves the bootloader and partition table and writes only the
application:

```bash
esptool --chip esp32c6 -p /dev/ttyACM0 -b 460800 \
  write_flash 0x10000 firmware/nesso_n1/firmware.bin
```

### Manual component flashing

```bash
esptool --chip esp32c6 -p /dev/ttyACM0 -b 460800 write_flash \
  0x0     firmware/nesso_n1/bootloader.bin \
  0x8000  firmware/nesso_n1/partitions.bin \
  0xe000  firmware/nesso_n1/boot_app0.bin \
  0x10000 firmware/nesso_n1/firmware.bin
```

### Provisioning persistence

Provisioning, saved radio configuration and the firmware-hash target are stored
in the NVS partition, not in the application image.

- **Factory image at `0x0`:** the merged image writes `0xFF` filler over the NVS
  and OTA-metadata regions, so provisioning is erased. Re-run the provisioning
  helper afterwards.
- **Application-only image at `0x10000`:** leaves NVS intact, so an existing
  provisioning survives. If the application hash changed, re-run the helper to
  update the firmware-hash target.
- **Full-flash backup/restore:** restores the complete NVS state, including
  provisioning.

### Provision after flashing

`rnodeconf` does not currently know the Nesso N1, so use the included helper:

```bash
python3 tools/provision_nesso.py \
  --port /dev/ttyACM0 \
  --firmware firmware/nesso_n1/firmware.bin \
  --yes
```

The helper writes the Nesso info block, the default radio configuration, the
EEPROM lock byte, and the expected firmware SHA-256 ("target"). On boot the
firmware hashes the running application image and compares it with this target; a
mismatch makes the firmware report an invalid image. Re-run the helper whenever
the application image changes. On an already-provisioned Nesso the helper keeps
the existing info block and only updates the firmware-hash target; `--force`
erases and rewrites the whole EEPROM.

Check the result with:

```bash
python3 tools/provision_nesso.py --port /dev/ttyACM0 --dump
```

## Before flashing an original device

If the Nesso N1 still runs its factory firmware, make a complete flash backup
first:

```bash
python3 tools/nesso_flash_backup.py backup --out-dir ~/nesso_backup
```

Restore it with:

```bash
python3 tools/nesso_flash_backup.py restore ~/nesso_backup/nesso_backup_XXXX.bin --yes
```

The repository does **not** contain full-flash dumps, device-specific
credentials, Wi-Fi passwords, private keys or MAC-address data.

## Protocol notes

- KISS commands with no payload need at least one dummy byte in the frame to be
  dispatched by this firmware.
- `CMD_DISP_READ` returns 1024 bytes: the first 512 bytes of the display canvas
  followed by the first 512 bytes of the status canvas.
- `CMD_STAT_TX` currently returns `00000000`. Its counter is not a reliable
  transmit confirmation in this build.
- `CMD_DISP_INT` with `0xFF` unblanks the display and stores the intensity.
- `CMD_DISP_RCND` enables display reconditioning until the next reboot.

## Contributing

Issues, test reports and pull requests are welcome, especially from people who
can test the remaining items with a second LoRa node or a BLE host.

Before contributing, read [`CONTRIBUTING.md`](./CONTRIBUTING.md). Report security
problems privately as described in [`SECURITY.md`](./SECURITY.md). Project
participation follows [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

The upstream project remains the authoritative source for generic RNode behavior:

- Upstream firmware: <https://github.com/markqvist/RNode_Firmware>
- Upstream README: [`README_UPSTREAM.md`](./README_UPSTREAM.md)
- Reticulum: <https://reticulum.network>

## License

This project is licensed under the **GNU General Public License v3.0**, the same
license as the upstream RNode Firmware. See [`LICENSE`](./LICENSE) for details.
