"""Video transitions and camera effects on a spoken word (learned from HyperFrames' transition catalog:
whip-pan, flash-through-white, zoom-through, camera-shake, glitch, light-leak).

An edit's `fx` list holds {"id", "kind", "w": word index, "dur": seconds (optional), "strength": 0-2 (optional)}.
The effect is centred on the moment the word is said (shake and light leak start on it).
"""
import math

import cv2
import numpy as np

from . import timeline

KINDS = {  # kind: (default seconds, centred on the word?, description)
    "flash": (0.30, True, "a white flash, like a camera flash or a hard cut through white"),
    "whip": (0.30, True, "a fast sideways whip-pan blur"),
    "zoom": (0.35, True, "a punchy zoom-through with motion blur"),
    "shake": (0.40, False, "a camera shake that settles, for impact"),
    "glitch": (0.25, True, "an RGB-split digital glitch with shifted slices"),
    "light_leak": (1.00, False, "a warm cinematic light leak sweeping across"),
}


def spans(p, words, segs):
    """[(fx, start, end)] on the output timeline."""
    out = []
    for f in p.get("fx", []):
        if f.get("kind") not in KINDS or not isinstance(f.get("w"), int):
            continue
        wo = None
        for j in range(f["w"], min(len(words), f["w"] + 40)):
            wo = timeline.word_out(words, segs, j)
            if wo:
                break
        if not wo:
            continue
        dur, centred, _ = KINDS[f["kind"]]
        dur = float(f.get("dur") or dur)
        a = wo[0] - dur / 2 if centred else wo[0]
        out.append((f, max(0.0, a), max(0.0, a) + dur))
    return out


def _bell(k):
    return math.sin(math.pi * max(0.0, min(1.0, k)))


def _scale_center(fr, s):
    if abs(s - 1) < 1e-3:
        return fr
    H, W = fr.shape[:2]
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
    return cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def footage(frame, f, k, n):
    """Effects on the footage (under the graphics). k = 0..1 through the effect, n = frame number (for seeding)."""
    kind, s = f["kind"], float(f.get("strength", 1.0) or 1.0)
    H, W = frame.shape[:2]
    if kind == "whip":
        b = _bell(k)
        L = int(2 + 90 * b * s)
        kern = np.zeros((1, L), np.float32)
        kern[0, :] = 1.0 / L
        sh = (k - 0.5) * W * 0.5 * s * (1 if f.get("dir", "left") == "left" else -1)
        M = np.float32([[1, 0, -sh], [0, 1, 0]])
        fr = cv2.warpAffine(frame, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return cv2.filter2D(fr, -1, kern)
    if kind == "zoom":
        b = _bell(k)
        base = 1 + 0.28 * b * s
        acc = np.zeros_like(frame, np.float32)
        for j, d in enumerate((0.0, 0.04, 0.08)):  # a few stacked scales = a cheap radial blur
            acc += _scale_center(frame, base + d * b * s).astype(np.float32)
        return (acc / 3).astype(np.uint8)
    if kind == "shake":
        amp = 22 * s * (1 - k) ** 1.5
        rng = np.random.default_rng(n * 7919 + 13)
        dx, dy = rng.uniform(-amp, amp, 2)
        rot = rng.uniform(-1, 1) * 0.8 * s * (1 - k)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.05)
        M[:, 2] += (dx, dy)
        return cv2.warpAffine(frame, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    if kind == "glitch":
        b = _bell(k)
        rng = np.random.default_rng(n * 104729 + 7)
        off = int(24 * s * b) + 2
        out = frame.copy()
        out[:, :, 2] = np.roll(frame[:, :, 2], off, axis=1)  # red one way, blue the other
        out[:, :, 0] = np.roll(frame[:, :, 0], -off, axis=1)
        for _ in range(int(3 + 5 * b)):
            y0 = int(rng.uniform(0, H - 40))
            h = int(rng.uniform(12, 90))
            out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.uniform(-80, 80) * s * b), axis=1)
        return out
    if kind == "light_leak":
        a = _bell(k) * 0.55 * s
        yy, xx = np.mgrid[0:H:8, 0:W:8]
        cx = W * (-0.2 + 1.4 * k)
        g = np.exp(-(((xx - cx) / (W * 0.45)) ** 2 + ((yy - H * 0.3) / (H * 0.6)) ** 2))
        g = cv2.resize(g.astype(np.float32), (W, H))[..., None] * a
        warm = np.array([60, 140, 255], np.float32)  # BGR: orange/pink glow
        fr = frame.astype(np.float32)
        return np.clip(255 - (255 - fr) * (1 - g * warm / 255), 0, 255).astype(np.uint8)  # screen blend
    return frame


def over_everything(frame, f, k):
    """Effects that sit on top of the graphics too (the white flash)."""
    if f["kind"] == "flash":
        a = _bell(k) ** 1.5 * min(1.0, float(f.get("strength", 1.0) or 1.0))
        return cv2.addWeighted(frame, 1 - a, np.full_like(frame, 255), a, 0)
    return frame
