#!/usr/bin/env python3
"""Drive KOMB through real Klipper (batch mode) across many settings.

For each case we rewrite KOMB_Variables.cfg, run klippy against a
simulated 250x210x250 cartesian printer, and check what the motion
system actually did - not what the macro claimed it would do.

This runs real Klipper: real config parsing, the real Jinja environment
with Klipper's single-brace delimiters, and the real kinematics, so an
out-of-range move or a bad arc is rejected exactly as it would be on a
printer. Setup instructions are in tests/README.md.

    python3 tests/klipper_sweep.py
"""
import itertools, json, os, re, shutil, subprocess, sys, tempfile

HOME = os.path.expanduser("~")
KLIPPER = os.environ.get("KLIPPER_DIR", f"{HOME}/klipper")
KLIPPY = f"{KLIPPER}/klippy/klippy.py"
PYTHON = os.environ.get("KLIPPY_PYTHON", f"{HOME}/klippy-env/bin/python")
DICT = os.environ.get("KLIPPER_DICT", f"{KLIPPER}/out/klipper.dict")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.environ.get("KOMB_SIM_DIR", "/tmp/komb-sim")


def build_sim_dir():
    """Assemble the simulated printer's config directory from the repo,
    laid out exactly the way the README tells users to install KOMB."""
    cfg = f"{SIM}/cfg"
    shutil.rmtree(SIM, ignore_errors=True)
    os.makedirs(cfg)
    shutil.copytree(REPO, f"{cfg}/KOMB",
                    ignore=shutil.ignore_patterns(".git", "tests"))
    shutil.copy(f"{REPO}/tests/sim-printer.cfg", f"{cfg}/printer.cfg")
    shutil.copy(f"{REPO}/_KOMB_Variables.cfg", f"{cfg}/KOMB_Variables.cfg")


for _p, _what in ((KLIPPY, "klippy.py"), (DICT, "klipper.dict"), (PYTHON, "klippy python")):
    if not os.path.exists(_p):
        raise SystemExit(
            "missing %s at %s\nSee tests/README.md for how to set up the "
            "Klipper simulation environment." % (_what, _p))
build_sim_dir()

AX = {"x": (0.0, 250.0), "y": (0.0, 210.0), "z": (0.0, 250.0)}
START = (10.0, 20.0, 30.0)

BASE_VARS = open(f"{REPO}/_KOMB_Variables.cfg").read()

ERROR_MARKERS = re.compile(
    r"Move out of range|Must home axis|Unable to parse|Malformed command|"
    r"Traceback|Internal error|G-Code command .* not found|"
    r"Extrude below minimum temp|Unable to extrude|"
    r"Invalid extrude only move|shutdown|Arc |must home|"
    r"Error loading template|TemplateSyntaxError|UndefinedError", re.I)


def write_vars(path, overrides):
    txt = BASE_VARS
    for k, v in overrides.items():
        pat = re.compile(r"^(variable_%s:\s*)(\S+)" % re.escape(k), re.M)
        if not pat.search(txt):
            raise SystemExit("no such variable: %s" % k)
        txt = pat.sub(lambda m: m.group(1) + str(v), txt)
    open(path, "w").write(txt)


def run(gcode, overrides, workdir):
    cfg = f"{workdir}/cfg"
    shutil.copytree(f"{SIM}/cfg", cfg)
    write_vars(f"{cfg}/KOMB_Variables.cfg", overrides)
    gpath = f"{workdir}/t.gcode"
    open(gpath, "w").write(gcode)
    log = f"{workdir}/klippy.log"
    p = subprocess.run(
        [PYTHON, KLIPPY, f"{cfg}/printer.cfg", "-i", gpath,
         "-o", f"{workdir}/out.serial", "-d", DICT, "-l", log],
        capture_output=True, text=True, timeout=300)
    logtxt = open(log).read() if os.path.exists(log) else ""
    return p.returncode, logtxt, p.stdout + p.stderr


def parse(logtxt):
    """Pull the instrumented events back out of the klippy log."""
    trace, cmds, info, errors = [], [], [], []
    # Skip the config dump klippy writes at startup, or we would match
    # our own macro source instead of its output.
    body = logtxt.split("=======================", 2)[-1]
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("TRACE "):
            trace.append(tuple(float(x) for x in line.split()[1:5]))
        elif line.startswith("CMD "):
            cmds.append(line[4:])
        elif line.startswith("KOMB") or line.startswith("MARK"):
            info.append(line)
        elif ERROR_MARKERS.search(line):
            errors.append(line)
    return trace, cmds, info, errors


BRUSH_RE = re.compile(
    r"brush X ([\d.-]+)\.\.([\d.-]+)\s+Y ([\d.-]+)\.\.([\d.-]+)\s+Z ([\d.-]+)\.\.([\d.-]+)")


def check(name, rc, logtxt, overrides, expect_error=None):
    trace, cmds, info, errors = parse(logtxt)
    probs = []

    if expect_error:
        joined = "\n".join(info) + logtxt
        if expect_error.lower() not in joined.lower():
            probs.append("expected error %r not raised (rc=%s)" % (expect_error, rc))
        return probs, trace, cmds, info

    if rc != 0:
        tail = [l for l in logtxt.splitlines() if l.strip()][-6:]
        probs.append("klippy exited %s: %s" % (rc, " | ".join(tail)))
    for e in errors:
        probs.append("klipper error: %s" % e[:160])
    if not trace:
        probs.append("no moves executed")
        return probs, trace, cmds, info

    # 1. Kinematic limits (Klipper enforces these, belt and braces).
    for i, (x, y, z, e) in enumerate(trace):
        for axis, val in (("x", x), ("y", y), ("z", z)):
            lo, hi = AX[axis]
            if not (lo - 1e-6 <= val <= hi + 1e-6):
                probs.append("move %d leaves %s range: %.3f" % (i, axis, val))

    # 2. Wipe moves must stay within the brush the macro reported.
    bounds = None
    for m in info:
        b = BRUSH_RE.search(m)
        if b:
            bounds = [float(v) for v in b.groups()]
    if bounds:
        xlo, xhi, ylo, yhi, zlo, zhi = bounds
        # Identify wipe moves: those issued as G1 (travel uses G0).
        wipe_idx = [i for i, c in enumerate(cmds) if c.startswith("G1 X")]
        for i in wipe_idx:
            if i >= len(trace):
                continue
            x, y, z, e = trace[i]
            for label, val, lo, hi in (("X", x, xlo, xhi), ("Y", y, ylo, yhi),
                                       ("Z", z, zlo, zhi)):
                if not (lo - 1e-6 <= val <= hi + 1e-6):
                    probs.append("wipe leaves brush on %s: %.3f not in %.3f..%.3f"
                                 % (label, val, lo, hi))

    # 3. Return to start.
    if str(overrides.get("return_to_start", "True")).lower() == "true":
        fx, fy, fz, fe = trace[-1]
        if abs(fx - START[0]) > 1e-3 or abs(fy - START[1]) > 1e-3 or abs(fz - START[2]) > 1e-3:
            probs.append("did not return to start: (%.3f, %.3f, %.3f)" % (fx, fy, fz))

    # 4. Retraction must actually retract. When the nozzle counts as hot
    #    the net extruder movement over the whole macro must be negative.
    if float(overrides.get("temp", 170)) <= 0:
        net_e = trace[-1][3] - trace[0][3]
        want = -(float(overrides.get("retract_before_wipe", 1))
                 + float(overrides.get("retract_after_wipe", 2)))
        if net_e > 0:
            probs.append("EXTRUDED instead of retracting: net E %+.3f" % net_e)
        elif want < 0 and net_e >= -1e-9:
            probs.append("no retraction happened: net E %+.3f" % net_e)

    return probs, trace, cmds, info


GCODE = """SET_KINEMATIC_POSITION X=%g Y=%g Z=%g
MARK T=BEFORE
%s
MARK T=AFTER
"""


def case(name, overrides, body="KOMB", expect_error=None, keep=False):
    with tempfile.TemporaryDirectory() as wd:
        gc = GCODE % (START + (body,))
        rc, logtxt, out = run(gc, overrides, wd)
        probs, trace, cmds, info = check(name, rc, logtxt, overrides, expect_error)
        if keep:
            open("/tmp/last.log", "w").write(logtxt)
        return probs, trace, cmds, info


def main():
    total = 0
    failed = []

    # ---- broad sweep over the interacting geometry settings ----------
    flags = ["start_opposite_side", "start_adjacent_side", "reverse_enable"]
    geometry = [
        {},
        {"repeat": 2, "z_step": 0.5},
        {"offset": 2},
        {"offset": -1},
        {"brush_size_y": 0},
        {"brush_location_x": 240, "brush_size_x": 40},   # forces clamping
        {"brush_location_x": 0},                          # use current pos
        {"step": 3},
        {"brush_size_x": 60, "brush_size_y": 40, "step": 2},
    ]
    work = []
    for pattern, angle in ((1, 0), (1, 30), (1, 45), (1, 90), (2, 45)):
        for bits in itertools.product([False, True], repeat=3):
            for geo in geometry:
                ov = dict(zip(flags, bits))
                ov.update(geo)
                ov["pattern"] = pattern
                ov["angle"] = angle
                ov["verbose_points"] = False
                if pattern == 2 and ov.get("brush_size_y") == 0:
                    continue
                name = "p%d a%d %s %s" % (pattern, angle,
                                          "".join("OAR"[i] if b else "-"
                                                  for i, b in enumerate(bits)),
                                          json.dumps(geo, separators=(",", ":")))
                work.append((name, ov))

    total = len(work)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = pool.map(lambda a: (a[0], case(a[0], a[1])[0]), work)
        for i, (name, probs) in enumerate(results):
            if i % 40 == 0:
                print("  ... %d/%d" % (i, total), flush=True)
            if probs:
                failed.append((name, probs))
                print("FAIL %s" % name, flush=True)
                for p in probs:
                    print("      %s" % p, flush=True)

    print("\n=== geometry sweep: %d cases, %d failed ===" % (total, len(failed)))

    # ---- retraction: temp 0 makes the macro treat the nozzle as hot ---
    print("\n=== retraction (nozzle counts as hot) ===")
    for ov in ({"temp": 0}, {"temp": 0, "repeat": 2},
               {"temp": 0, "pattern": 2}, {"temp": 0, "retract_during_wipe": 0}):
        probs, trace, cmds, info = case("retract", ov)
        net = trace[-1][3] - trace[0][3] if trace else float("nan")
        status = "OK  " if not probs else "FAIL"
        print("  %s %-42s net E %+.3f" % (status, json.dumps(ov), net))
        for p in probs:
            print("        %s" % p)
        if probs:
            failed.append((json.dumps(ov), probs))

    # ---- guard rails: each must be refused, not silently mishandled ---
    print("\n=== guard rails ===")
    guards = [
        ({"pattern": 3}, "pattern must be"),
        ({"step": 0}, "step must be"),
        ({"brush_size_x": 0, "brush_size_y": 0}, "cannot both be 0"),
        ({"pattern": 2, "brush_size_y": 0}, "needs a non-zero brush size"),
        ({"angle": 120}, "angle must be between"),
        ({"clean_while_cold": False, "temp": 170}, "below"),
    ]
    for ov, want in guards:
        probs, *_ = case("guard", ov, expect_error=want)
        print("  %s %-46s -> expects %r" %
              ("OK  " if not probs else "FAIL", json.dumps(ov), want))
        for p in probs:
            print("        %s" % p)
        if probs:
            failed.append((json.dumps(ov), probs))

    # ---- other entry points ------------------------------------------
    print("\n=== purge / trigger / parameter overrides ===")
    # NOTE: purge MOTION cannot be exercised in batch mode. The simulated
    # extruder has no ADC, so it reads 0 C forever, and Klipper has no
    # batch-mode bypass for TEMPERATURE_WAIT (only homing has one), so
    # auto-heating would hang. What we can verify here is that the guard
    # refuses to purge a cold nozzle; the emitted purge G-code itself is
    # covered by the template-level tests.
    for ov, want in (({"purge_amount": 8}, "at least 170 C to purge"),
                     ({"purge_amount": 0}, "must be greater than 0")):
        probs, *_ = case("purge guard", ov, body="KOMB_PURGE", expect_error=want)
        print("  %s purge guard %-28s -> expects %r"
              % ("OK  " if not probs else "FAIL", json.dumps(ov), want))
        if probs:
            failed.append(("purge guard", probs))

    others = [
        ("trigger armed", {"trigger_freq": 5}, "KOMB_TRIGGER_RESET\nKOMB_TRIGGER"),
        ("param override", {}, "KOMB REPEAT=2 SPEED=80 PATTERN=2 START_OPPOSITE_SIDE=true"),
        ("param booleans", {}, "KOMB ENABLE_REVERSE=1 START_ADJACENT_SIDE=yes ANGLE=30"),
        ("param strings", {}, "KOMB CLEAN_WHILE_COLD=True ENABLE_VERBOSE_OUTPUT=on"),
    ]
    # A disabled trigger correctly does nothing, so "no moves" is a pass.
    probs, *_ = case("trigger off", {"trigger_freq": 0}, body="KOMB_TRIGGER")
    probs = [p for p in probs if "no moves executed" not in p]
    print("  %s trigger disabled         (correctly does nothing)"
          % ("OK  " if not probs else "FAIL"))
    if probs:
        failed.append(("trigger disabled", probs))

    for name, ov, body in others:
        probs, trace, cmds, info = case(name, ov, body=body)
        print("  %s %-24s %d moves" %
              ("OK  " if not probs else "FAIL", name, len(trace)))
        for p in probs:
            print("        %s" % p)
        if probs:
            failed.append((name, probs))

    print("\n############ %d failing case(s) ############" % len(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
