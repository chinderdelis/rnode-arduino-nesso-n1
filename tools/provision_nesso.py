#!/usr/bin/env python3
"""Provision an RNode Nesso N1 over the KISS serial protocol.

The upstream `rnodeconf` utility does not know the Nesso N1 (product 0xEC,
models 0xEF/0xF1), so this script writes the minimum EEPROM state needed for
the firmware to consider the device provisioned:

  * info block (product / model / hwrev / serial / made) + MD5 checksum
  * optional default LoRa config (so the radio starts on boot)
  * info lock byte
  * firmware hash target (must match the running app partition)

The Ed25519 EEPROM signature is *not* written (it would need Mark Qvist's
private key). The firmware does not use it to gate the radio; it only affects
a cosmetic logo bitmap.

Usage:
    python3 tools/provision_nesso.py --port /dev/ttyACM0 --firmware .pio/build/nesso_n1/firmware.bin
    python3 tools/provision_nesso.py --dump

Requires pyserial (`pip install pyserial`).

NOTE: run this *after* flashing the Nesso build. It speaks the RNode KISS
protocol; it will refuse to touch a device that is not running RNode firmware.
"""

import argparse
import hashlib
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.stderr.write("pyserial is required: pip install pyserial\n")
    sys.exit(2)

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

CMD_FW_VERSION = 0x50
CMD_ROM_READ = 0x51
CMD_ROM_WRITE = 0x52
CMD_RESET = 0x55
CMD_FW_HASH = 0x58
CMD_UNLOCK_ROM = 0x59
CMD_HASHES = 0x60
CMD_ERROR = 0x90
ROM_UNLOCK_BYTE = 0xF8
CMD_RESET_BYTE = 0xF8

ADDR_PRODUCT = 0x00
ADDR_MODEL = 0x01
ADDR_HW_REV = 0x02
ADDR_SERIAL = 0x03
ADDR_MADE = 0x07
ADDR_CHKSUM = 0x0B
ADDR_INFO_LOCK = 0x9B
ADDR_CONF_SF = 0x9C
ADDR_CONF_CR = 0x9D
ADDR_CONF_TXP = 0x9E
ADDR_CONF_BW = 0x9F
ADDR_CONF_FREQ = 0xA3
ADDR_CONF_OK = 0xA7

CHECKSUMMED_SIZE = 0x0B
EEPROM_RESERVED = 200
ROM_READ_TIMEOUT = 2.5
INFO_LOCK_BYTE = 0x73
CONF_OK_BYTE = 0x73
PRODUCT_NESSO_N1 = 0xEC
MODEL_EF = 0xEF
MODEL_F1 = 0xF1
MODELS = {MODEL_EF: "868/915 MHz", MODEL_F1: "433 MHz"}


def escape(data):
    out = bytearray()
    for b in data:
        if b == FEND:
            out += bytes([FESC, TFEND])
        elif b == FESC:
            out += bytes([FESC, TFESC])
        else:
            out.append(b)
    return bytes(out)


def frame(cmd, data=b""):
    return bytes([FEND, cmd]) + escape(data) + bytes([FEND])


class KissParser:
    def __init__(self):
        self.in_frame = False
        self.cmd = None
        self.data = bytearray()
        self.escape = False

    def feed(self, buf):
        frames = []
        for b in buf:
            if b == FEND:
                if self.in_frame and self.cmd is not None:
                    frames.append((self.cmd, bytes(self.data)))
                self.in_frame = True
                self.cmd = None
                self.data = bytearray()
                self.escape = False
                continue
            if not self.in_frame:
                continue
            if self.cmd is None:
                self.cmd = b
                continue
            if b == FESC:
                self.escape = True
                continue
            if self.escape:
                if b == TFEND:
                    b = FEND
                elif b == TFESC:
                    b = FESC
                self.escape = False
            self.data.append(b)
        return frames


def find_port(explicit):
    if explicit:
        import os
        if os.path.exists(explicit):
            return explicit
    candidates = []
    for p in list_ports.comports():
        hay = " ".join(str(x) for x in (p.device, p.description, p.hwid) if x).upper()
        if "303A" in hay or "2341" in hay or "JTAG" in hay or "NESSO" in hay:
            candidates.append(p.device)
    if not candidates:
        candidates = [p.device for p in list_ports.comports()
                      if "ACM" in p.device or "USB" in p.device]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("no serial port found; use --port")
    raise RuntimeError("multiple serial ports found (%s); use --port" % ", ".join(candidates))


def open_serial(port):
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.bytesize = 8
    ser.parity = serial.PARITY_NONE
    ser.stopbits = 1
    ser.xonxoff = False
    ser.rtscts = False
    ser.dsrdtr = False
    ser.timeout = 0
    ser.write_timeout = 2
    # Avoid asserting DTR/RTS on open (can reset some boards).
    ser._dtr_state = False
    ser._rts_state = False
    ser.open()
    try:
        ser.dtr = False
        ser.rts = False
    except Exception:
        pass
    return ser


class Device:
    def __init__(self, port):
        self.port = port
        self.ser = None
        self.parser = KissParser()
        self.frames = []

    def connect(self, timeout=15):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                port = find_port(self.port)
                self.ser = open_serial(port)
                self.port = port
                self.parser = KissParser()
                self.frames = []
                time.sleep(0.2)
                return
            except Exception as e:
                last = e
                time.sleep(0.3)
        raise RuntimeError("could not open serial port: %s" % last)

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def send(self, cmd, data=b""):
        self.ser.write(frame(cmd, data))
        self.ser.flush()

    def pump(self, duration):
        deadline = time.time() + duration
        while time.time() < deadline:
            try:
                n = self.ser.in_waiting
                chunk = self.ser.read(n if n else 1)
            except Exception:
                time.sleep(0.02)
                continue
            if chunk:
                self.frames.extend(self.parser.feed(chunk))
            else:
                time.sleep(0.01)

    def wait_for(self, cmd, duration=2.0, min_len=0, pred=None):
        deadline = time.time() + duration
        while time.time() < deadline:
            for i, (c, d) in enumerate(self.frames):
                if c == cmd and len(d) >= min_len and (pred is None or pred(d)):
                    del self.frames[:i + 1]
                    return d
            self.pump(0.05)
        return None

    def read_rom(self, duration=2.5):
        self.frames = []
        self.send(CMD_ROM_READ, b"\x00")
        d = self.wait_for(CMD_ROM_READ, duration, EEPROM_RESERVED)
        if d is None:
            return None
        return d[:EEPROM_RESERVED]

    def read_hash(self, which, duration=2.0):
        self.frames = []
        self.send(CMD_HASHES, bytes([which]))
        d = self.wait_for(CMD_HASHES, duration, 33, lambda x: x[0] == which)
        if d is None:
            return None
        return d[1:33]

    def write_rom(self, addr, value):
        self.send(CMD_ROM_WRITE, bytes([addr, value]))
        self.pump(0.10)

    def reset(self):
        try:
            self.send(CMD_RESET, bytes([CMD_RESET_BYTE]))
            self.pump(0.2)
        except Exception:
            pass
        self.close()

    def reconnect(self, timeout=20):
        self.close()
        self.connect(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            rom = self.read_rom(duration=ROM_READ_TIMEOUT)
            if rom is not None:
                return rom
            self.close()
            time.sleep(0.3)
            try:
                self.connect(timeout=max(1, deadline - time.time()))
            except Exception:
                pass
        self.close()
        raise RuntimeError("device did not answer after reset")


def embedded_hash(path):
    data = open(path, "rb").read()
    if len(data) < 32:
        raise RuntimeError("firmware image too small: %s" % path)
    calc = hashlib.sha256(data[:-32]).digest()
    if calc != data[-32:]:
        raise RuntimeError("firmware image does not carry a valid appended SHA256")
    return data[-32:]


def build_info(model, hwrev, serial_no, made):
    info = bytearray()
    info.append(PRODUCT_NESSO_N1)
    info.append(model)
    info.append(hwrev)
    info += serial_no.to_bytes(4, "big")
    info += made.to_bytes(4, "big")
    return bytes(info)


def build_config(freq, bw, sf, cr, txp):
    cfg = bytearray()
    cfg += bytes([sf, cr, txp])
    cfg += int(bw).to_bytes(4, "big")
    cfg += int(freq).to_bytes(4, "big")
    cfg.append(CONF_OK_BYTE)
    return bytes(cfg)


def valid_info(rom, model):
    if rom[ADDR_PRODUCT] != PRODUCT_NESSO_N1:
        return False
    if rom[ADDR_MODEL] not in MODELS:
        return False
    if model is not None and rom[ADDR_MODEL] != model:
        return False
    if rom[ADDR_HW_REV] in (0x00, 0xFF):
        return False
    if rom[ADDR_INFO_LOCK] != INFO_LOCK_BYTE:
        return False
    calc = hashlib.md5(rom[:CHECKSUMMED_SIZE]).digest()
    return calc == bytes(rom[ADDR_CHKSUM:ADDR_CHKSUM + 16])


def dump(dev):
    rom = dev.read_rom()
    if rom is None:
        print("No RNode response. Is the Nesso RNode firmware flashed?")
        return 1
    print("EEPROM info block:")
    print("  product : 0x%02X" % rom[ADDR_PRODUCT])
    print("  model   : 0x%02X (%s)" % (rom[ADDR_MODEL], MODELS.get(rom[ADDR_MODEL], "unknown")))
    print("  hwrev   : 0x%02X" % rom[ADDR_HW_REV])
    print("  serial  : %s" % rom[ADDR_SERIAL:ADDR_SERIAL + 4].hex())
    print("  made    : %s" % rom[ADDR_MADE:ADDR_MADE + 4].hex())
    print("  lock    : 0x%02X (%s)" % (rom[ADDR_INFO_LOCK],
          "locked" if rom[ADDR_INFO_LOCK] == INFO_LOCK_BYTE else "unlocked"))
    print("  info ok : %s" % valid_info(rom, None))
    print("  conf ok : %s" % (rom[ADDR_CONF_OK] == CONF_OK_BYTE))
    tgt = dev.read_hash(0x01)
    cur = dev.read_hash(0x02)
    print("  fw hash target : %s" % (tgt.hex() if tgt else "n/a"))
    print("  fw hash actual : %s" % (cur.hex() if cur else "n/a"))
    if tgt and cur:
        print("  fw hash match  : %s" % (tgt == cur))
    return 0


def provision(dev, args):
    rom = dev.read_rom()
    if rom is None:
        print("No RNode response. Flash the Nesso RNode firmware first.")
        return 1

    locked = rom[ADDR_INFO_LOCK] == INFO_LOCK_BYTE
    already = valid_info(rom, args.model)

    if locked and not already:
        if not args.force:
            print("EEPROM is locked with a non-Nesso configuration.")
            print("Use --force to erase and re-provision (this wipes the EEPROM).")
            return 1
        print("Erasing locked EEPROM...")
        dev.frames = []
        dev.send(CMD_UNLOCK_ROM, bytes([ROM_UNLOCK_BYTE]))
        time.sleep(2.0)
        rom = dev.reconnect(timeout=30)
        locked = False

    if locked and already and not args.force:
        print("EEPROM already contains a valid Nesso configuration.")
    else:
        info = build_info(args.model, args.hwrev, args.serial, args.made)
        checksum = hashlib.md5(info).digest()
        cfg = build_config(args.freq, args.bw, args.sf, args.cr, args.txp)

        if not args.yes:
            ans = input("Write provisioning data to %s? [y/N] " % dev.port).strip().lower()
            if ans not in ("y", "yes"):
                return 1

        print("Writing info block...")
        for i, b in enumerate(info):
            dev.write_rom(ADDR_PRODUCT + i, b)
        print("Writing checksum...")
        for i, b in enumerate(checksum):
            dev.write_rom(ADDR_CHKSUM + i, b)
        if not args.no_config:
            print("Writing default LoRa config...")
            for i, b in enumerate(cfg):
                dev.write_rom(ADDR_CONF_SF + i, b)
        print("Locking EEPROM...")
        dev.write_rom(ADDR_INFO_LOCK, INFO_LOCK_BYTE)
        time.sleep(0.3)

        print("Resetting device...")
        dev.reset()
        rom = dev.reconnect()
        if not valid_info(rom, args.model):
            print("Provisioning verification failed (info/checksum/lock).")
            return 1
        print("Info block written and verified.")

    # Firmware hash: prefer the value computed by the device itself, fall back
    # to the SHA256 appended to the firmware image.
    current = dev.read_hash(0x02)
    target = None
    if current is not None and any(current):
        target = current
    elif args.firmware:
        target = embedded_hash(args.firmware)
        print("Device did not report a computed hash; using image hash.")
    else:
        print("Could not determine firmware hash. Pass --firmware <firmware.bin>.")
        return 1

    tgt = dev.read_hash(0x01)
    if tgt == target:
        print("Firmware hash already correct: %s" % target.hex())
    else:
        print("Writing firmware hash target: %s" % target.hex())
        dev.frames = []
        dev.send(CMD_FW_HASH, target)
        time.sleep(1.0)
        try:
            dev.reset()
        except Exception:
            dev.close()
        rom = dev.reconnect()

    tgt = dev.read_hash(0x01)
    cur = dev.read_hash(0x02)
    print("")
    print("Result:")
    print("  product/model : 0x%02X / 0x%02X (%s)" % (
        rom[ADDR_PRODUCT], rom[ADDR_MODEL], MODELS.get(rom[ADDR_MODEL], "unknown")))
    print("  lock          : %s" % ("locked" if rom[ADDR_INFO_LOCK] == INFO_LOCK_BYTE else "unlocked"))
    print("  info valid    : %s" % valid_info(rom, args.model))
    print("  config present: %s" % (rom[ADDR_CONF_OK] == CONF_OK_BYTE))
    print("  fw hash target: %s" % (tgt.hex() if tgt else "n/a"))
    print("  fw hash actual: %s" % (cur.hex() if cur else "n/a"))
    ok = bool(tgt) and bool(cur) and tgt == cur
    print("  fw hash match : %s" % ok)
    if not ok:
        print("")
        print("Firmware hash mismatch: the device will report an invalid firmware.")
        return 1
    print("")
    print("Provisioning complete.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Provision an RNode Nesso N1 over KISS serial")
    ap.add_argument("--port", help="serial port (auto-detected if omitted)")
    ap.add_argument("--firmware", help="firmware.bin used for the appended SHA256 fallback")
    ap.add_argument("--model", type=lambda x: int(x, 0), default=MODEL_EF,
                    choices=[MODEL_EF, MODEL_F1], help="0xEF = 868/915 MHz (default), 0xF1 = 433 MHz")
    ap.add_argument("--hwrev", type=lambda x: int(x, 0), default=0x01)
    ap.add_argument("--serial", type=lambda x: int(x, 0), default=0x00000001)
    ap.add_argument("--made", type=lambda x: int(x, 0), default=0x00000000)
    ap.add_argument("--freq", type=int, default=869525000)
    ap.add_argument("--bw", type=int, default=125000)
    ap.add_argument("--sf", type=int, default=8)
    ap.add_argument("--cr", type=int, default=5)
    ap.add_argument("--txp", type=int, default=14)
    ap.add_argument("--no-config", action="store_true", help="do not write a default LoRa config")
    ap.add_argument("--force", action="store_true", help="re-provision even if already valid / locked")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ap.add_argument("--dump", action="store_true", help="only print the current EEPROM state")
    args = ap.parse_args()

    dev = Device(args.port)
    try:
        dev.connect()
        if args.dump:
            return dump(dev)
        return provision(dev, args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 1
    finally:
        dev.close()


if __name__ == "__main__":
    sys.exit(main())
