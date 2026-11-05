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


# ---------------------------------------------------------------------------
# Burned-in captions (e.g. a CapCut export): find them, and paint them out.

def text_lines(bgr, ref_h=None):
    """Find caption-like text in a frame. Returns (mask of text pixels, [boxes x0,y0,x1,y1 in px]).
    Captions are bright/colored letters with a dark outline or shadow, in wide short lines,
    made of several separate letters (so logos and single bright shapes are ignored)."""
    h, w = bgr.shape[:2]
    rh = ref_h or h  # full-frame height at this scale (bgr may be a horizontal strip)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    bright = (gray > 185) | ((hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 170))
    dark = (gray < 70).astype(np.uint8)
    near_dark = cv2.dilate(dark, np.ones((5, 5), np.uint8)) > 0
    cand = (bright & near_dark).astype(np.uint8)
    lines = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, w // 25), 3)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(lines, 8)
    boxes = []
    mask = np.zeros_like(cand)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if bw < w * 0.12 or not (rh * 0.012 <= bh <= rh * 0.12) or bw < bh * 2.2:
            continue
        cx = x + bw / 2
        if not (w * 0.15 < cx < w * 0.85):
            continue
        sub = cand[y:y + bh, x:x + bw]
        if sub.mean() < 0.08:
            continue
        letters = cv2.connectedComponents(sub, 8)[0] - 1
        if letters < 4:
            continue
        boxes.append((int(x), int(y), int(x + bw), int(y + bh)))
        mask[lab == i] = 1  # the whole closed text line, not just the letter fill
    return mask, boxes


def scan_burned_text(video, fps=4, progress=None):
    """Sample the video and report where burned-in captions are.
    Returns {"coverage": share of sampled frames with text, "band": [y0, y1] (fractions), "boxes": [[t, x0, y0, x1, y1], ...]}"""
    cap = cv2.VideoCapture(str(video))
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    sfps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    total = n / sfps if n else None
    boxes, frames_with = [], 0
    samples = 0
    for t, _, small in _frames(video, fps, 360):
        if progress and total:
            progress(min(0.99, t / total))
        samples += 1
        h, w = small.shape[:2]
        _, bs = text_lines(small)
        if bs:
            frames_with += 1
        for x0, y0, x1, y1 in bs:
            boxes.append([round(t, 2), round(x0 / w, 4), round(y0 / h, 4), round(x1 / w, 4), round(y1 / h, 4)])
    res = {"coverage": round(frames_with / max(1, samples), 3), "boxes": boxes, "band": None}
    if boxes:
        # the captions live where text shows up most: the densest 25%-tall strip of the frame
        cy = [(b[2] + b[4]) / 2 for b in boxes]
        best = max((sum(1 for c in cy if s0 <= c <= s0 + 0.25), s0) for s0 in [k / 100 for k in range(0, 76)])[1]
        inband = [b for b, c in zip(boxes, cy) if best <= c <= best + 0.25]
        # A logo or print on clothing sits in the same spot at the same size the whole time.
        # Real captions change with every word, so their boxes move and change width.
        import statistics
        if len(inband) >= 5:
            widths = [b[3] - b[1] for b in inband]
            centers = [(b[1] + b[3]) / 2 for b in inband]
            if statistics.pstdev(widths) < 0.03:  # same size every time (it may move with the body)
                return {"coverage": 0.0, "boxes": [], "band": None, "static": True}
        res["band"] = [round(max(0.0, min(b[2] for b in inband) - 0.02), 3),
                       round(min(1.0, max(b[4] for b in inband) + 0.02), 3)]
        res["boxes"] = inband
        res["coverage"] = round(len({b[0] for b in inband}) / max(1, samples), 3)
    return res


def remove_burned_text(frame, band=None, scale=0.5, state=None):
    """Paint out burned-in caption text in place (inside the band of the frame, if given).
    Pass the same `state` dict for consecutive frames: if detection misses a frame, the last
    mask is reused briefly so old captions don't flicker back."""
    H, W = frame.shape[:2]
    y0, y1 = (int(band[0] * H), int(band[1] * H)) if band else (0, H)
    roi = frame[y0:y1]
    if roi.size == 0:
        return
    small = cv2.resize(roi, (int(W * scale), max(1, int((y1 - y0) * scale))), interpolation=cv2.INTER_AREA)
    mask, boxes = text_lines(small, ref_h=H * scale)
    if state is not None:
        if boxes:
            state["mask"], state["miss"] = mask, 0
        elif state.get("mask") is not None and state.get("miss", 0) < 4 and state["mask"].shape == mask.shape:
            mask, boxes = state["mask"], [None]
            state["miss"] = state.get("miss", 0) + 1
    if not boxes:
        return
    # cover each text line plus its outline and drop shadow
    k = max(9, int(small.shape[1] * 0.03)) | 1
    m = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    filled = cv2.inpaint(small, m * 255, 7, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(filled, (9, 9), 0)
    big = cv2.resize(filled, (W, y1 - y0), interpolation=cv2.INTER_LINEAR)
    mb = cv2.resize(cv2.GaussianBlur(m.astype(np.float32), (5, 5), 0), (W, y1 - y0))[:, :, None]
    mb = np.clip(mb * 1.2, 0, 1)
    frame[y0:y1] = (big * mb + roi * (1 - mb)).astype(np.uint8)


def face_focus(video, samples=10):
    """Where the speaker's eyes usually are, as (x, y) fractions of the frame, for punch-ins
    and split screens. Falls back to the upper third if no face is found."""
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    pts = []
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (k + 0.5) / samples))
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        small = cv2.resize(fr, (360, int(h * 360 / w)))
        g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        dets = cascade.detectMultiScale(g, 1.1, 6, minSize=(40, 40))
        if len(dets):
            x, y, fw, fh = max(dets, key=lambda d: d[2] * d[3])
            pts.append(((x + fw / 2) / small.shape[1], (y + fh * 0.4) / small.shape[0]))  # eye line
    cap.release()
    if not pts:
        return [0.5, 0.38]
    xs, ys = sorted(p[0] for p in pts), sorted(p[1] for p in pts)
    return [round(float(xs[len(xs) // 2]), 3), round(float(ys[len(ys) // 2]), 3)]
