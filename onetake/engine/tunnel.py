"""A private web link to your studio, so your phone can send videos from anywhere (Wi-Fi or mobile data).

Uses a free Cloudflare quick tunnel (no account): `cloudflared` makes an https://….trycloudflare.com link
that reaches this computer without port forwarding or router settings. It only runs while
"Send from your phone" is on, every request through it needs your PIN, and only the phone page's
routes are reachable through it (see server.TUNNEL_PATHS).

The link changes each time the studio restarts. The studio shows the new one (with a QR code), and
writes it to Google Drive "One Take/Open One Take.html" when Drive is shared with Linux.
"""
import atexit
import json
import os
import platform
import re
import signal
import subprocess
import threading
import time
import urllib.request

from . import config

BIN = config.ROOT / "bin" / "cloudflared"
PIDFILE = config.PROJECTS / ".tunnel.pid"
STATE = {"state": "off", "url": None, "error": None}
_proc = None
_gen = 0  # bumped by stop(): an old reconnect loop sees it and quits
_lock = threading.Lock()
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _arch():
    m = platform.machine().lower()
    return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(m, "arm" if m.startswith("arm") else "amd64")


def ensure_binary():
    """Download cloudflared (about 40 MB, once) into bin/."""
    import shutil
    found = shutil.which("cloudflared")
    if found:
        return found
    if BIN.exists():
        return str(BIN)
    BIN.parent.mkdir(exist_ok=True)
    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{_arch()}"
    tmp = BIN.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": "OneTakeStudio/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    tmp.chmod(0o755)
    tmp.rename(BIN)
    return str(BIN)


def _publish(url):
    """Leave the newest link where the phone can find it: Google Drive (if shared with Linux)."""
    try:
        from . import inbox
        inb, _, _ = inbox.folders()  # works with the default Drive folder and a custom "inbox" setting
        if not inb or not inb.parent.is_dir():
            return
        d = inb.parent
        (d / "Open One Take.html").write_text(
            f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={url}/phone">'
            f'<a href="{url}/phone" style="font:32px sans-serif">Open One Take</a>')
        (d / "One Take link.txt").write_text(f"{url}/phone\n")  # plain text: copy it into the browser if needed
    except OSError:
        pass


def _kill_leftover():
    """A link left running by a studio that was killed: close it, so only one link exists."""
    try:
        pid = int(PIDFILE.read_text())
        if "cloudflared" in open(f"/proc/{pid}/cmdline").read():
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    PIDFILE.unlink(missing_ok=True)


def _run(port, gen):
    global _proc
    try:
        exe = ensure_binary()
        _kill_leftover()
        while gen == _gen and config.settings().get("phone_access"):
            with _lock:
                if gen != _gen:
                    break
                _proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                PIDFILE.write_text(str(_proc.pid))
            for line in _proc.stderr:
                m = URL_RE.search(line)
                if m and STATE["url"] != m.group(0):
                    STATE.update(state="on", url=m.group(0), error=None)
                    print(f"Phone link: {m.group(0)}/phone")
                    _publish(m.group(0))
            _proc.wait()
            if gen != _gen or not config.settings().get("phone_access"):
                break
            STATE.update(state="starting", url=None, error="The phone link dropped. Reconnecting…")
            time.sleep(5)
    except Exception as e:  # no internet, download blocked…: the Wi-Fi address still works
        if gen == _gen:
            STATE.update(state="error", url=None, error=f"Couldn't make the phone link: {e}")
        return
    if gen == _gen:
        STATE.update(state="off", url=None)


def start(port=None):
    if STATE["state"] in ("starting", "on"):
        return
    port = port or config.settings()["port"]
    STATE.update(state="starting", url=None, error=None)
    threading.Thread(target=_run, args=(port, _gen), daemon=True).start()


def stop():
    global _gen
    with _lock:
        _gen += 1
        if _proc and _proc.poll() is None:
            _proc.terminate()
    STATE.update(state="off", url=None, error=None)


atexit.register(stop)


def status():
    return dict(STATE)


def qr_png(text):
    """PNG bytes of a QR code for `text`, or None if the qrcode package isn't installed."""
    try:
        import io
        import qrcode
    except ImportError:
        return None
    img = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    print(json.dumps(status()))
