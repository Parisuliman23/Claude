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

from . import analyze, bridge, config, draw, finish, looks, project, render

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
    from . import sfx
    out["sfx"] = sfx.library()
    fav = config.LOOKBOOK / "favorites.json"
    out["favorites"] = json.loads(fav.read_text()) if fav.exists() else []
    return out


def lookbook():
    return {"captions": project.caption_styles(), "looks": looks.all_looks(), "saved": project.saved_looks(),
            "emoji": draw.emoji_codes(),
            "filters": json.loads((config.LOOKBOOK / "filters.json").read_text()) if (config.LOOKBOOK / "filters.json").exists() else []}


def thumb(name, t, w=360):
    t = round(max(0.0, t), 1)
    out = project.pdir(name) / "cache" / "thumbs" / f"{t:.1f}.jpg"
    if not out.exists():
        import cv2
        out.parent.mkdir(parents=True, exist_ok=True)
        p = project.load(name)
        segs = project.segments(p)
        from . import timeline
        _, ts = timeline.out_to_src(segs, t)
        fr = render.FrameReader(config.absolute(p["source"])).at(ts)
        fr = render.cover_fit(fr, w, int(w * 16 / 9))
        cv2.imwrite(str(out), fr, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return out


def capcut_project(name, prog):
    from . import capcut_draft
    r = capcut_draft.build(name, progress=prog)
    project.update(name, lambda q: q.setdefault("exports", {}).update({"capcut_project": r}))
    return r


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

    def send_file(self, path):
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
        self.send_header("Cache-Control", "no-cache")
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

    def route(self, method):
        u = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(u.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if method == "GET":
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
                return self.send_json(project.list_projects())
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
                info = json.loads(st_f.read_text()) if st_f.exists() else {"status": "none"}
                info["log"] = log_f.read_text()[-3000:] if log_f.exists() and info.get("status") in ("done", "failed") else ""
                info["now"] = time.time()
                return self.send_json(info)
            if path == "/api/status":
                st = config.settings()
                return self.send_json({"claude": bool(bridge.claude_bin()) and st["claude_bridge"] == "auto",
                                       "stock": bool(os.environ.get("PIXABAY_API_KEY") or st.get("pixabay_key")),
                                       "settings": {k: st[k] for k in ("max_gap", "pad_before", "pad_after", "width", "height", "fps")}})
            m = re.fullmatch(r"/api/project/([a-z0-9-]+)/thumb", path)
            if m:  # a still of your own video at output time t, for previews drawn "on your frame"
                return self.send_file(thumb(m.group(1), float(q.get("t", 1))))
            m = re.fullmatch(r"/api/project/([a-z0-9-]+)(/rev)?", path)
            if m:
                p = project.load(m.group(1))
                if "focus" not in p and not m.group(2):  # projects from before face focus existed
                    foc = analyze.face_focus(config.absolute(p["source"]))
                    p = project.update(m.group(1), lambda q: q.update({"focus": foc}))
                if m.group(2):
                    return self.send_json({"rev": p.get("rev", 0), "jobs": jobs_for(m.group(1)),
                                           "requests": p.get("requests", [])})
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
            st = config.PROJECTS / ".newreel.json"
            if st.exists() and '"running"' in st.read_text():
                return self.send_json({"error": "Claude is still editing your last reel. Try again when it's done."}, 409)
            ext = Path(q.get("name", "clip.mp4")).suffix.lower()
            if ext not in config.VIDEO_EXT:
                return self.send_json({"error": "That isn't a video file (.mp4, .mov…)."}, 400)
            stem = re.sub(r"[^\w\- ]", "_", Path(q.get("name", "clip")).stem)[:60]
            dest = config.DROP / f"{int(q.get('index', 0)):02d}_{stem}{ext}"
            config.DROP.mkdir(exist_ok=True)
            left = int(self.headers.get("Content-Length") or 0)
            with open(dest.with_suffix(dest.suffix + ".part"), "wb") as fh:  # stream: never holds the video in memory
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            if left:
                dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
                return self.send_json({"error": "The upload was interrupted."}, 400)
            dest.with_suffix(dest.suffix + ".part").replace(dest)
            return self.send_json({"saved": dest.name})
        if path == "/api/new-reel-start":  # start editing what's in drop-in-order/, in the background
            import subprocess as sp
            if not [f for f in config.DROP.iterdir() if f.suffix.lower() in config.VIDEO_EXT]:
                return self.send_json({"error": "No video arrived."}, 400)
            st = config.PROJECTS / ".newreel.json"
            st.write_text(json.dumps({"status": "running", "started": time.time()}))
            env = dict(os.environ, ONETAKE_NO_BROWSER="1")
            sp.Popen(["bash", str(config.ROOT / "new-reel.sh")], cwd=config.ROOT, env=env,
                     stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
            return self.send_json({"started": True})
        if path == "/api/upload":
            kind = q.get("kind", "images")
            if kind not in ("gifs", "images", "broll", "sounds", "sfx"):
                return self.send_error(400)
            fname = re.sub(r"[^\w.\- ]", "_", Path(q.get("name", "upload")).name)
            dest = config.LIBRARY / kind / fname
            dest.write_bytes(self.body())
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
        if action == "sfx-auto":
            from . import sfx
            p = project.update(name, lambda q: (sfx.auto(q, replace=bool(b.get("replace", True))),
                                               q.update({"edit_rev": q.get("edit_rev", 0) + 1})))
            return self.send_json({"sfx": p.get("sfx", [])})
        if action == "sprite":
            meta = looks.sprite(b["look"], b.get("params", {}), float(b.get("dur", 3)),
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
    from . import inbox
    inbox.watch()  # phone uploads: Google Drive "One Take/Inbox" -> edited reel in "One Take/Ready"
    if inbox.status()["connected"]:
        print(f"Watching your phone uploads in {inbox.status()['inbox']}")
    if config.is_chromebook():
        print(f"(If that page won't load, also try http://localhost:{port}/)")
    if open_browser:
        threading.Timer(0.6, lambda: open_url(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
