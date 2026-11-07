"""The renderer: builds the finished reel (or separate layers for CapCut).
Nothing is rendered while you edit — the studio previews everything live in
the browser, and this runs only when you press "Lock in my looks"."""
import copy
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import analyze, config, draw, looks, project, timeline


class FrameReader:
    """Random-ish access to video frames, fast when reading forwards."""

    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.pos = -1
        self.frame = None

    def at(self, t):
        idx = max(0, int(round(t * self.fps)))
        if self.n:
            idx = min(idx, self.n - 1)
        if idx == self.pos and self.frame is not None:
            return self.frame
        if idx < self.pos or idx - self.pos > 45:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            self.pos = idx - 1
        while self.pos < idx:
            if not self.cap.grab():
                break
            self.pos += 1
        ok, fr = self.cap.retrieve()
        if ok:
            self.frame = fr
        return self.frame


BROLL_FADE = 0.25


class StillReader:
    """A photo/screenshot used as a cut-away (same interface as FrameReader)."""

    def __init__(self, path):
        im = cv2.imread(str(path), cv2.IMREAD_COLOR)
        self.frame = im if im is not None else np.zeros((16, 16, 3), np.uint8)

    def at(self, t):
        return self.frame


def _reader(src):
    if not src:
        return None  # a plain colour panel
    path = config.absolute(src)
    return StillReader(path) if path.suffix.lower() in config.IMAGE_EXT else FrameReader(path)


def _broll_frame(b, rd, t_local, W, H):
    if rd is None:
        col = draw.rgba(b.get("color", "#FFFFFF"))
        return np.full((H, W, 3), (col[2], col[1], col[0]), np.uint8)
    return cover_fit(rd.at(float(b.get("clip_start", 0)) + t_local), W, H)


def cover_fit(fr, W, H):
    h, w = fr.shape[:2]
    if (w, h) == (W, H):
        return fr.copy()
    sc = max(W / w, H / h)
    nw, nh = int(round(w * sc)), int(round(h * sc))
    r = cv2.resize(fr, (nw, nh), interpolation=cv2.INTER_AREA)
    x, y = (nw - W) // 2, (nh - H) // 2
    return r[y:y + H, x:x + W].copy()


def apply_variant(p, v):
    """A trial-reel variant: different opening line, length and/or hook text, same look."""
    p = copy.deepcopy(p)
    order = None
    if not v:
        return p, None
    if v.get("caption_style"):
        p["caption_style"] = v["caption_style"]
    if v.get("hook_text"):
        for ov in p["overlays"]:
            if ov.get("role") == "hook":
                ov.setdefault("params", {})["text"] = v["hook_text"]
    ls = [l for l in project.lines(p) if not l["cut"]]
    if v.get("drop_lines"):
        for l in project.lines(p):
            if l["id"] in v["drop_lines"]:
                for i in range(l["w0"], l["w1"] + 1):
                    p["words"][i]["cut"] = True
        ls = [l for l in project.lines(p) if not l["cut"]]
    if v.get("max_len"):
        # drop lines from the back half (never the first or last line) until it fits
        while len(ls) > 2 and timeline.total(project.segments(p)) > v["max_len"]:
            victim = ls[-2]
            for i in range(victim["w0"], victim["w1"] + 1):
                p["words"][i]["cut"] = True
            ls = [l for l in project.lines(p) if not l["cut"]]
    if v.get("open_line") is not None:
        first = next((l for l in ls if l["id"] == v["open_line"]), None)
        if first:
            order = [(first["w0"], first["w1"])] + [(l["w0"], l["w1"]) for l in ls if l["id"] != first["id"]]
    return p, order


def _has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True).stdout
    return bool(out.strip())


def _audio(p, segs, T, out):
    src = str(config.absolute(p["source"]))
    parts, fl = [], []
    for k, sg in enumerate(segs):
        ln = sg["e"] - sg["s"]
        fl.append(f"[0:a]atrim={sg['s']}:{sg['e']},asetpts=PTS-STARTPTS,"
                  f"afade=t=in:d=0.012,afade=t=out:st={max(0, ln - 0.012):.3f}:d=0.012[a{k}]")
        parts.append(f"[a{k}]")
    fl.append("".join(parts) + f"concat=n={len(segs)}:v=0:a=1[voice]")
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src]
    snd = p.get("sound") or {}
    mix = ["[voice]"]
    n_in = 1
    if snd.get("src") and config.absolute(snd["src"]).exists():
        cmd += ["-stream_loop", "-1", "-i", str(config.absolute(snd["src"]))]
        off = float(snd.get("offset", 0))
        fl.append(f"[{n_in}:a]atrim={off}:{off + T},asetpts=PTS-STARTPTS,volume={float(snd.get('volume', 0.12))},"
                  f"afade=t=in:d=0.3,afade=t=out:st={max(0, T - 1.5):.3f}:d=1.5[m]")
        mix.append("[m]")
        n_in += 1
    for k, b in enumerate(p.get("broll", [])):  # cut-away clips whose sound plays under the voice
        if b.get("audio") != "under" or not b.get("src"):
            continue
        path = config.absolute(b["src"])
        if path.suffix.lower() not in config.VIDEO_EXT or not _has_audio(path):
            continue
        sp = timeline.range_out(p["words"], segs, b["w0"], b["w1"])
        if not sp:
            continue
        cs = float(b.get("clip_start", 0))
        cmd += ["-i", str(path)]
        fl.append(f"[{n_in}:a]atrim={cs:.3f}:{cs + sp[1] - sp[0]:.3f},asetpts=PTS-STARTPTS,aresample=48000,volume=0.35,"
                  f"afade=t=in:d=0.15,afade=t=out:st={max(0, sp[1] - sp[0] - 0.2):.3f}:d=0.2,adelay={int(sp[0] * 1000)}:all=1[br{k}]")
        mix.append(f"[br{k}]")
        n_in += 1
    if p.get("sfx_on", True):  # sound effects, each delayed to its moment
        from . import sfx
        master = float(p.get("sfx_volume", 0.6))
        for k, (fx, t) in enumerate(sfx.times(p, segs)):
            path = config.absolute(fx["src"]) if fx.get("src") else None
            if fx.get("muted") or not path or not path.exists() or t >= T:
                continue
            cmd += ["-i", str(path)]
            ms = int(t * 1000)
            fl.append(f"[{n_in}:a]aresample=48000,volume={float(fx.get('volume', 0.4)) * master:.3f},"
                      f"adelay={ms}:all=1[fx{k}]")
            mix.append(f"[fx{k}]")
            n_in += 1
    if len(mix) > 1:
        fl.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first[out]")
    else:
        fl.append("[voice]anull[out]")
    script = Path(out).with_suffix(".filter.txt")
    script.write_text(";\n".join(fl))
    cmd += ["-filter_complex_script", str(script), "-map", "[out]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)]
    subprocess.run(cmd, check=True)
    script.unlink()


def _cover(frame, pos, cov, W, H):
    cx, cy, s = pos
    size = int(s * W * float(cov.get("scale", 1.3)) * 1.25)
    if size < 8:
        return
    X, Y = int(cx * W), int(cy * H)
    style = cov.get("style", "emoji")
    if style in ("blur", "pixelate"):
        x0, y0, x1, y1 = max(0, X - size // 2), max(0, Y - int(size * 0.6)), min(W, X + size // 2), min(H, Y + int(size * 0.6))
        if x1 <= x0 or y1 <= y0:
            return
        roi = frame[y0:y1, x0:x1]
        if style == "blur":
            k = max(3, (size // 3) | 1)
            fx = cv2.GaussianBlur(roi, (k, k), 0)
            fx = cv2.GaussianBlur(fx, (k, k), 0)
        else:
            small = cv2.resize(roi, (max(1, roi.shape[1] // 18), max(1, roi.shape[0] // 18)), interpolation=cv2.INTER_AREA)
            fx = cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask = np.zeros(roi.shape[:2], np.uint8)
        cv2.ellipse(mask, (roi.shape[1] // 2, roi.shape[0] // 2), (roi.shape[1] // 2, roi.shape[0] // 2), 0, 0, 360, 255, -1)
        mask = cv2.GaussianBlur(mask, (21, 21), 0)[:, :, None] / 255.0
        frame[y0:y1, x0:x1] = (fx * mask + roi * (1 - mask)).astype(np.uint8)
    else:
        kind, ref = ("emoji", cov.get("emoji", "1f60a")) if style == "emoji" else ("image", str(config.absolute(cov["image"])))
        base = draw.emoji(ref) if kind == "emoji" else draw.load_image(ref)
        if base is None:
            return
        r = size / max(base.size)
        draw.blend(frame, draw.resized(kind, ref, base.width * r, base.height * r), X, Y)


def _overlay_img(ov, t_local, dur, W, H):
    kind = ov["kind"]
    if kind == "look":
        img = looks.frame(ov["look"], ov.get("params", {}), t_local, dur, W, H)
        if img is None:
            return None
        sc = float(ov.get("scale", 1.0))
    else:
        if kind == "emoji":
            img = draw.emoji(ov["emoji"])
        else:
            img = draw.media_image(str(config.absolute(ov["src"])), t_local)
        if img is None:
            return None
        sc = float(ov.get("scale", 0.5)) * W / img.width
        if kind == "emoji" or draw.load_image(str(config.absolute(ov["src"]))) is not None:  # static: cache
            ref = ov["emoji"] if kind == "emoji" else str(config.absolute(ov["src"]))
            return draw.resized("emoji" if kind == "emoji" else "image", ref, img.width * sc, img.height * sc)
    if abs(sc - 1.0) > 0.01:
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.LANCZOS)
    return img


def blend_onto_rgba(layer, img, cx, cy):
    """'over' compositing onto a transparent BGRA layer."""
    H, W = layer.shape[:2]
    w, h = img.size
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    a = np.asarray(img)[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    sa = a[:, :, 3:4] / 255.0
    src = a[:, :, 2::-1]
    dst = layer[fy0:fy1, fx0:fx1].astype(np.float32)
    da = dst[:, :, 3:4] / 255.0
    oa = sa + da * (1 - sa)
    rgb = (src * sa + dst[:, :, :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    layer[fy0:fy1, fx0:fx1, :3] = rgb.astype(np.uint8)
    layer[fy0:fy1, fx0:fx1, 3:4] = (oa * 255).astype(np.uint8)


class Composer:
    """Builds output frames for one edit. Used by render() and by `engine still`."""

    def __init__(self, name, variant=None, layer="full", p=None):
        s = config.settings()
        self.W, self.H, self.fps = s["width"], s["height"], s["fps"]
        p = p or project.load(name)
        p, order = apply_variant(p, variant)
        self.p, self.layer = p, layer
        self.words = words = p["words"]
        self.segs = segs = project.segments(p, order=order)
        if not segs:
            raise RuntimeError("Everything is cut — nothing to render.")
        self.T = timeline.total(segs)
        styles = {c["id"]: c for c in project.caption_styles()}
        self.style = dict(styles.get(p.get("caption_style")) or next(iter(styles.values())))
        if p.get("caption_y") is not None:  # per-reel caption height override
            self.style["y"] = float(p["caption_y"])
        self.groups = timeline.caption_groups(words, segs, self.style) if p.get("captions", True) else []
        self.ovs = []
        for ov in p.get("overlays", []):
            sp = timeline.overlay_span(p, words, segs, ov)
            if sp:
                self.ovs.append((ov, sp))
        self.brolls = []
        for b in p.get("broll", []):
            sp = timeline.range_out(words, segs, b["w0"], b["w1"])
            if sp:
                self.brolls.append((b, sp, _reader(b.get("src"))))
        self.tracks = {f["id"]: f["track"] for f in p.get("faces", {}).get("detected", [])}
        self.covers = [c for c in p.get("faces", {}).get("covers", []) if c.get("face") in self.tracks]
        self.src = FrameReader(config.absolute(p["source"]))
        bc = p.get("burned_captions") or {}
        self.burn_band = (bc.get("band") or [0.0, 1.0]) if bc.get("remove") else None
        self.burn_state = {}
        fid = p.get("filter") or "none"
        self.filter = next((x for x in json.loads((config.LOOKBOOK / "filters.json").read_text()) if x["id"] == fid), None) \
            if (config.LOOKBOOK / "filters.json").exists() else None
        self.transparent = layer in ("captions", "graphics")
        self.cap_cache = {}

    def frame(self, t):
        W, H, layer, words, segs, style = self.W, self.H, self.layer, self.words, self.segs, self.style
        if self.transparent:
            frame = np.zeros((H, W, 4), np.uint8)
            put = lambda img, x, y: blend_onto_rgba(frame, img, x, y)
        else:
            sg, ts = timeline.out_to_src(segs, t)
            br = next(((b, sp, rd) for b, sp, rd in self.brolls if sp[0] <= t < sp[1]), None)
            split = bool(br and br[0].get("layout") == "split")
            if br and not split:
                b, sp, rd = br
                frame = draw.apply_filter(_broll_frame(b, rd, t - sp[0], W, H), self.filter)
                if b.get("trans") == "fade":  # "Comes in: Fade" — cross-dissolve with the speaker
                    k = min(1.0, (t - sp[0]) / BROLL_FADE, (sp[1] - t) / BROLL_FADE)
                    if k < 1.0:
                        frame = cv2.addWeighted(frame, k, self.speaker(ts, t), 1 - k, 0)
            else:
                frame = self.speaker(ts, t)
                if split:  # top half: the clip/graphic, bottom half: the speaker (eyes kept in view)
                    b, sp, rd = br
                    top = draw.apply_filter(_broll_frame(b, rd, t - sp[0], W, H // 2), self.filter)
                    if b.get("trans") == "fade":
                        k = min(1.0, (t - sp[0]) / BROLL_FADE, (sp[1] - t) / BROLL_FADE)
                        if k < 1.0:
                            top = cv2.addWeighted(top, k, frame[:H // 2], 1 - k, 0)
                    # keep the eyes ~40% down the bottom half
                    y0 = int(min(max(0, timeline.focus(self.p)[1] * H - 0.4 * (H // 2)), H - (H - H // 2)))
                    bottom = frame[y0:y0 + (H - H // 2)].copy()
                    frame = np.vstack([top, bottom])
            dim = max((float(ov.get("dim", 0)) for ov, (a, b) in self.ovs if a <= t < b), default=0.0)
            if dim > 0:  # receipt stacks: darken the background so the cards read
                frame = (frame * (1 - min(0.8, dim))).astype(np.uint8)
            put = lambda img, x, y: draw.blend(frame, img, x, y)
        if layer in ("full", "graphics"):
            for ov, (a, b) in self.ovs:
                if a <= t < b:
                    img = _overlay_img(ov, t - a, b - a, W, H)
                    if img is None:
                        continue
                    st = draw.overlay_state(ov, t, a, b)
                    ps = draw.push_scale(ov, t, a, b)
                    if ps != 1.0:
                        st = dict(st, scale=st["scale"] * ps)
                    img = draw.transform(img, st)
                    put(img, (float(ov.get("x", 0.5)) + st["dx"]) * W, (float(ov.get("y", 0.5)) + st["dy"]) * H)
        if layer in ("full", "captions"):
            g = next((g for g in self.groups if g["start"] <= t < g["end"]), None)
            if g:
                gi = self.groups.index(g)
                active = g["w"][0]
                for i in g["w"]:
                    wo = timeline.word_out(words, segs, i)
                    if wo and wo[0] <= t:
                        active = i
                t_in = t - g["start"]
                pop = bool(style.get("pop"))
                key = (gi, active, min(5, int(t_in * self.fps)) if pop else 0)
                if key not in self.cap_cache:
                    if len(self.cap_cache) > 200:
                        self.cap_cache.clear()
                    self.cap_cache[key] = draw.caption_image(words, g, active, style, W, t_in if pop else None)
                in_split = any(b.get("layout") == "split" and sp[0] <= t < sp[1] for b, sp, _ in self.brolls)
                cy = 0.5 if in_split else style.get("y", 0.7)  # split screen: caption sits on the seam
                cap = self.cap_cache[key]
                fade = float(style.get("fade") or 0)
                if fade and t_in < fade:  # word swap as a 2-frame cross-dissolve, like the notebook style
                    k = t_in / fade
                    prev = self.groups[gi - 1] if gi else None
                    if prev and g["start"] - prev["end"] < 0.05:
                        pkey = ("fadeout", gi - 1)
                        if pkey not in self.cap_cache:
                            self.cap_cache[pkey] = draw.caption_image(words, prev, prev["w"][-1], style, W, None)
                        put(draw.transform(self.cap_cache[pkey], {"scale": 1, "rot": 0, "alpha": 1 - k, "dx": 0, "dy": 0}),
                            float(style.get("x", 0.5)) * W, cy * H)
                    cap = draw.transform(cap, {"scale": 1, "rot": 0, "alpha": k, "dx": 0, "dy": 0})
                put(cap, float(style.get("x", 0.5)) * W, cy * H)
        return frame

    def speaker(self, ts, t):
        """The talking-head frame at source time ts: old captions painted out, faces covered, camera zoom."""
        W, H = self.W, self.H
        frame = cover_fit(self.src.at(ts), W, H)
        if self.burn_band:  # paint out captions that were already in the video
            analyze.remove_burned_text(frame, self.burn_band, state=self.burn_state)
        frame = draw.apply_filter(frame, self.filter)  # color filter on footage only, not covers or graphics
        for c in self.covers:
            pos = analyze.face_at(self.tracks[c["face"]], ts)
            if pos:
                _cover(frame, pos, c, W, H)
        z = timeline.camera_zoom(self.p, self.words, self.segs, t)
        if z > 1.001:
            cw, ch = W / z, H / z
            ax, ay = timeline.focus(self.p)
            x0 = min(max(0, ax * W - cw * ax), W - cw)
            y0 = min(max(0, ay * H - ch * ay), H - ch)
            frame = cv2.resize(frame[int(y0):int(y0 + ch), int(x0):int(x0 + cw)], (W, H), interpolation=cv2.INTER_LINEAR)
        return frame


_ENC = None


def _prores_alpha():
    """Transparent ProRes 4444 for CapCut. Uses the Mac's hardware encoder when ffmpeg has it."""
    global _ENC
    if _ENC is None:
        encs = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        _ENC = "prores_videotoolbox" if "prores_videotoolbox" in encs else "prores_ks"
    if _ENC == "prores_videotoolbox":
        return ["-c:v", "prores_videotoolbox", "-profile:v", "4444", "-pix_fmt", "bgra"]
    return ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"]


def still(name, t, out):
    c = Composer(name)
    fr = c.frame(min(t, c.T - 0.01))
    cv2.imwrite(str(out), fr)
    return out


def render(name, out=None, variant=None, layer="full", progress=None, p=None):
    """layer: full | base (video, no graphics) | captions | graphics (transparent .mov)"""
    c = Composer(name, variant, layer, p)
    W, H, fps = c.W, c.H, c.fps
    N = int(c.T * fps)
    out = Path(out or project.pdir(name) / "exports" / ("reel.mp4" if not c.transparent else f"{layer}.mov"))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_audio = out.with_name(out.stem + "_audio.m4a")
    if not c.transparent:
        _audio(c.p, c.segs, c.T, tmp_audio)
        enc = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-", "-i", str(tmp_audio), "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast" if config.fast() else "fast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "copy",
               "-shortest", "-movflags", "+faststart", str(out)]
    else:
        enc = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-"] + _prores_alpha() + [str(out)]
    proc = subprocess.Popen(enc, stdin=subprocess.PIPE)
    try:
        for n in range(N):
            proc.stdin.write(c.frame(n / fps).tobytes())
            if progress and n % 15 == 0:
                progress(n / N)
    finally:
        proc.stdin.close()
        proc.wait()
        if tmp_audio.exists():
            tmp_audio.unlink()
    if proc.returncode != 0:
        global _ENC
        if c.transparent and _ENC == "prores_videotoolbox":  # hardware encoder refused: fall back
            _ENC = "prores_ks"
            return render(name, out, variant, layer, progress, p)
        raise RuntimeError("ffmpeg failed while encoding")
    speed = float(c.p.get("speed") or 1.0)
    if abs(speed - 1.0) > 1e-3:  # play the whole reel faster (pitch kept)
        tmp = out.with_name(out.stem + "_speed" + out.suffix)
        cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(out), "-filter:v", f"setpts=PTS/{speed}"]
        if c.transparent:
            cmd += _prores_alpha()
        else:
            cmd += ["-filter:a", f"atempo={speed}", "-c:v", "libx264", "-preset", "veryfast" if config.fast() else "fast", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
        subprocess.run(cmd + [str(tmp)], check=True)
        tmp.replace(out)
    if progress:
        progress(1.0)
    return out
