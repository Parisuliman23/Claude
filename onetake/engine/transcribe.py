"""Word-level transcription with faster-whisper (runs on your computer, free)."""
import os
import re
import subprocess

import numpy as np

from . import config


def load_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "s16le",
                          "-ac", "1", "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


_model = None


def model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        name = os.environ.get("ONETAKE_WHISPER_MODEL") or config.settings()["whisper_model"]
        _model = WhisperModel(name, device="cpu", compute_type="int8")
    return _model


def run(path):
    audio = load_audio(path)
    segs, _ = model().transcribe(audio, language="en", word_timestamps=True, vad_filter=False,
                                 condition_on_previous_text=False,
                                 # keeps "um"/"uh" in the text so the rough cut can remove them
                                 initial_prompt="Um, uh, so, like, okay. Hmm, I mean, yeah.")
    words = []
    for seg in segs:
        for w in seg.words or []:
            t = w.word.strip()
            if t:
                words.append({"t": t, "s": round(w.start, 3), "e": round(max(w.end, w.start + 0.05), 3)})
    # Whisper sometimes splits numbers ("$50" ",000"): join them back into one word.
    merged = []
    for w in words:
        if merged and re.match(r"^[,.]\d", w["t"]) and re.search(r"\d$", merged[-1]["t"]):
            merged[-1]["t"] += w["t"]
            merged[-1]["e"] = w["e"]
        else:
            merged.append(w)
    words = merged
    # Lines = sentences. Also break on a long pause, or at a comma once a line gets long.
    line, count = 0, 0
    for k, w in enumerate(words):
        if k and (re.search(r"[.!?]$", words[k - 1]["t"]) or w["s"] - words[k - 1]["e"] > 0.8
                  or (count >= 14 and words[k - 1]["t"].endswith(",")) or count >= 24):
            line += 1
            count = 0
        w["l"] = line
        count += 1
    # renumber lines 0..n
    remap = {}
    for w in words:
        w["l"] = remap.setdefault(w["l"], len(remap))
    return words, len(remap)
