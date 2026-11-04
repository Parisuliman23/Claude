"""Makes a few simple royalty-free background tracks so the studio has sounds
out of the box. Add your own (or licensed) music to library/sounds/."""
import subprocess
import wave

import numpy as np

from . import config

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(n, octave):
    return 440.0 * 2 ** ((NOTE[n] + 12 * (octave - 4) - 9) / 12)


def chord(root, minor=False):
    i = [0, 3 if minor else 4, 7, 12]
    return [hz(root, 3) * 2 ** (k / 12) for k in i]


def tone(f, dur, kind="pad"):
    t = np.arange(int(SR * dur)) / SR
    if kind == "pad":
        w = sum(np.sin(2 * np.pi * f * m * t) / (m * 1.6) for m in (1, 2, 3)) * 0.5
        env = np.minimum(1, t / 0.25) * np.minimum(1, (dur - t) / 0.4)
    else:  # pluck
        w = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
        env = np.exp(-t * 6)
    return w * env


def kick(dur=0.25):
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 12)


def hat(dur=0.06, rng=np.random.default_rng(1)):
    t = np.arange(int(SR * dur)) / SR
    n = rng.standard_normal(len(t))
    return np.diff(n, prepend=0) * np.exp(-t * 60) * 0.25


def track(prog, bpm, length, pluck=False, drums=True):
    beat = 60 / bpm
    bar = beat * 4
    out = np.zeros(int(SR * (length + 2)))

    def add(sig, at):
        i = int(at * SR)
        out[i:i + len(sig)] += sig[: len(out) - i]

    t, k = 0.0, 0
    while t < length:
        root, minor = prog[k % len(prog)]
        for f in chord(root, minor):
            add(tone(f, bar, "pad") * 0.16, t)
        if pluck:
            for b in range(8):
                f = chord(root, minor)[[0, 2, 1, 3, 2, 1, 3, 2][b]] * 2
                add(tone(f, beat, "pluck") * 0.1, t + b * beat / 2)
        if drums:
            for b in range(4):
                add(kick() * 0.5, t + b * beat)
                add(hat(), t + b * beat + beat / 2)
        t += bar
        k += 1
    out = out[: int(SR * length)]
    fade = int(SR * 2)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() or 1) * 0.8


TRACKS = {
    "warm-pad (built-in)": dict(prog=[("C", False), ("A", True), ("F", False), ("G", False)], bpm=80, drums=False),
    "upbeat-pluck (built-in)": dict(prog=[("G", False), ("D", False), ("E", True), ("C", False)], bpm=112, pluck=True),
    "chill-beat (built-in)": dict(prog=[("D", True), ("A#", False), ("F", False), ("C", False)], bpm=90, pluck=True),
}


def make_all(length=75):
    d = config.LIBRARY / "sounds"
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for name, kw in TRACKS.items():
        out = d / f"{name}.m4a"
        if out.exists():
            continue
        x = track(length=length, **kw)
        wav = d / "_tmp.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "160k",
                        str(out)], check=True)
        wav.unlink()
        made.append(out.name)
    return made
