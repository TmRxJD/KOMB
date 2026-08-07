# KOMB — Klipper Optimized Macro for Brushing

A flexible nozzle-brushing macro for Klipper. It works with bed-mounted, gantry-mounted and
frame-mounted brushes, sweeps in three dimensions, and generates the whole tool path up front so
every move is checked against your printer's travel limits before anything starts moving.

> ⚠️ **Read this first.** KOMB drives your nozzle around near your bed and brush. Measure carefully,
> dry-run in the air before letting the nozzle touch anything, and make sure `position_min` /
> `position_max` are set correctly for every axis. See
> [rootiest's axis limits guide](https://github.com/rootiest/zippy_guides/blob/main/guides/axis_limits.md)
> if you are not sure.

---

## Installation

The easiest way to install is with Moonraker's Update Manager, so you get future updates
automatically.

### 1. Clone the repo onto your Klipper host

SSH into your printer and run:

```bash
cd ~
git clone https://github.com/TmRxJD/KOMB
ln -s ~/KOMB ~/printer_data/config/KOMB
cp ~/KOMB/_KOMB_Variables.cfg ~/printer_data/config/KOMB_Variables.cfg
```

The symlink lets Klipper read the macros. The copy is *your* settings file — it lives outside the
repo so updates never overwrite it.

### 2. Include your settings file from `printer.cfg`

Add this line to `~/printer_data/config/printer.cfg`:

```ini
[include KOMB_Variables.cfg]
```

That single include pulls in everything: `KOMB_Variables.cfg` loads `KOMB.cfg`, which in turn loads
`KOMB_Purge.cfg` and `KOMB_Trigger.cfg`.

### 3. (Optional) Enable Moonraker updates

Add to `~/printer_data/config/moonraker.conf`:

```ini
[update_manager KOMB]
type: git_repo
path: ~/KOMB
origin: https://github.com/TmRxJD/KOMB
primary_branch: main
managed_services: klipper
```

Restart Moonraker for this to take effect.

### 4. (Optional) Enable arc support

Pattern 2 (circles) needs arc moves. Add to `printer.cfg` if you don't have it already:

```ini
[gcode_arcs]
resolution: 0.1
```

### 5. Configure and restart

Edit `KOMB_Variables.cfg` to match your brush (see [Measuring your brush](#measuring-your-brush)),
then `FIRMWARE_RESTART`.

---

## Usage

| Macro | What it does |
|---|---|
| `KOMB` | Run a brushing sequence. |
| `KOMB_PURGE` | Purge filament into your purge bucket. |
| `KOMB_TRIGGER` | Layer-change hook — runs `KOMB` every `trigger_freq` mm of height. |
| `KOMB_TRIGGER_RESET` | Resets the trigger height counter. Call from `PRINT_START`. |

Run `KOMB` from the console, from a UI macro button, or from your `PRINT_START` macro.

Every setting can be overridden for a single call without editing the config:

```gcode
KOMB REPEAT=3 SPEED=80 PATTERN=2
```

### Measuring your brush

1. Home the printer, then jog the nozzle to the **bottom-left corner** of the brush. Those X/Y
   readings are `brush_location_x` and `brush_location_y`.
2. Jog to the **top-right corner**. Subtract the first reading from the second to get
   `brush_size_x` and `brush_size_y`.
3. Jog down until the nozzle just touches the top of the bristles. That Z reading is
   `brush_location_z`.
4. `brush_size_z` is how much *further* down the nozzle may sink into the bristles. Start at 1–2 mm.

Set `brush_location_z` a few millimetres high and run `KOMB` once to watch the path in the air
before you let it touch the brush.

A location of `0` means "use wherever the nozzle already is on that axis" — useful for gantry-mounted
brushes where only one axis matters. The printer must already be homed for that to work.

---

## Features

**Flexible movement.** By default KOMB sweeps along X starting from the bottom-left corner. Set
`start_adjacent_side` to sweep along Y instead, and `start_opposite_side` to start at the far end
and sweep back. The two combine, so all four directions are available.

**Two patterns.**

- **Pattern 1 — diagonals.** A zig-zag that crosses the full depth of the brush on every stroke.
  `angle` sets how slanted each stroke is, which in turn sets how far one crossing travels along
  the brush: at 45° a crossing advances by exactly the brush depth, steeper angles advance less and
  scrub more densely, and `0` gives a plain straight-line wipe with no crossing at all. `step` is
  the minimum advance, so a steep angle on a deep brush still makes progress.
- **Pattern 2 — circles.** Walks along the travel axis scribing a full circle at every step. The
  circle radius is half the brush's short side, so it always fits. Requires `[gcode_arcs]`.

**Three-dimensional brushing.** With `repeat` and `z_step`, the nozzle descends a little after each
pass, so more of the nozzle's surface reaches the bristles instead of only the very tip. It never
goes below `brush_location_z - brush_size_z`.

**Mid-print brushing.** `KOMB_TRIGGER` runs KOMB every `trigger_freq` mm of print height. Add it to
your slicer's *after layer change* custom G-code and add `KOMB_TRIGGER_RESET` to `PRINT_START`.
`return_to_start` must be enabled or the toolhead will not come back to the print.

Triggering is not suitable for per-object printing, and needs care with bed-mounted brushes on
bed-slingers — check your clearances. Z-hop applies to the moves to and from the brush, so give
yourself room with `z_hop_height` (2 mm minimum is strongly recommended).

**Purging.** `KOMB_PURGE` extrudes a measured amount into a purge bucket. Useful before Z-offset
probing or any measurement where a clean, ooze-free nozzle matters, without wasting a whole purge
line. Set `purge_amount` above 0 and KOMB will purge before it brushes; or call `KOMB_PURGE` on its
own. Flow rate is set volumetrically in mm³/s and converted using `filament_diameter`.

**Retraction control.** PETG in particular loves to dribble, so retraction is configurable before,
during and after the sequence. Retraction is only applied when the nozzle is actually hot enough
to move filament.

**Safety by construction.** All coordinates are computed and clamped to your configured axis limits
*before* any motion is commanded, and clamped again on the way out. A mis-measured brush produces a
short or oddly-shaped wipe, not an out-of-range error or a crash into a frame member. Settings that
cannot work (zero brush on both axes, circles on a single-axis brush, an out-of-range angle) are
rejected up front with an explanatory message rather than failing mid-move.

**Verbose feedback.** `verbose_enable` prints a summary of what was calculated. `verbose_points`
prints every generated move — very noisy, for debugging only.

Full descriptions of every setting are in the comments in
[`_KOMB_Variables.cfg`](_KOMB_Variables.cfg).

---

## Troubleshooting

**"printer must be homed first"** — Home the printer, or set `auto_home_enable: True`.

**"a brush_location of 0 means 'use the current position'…"** — Klipper renders the whole macro
before it runs any of it, so a `G28` issued by KOMB cannot tell KOMB where the nozzle ended up.
Home first, or give explicit coordinates.

**"nozzle is below N C"** — Either set `clean_while_cold: True`, or set `auto_heat_nozzle: True` so
KOMB heats up for you.

**"pattern 2 needs a non-zero brush size on BOTH axes"** — Circles need area. Use pattern 1 for a
brush measured on one axis only.

**Circles do nothing / arc errors** — Add `[gcode_arcs]` to `printer.cfg`.

**The wipe is shorter than the brush** — Your brush probably extends past a `position_min` /
`position_max` limit and got clamped. Turn on `verbose_enable` to see the clamped bounds.

---

## Testing

KOMB has two test suites, neither of which needs a printer. Please run them before opening a pull
request — see [`tests/README.md`](tests/README.md) for setup.

```bash
python tests/render_test.py     # fast: renders the macros, checks the G-code
python3 tests/klipper_sweep.py  # thorough: runs real Klipper on a simulated printer
```

The second one drives ~360 setting combinations through Klipper's actual config parser, Jinja
environment, motion planner and arc module, and checks what the motion system *did* — that the
toolhead returned to where it started, that the extruder axis moved backwards when retracting, and
that no move or arc left the travel volume.

Neither suite knows anything physical: there is no model of your brush, mount or frame, and no
collision detection. Always dry-run in the air on real hardware before letting the nozzle touch
the brush.

## Contributing

Issues and pull requests are welcome. KOMB has a lot of settings and not every combination has been
exercised on real hardware — if you find one that misbehaves, please open an issue with your
`_KOMB_Variables.cfg` and the verbose console output.

## License

KOMB is free software, licensed under the **GNU General Public License v3.0 or later**. You are free
to use, study, modify and redistribute it, including in forks, provided derivative works are
released under the same license. See [LICENSE](LICENSE) for the full text.

Copyright © 2024 TmRxJD

## Support

If KOMB saved you some nozzle-wiping misery, you can [buy me a Ko-fi](https://ko-fi.com/tmrxjd).

Happy KOMBing!
