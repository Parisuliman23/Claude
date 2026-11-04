"""Requests from the studio to Claude ("make me a count-up look", "write my
carousel", …). Each request is stored in the project. If the `claude` command
is installed, the studio starts Claude Code in the background to handle it;
otherwise it waits until you tell Claude "check my studio requests"."""
import shutil
import subprocess
import threading
import time

from . import config, project

PROMPT = """A request just came in from the Reelsmith studio app.
Project: {name}
Request id: {rid}

Follow the "Studio requests" section of CLAUDE.md to handle it: read the request with
`python3 -m engine requests {name}`, do the work, then mark it finished with
`python3 -m engine request-done {name} {rid} --note "<one short sentence for the user>"`
(add --options a,b,c when you made look options). Work only inside this folder."""


def claude_bin():
    return shutil.which("claude")


def submit(name, req):
    req = dict(req)
    req["id"] = project.new_id("r")
    req["created"] = time.time()
    auto = config.settings()["claude_bridge"] == "auto" and claude_bin()
    req["status"] = "running" if auto else "waiting"
    project.update(name, lambda p: p.setdefault("requests", []).append(req))
    if auto:
        threading.Thread(target=_run, args=(name, req["id"]), daemon=True).start()
    return req


def _set(name, rid, **kw):
    def fn(p):
        for r in p.get("requests", []):
            if r["id"] == rid:
                r.update(kw)
    project.update(name, fn)


def _run(name, rid):
    cmd = [claude_bin(), "-p", PROMPT.format(name=name, rid=rid), "--permission-mode", "acceptEdits",
           "--allowedTools", "Bash(python3 -m engine:*)", "Bash(python -m engine:*)", "Read", "Write", "Edit",
           "Glob", "Grep"]
    try:
        res = subprocess.run(cmd, cwd=config.ROOT, capture_output=True, text=True, timeout=1800)
        p = project.load(name)
        r = next((r for r in p.get("requests", []) if r["id"] == rid), {})
        if r.get("status") in ("done", "failed"):
            return
        if res.returncode == 0:
            _set(name, rid, status="done", note=(res.stdout.strip().splitlines() or ["Done."])[-1][:300])
        else:
            _set(name, rid, status="failed", note=(res.stderr or res.stdout)[-300:])
    except Exception as e:  # noqa: BLE001
        _set(name, rid, status="failed", note=str(e)[:300])
