# Testing KOMB

KOMB moves a nozzle around near your bed at speed, so changes to it should be
checked before they reach hardware. There are two levels of test here, and
neither one needs a printer.

## 1. Template tests — fast, no Klipper

```bash
pip install jinja2
python tests/render_test.py
```

Renders every macro through Jinja using **Klipper's delimiters** (blocks are
`{% %}`, but expressions are *single* braces) against a stub `printer` object,
then inspects the G-code that comes out. About a second to run.

Catches: template syntax errors, undefined variables, coordinates outside the
travel volume, wipes that escape the brush footprint, unrendered template
fragments, non-positive feedrates, and whether each guard rail fires with the
message it should.

> Note the single-brace delimiter. It means `E{-value}` is parsed as Jinja's
> whitespace-strip marker and the minus sign is silently swallowed — which is
> how a retraction becomes an extrusion. Always negate with `* -1`.

## 2. Klipper simulation — slower, catches what templates can't

```bash
python3 tests/klipper_sweep.py
```

Runs **real Klipper** in batch mode against a simulated 250×210×250 cartesian
printer: real config parsing, the real Jinja environment, the real motion
planner and the real `gcode_arcs` module. Roughly 360 cases, a few minutes on
8 cores.

This catches things the template tests structurally cannot. For example, a
circle's *arc path* bulges one radius past its own start point, so a G2 whose
endpoints are all in range can still leave the travel volume mid-arc. Klipper
rejects that with `Move out of range`; a template renderer never will.

It also verifies against the motion system rather than the macro's own claims:
that the toolhead really does come back to where it started, and that the
extruder axis really does move *backwards* when retracting.

### Setting it up

You need Klipper's host software, its Python dependencies, and an MCU command
dictionary. No hardware, no Docker, no root:

```bash
git clone --depth 1 https://github.com/Klipper3d/klipper.git ~/klipper
cd ~/klipper
printf 'CONFIG_LOW_LEVEL_OPTIONS=y\nCONFIG_MACH_LINUX=y\n' > .config
make olddefconfig && make -j"$(nproc)"      # produces out/klipper.dict
```

Klipper pins Jinja2 2.11.3, which needs an older Python than most current
distributions ship. [uv](https://docs.astral.sh/uv/) can fetch one without
touching your system:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 ~/klippy-env
uv pip install --python ~/klippy-env/bin/python -r ~/klipper/scripts/klippy-requirements.txt
```

Override the defaults with `KLIPPER_DIR`, `KLIPPY_PYTHON` and `KLIPPER_DICT`
if you keep things elsewhere.

### What it cannot check

- **Anything physical.** There is no collision detection and no model of your
  brush, mount or frame. It only knows the axis-aligned travel volume from
  `printer.cfg`. It cannot tell you the nozzle will hit your brush holder.
- **Purge motion.** The simulated extruder has no ADC, so it reads 0 °C
  forever, and Klipper has no batch-mode bypass for `TEMPERATURE_WAIT` (only
  homing has one). The sweep therefore verifies that `KOMB_PURGE` correctly
  *refuses* a cold nozzle; the purge G-code itself is covered by the template
  tests.
- **Whether the path is a good idea.** A wipe that is legal, in-bounds and
  useless will pass both suites.

Always dry-run a change in the air on real hardware before letting the nozzle
touch the brush.
