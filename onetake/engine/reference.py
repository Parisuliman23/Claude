"""Reference reels: videos the user loves, studied so their style can guide the edits.

`study(path)` does the measuring an editor would do and leaves it in lookbook/references/<name>/ for Claude to read:
  sheet_1.png, sheet_2.png…  one frame per second, numbered, 8 x 6 per sheet (Claude looks at these)
  cuts.json                  every shot change (s) and the average shot length
  transcript.txt             what's said, with word timings in transcript.json
  stats.json                 pace (words/s), cuts per minute, pauses, whether music sits under the voice
Claude then writes lookbook/style/NN-<name>.md and adds the style to lookbook/STYLE.md (see CLAUDE.md, kind "reference").
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from . import config

REF_DIR = config.LIBRARY / "references"


def slug(path):
    return re.sub(r"[^a-z0-9]+", "-", Path(path).stem.lower()).strip("-")[:40] or "reference"


def out_dir(path):
    return config.LOOKBOOK / "references" / slug(path)


def _cuts(video):
    import cv2
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    prev = prevg = None
    cuts, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        s = cv2.resize(f, (90, 160))
        g = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY)
        h = cv2.calcHist([s], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
        h = cv2.normalize(h, h).flatten()
        if prev is not None:
            d = cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA)
            px = float(np.abs(g.astype(int) - prevg.astype(int)).mean())
            t = i / fps
            if (d > 0.25 or px > 28) and (not cuts or t - cuts[-1] > 0.25):
                cuts.append(round(t, 2))
        prev, prevg, i = h, g, i + 1
    return cuts, i / fps


def _sheets(video, out, dur):
    tiles = out / "frames"
    tiles.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-vf",
                    "fps=1,scale=150:-1,drawtext=text='%{eif\\:t\\:d}':x=2:y=2:fontsize=14:fontcolor=yellow:box=1:boxcolor=black",
                    str(tiles / "%03d.png")], check=True)
    n = len(list(tiles.glob("*.png")))
    sheets = []
    for k in range((n + 47) // 48):
        sheet = out / f"sheet_{k + 1}.png"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-start_number", str(k * 48 + 1), "-i",
                        str(tiles / "%03d.png"), "-frames:v", "1", "-vf", "tile=8x6", str(sheet)], check=True)
        sheets.append(config.rel(sheet))
    for f in tiles.glob("*.png"):
        f.unlink()
    tiles.rmdir()
    return sheets


def study(path, log=print):
    video = config.absolute(path) if not Path(path).is_absolute() else Path(path)
    out = out_dir(video)
    out.mkdir(parents=True, exist_ok=True)
    log("  frames…")
    cuts, dur = _cuts(video)
    sheets = _sheets(video, out, dur)
    log("  words…")
    from . import transcribe
    words, _ = transcribe.run(video)
    (out / "transcript.json").write_text(json.dumps(words))
    (out / "transcript.txt").write_text(" ".join(w["t"] for w in words))
    stats = {"duration": round(dur, 1), "cuts": len(cuts), "cuts_per_min": round(len(cuts) / max(dur, 1) * 60, 1),
             "avg_shot_s": round(dur / max(1, len(cuts)), 2)}
    if words:
        span = max(0.1, words[-1]["e"] - words[0]["s"])
        gaps = [b["s"] - a["e"] for a, b in zip(words, words[1:])]
        stats.update(words_per_s=round(len(words) / span, 2), pauses_over_third_s=sum(1 for g in gaps if g > 0.33))
    log("  sound…")
    try:  # music bed: how loud the pauses are compared with speech
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        db = lambda a: float(20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9))
        gp = [x[int(a["e"] * 16000) + 800:int(b["s"] * 16000) - 800] for a, b in zip(words, words[1:]) if b["s"] - a["e"] > 0.3]
        gp = [g for g in gp if len(g) > 1600]
        if gp:
            stats["pause_level_db"] = round(float(np.median([db(g) for g in gp])), 1)
            stats["speech_level_db"] = round(db(x), 1)
            stats["music_under_voice"] = stats["pause_level_db"] > stats["speech_level_db"] - 6
    except Exception:  # noqa: BLE001
        pass
    (out / "cuts.json").write_text(json.dumps({"cuts": cuts}))
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    info = {"video": config.rel(video), "sheets": sheets, "dir": config.rel(out), **stats}
    (out / "info.json").write_text(json.dumps(info, indent=1))
    return info


def listing():
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(REF_DIR.glob("*")):
        if f.suffix.lower() not in config.VIDEO_EXT:
            continue
        d = out_dir(f)
        info = json.loads((d / "info.json").read_text()) if (d / "info.json").exists() else None
        guide = list(config.LOOKBOOK.glob(f"style/*-{slug(f)}.md"))
        out.append({"path": config.rel(f), "name": f.stem, "studied": bool(info), "guide": config.rel(guide[0]) if guide else None,
                    "sheet": (info or {}).get("sheets", [None])[0]})
    return out
