"""Send to CapCut: writes a real CapCut project (a "draft") you keep editing in CapCut desktop.

- Your cut: the original footage on the main track, one clip per kept piece, so you can still
  drag any cut open again in CapCut.
- Every look on its own track (rendered as a transparent clip, already in position).
- Captions as real, editable CapCut text.
- Cut-aways, music, and every sound effect as its own clip.

Built with pyJianYingDraft (Apache-2.0, https://github.com/GuanYixuan/pyJianYingDraft), which
writes the draft format CapCut and its sister app share. CapCut desktop (Windows / Mac) opens it
from its drafts folder. If that folder isn't on this computer (e.g. a Chromebook), the project is
zipped so you can copy it to a computer that has CapCut.
"""
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import cv2
import numpy as np

from . import analyze, config, draw, project, render, sfx as sfx_mod, timeline

SEC = 1_000_000  # drafts count time in microseconds


def drafts_folder():
    """CapCut's drafts folder on this computer (settings "capcut_drafts" wins), or None."""
    s = config.settings()
    if s.get("capcut_drafts"):
        p = Path(os.path.expanduser(s["capcut_drafts"]))
        return p if p.exists() else None
    cands = []
    if sys.platform == "win32":
        la = os.environ.get("LOCALAPPDATA", "")
        cands += [Path(la) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"]
    elif sys.platform == "darwin":
        cands += [Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft",
                  Path.home() / "Movies" / "CapCut Drafts"]
    return next((c for c in cands if c.exists()), None)


def _key(*parts):
    import hashlib
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:14]


def _us(sec):
    return int(round(max(0.0, sec) * SEC))


def _clean_footage(p, out, progress=None):
    """The whole source (uncut) with face covers, old-caption removal and the color filter baked in,
    so the CapCut cut still lines up with your original footage. Camera zooms are left out on purpose:
    add them in CapCut if you want them."""
    s = config.settings()
    W, H, fps = s["width"], s["height"], s["fps"]
    comp = render.Composer.__new__(render.Composer)  # reuse speaker() without building the edit
    comp.W, comp.H, comp.p, comp.words = W, H, p, p["words"]
    comp.segs = [{"w0": 0, "w1": max(0, len(p["words"]) - 1), "s": 0.0, "e": p["duration"], "o": 0.0}]
    comp.src = render.FrameReader(config.absolute(p["source"]))
    bc = p.get("burned_captions") or {}
    comp.burn_band = (bc.get("band") or [0.0, 1.0]) if bc.get("remove") else None
    comp.burn_state = {}
    comp.tracks = {f["id"]: f["track"] for f in p.get("faces", {}).get("detected", [])}
    comp.covers = [c for c in p.get("faces", {}).get("covers", []) if c.get("face") in comp.tracks]
    fid = p.get("filter") or "none"
    ff = config.LOOKBOOK / "filters.json"
    comp.filter = next((x for x in json.loads(ff.read_text()) if x["id"] == fid), None) if ff.exists() else None
    p_nozoom = dict(p, camera={})
    comp.p = p_nozoom
    N = int(p["duration"] * fps)
    tmpv = out.with_suffix(".video.mp4")
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                            "-pix_fmt", "yuv420p", str(tmpv)], stdin=subprocess.PIPE)
    try:
        for n in range(N):
            t = n / fps
            enc.stdin.write(comp.speaker(t, t).tobytes())
            if progress and n % 30 == 0:
                progress(n / N)
    finally:
        enc.stdin.close()
        enc.wait()
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmpv), "-i", str(config.absolute(p["source"])),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    tmpv.unlink()
    return out


def _look_clip(p, ov, span, out, W=1080, H=1920, fps=30):
    """One look as a full-canvas transparent clip (already positioned and animated)."""
    a, b = span
    n = max(1, int(round((b - a) * fps)))
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra",
                            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"] + render._prores_alpha() + [str(out)],
                           stdin=subprocess.PIPE)
    try:
        for k in range(n):
            t = a + k / fps
            layer = np.zeros((H, W, 4), np.uint8)
            img = render._overlay_img(ov, t - a, b - a, W, H)
            if img is not None:
                st = draw.overlay_state(ov, t, a, b)
                ps = draw.push_scale(ov, t, a, b)
                if ps != 1.0:
                    st = dict(st, scale=st["scale"] * ps)
                img = draw.transform(img, st)
                render.blend_onto_rgba(layer, img, (float(ov.get("x", 0.5)) + st["dx"]) * W,
                                       (float(ov.get("y", 0.5)) + st["dy"]) * H)
            enc.stdin.write(layer.tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
    return out


def _caption_text(p, g, style):
    t = " ".join(p["words"][i]["t"] for i in g["w"])
    return draw.case(t, style)


def build(name, progress=None):
    import pyJianYingDraft as dr

    prog = progress or (lambda x: None)
    p = project.load(name)
    s = config.settings()
    W, H, fps = s["width"], s["height"], s["fps"]
    words = p["words"]
    segs = project.segments(p)
    T = timeline.total(segs)
    speed = float(p.get("speed") or 1.0)
    sp = lambda x: x / speed  # project time -> CapCut timeline time

    folder = drafts_folder()
    root = folder or (project.pdir(name) / "exports" / "capcut-project")
    root.mkdir(parents=True, exist_ok=True)
    import re as _re
    dname = _re.sub(r"[^A-Za-z0-9 _-]+", "", (p.get("title") or name)).strip()[:50] or name
    dname += " - One Take"
    dpath = root / dname
    if dpath.exists():
        shutil.rmtree(dpath)
    script = dr.DraftFolder(str(root)).create_draft(dname, W, H, fps, allow_replace=True)
    media = dpath / "onetake_media"
    media.mkdir(parents=True, exist_ok=True)

    # 1. your cut, on the original (cleaned) footage
    needs_clean = bool(p.get("faces", {}).get("covers") or (p.get("burned_captions") or {}).get("remove")
                       or (p.get("filter") or "none") != "none")
    footage = media / "footage.mp4"
    cache = project.pdir(name) / "cache" / "capcut"
    cache.mkdir(parents=True, exist_ok=True)
    if needs_clean:
        key = _key(p.get("faces", {}).get("covers"), p.get("burned_captions", {}).get("remove"),
                   p.get("burned_captions", {}).get("band"), p.get("filter"), p["source"])
        cached = cache / f"footage_{key}.mp4"
        if not cached.exists():
            _clean_footage(p, cached, progress=lambda x: prog(x * 0.45))
        shutil.copy2(cached, footage)
    else:
        shutil.copy2(config.absolute(p["source"]), footage)
    prog(0.45)
    mat = dr.VideoMaterial(str(footage))
    main = script.append_track(dr.TrackSpec(dr.TrackType.video, "Your cut"))
    for sg in segs:
        dur = min(sg["e"] - sg["s"], mat.duration / SEC - sg["s"] - 0.001)
        if dur <= 0.02:
            continue
        tgt = dr.Timerange(_us(sp(sg["o"])), _us(sp(dur)))
        script.add_segment(dr.VideoSegment(mat, tgt, source_timerange=dr.Timerange(_us(sg["s"]), _us(dur)),
                                           speed=speed if speed != 1.0 else None), main)

    # 2. cut-aways
    brolls = [(b, timeline.range_out(words, segs, b["w0"], b["w1"])) for b in p.get("broll", [])]
    brolls = [(b, r) for b, r in brolls if r]
    if brolls:
        btrack = script.append_track(dr.TrackSpec(dr.TrackType.video, "Cut-aways"))
        for k, (b, (a, z)) in enumerate(brolls):
            if b.get("src"):
                src = config.absolute(b["src"])
                dst = media / f"broll_{k}{src.suffix.lower()}"
                shutil.copy2(src, dst)
            else:  # plain panel
                dst = media / f"panel_{k}.png"
                col = draw.rgba(b.get("color", "#FFFFFF"))
                cv2.imwrite(str(dst), np.full((H, W, 3), (col[2], col[1], col[0]), np.uint8))
            bm = dr.VideoMaterial(str(dst))
            is_img = dst.suffix.lower() in config.IMAGE_EXT
            if not is_img:
                cs = min(float(b.get("clip_start", 0)), max(0.0, bm.duration / SEC - (z - a) - 0.01))
                b = dict(b, clip_start=cs)
                z = min(z, a + bm.duration / SEC - cs - 0.001)
            seg = dr.VideoSegment(bm, dr.Timerange(_us(sp(a)), _us(sp(z - a))),
                                  source_timerange=None if is_img else dr.Timerange(_us(float(b.get("clip_start", 0))), _us(z - a)),
                                  volume=0.35 if b.get("audio") == "under" else 0.0,
                                  clip_settings=dr.ClipSettings(scale_x=0.5, scale_y=0.5, transform_y=0.5)
                                  if b.get("layout") == "split" else None)
            script.add_segment(seg, btrack)
    prog(0.5)

    # 3. every look on its own track
    ovs = [(ov, timeline.overlay_span(p, words, segs, ov)) for ov in p.get("overlays", [])]
    ovs = [(ov, r) for ov, r in ovs if r]
    for k, (ov, (a, z)) in enumerate(ovs):
        label = (ov.get("look") or ov.get("emoji") or Path(ov.get("src") or "media").stem)
        cached = cache / f"look_{_key(ov, round(z - a, 3))}.mov"
        if not cached.exists():
            _look_clip(p, ov, (a, z), cached, W, H, fps)
        clip = media / f"look_{k:02d}_{label}.mov"
        shutil.copy2(cached, clip)
        lm = dr.VideoMaterial(str(clip))
        tr = script.append_track(dr.TrackSpec(dr.TrackType.video, f"Look {k + 1}: {label}"))
        dur = min(z - a, lm.duration / SEC - 0.001)
        script.add_segment(dr.VideoSegment(lm, dr.Timerange(_us(sp(a)), _us(sp(dur))),
                                           source_timerange=dr.Timerange(0, _us(dur)),
                                           speed=speed if speed != 1.0 else None), tr)
        prog(0.5 + 0.35 * (k + 1) / max(1, len(ovs)))

    # 4. captions as editable CapCut text
    if p.get("captions", True):
        styles = {c["id"]: c for c in project.caption_styles()}
        style = dict(styles.get(p.get("caption_style")) or next(iter(styles.values())))
        if p.get("caption_y") is not None:
            style["y"] = float(p["caption_y"])
        groups = timeline.caption_groups(words, segs, style)
        if groups:
            ttrack = script.append_track(dr.TrackSpec(dr.TrackType.text, "Captions"))
            col = draw.rgba(style.get("color", "#FFFFFF"))
            size = max(5.0, min(14.0, style["size"] / 9.0))
            border = dr.TextBorder(color=(0.0, 0.0, 0.0), width=min(80.0, style.get("stroke_w", 0) * 8.0)) \
                if style.get("stroke_w") else None
            for gi, g in enumerate(groups):
                a, z = g["start"], g["end"]
                if gi + 1 < len(groups):
                    z = min(z, groups[gi + 1]["start"])
                if z - a < 0.04:
                    continue
                script.add_segment(dr.TextSegment(
                    _caption_text(p, g, style), dr.Timerange(_us(sp(a)), _us(sp(z - a))),
                    style=dr.TextStyle(size=size, bold=True, color=(col[0] / 255, col[1] / 255, col[2] / 255), align=1),
                    border=border,
                    clip_settings=dr.ClipSettings(transform_x=(float(style.get("x", 0.5)) - 0.5) * 2,
                                                  transform_y=-(float(style.get("y", 0.7)) - 0.5) * 2)), ttrack)

    # 5. music
    snd = p.get("sound") or {}
    if snd.get("src") and config.absolute(snd["src"]).exists():
        src = config.absolute(snd["src"])
        dst = media / ("music" + src.suffix.lower())
        shutil.copy2(src, dst)
        am = dr.AudioMaterial(str(dst))
        mlen = am.duration / SEC
        mtrack = script.append_track(dr.TrackSpec(dr.TrackType.audio, "Music"))
        t, off = 0.0, float(snd.get("offset", 0))
        total = sp(T)
        while t < total - 0.05 and mlen > 0.5:
            piece = min(total - t, mlen - off)
            script.add_segment(dr.AudioSegment(am, dr.Timerange(_us(t), _us(piece)),
                                               source_timerange=dr.Timerange(_us(off), _us(piece)),
                                               volume=float(snd.get("volume", 0.12))), mtrack)
            t += piece
            off = 0.0

    # 6. every sound effect as its own clip
    if p.get("sfx_on", True):
        master = float(p.get("sfx_volume", 0.6))
        lanes = []  # (track, end time) so effects never overlap on one track
        for fx, t in sorted(sfx_mod.times(p, segs), key=lambda x: x[1]):
            path = config.absolute(fx["src"]) if fx.get("src") else None
            if fx.get("muted") or not path or not path.exists() or t >= T:
                continue
            dst = media / f"sfx_{path.name}"
            if not dst.exists():
                shutil.copy2(path, dst)
            am = dr.AudioMaterial(str(dst))
            dur = min(am.duration / SEC, max(0.05, T - t))
            a = sp(t)
            lane = next((l for l in lanes if l[1] <= a), None)
            if lane is None:
                lane = [script.append_track(dr.TrackSpec(dr.TrackType.audio, f"Sound FX {len(lanes) + 1}")), 0.0]
                lanes.append(lane)
            script.add_segment(dr.AudioSegment(am, dr.Timerange(_us(a), _us(dur)),
                                               volume=float(fx.get("volume", 0.4)) * master), lane[0])
            lane[1] = a + dur

    script.save()
    _brand_as_capcut(dpath)
    prog(0.97)

    out = {"folder": str(dpath), "in_capcut": bool(folder)}
    if not folder:  # no CapCut here: zip it, with one-click installers for Windows and Mac
        _make_portable(dpath)
        z = project.pdir(name) / "exports" / "capcut-project.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            for f in sorted(dpath.rglob("*")):
                zf.write(f, f"{dname}/{f.relative_to(dpath)}")
            for fname, body, mode in _installers(dname):
                info = zipfile.ZipInfo(fname)
                info.external_attr = (mode << 16)
                zf.writestr(info, body)
        out["zip"] = config.rel(z)
    prog(1.0)
    return out


def _brand_as_capcut(dpath):
    """Mark the draft as a CapCut (international) project and fill in its folder details."""
    content = dpath / "draft_content.json"
    d = json.loads(content.read_text(encoding="utf-8"))
    plat = {"app_id": 359289, "app_source": "cc", "app_version": "5.9.0",
            "os": "mac" if sys.platform == "darwin" else "windows"}
    d["platform"] = dict(plat)
    d["last_modified_platform"] = dict(plat)
    content.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    meta_f = dpath / "draft_meta_info.json"
    meta = json.loads(meta_f.read_text(encoding="utf-8"))
    meta["draft_id"] = str(uuid.uuid4()).upper()
    meta["draft_name"] = dpath.name
    meta["draft_fold_path"] = str(dpath).replace("\\", "/")
    meta["draft_root_path"] = str(dpath.parent).replace("\\", "/")
    meta["tm_duration"] = d.get("duration", 0)
    meta_f.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


PLACEHOLDER = "__ONETAKE_DRAFT_DIR__"


def _make_portable(dpath):
    """Swap this computer's folder for a placeholder; the installer fills in the real one."""
    here = str(dpath).replace("\\", "/")
    root = str(dpath.parent).replace("\\", "/")
    for fn in ("draft_content.json", "draft_meta_info.json"):
        f = dpath / fn
        t = f.read_text(encoding="utf-8").replace(here, PLACEHOLDER).replace(root, PLACEHOLDER + "/..")
        f.write_text(t, encoding="utf-8")


def _installers(dname):
    win = f"""@echo off
rem One Take Studio: puts this project into CapCut (Windows). Close CapCut first.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$src = Join-Path '%~dp0' '{dname}';" ^
 "$root = Join-Path $env:LOCALAPPDATA 'CapCut\\User Data\\Projects\\com.lveditor.draft';" ^
 "if (-not (Test-Path $root)) {{ Write-Host 'CapCut drafts folder not found. Open CapCut once, or copy the project folder into your CapCut drafts folder (CapCut: Settings - Drafts location).'; pause; exit 1 }};" ^
 "$dst = Join-Path $root '{dname}'; if (Test-Path $dst) {{ Remove-Item -Recurse -Force $dst }};" ^
 "Copy-Item -Recurse -Force $src $dst;" ^
 "$real = ($dst -replace '\\\\','/');" ^
 "foreach ($f in 'draft_content.json','draft_meta_info.json') {{ $p = Join-Path $dst $f; $t = [IO.File]::ReadAllText($p); [IO.File]::WriteAllText($p, $t.Replace('{PLACEHOLDER}/..', ($root -replace '\\\\','/')).Replace('{PLACEHOLDER}', $real)) }};" ^
 "Write-Host 'Done! Open CapCut and you will find: {dname}'"
pause
"""
    mac = f"""#!/bin/bash
# One Take Studio: puts this project into CapCut (Mac). Close CapCut first.
cd "$(dirname "$0")"
ROOT="$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft"
[ -d "$ROOT" ] || ROOT="$HOME/Movies/CapCut Drafts"
if [ ! -d "$ROOT" ]; then echo "CapCut drafts folder not found. Open CapCut once, or copy the project folder into your CapCut drafts folder (CapCut: Settings - Drafts location)."; read -n 1; exit 1; fi
DST="$ROOT/{dname}"
rm -rf "$DST"; cp -R "{dname}" "$DST"
for f in draft_content.json draft_meta_info.json; do
  /usr/bin/perl -pi -e 's#\\Q{PLACEHOLDER}/..\\E#$ENV{{ROOT}}#g; s#\\Q{PLACEHOLDER}\\E#$ENV{{DST}}#g' "$DST/$f"
done
echo "Done! Open CapCut and you will find: {dname}"
"""
    mac = mac.replace("for f in", "export ROOT DST\nfor f in")
    readme = f"""HOW TO OPEN THIS IN CAPCUT (desktop app, Windows or Mac)

1. Unzip this file.
2. Close CapCut.
3. Windows: double-click "Install in CapCut (Windows).bat"
   Mac:     double-click "Install in CapCut (Mac).command"
            (first time: right-click it > Open, because it was downloaded)
4. Open CapCut. "{dname}" is in your projects.

What's inside: your cut on the original footage (drag any clip edge to bring a cut back),
every look on its own track, captions as editable CapCut text, cut-aways, music, and every
sound effect as its own clip.

If CapCut stores drafts somewhere else (CapCut > Settings > Drafts location), copy the
"{dname}" folder there yourself, then run the installer from that folder's parent.
"""
    return [("Install in CapCut (Windows).bat", win.replace("\n", "\r\n"), 0o644),
            ("Install in CapCut (Mac).command", mac, 0o755),
            ("HOW TO OPEN IN CAPCUT.txt", readme, 0o644)]
