#!/usr/bin/env python3
"""Full-flash backup / restore helper for the Arduino Nesso N1 (ESP32-C6).

The Nesso N1 ships with Meshtastic. Before flashing the experimental RNode
port we take a complete image of the 16 MB SPI flash: that single file
contains the Meshtastic 2.8.1 application, bootloader, partition table, NVS
(settings and keys), SPIFFS and otadata, so it is enough to put the device
back exactly as it was.

Usage:
    python3 tools/nesso_flash_backup.py info
    python3 tools/nesso_flash_backup.py backup --out-dir ~/nesso_backup
    python3 tools/nesso_flash_backup.py restore ~/nesso_backup/nesso_backup_XXXX.bin --yes

The script uses the system `esptool` (or `esptool` from PATH) and auto-detects
the serial port when only one /dev/ttyACM* or /dev/ttyUSB* device is present.
"""

import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time


ESPTOOL = "/usr/bin/esptool" if os.path.exists("/usr/bin/esptool") else shutil.which("esptool")
CHIP = "esp32c6"
BAUD = 460800
DEFAULT_OUT_DIR = os.path.join(os.path.expanduser("~"), "nesso_backup")


def find_port(explicit):
    if explicit:
        if not os.path.exists(explicit):
            sys.exit("port does not exist: %s" % explicit)
        return explicit
    ports = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    if not ports:
        sys.exit("no serial port found; connect the Nesso N1 or pass --port")
    if len(ports) > 1:
        sys.exit("multiple serial ports found (%s); pass --port" % ", ".join(ports))
    return ports[0]


def esptool_base(port):
    return [ESPTOOL, "--chip", CHIP, "-p", port, "-b", str(BAUD)]


def run(cmd, capture=False):
    print("+ " + " ".join(cmd), flush=True)
    if capture:
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return subprocess.run(cmd)


def probe_flash(port):
    res = run(esptool_base(port) + ["flash_id"], capture=True)
    out = res.stdout or ""
    print(out, end="" if out.endswith("\n") else "\n", flush=True)
    if res.returncode != 0:
        sys.exit("esptool flash_id failed (exit %d)" % res.returncode)
    match = re.search(r"Detected flash size:\s*(\d+)\s*(MB|KB)", out)
    if not match:
        sys.exit("could not parse flash size from esptool output")
    value, unit = int(match.group(1)), match.group(2)
    size = value * 1024 * 1024 if unit == "MB" else value * 1024
    return size, out


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cmd_info(args):
    port = find_port(args.port)
    probe_flash(port)


def cmd_backup(args):
    port = find_port(args.port)
    flash_size, info = probe_flash(port)
    os.makedirs(args.out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(args.out_dir, "nesso_backup_%s.bin" % stamp)

    res = run(esptool_base(port) + ["read_flash", "0x0", hex(flash_size), path])
    if res.returncode != 0:
        sys.exit("read_flash failed (exit %d)" % res.returncode)

    actual = os.path.getsize(path)
    if actual != flash_size:
        sys.exit("backup size %d != detected flash size %d" % (actual, flash_size))

    digest = sha256_file(path)
    with open(path + ".sha256", "w") as handle:
        handle.write("%s  %s\n" % (digest, os.path.basename(path)))
    with open(path + ".info.txt", "w") as handle:
        handle.write(info)
        handle.write("\nflash_size=%d\nsha256=%s\n" % (flash_size, digest))

    if not args.no_verify:
        res = run(esptool_base(port) + ["verify_flash", "0x0", path])
        if res.returncode != 0:
            sys.exit("verify_flash failed: backup does not match flash")

    print("\nbackup: %s" % path)
    print("size:   %d bytes" % actual)
    print("sha256: %s" % digest)


def cmd_restore(args):
    path = os.path.abspath(args.backup)
    if not os.path.exists(path):
        sys.exit("backup not found: %s" % path)

    sha_path = path + ".sha256"
    if os.path.exists(sha_path):
        expected = open(sha_path).read().split()[0]
        actual = sha256_file(path)
        if expected != actual:
            sys.exit("backup checksum mismatch: %s != %s" % (actual, expected))
        print("checksum OK: %s" % actual)

    port = find_port(args.port)
    flash_size, _ = probe_flash(port)
    image_size = os.path.getsize(path)
    if image_size != flash_size:
        sys.exit("backup size %d != detected flash size %d" % (image_size, flash_size))

    if not args.yes:
        print("About to overwrite the whole %d byte flash of %s with:\n  %s" % (flash_size, port, path))
        if input("Type YES to continue: ") != "YES":
            sys.exit("aborted")

    res = run(esptool_base(port) + ["write_flash", "0x0", path])
    if res.returncode != 0:
        sys.exit("write_flash failed (exit %d)" % res.returncode)

    res = run(esptool_base(port) + ["verify_flash", "0x0", path])
    if res.returncode != 0:
        sys.exit("verify_flash failed: restore does not match backup")

    print("\nrestore complete: %s" % path)


def main():
    ap = argparse.ArgumentParser(description="Backup/restore the full Nesso N1 flash")
    sub = ap.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="show chip and flash information")
    info.add_argument("--port")
    info.set_defaults(func=cmd_info)

    backup = sub.add_parser("backup", help="dump the whole SPI flash")
    backup.add_argument("--port")
    backup.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    backup.add_argument("--no-verify", action="store_true", help="skip read-back verification")
    backup.set_defaults(func=cmd_backup)

    restore = sub.add_parser("restore", help="write a full-flash backup back to the device")
    restore.add_argument("backup")
    restore.add_argument("--port")
    restore.add_argument("--yes", action="store_true")
    restore.set_defaults(func=cmd_restore)

    args = ap.parse_args()
    if not ESPTOOL:
        sys.exit("esptool not found; install it or use /usr/bin/esptool")
    args.func(args)


if __name__ == "__main__":
    main()
