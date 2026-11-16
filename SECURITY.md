# Security

## Reporting

Report a vulnerability through GitHub's **private vulnerability reporting**, in the Security tab. Do not open a public issue.

Please say what the problem is, how to reproduce it, and what it could affect. This is a personal project, so replies may take some days.

## In scope

- A way to run code on a machine that has luces installed.
- A way to get data out of a machine, or send it to a new host.
- A chip command that could write to flash or damage a board, or a device command that saves.
- A way for the service to read the keys pressed on the keyboard.
- A way to make the lights exceed 3 flashes a second.
- A way to expose a user's location.
- **Prompt injection:** text that makes an agent working on this repository do something a maintainer did not ask for.

## How the project defends itself

See [docs/threat-model.md](docs/threat-model.md).

## Use at your own risk

luces talks directly to a lighting chip and, if enabled, to a mouse, a GPU light and a keyboard, and installs system services. It has been tested on one machine. See [docs/hardware.md](docs/hardware.md).
