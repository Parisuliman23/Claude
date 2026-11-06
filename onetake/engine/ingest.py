"""Step 1: take the clips in drop-in-order/ (sorted by name), join them into
one vertical master video, transcribe it and make the automatic rough cut."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import config, project, transcribe, roughcut


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate:stream_tags=rotate:stream_side_data=rotation",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def duration(path):
    return float(ffprobe(path)["format"]["duration"])


def has_audio(path):
    return any(s.get("codec_type") == "audio" for s in ffprobe(path).get("streams", []))


def is_hdr(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
    return out in ("arib-std-b67", "smpte2084")


# iPhone HDR (HLG/PQ) -> normal colors. Needs ffmpeg built with zimg (Homebrew's is).
TONEMAP = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,"


def drop_clips(folder=None):
    folder = Path(folder or config.DROP)
    return sorted([p for p in folder.iterdir() if p.suffix.lower() in config.VIDEO_EXT], key=lambda p: p.name.lower())


def make_master(clips, out, log=print):
    """Normalize every clip to W x H (cover-crop), constant fps, then join."""
    s = config.settings()
    W, H, fps = s["width"], s["height"], s["fps"]
    tmp = out.parent / "_parts"
    tmp.mkdir(exist_ok=True)
    parts = []
    from . import progress
    clip_secs = []
    for c in clips:
        try:
            clip_secs.append(duration(c))
        except Exception:  # noqa: BLE001
            clip_secs.append(0)
    total = sum(clip_secs)
    for n, c in enumerate(clips):
        part = tmp / f"{n:03d}.mp4"
        log(f"  preparing {c.name}")
        cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(c)]
        if not has_audio(c):
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-shortest"]
        # frame rate and size first: everything after (HDR color fix, encoding) then works on far fewer pixels
        vf = f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        tail = ["-map", "0:v:0", "-map", "0:a:0" if has_audio(c) else "1:a:0",
                # this file is only the editing master: on a slow computer, encode fast and keep quality with crf
                "-c:v", "libx264", "-preset", "ultrafast" if config.is_chromebook() else "veryfast",
                "-crf", "17", "-pix_fmt", "yuv420p",
                # a keyframe every 0.5s keeps scrubbing in the browser snappy
                "-g", str(fps // 2), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "1",
                "-progress", "pipe:1", "-nostats", str(part)]
        done_before = sum(clip_secs[:n])

        def run(filters):
            """ffmpeg with the % of this clip reported to the new-reel progress bar."""
            p = subprocess.Popen(cmd + ["-vf", filters] + tail, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in p.stdout:
                if line.startswith("out_time_us=") and total > 0:
                    try:
                        progress.mark("join", (done_before + int(line.split("=")[1]) / 1e6) / total)
                    except ValueError:
                        pass
            err = p.stderr.read()
            if p.wait():
                raise subprocess.CalledProcessError(p.returncode, "ffmpeg", stderr=err)
        if is_hdr(c):
            try:
                run(vf.replace(",setsar=1", "") + "," + TONEMAP + "setsar=1")
                parts.append(part)
                continue
            except subprocess.CalledProcessError:
                log("  (couldn't convert HDR colors with this ffmpeg — colors may look flat)")
        run(vf)
        parts.append(part)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp)


def new(name=None, clips=None, log=print, move=True):
    clips = [Path(c) for c in clips] if clips else drop_clips()
    if not clips:
        raise SystemExit(f"No videos found. Drop your clips into {config.DROP} (they're used in name order).")
    name = project.slug(name or re.sub(r"^\d{2}_", "", clips[0].stem))  # drop the order prefix from dragged-in files
    for d in config.PROJECTS.glob("*/raw"):  # an earlier try at these same clips that stopped halfway: replace it
        if not (d.parent / "project.json").exists() and {f.name for f in d.iterdir()} == {c.name for c in clips}:
            shutil.rmtree(d.parent, ignore_errors=True)
    base = name
    k = 2
    while project.exists(name):
        name = f"{base}-{k}"
        k += 1
    d = project.pdir(name)
    (d / "raw").mkdir(parents=True)
    (d / "exports").mkdir()
    (d / "frames").mkdir()
    log(f"New project: {name}")
    from . import progress
    progress.mark("join")
    for c in clips:
        shutil.copy2(c, d / "raw" / c.name)
    make_master(clips, d / "source.mp4", log)
    log("  transcribing (word by word)…")
    progress.mark("transcribe", 0)
    words, lines = transcribe.run(d / "source.mp4", progress=lambda f: progress.mark("transcribe", f))
    progress.mark("analyze")
    dur = duration(d / "source.mp4")
    s = config.settings()
    title = name.replace("-", " ")
    if re.fullmatch(r"(img|vid|pxl|video|mov|movie|clip|screen recording)[ _-]?\d[\d _-]*", title, re.I) and words:
        title = " ".join(w["t"] for w in words[:7]).strip(" ,.!?").capitalize()  # phone file name: use what you say
    p = {
        "title": title,
        "created": time.time(),
        "source": config.rel(d / "source.mp4"),
        "duration": dur,
        "fps": s["fps"],
        "words": words,
        "engine_cuts": [],
        "caption_style": s["default_caption_style"],
        "overlays": [],
        "broll": [],
        "faces": {"detected": [], "covers": []},
        "camera": {"push_in": 7, "push_amount": 0.08, "punches": [], "punch_scale": 1.12},
        "sound": {"src": None, "volume": s["music_volume"], "offset": 0},
        "sfx": [], "sfx_on": True, "sfx_volume": 0.6,
        "hook_duration": 5.0,
        "frames": [],
        "exports": {},
        "requests": [],
        "render": {"status": "none"},
        "rev": 0,
    }
    from . import analyze as _an
    p["focus"] = _an.face_focus(d / "source.mp4")  # where the eyes are: punch-ins and split screens aim here
    log("  checking for captions already in the video…")
    from . import analyze
    scan = analyze.scan_burned_text(d / "source.mp4", fps=2 if config.fast() else 4)
    if scan["coverage"] >= 0.5 and scan["band"]:
        p["burned_captions"] = {"remove": True, **scan}
        # put our captions where the old ones were, so they cover any trace
        p["caption_y"] = round(min(0.85, max(0.15, (scan["band"][0] + scan["band"][1]) / 2)), 3)
        log(f"  found captions in {scan['coverage'] * 100:.0f}% of the video — they'll be painted out "
            f"and replaced with yours")
    progress.mark("cut")
    log("  making the rough cut…")
    roughcut.run(p)
    # Default look: the first line becomes a styled hook title.
    first = next((w for w in p["words"] if not w.get("cut")), None)
    if first is not None:
        ls = [l for l in project.lines(p) if not l["cut"]]
        p["overlays"].append({
            "id": project.new_id(), "kind": "look", "look": s["default_hook_look"], "role": "hook",
            "w0": ls[0]["w0"], "w1": ls[0]["w1"], "x": 0.5, "y": 0.13, "scale": 1.0,
            # your style: the headline types on from frame 1 and hard-cuts off
            "anim_in": "none", "anim_out": "none", "params": {"text": ls[0]["text"]},
        })
    sounds = sorted((config.LIBRARY / "sounds").glob("*"))
    sounds = [x for x in sounds if x.suffix.lower() in config.AUDIO_EXT]
    if sounds:
        p["sound"]["src"] = config.rel(sounds[0])
    project.save(name, p)
    if move:  # empty the drop folder so the next reel starts clean (only now: if the import stops, they're still there)
        for c in clips:
            if c.parent.resolve() == config.DROP.resolve():
                c.unlink(missing_ok=True)
    log(f"Done. {len(p['words'])} words, {len(p['engine_cuts'])} lines cut automatically.")
    return name
