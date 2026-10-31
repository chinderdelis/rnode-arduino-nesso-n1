# Security Policy

## Supported versions

This repository contains an experimental, hardware-tested port. Only the latest
release and the current `master` branch receive fixes. Older builds and local
modifications are unsupported.

## Reporting a vulnerability

Please do not open a public issue for security problems.

Use GitHub's private vulnerability reporting for this repository:

<https://github.com/chinderdelis/rnode-arduino-nesso-n1/security/advisories/new>

If that form is unavailable, contact the repository maintainer through GitHub
and ask for a private reporting channel. Do not include passwords, private keys,
API tokens, full flash dumps or other sensitive data in a public issue, pull
request or log.

## What to include

- Affected firmware version, release tag or commit.
- Nesso N1 hardware and radio configuration.
- A description of the issue and its impact.
- Reproduction steps or a proof of concept.
- Relevant logs with secrets and device-specific identifiers removed.
- Any suggested mitigation.

## Scope

Security reports are especially relevant for:

- Radio protocol handling and packet parsing.
- KISS/HDLC framing and command handling.
- BLE pairing, connection handling and data transport.
- Firmware update and provisioning paths.
- Handling of untrusted serial or over-the-air input.

This project is not production-ready, is distributed under GPLv3 and is provided
without warranty. See [`LICENSE`](./LICENSE) for the full license terms.
