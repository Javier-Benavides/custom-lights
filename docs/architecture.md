# Architecture

luces is small on purpose: Python's standard library, `curl`, and about 3,100 lines. Each folder has one job, and a test stops the layers from mixing.

## Layers

```text
                    cli.py   service.py
                       │         │
        ┌──────────────┼─────────┼──────────────┐
        ▼              ▼         ▼              ▼
    settings.py     scenes/   hardware/       data/
                       │      (LEDs)          (network)
                       ▼
                    color.py
                       │
                       ▼
                    physics/     nothing below this
```

| Folder | Job | May import |
|---|---|---|
| `luces/physics/` | Models of light and motion: numbers in, numbers out | Only the standard library and itself |
| `luces/color.py` | From what the eye sees to bytes | `physics` |
| `luces/scenes/` | One scene per file: an instant becomes colors per zone | `physics`, `color` |
| `luces/data/` | Downloads and parses observed data. The only network code | `settings`, `paths` |
| `luces/hardware/` | Talks to real LEDs and devices | Nothing of this project |
| `luces/emitter.py` | Sends colors to one slow device from its own thread | `color` |
| `luces/service.py` | The loop: read, compute, smooth, send | Everything above |
| `luces/cli.py` | The `luces` command. Writes a small file the service watches | Everything above |
| `luces/settings.py`, `paths.py` | Reads and validates settings, and where files live | Nothing else |

`tests/test_architecture.py` fails if these rules break.

## One frame

1. `service.cycle()` reads the control files, only if they changed.
2. `scenes.render(name, ctx)` gives `{zone: (rgb, brightness)}`. Scenes are pure: the same `Context` gives the same result.
3. `linear_target` turns color and brightness into light.
4. `Fade.step` smooths in linear light.
5. `with_flash` puts lightning on top: it lasts less than the smoothing does.
6. `device_color` gives each enabled device the light of its zone, and its emitter takes it without making the loop wait.
7. `frame` turns light into bytes per LED.
8. It sends only if the frame changed, plus one refresh a minute.

## Two services, least privilege

| Service | Network | Chip | Why |
|---|---|---|---|
| `luces.service` | None | Yes, and the enabled devices | Touches the hardware, so it cannot reach the internet |
| `luces-data.service` | Yes | None | Reaches the internet, so it cannot see any device |

They share only JSON files under `/var/lib/luces`. Both run as a system user with a tight systemd sandbox, in `system/`.

## Where to change what

| I want to | Go to |
|---|---|
| Change a color, a rhythm or a time | `luces/settings.toml`, or `luces settings` on an installed system |
| Change how a phenomenon works | `luces/physics/`, and its page in `docs/physics/` |
| Change how a scene combines things | `luces/scenes/` |
| Parse a new data format | `luces/data/` |
| Support a new controller or device | `luces/hardware/`, with the hardware in hand |
| Add a command | `luces/cli.py` |

## How to add things

**A pattern.** A frozen dataclass in `luces/physics/` whose `__call__(t)` returns a number, with no clock, files or settings. Add a test in `tests/physics/` that uses it alone, and a section in its page. See [`luces/physics/AGENTS.md`](../luces/physics/AGENTS.md).

**A scene.** A new file in `luces/scenes/` with `render(ctx)` and `SCENE = Scene(...)`. Register it in `luces/scenes/__init__.py`, add its settings to `settings.toml`, validate them in `settings.py`, and add the name to `SCENES` in `settings.py` and `NAMES` in `cli.py`.

**A data source.** See [data-sources.md](data-sources.md). A new host needs a maintainer.

**An output or a device.** See [hardware.md](hardware.md).

## Design rules

- **Stateless scenes.** Time goes in, color comes out. Nothing depends on what happened before, so everything can be tested and replayed.
- **Data is optional.** Every source can fail, and the scene goes on.
- **Settings are data.** Anything a person might tune lives in `settings.toml`, is validated, and has a comment.
- **Bad settings never stop the lights.** The service keeps the last valid ones and reports the error.
- **Small files.** One concept per file, so a person or an agent reads only what the task needs.
