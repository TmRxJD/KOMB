"""Render KOMB's gcode templates the way Klipper does, against a fake printer.

This is the fast check: it needs only `pip install jinja2`, runs in about a
second, and catches template errors, out-of-range coordinates and wipes that
escape the brush. It does NOT run Klipper - see klipper_sweep.py for that.

    python tests/render_test.py
"""
import os, re, sys, itertools
from jinja2 import Environment, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Dot(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)

def parse_cfg(path):
    """Return {macro_name: (variables_dict, gcode_template_string)}."""
    macros = {}
    cur = None
    for raw in open(path, encoding="utf-8"):
        m = re.match(r"\[gcode_macro (\S+)\]", raw.strip())
        if m:
            cur = {"name": m.group(1), "vars": {}, "gcode": None, "lines": []}
            macros[m.group(1).lower()] = cur
            continue
        if cur is None:
            continue
        if cur["gcode"] is None:
            v = re.match(r"variable_(\w+)\s*:\s*([^#\n]+)", raw)
            if v:
                val = v.group(2).strip()
                try: val = eval(val, {"__builtins__": {}}, {"True": True, "False": False})
                except Exception: pass
                cur["vars"][v.group(1)] = val
            if raw.strip().startswith("gcode:"):
                cur["gcode"] = []
        else:
            if raw.strip() and not raw[0].isspace():
                cur = None
                continue
            cur["gcode"].append(raw)
    return {k: (v["vars"], "".join(v["gcode"] or [])) for k, v in macros.items()}

cfgs = {}
for f in ("KOMB.cfg", "KOMB_Purge.cfg", "KOMB_Trigger.cfg", "_KOMB_Variables.cfg"):
    cfgs.update(parse_cfg(os.path.join(ROOT, f)))

USER_VARS = cfgs["_komb_variables"][0]

class Err(Exception): pass

def make_printer(homed=True, temp=25.0, pos=(10.0, 20.0, 30.0), uservars=None):
    uv = Dot(uservars or USER_VARS)
    return Dot({
        "toolhead": Dot(position=Dot(x=pos[0], y=pos[1], z=pos[2]),
                        homed_axes="xyz" if homed else "",
                        axis_minimum=Dot(x=0.0, y=0.0, z=0.0),
                        axis_maximum=Dot(x=250.0, y=210.0, z=250.0)),
        "extruder": Dot(temperature=temp),
        "gcode_macro _KOMB_Variables": uv,
        "gcode_macro KOMB_TRIGGER": Dot(cfgs["komb_trigger"][0]),
    })

def render(macro, params=None, **kw):
    # Klipper's delimiters: blocks are {% %}, expressions are single braces.
    env = SandboxedEnvironment(
        block_start_string="{%", block_end_string="%}",
        variable_start_string="{", variable_end_string="}",
        undefined=StrictUndefined)
    msgs, errors = [], []
    def info(t): msgs.append(str(t)); return ""
    def raise_err(t): raise Err(str(t))
    ctx = {
        "printer": make_printer(**kw),
        "params": Dot({k: str(v) for k, v in (params or {}).items()}),
        "action_respond_info": info,
        "action_raise_error": raise_err,
        "action_emergency_stop": raise_err,
    }
    out = env.from_string(cfgs[macro][1]).render(ctx)
    return out, msgs

def gcode_lines(out):
    return [l.strip() for l in out.splitlines()
            if l.strip() and not l.strip().startswith("#")]

# ---------------------------------------------------------------- checks
AXMIN, AXMAX = (0.0, 0.0, 0.0), (250.0, 210.0, 250.0)
MOVE = re.compile(r"^(G[0-9]+)\s+(.*)$")

KNOWN = re.compile(r"^(SAVE_GCODE_STATE|RESTORE_GCODE_STATE|M8[23]|SET_HEATER_TEMPERATURE|"
                   r"TEMPERATURE_WAIT|KOMB|SET_GCODE_VARIABLE|G4 |G2[0-9]?$|G9[013]$)")

def check_moves(lines, label):
    problems = []
    relative = False
    for l in lines:
        if l == "G91": relative = True; continue
        if l == "G90": relative = False; continue
        if "%}" in l or "{%" in l or "{" in l or "}" in l:
            problems.append(f"{label}: unrendered template in {l!r}")
        m = MOVE.match(l)
        if not m:
            if not KNOWN.match(l):
                problems.append(f"{label}: unrecognised output line: {l!r}")
            continue
        # Relative moves cannot be bounds-checked from the text alone.
        for axis, lo, hi in ([] if relative else zip("XYZ", AXMIN, AXMAX)):
            f = re.search(rf"\b{axis}(-?[\d.]+)", m.group(2))
            if f:
                v = float(f.group(1))
                if not (lo - 1e-6 <= v <= hi + 1e-6):
                    problems.append(f"{label}: {axis}={v} out of range in {l!r}")
        f = re.search(r"\bF(-?[\d.]+)", m.group(2))
        if f and float(f.group(1)) <= 0:
            problems.append(f"{label}: non-positive feedrate in {l!r}")
    return problems

BRUSH = re.compile(r"brush X ([\d.-]+)\.\.([\d.-]+)\s+Y ([\d.-]+)\.\.([\d.-]+)\s+Z ([\d.-]+)\.\.([\d.-]+)")

def check_inside_brush(lines, msgs, label):
    """Every wiping move (G1/G2/G3) must stay within the brush footprint."""
    bounds = None
    for m in msgs:
        b = BRUSH.search(m)
        if b:
            bounds = [float(x) for x in b.groups()]
    if not bounds:
        return [f"{label}: no brush bounds reported"]
    xlo, xhi, ylo, yhi, zlo, zhi = bounds
    problems = []
    for l in lines:
        if not l.startswith("G1 X"):
            continue
        for axis, lo, hi in (("X", xlo, xhi), ("Y", ylo, yhi), ("Z", zlo, zhi)):
            f = re.search(rf"\b{axis}(-?[\d.]+)", l)
            if f and not (lo - 1e-6 <= float(f.group(1)) <= hi + 1e-6):
                problems.append(f"{label}: wipe leaves brush on {axis} "
                                f"({f.group(1)} not in {lo}..{hi}): {l!r}")
    return problems

def combos():
    keys = ["start_opposite_side", "start_adjacent_side", "reverse_enable"]
    for bits in itertools.product([False, True], repeat=3):
        yield dict(zip(keys, bits))

total, fails = 0, []
for pattern in (1, 2):
    for angle in (0, 30, 45, 90):
        if pattern == 2 and angle != 45:
            continue
        for flags in combos():
            for extra in ({}, {"repeat": 2, "z_step": 0.5, "offset": 2},
                          {"brush_size_y": 0} if pattern == 1 else {"brush_size_y": 5},
                          {"brush_location_x": 240, "brush_size_x": 40},  # forces clamping
                          {"purge_amount": 5}):
                uv = dict(USER_VARS)
                uv.update(flags); uv.update(extra)
                uv["pattern"] = pattern; uv["angle"] = angle
                uv["verbose_points"] = True
                label = f"p{pattern} a{angle} {flags} {extra}"
                total += 1
                try:
                    out, msgs = render("komb", uservars=uv, temp=200.0)
                except Err as e:
                    fails.append(f"{label}: raised: {e}")
                    continue
                except Exception as e:
                    fails.append(f"{label}: TEMPLATE ERROR {type(e).__name__}: {e}")
                    continue
                fails.extend(check_moves(gcode_lines(out), label))
                fails.extend(check_inside_brush(gcode_lines(out), msgs, label))

print(f"KOMB: {total} combinations rendered, {len(fails)} problems")
for f in fails[:40]:
    print("  -", f)

# purge + trigger + validation paths
extra_cases = [
    ("purge", "komb_purge", dict(uservars={**USER_VARS, "purge_amount": 8}, temp=200.0)),
    ("purge cold, no autoheat", "komb_purge", dict(uservars={**USER_VARS, "purge_amount": 8}, temp=25.0)),
    ("purge cold, autoheat", "komb_purge",
     dict(uservars={**USER_VARS, "purge_amount": 8, "auto_heat_nozzle": True}, temp=25.0)),
    ("trigger off", "komb_trigger", dict(uservars=USER_VARS)),
    ("trigger on", "komb_trigger", dict(uservars={**USER_VARS, "trigger_freq": 5}, pos=(1, 1, 12.4))),
    ("trigger reset", "komb_trigger_reset", dict(uservars=USER_VARS)),
    ("unhomed no autohome", "komb", dict(uservars={**USER_VARS, "auto_home_enable": False}, homed=False)),
    ("unhomed autohome", "komb", dict(uservars=USER_VARS, homed=False)),
    ("unhomed autohome, loc 0", "komb", dict(uservars={**USER_VARS, "brush_location_x": 0}, homed=False)),
    ("cold, no cold clean", "komb", dict(uservars={**USER_VARS, "clean_while_cold": False}, temp=25.0)),
    ("bad pattern", "komb", dict(uservars={**USER_VARS, "pattern": 3})),
    ("bad step", "komb", dict(uservars={**USER_VARS, "step": 0})),
    ("zero brush", "komb", dict(uservars={**USER_VARS, "brush_size_x": 0, "brush_size_y": 0})),
    ("p2 single axis", "komb", dict(uservars={**USER_VARS, "pattern": 2, "brush_size_y": 0})),
    ("bad angle", "komb", dict(uservars={**USER_VARS, "angle": 120})),
]
print()
for label, macro, kw in extra_cases:
    try:
        out, msgs = render(macro, **kw)
        probs = check_moves(gcode_lines(out), label)
        n = len(gcode_lines(out))
        print(f"  {label:28s} OK  ({n} lines)" + ("  PROBLEMS: " + "; ".join(probs) if probs else ""))
    except Err as e:
        print(f"  {label:28s} error -> {e}")
    except Exception as e:
        print(f"  {label:28s} TEMPLATE ERROR {type(e).__name__}: {e}")

# param override path (params arrive as strings, as Klipper delivers them)
print()
try:
    out, msgs = render("komb", params={"REPEAT": 3, "SPEED": 80, "PATTERN": 2,
                                       "START_OPPOSITE_SIDE": "true",
                                       "ENABLE_VERBOSE_OUTPUT": "1"}, temp=200.0)
    print("  string params OK,", len(gcode_lines(out)), "lines;", len(msgs), "messages")
    print("  ", check_moves(gcode_lines(out), "params") or "no problems")
except Exception as e:
    print("  string params FAILED:", type(e).__name__, e)

# sample output
print("\n--- sample: defaults, pattern 1, angle 45 ---")
out, msgs = render("komb", uservars={**USER_VARS, "verbose_points": False}, temp=200.0)
for m in msgs: print("  //", m)
print("\n".join("  " + l for l in gcode_lines(out)[:20]))
print("  ... total", len(gcode_lines(out)), "lines")
