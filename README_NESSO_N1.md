# RNode Firmware — Experimental port for the Arduino Nesso N1

> **Status: EXPERIMENTAL / IN TESTING**
>
> This is an unofficial, work-in-progress port of the [RNode Firmware](https://github.com/markqvist/RNode_Firmware)
> to the **Arduino Nesso N1** (ESP32-C6 + SX1262). It currently **builds successfully** but has
> **not yet been fully validated on real hardware**. Expect bugs, incomplete features and
> breaking changes. Do not rely on it for production or critical use yet.

This port is based on the upstream RNode Firmware by Mark Qvist and is distributed under the
same **GPLv3** license. All original copyrights remain with their respective authors.

---

## Target hardware

| Item | Details |
|------|---------|
| Board | Arduino Nesso N1 (M5Stack / Arduino) |
| MCU | ESP32-C6 (RISC-V, Wi-Fi 6 / BLE 5) |
| Radio | Semtech SX1262 (LoRa) |
| Display | ST7789 240x135 IPS (SPI) |
| Power | BQ27220 fuel gauge + AW32001 charger |
| Expansion | 2x PI4IOE5V6408 I2C GPIO expanders |
| Buttons | KEY1 / KEY2 on the GPIO expander |

## Implemented features

- **LoRa radio (SX1262)** on SPI with TCXO at 3.0 V and `DIO2` used as RF switch.
  The LoRa control lines (`NRST`, `ANT_SW`, `LNA_EN`) are driven through the
  PI4IOE5V6408 I2C GPIO expanders.
- **USB serial interface** (standard RNode KISS/HDLC framing).
- **BLE interface** using **NimBLE only** — the ESP32-C6 has no Bluedroid stack and
  no Bluetooth Classic, so the Bluedroid code paths are compiled out and replaced with
  their NimBLE equivalents (`BLESecurity`, `ble_store_util_delete_all`, etc.).
- **ST7789 display** in **landscape** orientation, showing the standard RNode UI
  (status area + display area) scaled 2x and centered on the 240x135 panel.
  The LCD reset and backlight are controlled through the I2C expander.
- **Input**: the primary RNode button is mapped to `KEY1` on the I2C expander
  (with a board-specific read path, since it is not a native GPIO).
- **Battery / PMU**: reads voltage, state of charge and current directly from the
  on-board **BQ27220** fuel gauge over I2C; charging state is inferred from the
  USB VIN-detect line and the measured current direction.
- **persistent configuration** using the ESP32 EEPROM emulation (1024 bytes).

## Build instructions

The port is built with [PlatformIO](https://platformio.org/) (the classic Arduino
`Makefile` / `arduino-cli` flow does not support the ESP32-C6 target used here).

```bash
# Build
pio run -e nesso_n1

# Upload
pio run -e nesso_n1 -t upload
```

Build output is placed in `.pio/build/nesso_n1/`:

- `firmware.bin` — application image
- `firmware.factory.bin` — merged image (bootloader + partition table + app),
  flash from offset `0x0`

The current build uses roughly **71% of the 1.25 MB application slot** and about
**17% of RAM**.

## Known limitations / not yet done

- **Not hardware-tested**: display initialization, button mapping, battery scaling
  and RF switching all still need verification on a physical unit.
- **No Wi-Fi / Remote** support (`HAS_WIFI` disabled).
- **No console** (USB console is disabled in this build).
- **Deep sleep / power-off** is not implemented for this board yet.
- The BLE and display code paths share the SPI/I2C buses with the radio; timing issues
  under load have not been fully characterized.
- Radio and display share the same SPI bus, so display refreshes are kept small and
  are done outside the radio's critical sections where possible.

## Contributing / feedback

This is an experimental personal port. Issues, testing feedback and pull requests are
welcome, but keep in mind that the upstream project is the authoritative source for
RNode. For anything not specific to the Nesso N1, please refer to the upstream
repository and documentation:

- Upstream firmware: <https://github.com/markqvist/RNode_Firmware>
- Reticulum network: https://reticulum.network

## License

This project is licensed under the **GNU General Public License v3.0**, the same
license as the upstream RNode Firmware. See the [`LICENSE`](./LICENSE) file for details.
