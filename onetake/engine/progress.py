"""How far along a new reel's edit is, for the % shown in the studio and on the phone.

The edit runs in steps (import → Claude's cut → visuals → sound → checks → render). Each step marks
where it's reached in projects/.newreel.json; between marks the % creeps forward with time, never
past the next step, so it keeps moving without overpromising.
"""
import json
import math
import time

from . import config

FILE = config.PROJECTS / ".newreel.json"

# step: (% when it starts, what the user sees, typical seconds it takes)
STEPS = {
    "start": (0, "Getting started", 30),
    "join": (3, "Joining your clips", 40),
    "transcribe": (8, "Listening to your video and writing captions", 180),
    "analyze": (25, "Finding your face and any old captions", 40),
    "cut": (30, "Claude is tightening the cut", 150),
    "style": (45, "Claude is adding your hook, visuals and captions", 360),
    "sfx": (75, "Adding sound effects", 40),
    "check": (80, "Final checks", 60),
    "render": (85, "Rendering your video", 240),
    "end": (100, "Done", 1),
}
ORDER = list(STEPS)

# engine commands Claude runs while editing → the step they belong to
COMMAND_STEP = {
    "show": "cut", "cut": "cut", "restore": "cut", "cut-line": "cut", "restore-line": "cut", "retext": "cut",
    "set": "style", "overlay": "style", "add-overlay": "style", "add-broll": "style", "broll-find": "style",
    "highlight": "style", "still": "style", "look-preview": "style", "remove-captions": "style",
    "sfx-auto": "sfx", "sfx-list": "sfx",
    "edge-check": "check",
}


def _read():
    try:
        return json.loads(FILE.read_text())
    except (OSError, ValueError):
        return {}


def mark(step, frac=None):
    """Record that the running edit reached `step` (frac = 0–1 within it, when known). Never goes backwards."""
    info = _read()
    if info.get("status") != "running" or step not in STEPS:
        return
    cur = info.get("step", "start")
    if ORDER.index(step) < ORDER.index(cur if cur in STEPS else "start"):
        return
    if step != cur:
        info.update(step=step, step_at=time.time(), frac=None)
    if frac is not None:
        info["frac"] = round(max(0.0, min(1.0, frac)), 3)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(info))
    tmp.replace(FILE)


def _alive(pid):
    import os
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def check():
    """The edit's status file, with a stuck edit fixed: if the edit's process is gone (Chromebook slept or
    restarted, Linux was shut down…) or it has run far too long, it's marked failed so you can try again."""
    info = _read()
    if info.get("status") != "running":
        return info
    age = time.time() - info.get("started", time.time())
    gone = info.get("pid") and not _alive(info["pid"]) and age > 20
    if gone or age > 2 * 3600 or (not info.get("pid") and age > 600):
        info.update(status="failed", ended=time.time(), stuck=True)
        FILE.write_text(json.dumps(info))
        log = config.PROJECTS / ".newreel.log"
        with open(log, "a") as fh:
            fh.write("\n\nThe edit stopped before it finished (the Chromebook may have gone to sleep or Linux restarted). "
                     "Your video is still waiting. Send it again, or click One Take – New reel.\n")
    return info


def busy():
    return check().get("status") == "running"


def for_command(cmd):
    if cmd in COMMAND_STEP:
        mark(COMMAND_STEP[cmd])


def estimate(info, now=None):
    """(percent 0–99, label, seconds left or None) for a running edit."""
    now = now or time.time()
    step = info.get("step") if info.get("step") in STEPS else "start"
    lo, label, typical = STEPS[step]
    nxt = ORDER[min(ORDER.index(step) + 1, len(ORDER) - 1)]
    if step == "check" and not info.get("auto_render"):
        nxt = "end"
    hi = STEPS[nxt][0]
    if info.get("frac") is not None:  # the step reports its own progress (transcribing, rendering)
        f = info["frac"]
    else:  # otherwise creep toward the next step with time, slowing down as it gets close
        f = 0.9 * (1 - math.exp(-(now - info.get("step_at", info.get("started", now))) / typical))
    pct = int(min(99, lo + (hi - lo) * f))
    # time left = the rest of this step + the usual length of the steps after it
    later = ORDER[ORDER.index(step) + 1:ORDER.index("end")]
    if not info.get("auto_render") and "render" in later:
        later.remove("render")
    left = typical * (1 - f) + sum(STEPS[k][2] for k in later)
    return pct, label, max(30, left)
