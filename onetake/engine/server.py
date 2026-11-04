"""The studio: a small local web server (only reachable from your own computer)."""
import json
import mimetypes
import re
import threading
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
    return out


def lookbook():
    return {"captions": project.caption_styles(), "looks": looks.all_looks(), "saved": project.saved_looks(),
            "emoji": draw.emoji_codes()}


def render_full(name):
    def fn(prog):
        p = project.load(name)
        edit_rev = p.get("edit_rev", 0)
        out = render.render(name, project.pdir(name) / "exports" / "reel.mp4", progress=prog, p=p)

        def mark(q):
            q["render"] = {"status": "done", "file": config.rel(out), "edit_rev": edit_rev}
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
            if path == "/api/status":
                st = config.settings()
                return self.send_json({"claude": bool(bridge.claude_bin()) and st["claude_bridge"] == "auto",
                                       "settings": {k: st[k] for k in ("max_gap", "pad_before", "pad_after", "width", "height", "fps")}})
            m = re.fullmatch(r"/api/project/([a-z0-9-]+)(/rev)?", path)
            if m:
                p = project.load(m.group(1))
                if m.group(2):
                    return self.send_json({"rev": p.get("rev", 0), "jobs": jobs_for(m.group(1)),
                                           "requests": p.get("requests", [])})
                return self.send_json(p)
            return self.send_error(404)

        if path == "/api/upload":
            kind = q.get("kind", "images")
            if kind not in ("gifs", "images", "broll", "sounds"):
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
                   "capcut": lambda prog: finish.capcut(name, progress=prog)}
            return self.send_json(run_job(name, kind, fns[kind]))
        if action == "request":
            return self.send_json(bridge.submit(name, b))
        if action == "save-look":
            project.save_look(b)
            return self.send_json({"ok": True})
        return self.send_error(404)


def serve(name=None, open_browser=True, port=None):
    port = port or config.settings()["port"]
    url = f"http://localhost:{port}/" + (f"#{name}" if name else "")
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:  # already running (e.g. Claude started it earlier) — just show it
        print(f"Studio is already running at {url}")
        if open_browser:
            webbrowser.open(url)
        return
    print(f"Studio running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
