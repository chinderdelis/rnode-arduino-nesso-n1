# RNode Firmware for Arduino Nesso N1

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

| Item | Value |
|------|-------|
| RNode firmware | `1.56` (`0x0156`) |
| Board model | `0x43` |
| RNode product / model | `0xEC` / `0xEF` (868/915 MHz) |
| RAM usage | `120152 / 327680` bytes (`36.7%`) |
| Flash application usage | `930566 / 1310720` bytes (`71.0%`) |
| Application image | `978128` bytes |
| Factory image | `1043664` bytes |
| Application image SHA-256 | `d952dc9a19f38227f9ea64acaf822d9c9b1960c0835f949a25ec4bd99c420589` |
| Embedded firmware hash | `127d0a5026b57f2913bbec5a975646f5036788058a04244e17a152c89aa13dfb` |

Prebuilt binaries, flashing instructions and checksums are in
[`firmware/nesso_n1/`](./firmware/nesso_n1/).

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
| Radio transmit path | A KISS transmit command was accepted and completed without a firmware error. No second LoRa node was available to confirm over-the-air reception. |
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

- **LoRa receive:** not tested end-to-end, because no second LoRa peer was
  available.
- **Over-the-air transmit confirmation:** the transmit path completed without a
  firmware error, but no receiver confirmed the packet.
- **BLE data transport:** pairing, connection stability and KISS data transfer
  over BLE were not completed.
- **Display modes:** portrait orientation, recondition mode, automatic display
  blanking and the console/update screens were not validated.
- **Firmware update flow:** the RNode firmware-update display path was not
  validated.
- **Wi-Fi / Remote:** not enabled in this build.
- **Deep sleep / power-off:** not implemented for this board.
- **KEY2, Grove and other expansion features:** not mapped or implemented.
- **Battery details:** voltage, charge current and charging behavior were not
  validated under different power conditions. The 100% reading was observed on
  USB.
- **ESP32-C6 temperature:** not exposed by this port.
- **Long-term stability:** one interrupt watchdog panic was observed once after
  a USB/RTS reset. It did not reproduce during subsequent testing. This remains
  under investigation.

## Display implementation

The Nesso N1 display path is intentionally different from the small OLED boards:

- The standard 128x64 RNode UI is composed into a static `240x135` RGB565 frame
  buffer.
- Landscape mode renders at `240x120`, centered with 7-pixel black bars above
  and below.
- Portrait mode code exists and renders at `120x240`, centered with 7-pixel
  black bars on the left and right. Portrait has not yet been visually tested.
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

### Provision after flashing

`rnodeconf` does not currently know the Nesso N1, so use the included helper:

```bash
python3 tools/provision_nesso.py \
  --port /dev/ttyACM0 \
  --firmware firmware/nesso_n1/firmware.bin \
  --yes
```

The helper writes the Nesso info block, the default radio configuration, the
EEPROM lock byte and the firmware hash target. It refuses to overwrite a
non-Nesso locked EEPROM unless `--force` is supplied.

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
can test the remaining items with a second LoRa node or a BLE host. The upstream
project remains the authoritative source for generic RNode behavior:

- Upstream firmware: <https://github.com/markqvist/RNode_Firmware>
- Reticulum: <https://reticulum.network>

## License

This project is licensed under the **GNU General Public License v3.0**, the same
license as the upstream RNode Firmware. See [`LICENSE`](./LICENSE) for details.
