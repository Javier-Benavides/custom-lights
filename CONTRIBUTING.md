# Contributing

Thanks for looking at this. You can run everything here with no LEDs.

## Start

```bash
git clone <this repository>
cd luces
python3 -m unittest discover -s tests -t .
python3 examples/fire_in_terminal.py
```

Python 3.11 or newer. There is nothing to install.

## What is welcome

- **A new pattern:** rain, waves, a candle, an aurora. Bring a source or a measurement.
- **Better physics:** a better model, a real measurement, a source that contradicts ours.
- **A new scene.**
- **A new controller or device:** see [docs/hardware.md](docs/hardware.md). You need the hardware.
- **Calibration:** how the colors look on your LEDs.

Read [docs/architecture.md](docs/architecture.md) for where things go, and [docs/decisions.md](docs/decisions.md) before changing behavior.

## Issues

Use the forms: they ask what a person or an agent needs in order to act. Issues here may be worked by an AI agent after a maintainer writes a spec, see [docs/ai-workflow.md](docs/ai-workflow.md).

Do not post your location. Remove it from logs and `luces status` output.

## Pull requests

- One concept per PR, with tests.
- `python3 -m unittest discover -s tests -t .` and `python3 tools/check_text.py` must pass.
- New physics comes with a source, in `docs/physics/`.
- If you used an AI, say so. It is welcome, and you are still responsible for the code.

Some paths need the owner's review because of what they can break: see `.github/CODEOWNERS`.

## Using an AI agent

Point it at [AGENTS.md](AGENTS.md). `CLAUDE.md` is a link to the same file.

## Style

- Plain Python, standard library only.
- Names say the unit: `fall_s`, `height_km`.
- A comment explains why, not what.
- Numbers a person might tune go in `settings.toml`.

By contributing you agree your work is under the [MIT license](LICENSE), or under the GPL if it goes in `luces/hardware/ite.py`, `razer.py` or `msi_gpu.py`.
