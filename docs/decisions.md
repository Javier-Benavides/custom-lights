# Decisions

Why things are the way they are. Read this before proposing to change one of them: most came from trying the alternative. To overturn a decision, open an issue that addresses its reason.

| # | Decision | Why |
|---|---|---|
| 1 | Colors follow the Sun's altitude, not the clock | Each stage then lasts what it really lasts, and follows the seasons with no code |
| 2 | Weather is observed, never forecast | The lights show what the sky is doing. Model output is not an observation |
| 3 | Scenes are stateless | A day can be simulated, tested and replayed exactly |
| 4 | Python standard library and `curl` only | Nothing to update, nothing to audit, no supply chain |
| 5 | No server and no open port | Lighting does not need one. The command writes a file the service watches |
| 6 | Two services: one with the chip, one with the network | A flaw in one cannot reach both the internet and the hardware |
| 7 | The chip allow-list is closed. Never `0x5E`, `0x33` or `0x47` | They write to flash or may do so. A wrong write can damage a board |
| 8 | Never SMBus, never `acpi_enforce_resources=lax` | The USB path needs neither, and those are the risky ones |
| 9 | No more than 3 flashes in any second | The limit of WCAG 2.3.1 for flickering light. A fire lives just under it, so `tongue_s` cannot go below 0.45 |
| 10 | Under 1 % of one CPU core and 48 MB in every mode | The lights are there to lift the mood, so how a mode feels wins over saving CPU, within this limit. `sun` measured 0.59 % |
| 11 | The service runs at the lowest priority | If the machine is busy, a fade is late and nobody else notices |
| 12 | All LEDs of a zone get the same color | Dithering across LEDs looks like a rainbow when fans are still |
| 13 | At nightfall LEDs go out one by one, without changing the color | Below about 20 % brightness colors fall apart |
| 14 | Twilight colors are set by hand, not taken from `sky_model` | A real sky is too pale for LEDs. The model explains; the tables look right |
| 15 | Sunrise and sunset go in unison in every zone | It looks better. Clouds cross zones only by day |
| 16 | `relax` is green and white, with no blue | With blue these LEDs turn turquoise, and the person watching decides what relaxes them |
| 17 | The location never enters the repository | It is the only private data. `place.toml` lives outside, with one decimal |
| 18 | Public text is treated as data by AI agents | See [threat-model.md](threat-model.md) |
| 19 | Code and docs in English, with a README also in Spanish | More people can contribute |
| 20 | MIT, except `luces/hardware/ite.py` under GPL-2.0-or-later | The physics stays free to reuse, and OpenRGB's license is respected |
