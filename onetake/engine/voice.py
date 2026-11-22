"""The user's own cloned voice from ElevenLabs, for lines they didn't say on camera.

Key and voice live only in settings.json (never on GitHub): "elevenlabs_key", "elevenlabs_voice" (default: the
user's professional clone). Every call is counted in settings "elevenlabs_chars" and a single call over MAX_CHARS is
refused, so a mistake can't burn the user's credits.

Good uses: a fixed word or an added line over a cut-away / split screen (lips aren't visible), voiceover-only reels.
Only ever the user's OWN voice.
"""
import json
import re
import urllib.request

from . import config

API = "https://api.elevenlabs.io/v1"
MAX_CHARS = 1200          # per call (~1 min of speech)
MODEL = "eleven_multilingual_v2"


def _settings():
    f = config.ROOT / "settings.json"
    return f, (json.loads(f.read_text()) if f.exists() else {})


def key():
    k = _settings()[1].get("elevenlabs_key")
    if not k:
        raise SystemExit("No ElevenLabs key saved (settings.json \"elevenlabs_key\").")
    return k


def _req(path, data=None):
    req = urllib.request.Request(API + path, headers={"xi-api-key": key(), "Content-Type": "application/json"},
                                 data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def voices():
    return json.loads(_req("/voices")).get("voices", [])


def default_voice():
    """The user's professional clone (best quality), else their instant clone."""
    f, st = _settings()
    if st.get("elevenlabs_voice"):
        return st["elevenlabs_voice"]
    mine = [v for v in voices() if v.get("category") in ("professional", "cloned")]
    mine.sort(key=lambda v: 0 if v.get("category") == "professional" else 1)
    if not mine:
        raise SystemExit("No cloned voice found in the ElevenLabs account.")
    st["elevenlabs_voice"] = mine[0]["voice_id"]
    f.write_text(json.dumps(st, indent=1))
    return st["elevenlabs_voice"]


def say(text, out=None, voice=None, stability=0.5, similarity=0.85, style=0.2):
    """Make `text` in the user's voice. Returns the mp3 path (library/voice/…)."""
    text = text.strip()
    if not text:
        raise SystemExit("Nothing to say.")
    if len(text) > MAX_CHARS:
        raise SystemExit(f"That's {len(text)} characters; the limit per line is {MAX_CHARS} (to protect your credits).")
    vid = voice or default_voice()
    audio = _req(f"/text-to-speech/{vid}?output_format=mp3_44100_128",
                 {"text": text, "model_id": MODEL,
                  "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style,
                                     "use_speaker_boost": True}})
    folder = config.LIBRARY / "voice"
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "line"
    out = out or folder / f"{slug}.mp3"
    with open(out, "wb") as fh:
        fh.write(audio)
    f, st = _settings()
    st["elevenlabs_chars"] = int(st.get("elevenlabs_chars", 0)) + len(text)
    f.write_text(json.dumps(st, indent=1))
    return out


def usage():
    st = _settings()[1]
    return f"Characters used by One Take so far: {st.get('elevenlabs_chars', 0)}"


def convert(audio_in, out, voice=None, model="eleven_multilingual_sts_v2", remove_noise=False):
    """Speech to Speech: re-voice an existing recording as the user (same timing, pauses and emphasis)."""
    import uuid
    from pathlib import Path
    vid = voice or default_voice()
    data = Path(audio_in).read_bytes()
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("model_id", model), ("remove_background_noise", "true" if remove_noise else "false"),
                 ("voice_settings", json.dumps({"stability": 0.5, "similarity_boost": 0.9, "style": 0.0,
                                                "use_speaker_boost": True}))):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="audio"; filename="in.mp3"\r\n'
                 f'Content-Type: audio/mpeg\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"{API}/speech-to-speech/{vid}?output_format=mp3_44100_192", data=b"".join(parts),
                                 headers={"xi-api-key": key(), "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        Path(out).write_bytes(r.read())
    return out
