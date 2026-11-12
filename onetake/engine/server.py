"""The studio: a small local web server (only reachable from your own computer)."""
import json
import mimetypes
import os
import re
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analyze, bridge, config, draw, finish, looks, project, render, timeline

JOBS = {}  # (name, kind) -> {status, progress, result, error}
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("audio/mp4", ".m4a")


def run_job(name, kind, fn):
    key = (name, kind)
    if JOBS.get(key, {}).get("status") == "running":
        return JOBS[key]
    job = {"status": "running", "progress": 0.0, "kind": kind}
    JOBS[key] = job

    def prog(x):
        job["progress"] = round(float(x), 3)

    def go():
        try:
            job["result"] = fn(prog)
            job["status"] = "done"
            job["progress"] = 1.0
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            job["status"] = "error"
            job["error"] = str(e)

    threading.Thread(target=go, daemon=True).start()
    return job


def jobs_for(name):
    return {k: v for (n, k), v in JOBS.items() if n == name}


def library():
    out = {}
    for kind, exts in (("gifs", config.IMAGE_EXT), ("images", config.IMAGE_EXT), ("broll", config.VIDEO_EXT),
                       ("sounds", config.AUDIO_EXT)):
        d = config.LIBRARY / kind
        files = sorted([f for f in d.glob("*") if f.suffix.lower() in exts], key=lambda f: f.name.lower()) if d.exists() else []
        out[kind] = [{"path": config.rel(f), "name": f.stem} for f in files]
    from . import sfx, reference
    out["sfx"] = sfx.library()
    out["references"] = reference.listing()
    fav = config.LOOKBOOK / "favorites.json"
    out["favorites"] = json.loads(fav.read_text()) if fav.exists() else []
    return out


def lookbook():
    return {"captions": project.caption_styles(), "looks": looks.all_looks(), "saved": project.saved_looks(),
            "emoji": draw.emoji_codes(),
            "filters": json.loads((config.LOOKBOOK / "filters.json").read_text()) if (config.LOOKBOOK / "filters.json").exists() else []}


def thumb(name, t, w=360, src=False):
    """A still at output time t (or, with src=True, at source time t: the timeline's film strip)."""
    t = round(max(0.0, t), 1)
    out = project.pdir(name) / "cache" / "thumbs" / (f"s{t:.1f}_{w}.jpg" if src else f"{t:.1f}.jpg")
    if not out.exists():
        import cv2
        out.parent.mkdir(parents=True, exist_ok=True)
        p = project.load(name)
        segs = project.segments(p)
        from . import timeline
        ts = t if src else timeline.out_to_src(segs, t)[1]
        reader = render.FrameReader(config.absolute(p["source"]))
        fr = None
        for back in (0, 0.5, 2, 5):  # the last frames of some phone videos can't be read: step back a little
            fr = reader.at(max(0.0, ts - back))
            if fr is not None:
                break
        if fr is None:  # video missing or unreadable: no thumbnail, but don't crash the studio
            return None
        fr = render.cover_fit(fr, w, int(w * 16 / 9))
        cv2.imwrite(str(out), fr, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return out


def capcut_project(name, prog):
    from . import capcut_draft
    r = capcut_draft.build(name, progress=prog)
    project.update(name, lambda q: q.setdefault("exports", {}).update({"capcut_project": r}))
    return r


LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>One Take Studio</title><style>body{font-family:system-ui,sans-serif;background:#F3F2F7;color:#17171C;display:grid;place-items:center;min-height:100vh;margin:0}
form{background:#fff;padding:28px;border-radius:18px;box-shadow:0 8px 30px rgba(20,16,60,.1);width:min(340px,90vw);text-align:center}
input{font-size:28px;letter-spacing:.3em;text-align:center;width:100%;padding:10px;border:1px solid #ddd;border-radius:12px;box-sizing:border-box}
button{margin-top:14px;width:100%;padding:12px;font-size:17px;border:0;border-radius:12px;background:#5B4BDB;color:#fff}
.m{color:#C2410C;min-height:20px}</style></head><body><form method="post" action="/login">
<h2>✂ One Take Studio</h2><p>Enter the PIN shown on your Chromebook's studio.</p>
<input name="pin" inputmode="numeric" autocomplete="one-time-code" autofocus><input type="hidden" name="next" value="{{next}}">
<p class="m">{{msg}}</p><button>Open</button></form></body></html>"""


# Through the phone link (a Cloudflare tunnel) only the phone page and what it needs are reachable.
TUNNEL_PATHS = re.compile(r"/phone/?|/login|/api/projects|/api/project/[a-z0-9-]+(/free-space)?|/api/newreel|/api/new-reel-file"
                          r"|/api/new-reel-start|/media/projects/.+")
_wrong_pins = []  # times of wrong PIN tries: after 5 in 15 minutes, PIN entry pauses for 15 minutes


def pin_locked():
    now = time.time()
    _wrong_pins[:] = [t for t in _wrong_pins if now - t < 900]
    return len(_wrong_pins) >= 5


def pin_token(st):
    import hashlib
    return hashlib.sha256(f"onetake:{st.get('phone_pin')}".encode()).hexdigest()[:32]


def render_full(name):
    def fn(prog):
        p = project.load(name)
        edit_rev = p.get("edit_rev", 0)
        out = render.render(name, project.pdir(name) / "exports" / "reel.mp4", progress=lambda x: prog(x * 0.96), p=p)
        phone = finish.phone_copy(out, out.with_name("reel_phone.mp4"))
        cov = finish.cover(name)

        def mark(q):
            q["render"] = {"status": "done", "file": config.rel(out), "edit_rev": edit_rev, "phone": config.rel(phone)}
            if cov:
                q.setdefault("exports", {})["cover"] = cov
        project.update(name, mark)
        return config.rel(out)
    return fn


class Handler(BaseHTTPRequestHandler):
    server_version = "OneTakeStudio"

    def log_message(self, fmt, *args):
        pass

    # ---- helpers
    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def jbody(self):
        b = self.body()
        return json.loads(b) if b else {}

    def send_file(self, path, cache=False):
        path = Path(path)
        if not path.is_file():
            return self.send_error(404)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "public, max-age=604800" if cache else "no-cache")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    # ---- routing
    def do_GET(self):
        try:
            self.route("GET")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.send_json({"error": str(e)}, 500)

    def do_POST(self):
        try:
            self.route("POST")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.send_json({"error": str(e)}, 500)

    do_PUT = do_POST

    remote = False  # RemoteHandler: the port the permanent phone link forwards to

    def via_tunnel(self):
        """True for requests that came in through the phone link (Cloudflare adds these headers; everything on the
        permanent link's port counts)."""
        return self.remote or bool(self.headers.get("Cf-Connecting-Ip") or self.headers.get("Cf-Ray"))

    def authorized(self):
        """With phone access on, every request needs the PIN cookie (set once per device)."""
        st = config.settings()
        if not st.get("phone_access"):
            return not self.via_tunnel()
        if st.get("phone_pin_off") and not (self.via_tunnel() and st.get("phone_link") == "permanent"):
            return True  # you chose no PIN on the changing link (a permanent link always asks, once per phone)
        c = self.headers.get("Cookie") or ""
        return f"onetake_pin={pin_token(st)}" in c.replace(" ", "").split(";")

    def login_page(self, nxt, wrong=False):
        html = LOGIN_HTML.replace("{{next}}", urllib.parse.quote(nxt, safe="/#")).replace(
            "{{msg}}", "Too many wrong tries. Wait 15 minutes, then try again." if wrong == "locked"
            else "That PIN didn't match. Try again." if wrong else "")
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self, method):
        u = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(u.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if self.via_tunnel():
            if not config.settings().get("phone_access"):
                return self.send_error(403)
            full = config.settings().get("phone_studio", True)  # the whole studio on your phone, not only uploads
            if path in ("/", "/index.html") and not full:
                self.send_response(303)
                self.send_header("Location", "/phone")
                self.end_headers()
                return
            if not full and not TUNNEL_PATHS.fullmatch(path) or not full and (
                    method != "GET" and path not in ("/login", "/api/new-reel-file", "/api/new-reel-start")
                    and not path.endswith("/free-space")):
                return self.send_error(404)
        if path == "/login" and method == "POST":
            form = dict(urllib.parse.parse_qsl(self.body().decode()))
            st = config.settings()
            if pin_locked():
                return self.login_page(form.get("next") or "/", wrong="locked")
            if st.get("phone_pin") and str(form.get("pin", "")).strip() == str(st.get("phone_pin")):
                self.send_response(303)
                self.send_header("Set-Cookie", f"onetake_pin={pin_token(st)}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly")
                nxt = form.get("next") or "/"
                self.send_header("Location", nxt if nxt.startswith("/") and not nxt.startswith("//") else "/")
                self.end_headers()
                return
            _wrong_pins.append(time.time())
            return self.login_page(form.get("next") or "/", wrong=True)
        if not self.authorized():
            if path.startswith("/api/") or path.startswith("/media/"):
                return self.send_json({"error": "Enter your One Take PIN first."}, 401)
            if not path.startswith("/assets/fonts/"):
                return self.login_page(self.path)
        if method == "GET":
            if path in ("/phone", "/phone/"):
                return self.send_file(config.APP / "phone.html")
            if path in ("/", "/index.html"):
                return self.send_file(config.APP / "index.html")
            if path.startswith("/app/"):
                return self.send_file(config.APP / Path(path[5:]).name)
            if path.startswith("/assets/") or path.startswith("/media/"):
                rel = path.split("/", 2)[2] if path.startswith("/media/") else path[1:]
                f = config.absolute(rel)
                top = f.relative_to(config.ROOT).parts[0]
                if top not in ("projects", "library", "lookbook", "assets"):
                    return self.send_error(403)
                return self.send_file(f)
            if path == "/api/projects":
                from . import space
                out = project.list_projects()
                for p in out:  # how much each reel takes on this computer, and whether it was already cleared
                    try:
                        q = project.load(p["name"])
                        p["archived"] = bool(q.get("archived"))
                        p["mb"] = 0 if q.get("variant_of") else round(space.freeable(p["name"]) / 1e6)
                    except Exception:  # noqa: BLE001
                        p["archived"], p["mb"] = False, 0
                return self.send_json(out)
            if path == "/api/phone-qr.png":  # QR code of the phone link, to scan with the phone's camera
                from . import tunnel
                url = tunnel.status().get("url")
                png = tunnel.qr_png(url + "/phone") if url else None
                if not png:
                    return self.send_error(404)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(png)))
                self.end_headers()
                self.wfile.write(png)
                return
            if path == "/api/lookbook":
                return self.send_json(lookbook())
            if path == "/api/library":
                return self.send_json(library())
            if path == "/api/inbox":
                from . import inbox
                return self.send_json(inbox.status())
            if path == "/api/broll-job":  # progress of a B-roll download
                return self.send_json(JOBS.get(("_library", "broll"), {}))
            if path == "/api/newreel":  # progress of an edit started from the "New reel" app icon
                st_f, log_f = config.PROJECTS / ".newreel.json", config.PROJECTS / ".newreel.log"
                from . import progress
                info = progress.check() if st_f.exists() else {}
                info = info or {"status": "none"}
                info["log"] = log_f.read_text()[-3000:] if log_f.exists() and info.get("status") in ("done", "failed") else ""
                info["now"] = time.time()
                info["waiting"] = (len([f for f in config.DROP.glob("*") if f.suffix.lower() in config.VIDEO_EXT])
                                   if config.DROP.exists() else 0) or (1 if progress.orphan() else 0)
                if info.get("status") == "running":
                    from . import progress
                    info["pct"], info["label"], info["left"] = progress.estimate(info, info["now"])
                return self.send_json(info)
            if path == "/api/status":
                st = config.settings()
                from . import space, tunnel
                return self.send_json({"phone_access": bool(st.get("phone_access")), "phone_pin": st.get("phone_pin"),
                                       "phone_pin_off": bool(st.get("phone_pin_off")) and st.get("phone_link") != "permanent",
                                       "phone_link": tunnel.status(),
                                       "disk_free_mb": round(space.disk_free() / 1e6),
                                       "claude": bool(bridge.claude_bin()) and st["claude_bridge"] == "auto",
                                       "stock": bool(os.environ.get("PIXABAY_API_KEY") or st.get("pixabay_key")),
                                       "settings": {k: st[k] for k in ("max_gap", "pad_before", "pad_after", "width", "height", "fps")}})
            m = re.fullmatch(r"/api/project/([a-z0-9-]+)/thumb", path)
            if m:  # a still of your own video at output time t, for previews drawn "on your frame"
                f = thumb(m.group(1), float(q.get("t", 1)), int(q.get("w", 360)), bool(q.get("src")))
                return self.send_file(f, cache=bool(q.get("src"))) if f else self.send_error(404)
            m = re.fullmatch(r"/api/project/([a-z0-9-]+)(/rev)?", path)
            if m:
                p = project.load(m.group(1))
                if "focus" not in p and not m.group(2) and not p.get("archived"):  # projects from before face focus existed
                    foc = analyze.face_focus(config.absolute(p["source"]))
                    p = project.update(m.group(1), lambda q: q.update({"focus": foc}))
                if m.group(2):
                    return self.send_json({"rev": p.get("rev", 0), "jobs": jobs_for(m.group(1)),
                                           "requests": p.get("requests", [])})
                prox = project.pdir(m.group(1)) / "cache" / "proxy.mp4"
                if prox.exists() and prox.stat().st_mtime >= config.absolute(p["source"]).stat().st_mtime:
                    p = dict(p, _proxy=config.rel(prox))  # the light preview copy made at import
                return self.send_json(p)
            return self.send_error(404)

        if path == "/api/favorite":  # star/unstar a library item (favorites show first)
            b = self.jbody()
            fav = config.LOOKBOOK / "favorites.json"
            favs = json.loads(fav.read_text()) if fav.exists() else []
            favs = [x for x in favs if x != b["path"]] + ([b["path"]] if b.get("on") else [])
            fav.write_text(json.dumps(favs, indent=1))
            return self.send_json({"favorites": favs})
        if path == "/api/stock-key":
            from . import stock
            stock.save_key(self.jbody().get("key", ""))
            return self.send_json({"ok": True})
        if path == "/api/broll-find":
            from . import stock
            b = self.jbody()
            if not stock.has_key():
                return self.send_json({"need_key": True})
            q, n = b.get("query", "").strip(), int(b.get("n", 5))
            fn = (lambda prog: stock.starter_pack(progress=prog)) if b.get("starter") else (lambda prog: stock.search(q, n))
            return self.send_json(run_job("_library", "broll", fn))
        if path == "/api/new-reel-file":  # a video dragged/pasted onto the studio: stream it to drop-in-order/
            from . import progress
            if progress.busy():
                return self.send_json({"error": "Claude is still editing your last reel. Try again when it's done."}, 409)
            ext = Path(q.get("name", "clip.mp4")).suffix.lower()
            if ext not in config.VIDEO_EXT:
                return self.send_json({"error": "That isn't a video file (.mp4, .mov…)."}, 400)
            stem = re.sub(r"[^\w\- ]", "_", Path(q.get("name", "clip")).stem)[:60]
            dest = config.DROP / f"{int(q.get('index', 0)):02d}_{stem}{ext}"
            config.DROP.mkdir(exist_ok=True)
            part = dest.with_suffix(dest.suffix + ".part")
            left = int(self.headers.get("Content-Length") or 0)
            offset = int(q.get("offset", 0))  # big videos come in pieces: offset = bytes already sent
            total = int(q.get("total", 0)) or offset + left
            have = part.stat().st_size if part.exists() else 0
            if offset and offset != have:  # a piece went missing: tell the phone where to carry on
                return self.send_json({"error": "Out of step", "have": have}, 409)
            with open(part, "ab" if offset else "wb") as fh:  # stream: never holds the video in memory
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            if left:  # this piece broke off: drop just this piece so the phone can resend it
                if offset:
                    os.truncate(part, offset)
                else:
                    part.unlink(missing_ok=True)
                return self.send_json({"error": "The upload was interrupted.", "have": offset}, 400)
            if part.stat().st_size < total:
                return self.send_json({"have": part.stat().st_size})
            part.replace(dest)
            return self.send_json({"saved": dest.name})
        if path == "/api/phone-pin":  # ask for a PIN on the phone link, or not
            f = config.ROOT / "settings.json"
            st = json.loads(f.read_text()) if f.exists() else {}
            st["phone_pin_off"] = not bool(self.jbody().get("on"))
            f.write_text(json.dumps(st, indent=1))
            return self.send_json({"pin_on": not st["phone_pin_off"]})
        if path == "/api/phone-access":  # turn sending from your phone on/off (creates the PIN)
            import secrets
            b = self.jbody()
            f = config.ROOT / "settings.json"
            st = json.loads(f.read_text()) if f.exists() else {}
            st["phone_access"] = bool(b.get("on"))
            if st["phone_access"] and not st.get("phone_pin"):
                st["phone_pin"] = f"{secrets.randbelow(900000) + 100000}"
            f.write_text(json.dumps(st, indent=1))
            from . import tunnel
            tunnel.start() if st["phone_access"] else tunnel.stop(close_permanent=True)
            resp = {"on": st["phone_access"], "pin": st.get("phone_pin")}
            body = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if st["phone_access"]:  # keep this device signed in
                self.send_header("Set-Cookie", f"onetake_pin={pin_token(st)}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/new-reel-start":  # start editing what's in drop-in-order/, in the background
            import subprocess as sp
            from . import progress
            if not [f for f in config.DROP.glob("*") if f.suffix.lower() in config.VIDEO_EXT]:
                progress.recover_orphan()  # "Try again" after an import that stopped halfway
            if not [f for f in config.DROP.iterdir() if f.suffix.lower() in config.VIDEO_EXT]:
                return self.send_json({"error": "No video arrived."}, 400)
            st = config.PROJECTS / ".newreel.json"
            auto = bool(self.jbody().get("auto_render"))
            st.write_text(json.dumps({"status": "running", "started": time.time(), "step": "start",
                                      "step_at": time.time(), "auto_render": auto}))
            env = dict(os.environ, ONETAKE_NO_BROWSER="1")
            if auto:  # from the phone: render it so it can be downloaded right away
                env["ONETAKE_AUTO_RENDER"] = "1"
            sp.Popen(["bash", str(config.ROOT / "new-reel.sh")], cwd=config.ROOT, env=env,
                     stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
            return self.send_json({"started": True})
        if path == "/api/upload":
            kind = q.get("kind", "images")
            if kind not in ("gifs", "images", "broll", "sounds", "sfx", "references"):
                return self.send_error(400)
            fname = re.sub(r"[^\w.\- ]", "_", Path(q.get("name", "upload")).name)
            dest = config.LIBRARY / kind / fname
            dest.parent.mkdir(parents=True, exist_ok=True)
            left = int(self.headers.get("Content-Length") or 0)
            with open(dest, "wb") as fh:  # stream: reference reels can be big
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            return self.send_json({"path": config.rel(dest)})
        m = re.fullmatch(r"/api/project/([a-z0-9-]+)(?:/([a-z-]+))?", path)
        if not m:
            return self.send_error(404)
        name, action = m.group(1), m.group(2)
        if action is None:  # save
            b = self.jbody()
            try:
                rev = project.save(name, b["project"], expect_rev=b.get("rev"))
                return self.send_json({"rev": rev})
            except project.ConflictError as e:
                return self.send_json({"conflict": True, "rev": e.rev}, 409)
        b = self.jbody()
        if action == "delete":  # delete a whole reel (its folder in projects/)
            import shutil
            d = project.pdir(name)
            if d.resolve().parent != config.PROJECTS.resolve() or not (d / "project.json").exists():
                return self.send_error(400)
            shutil.rmtree(d)
            return self.send_json({"deleted": name})
        if action == "free-space":  # the reel is saved on the phone: delete its big files here
            from . import space
            if any(j.get("status") == "running" for j in jobs_for(name).values()):
                return self.send_json({"error": "This reel is still rendering. Try again when it's finished."}, 400)
            freed = space.free(name)
            return self.send_json({"freed_mb": round(freed / 1e6), "disk_free_mb": round(space.disk_free() / 1e6)})
        if action == "sfx-auto":
            from . import sfx
            p = project.update(name, lambda q: (sfx.auto(q, replace=bool(b.get("replace", True))),
                                               q.update({"edit_rev": q.get("edit_rev", 0) + 1})))
            return self.send_json({"sfx": p.get("sfx", [])})
        if action == "sprite":
            params = b.get("params", {})
            if b.get("w0") is not None:  # time word cues to this reel's words
                p = project.load(name)
                words, segs = p["words"], project.segments(p)
                wo = timeline.word_out(words, segs, int(b["w0"]))
                if wo:
                    params = timeline.resolve_cues(params, words, segs, wo[0])
            meta = looks.sprite(b["look"], params, float(b.get("dur", 3)),
                                project.pdir(name) / "cache")
            return self.send_json(meta)
        if action == "faces":
            def fn(prog):
                p = project.load(name)
                res = analyze.detect_faces(config.absolute(p["source"]), project.pdir(name) / "cache" / "faces", progress=prog)
                project.update(name, lambda q: q.setdefault("faces", {}).update({"detected": res}))
                return len(res)
            return self.send_json(run_job(name, "faces", fn))
        if action == "broll-moment":
            return self.send_json({"clip_start": analyze.best_moment(config.absolute(b["src"]), float(b["dur"]))})
        if action == "render":
            return self.send_json(run_job(name, "render", render_full(name)))
        if action == "frame":
            return self.send_json({"file": finish.save_frame(name, float(b["t"]))})
        if action == "export":
            kind = b["kind"]
            fns = {"carousel": lambda prog: finish.carousel(name), "story": lambda prog: finish.story(name),
                   "trials": lambda prog: finish.trials(name, progress=prog),
                   "capcut": lambda prog: finish.capcut(name, progress=prog),
                   "storyboard": lambda prog: finish.storyboard(name, progress=prog),
                   "capcut_project": lambda prog: capcut_project(name, prog)}
            return self.send_json(run_job(name, kind, fns[kind]))
        if action == "edge-check":
            return self.send_json({"flags": finish.edge_check(project.load(name))})
        if action == "edge-fix":
            moved = {}

            def fx(q):
                moved["n"] = finish.fix_edges(q)
                q["edit_rev"] = q.get("edit_rev", 0) + 1
            project.update(name, fx)
            return self.send_json({"moved": moved["n"], "flags": finish.edge_check(project.load(name))})
        if action == "request":
            return self.send_json(bridge.submit(name, b))
        if action == "save-look":
            project.save_look(b)
            return self.send_json({"ok": True})
        return self.send_error(404)


class RemoteHandler(Handler):
    remote = True


def _serve_remote(port):
    """The local-only port the permanent phone link (Tailscale Funnel) forwards to."""
    from . import tunnel
    try:
        h = ThreadingHTTPServer(("127.0.0.1", tunnel.remote_port(port)), RemoteHandler)
    except OSError:
        return
    threading.Thread(target=h.serve_forever, daemon=True).start()


def open_url(url):
    """Open a link in the normal browser (works on Chromebook Linux too)."""
    import subprocess
    try:
        subprocess.Popen(["bash", str(config.ROOT / "open-url.sh"), url])
    except Exception:
        webbrowser.open(url)


def serve(name=None, open_browser=True, port=None):
    port = port or config.settings()["port"]
    bind, _ = config.studio_host()
    url = config.studio_url(port) + (f"#{name}" if name else "")
    try:
        httpd = ThreadingHTTPServer((bind, port), Handler)
    except OSError:  # already running (e.g. Claude started it earlier) — just show it
        print(f"Studio is already running at {url}")
        if open_browser:
            open_url(url)
        return
    print(f"Studio running at {url}  (Ctrl+C to stop)")
    _serve_remote(port)
    from . import inbox
    inbox.watch()  # phone uploads: Google Drive "One Take/Inbox" -> edited reel in "One Take/Ready"
    if inbox.status()["connected"]:
        print(f"Watching your phone uploads in {inbox.status()['inbox']}")
    if config.is_chromebook():
        print(f"(If that page won't load, also try http://localhost:{port}/)")
    if config.settings().get("phone_access"):  # "Send from your phone" is on: make the phone link
        from . import tunnel
        tunnel.start(port)
    if open_browser:
        threading.Timer(0.6, lambda: open_url(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
