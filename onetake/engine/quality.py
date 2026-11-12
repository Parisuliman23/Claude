"""Footage check: how clear and real a clip will look, measured, with filming tips (no filters).

Benchmarks come from a creator the user admires (same phone, no filters; studied Nov 2026): at 720 px wide his
frames measure contrast ~66, fine detail ~250, brightness ~123. The user's indoor clip measured contrast ~39,
detail ~56, brightness ~117: about as bright and colourful, but flat and soft. The difference is how it's filmed:
daylight on the face, a background with depth and texture, the rear camera, HDR video off.
"""
import json
import subprocess

from . import config

GOOD = {"contrast": 55, "detail": 120, "bright_lo": 95, "bright_hi": 165}


def _frames(path, n=5):
    import cv2
    import numpy as np
    from . import ingest
    dur = max(0.5, ingest.duration(path))
    vf = (ingest.TONEMAP if ingest.is_hdr(path) else "") + "scale=720:-2"  # HDR: measure it as it will look
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                            "-frames:v", "1", "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True, timeout=60)
        if r.stdout:
            out.append(cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR))
    return [f for f in out if f is not None]


def measure(path):
    """Brightness, contrast, fine detail, clipped highlights (median over 5 frames) + the file's format."""
    import cv2
    import numpy as np
    from . import ingest
    vals = []
    for im in _frames(path):
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        vals.append((g.mean(), g.std(), cv2.Laplacian(g, cv2.CV_32F).var(), (g > 245).mean() * 100))
    m = np.median(np.array(vals), 0) if vals else [0, 0, 0, 0]
    info = ingest.ffprobe(path)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rate = v.get("r_frame_rate", "30/1").split("/")
    return {"bright": round(float(m[0])), "contrast": round(float(m[1])), "detail": round(float(m[2])),
            "blown": round(float(m[3]), 1), "hdr": ingest.is_hdr(path), "short_side": min(w, h),
            "fps": round(int(rate[0]) / max(1, int(rate[1] or 1))) if rate[0].isdigit() else 30}


def tips(m):
    """Plain-language advice, most important first. Empty list = looks great."""
    out = []
    if m["hdr"]:
        out.append("Turn HDR video OFF in the camera (Camera → Settings → Advanced video options → HDR10+ video / "
                   "'HDR' off). Instagram and editors show plain video truer; HDR has to be converted and looks flatter.")
    if m["contrast"] < GOOD["contrast"]:
        out.append("It looks flat. Film facing a window or outside in open shade, so daylight falls on your face from "
                   "the front or side, and put some space and texture behind you (a room, shelves, a street) instead "
                   "of a plain wall right behind you.")
    if m["detail"] < GOOD["detail"]:
        out.append("It looks soft. Use the back (main) camera, not the selfie camera, wipe the lens, and film in more "
                   "light (soft footage is mostly the phone smoothing out noise in dim rooms). 4K gives extra detail.")
    if m["bright"] < GOOD["bright_lo"]:
        out.append("It's a bit dark: add light in front of you (a window or a soft lamp) rather than brightening it later.")
    if m["blown"] > 3 or m["bright"] > GOOD["bright_hi"]:
        out.append("Parts are too bright (skin or a light behind you is washing out): move the light further away, "
                   "turn a little away from it, or tap your face on the screen and drag the brightness down slightly.")
    if m["short_side"] and m["short_side"] < 1080:
        out.append("Record in at least FHD (1080p); 4K is even sharper.")
    return out


def check(paths):
    res = []
    for p in paths:
        m = measure(p)
        res.append({"file": getattr(p, "name", str(p)), "measured": m, "tips": tips(m)})
    return res


def report(res):
    lines = []
    for r in res:
        m = r["measured"]
        lines.append(f"{r['file']}: brightness {m['bright']}, contrast {m['contrast']} (clear: {GOOD['contrast']}+), "
                     f"detail {m['detail']} (clear: {GOOD['detail']}+), HDR {'on' if m['hdr'] else 'off'}, "
                     f"{m['short_side']}p {m['fps']}fps")
        lines += [f"  - {t}" for t in r["tips"]] or ["  ✓ Clear, real-looking footage. Film like this every time."]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(json.dumps(check(sys.argv[1:]), indent=1))
