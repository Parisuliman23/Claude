"""Video analysis: find faces to cover, and pick the best moment of a B-roll clip."""
import math
from pathlib import Path

import cv2
import numpy as np

from . import config


def _frames(path, fps=4, width=360):
    cap = cv2.VideoCapture(str(path))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, int(round(src_fps / fps)))
    i = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, fr = cap.retrieve()
            if ok:
                h, w = fr.shape[:2]
                small = cv2.resize(fr, (width, int(h * width / w)))
                yield i / src_fps, fr, small
        i += 1
    cap.release()


def detect_faces(video, out_dir, fps=4, progress=None):
    """Find the different faces in the video and follow each one.
    Returns [{id, thumb, track: [[t, cx, cy, size], ...]}] with coords as fractions of the frame width/height."""
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    tracks = []
    total = None
    cap = cv2.VideoCapture(str(video))
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    sfps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    total = n / sfps if n else None
    for t, full, small in _frames(video, fps):
        if progress and total:
            progress(min(0.99, t / total))
        g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        h, w = g.shape
        dets = cascade.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(int(w * 0.07), int(w * 0.07)))
        for (x, y, fw, fh) in dets:
            cx, cy, s = (x + fw / 2) / w, (y + fh / 2) / h, fw / w
            best = None
            for tr in tracks:
                lt, lx, ly, ls = tr["track"][-1]
                if t - lt > 1.5 or lt == t:
                    continue
                d = math.hypot((cx - lx), (cy - ly) * h / w)
                if d < max(ls, s) * 0.8 and (best is None or d < best[1]):
                    best = (tr, d)
            if best:
                tr = best[0]
            else:
                tr = {"track": [], "best": 0}
                tracks.append(tr)
            tr["track"].append([round(t, 3), round(cx, 4), round(cy, 4), round(s, 4)])
            if s > tr["best"]:
                H, W = full.shape[:2]
                X, Y, S = int(cx * W), int(cy * H), int(s * W * 0.75)
                crop = full[max(0, Y - S):Y + S, max(0, X - S):X + S]
                if crop.size:
                    tr["best"] = s
                    tr["crop"] = cv2.resize(crop, (160, 160))
    tracks = [t for t in tracks if len(t["track"]) >= 3]
    tracks = _merge(tracks)
    tracks.sort(key=lambda t: -len(t["track"]))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = []
    for k, tr in enumerate(tracks[:8]):
        fid = f"face{k + 1}"
        thumb = out_dir / f"{fid}.jpg"
        if "crop" in tr:
            cv2.imwrite(str(thumb), tr["crop"])
        res.append({"id": fid, "name": f"Face {k + 1}", "thumb": config.rel(thumb), "track": tr["track"],
                    "seen": round(len(tr["track"]) / fps, 1)})
    return res


def _merge(tracks):
    """Join tracks that are clearly the same face after a short dropout."""
    tracks = sorted(tracks, key=lambda t: t["track"][0][0])
    out = []
    for tr in tracks:
        for o in out:
            lt, lx, ly, ls = o["track"][-1]
            ft, fx, fy, fs = tr["track"][0]
            if 0 <= ft - lt < 3.0 and math.hypot(fx - lx, fy - ly) < max(ls, fs) * 1.5:
                o["track"] += tr["track"]
                if tr.get("best", 0) > o.get("best", 0) and "crop" in tr:
                    o["best"], o["crop"] = tr["best"], tr["crop"]
                break
        else:
            out.append(tr)
    return out


def face_at(track, t, hold=0.6, max_gap=1.6):
    """Interpolated (cx, cy, size) at source time t, or None. Mirrored in app.js."""
    if not track or t < track[0][0] - hold or t > track[-1][0] + hold:
        return None
    if t <= track[0][0]:
        return track[0][1:]
    if t >= track[-1][0]:
        return track[-1][1:]
    lo, hi = 0, len(track) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if track[mid][0] <= t:
            lo = mid
        else:
            hi = mid
    a, b = track[lo], track[hi]
    if b[0] - a[0] > max_gap:
        return a[1:] if t - a[0] < hold else (b[1:] if b[0] - t < hold else None)
    k = (t - a[0]) / (b[0] - a[0])
    return [a[i] + (b[i] - a[i]) * k for i in (1, 2, 3)]


def best_moment(path, dur, fps=4):
    """Start time of the most watchable `dur`-second stretch of a clip (sharp, with some movement)."""
    sharp, motion, times = [], [], []
    prev = None
    for t, _, small in _frames(path, fps, 240):
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        sharp.append(cv2.Laplacian(g, cv2.CV_64F).var())
        motion.append(0.0 if prev is None else float(np.mean(cv2.absdiff(g, prev))))
        times.append(t)
        prev = g
    if not times:
        return 0.0
    length = times[-1] + 1 / fps
    if length <= dur:
        return 0.0
    s = np.array(sharp)
    m = np.clip(np.array(motion), 0, 25)  # some movement is good, chaos isn't
    score = (s / (s.max() or 1)) * 0.6 + (m / (m.max() or 1)) * 0.4
    win = max(1, int(dur * fps))
    best_i, best_v = 0, -1
    for i in range(0, len(score) - win + 1):
        v = score[i:i + win].mean()
        if v > best_v:
            best_i, best_v = i, v
    return round(min(times[best_i], length - dur), 2)
