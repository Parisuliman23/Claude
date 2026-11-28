"""Edit the clips in drop-in-order/ in the background (what the studio's "New reel" button and phone uploads run).

Same steps as new-reel.sh, in Python so it also runs on Windows (no bash there):
1. import here (join, transcribe, rough cut), so it never depends on Claude waiting for it;
2. Claude reviews the cut and styles it (instructions: lookbook/new-reel-prompt.md, else the default below);
3. without Claude (not installed, usage limit, stuck): finish the automatic styling (sounds, safe area);
4. phone uploads (ONETAKE_AUTO_RENDER): render and deliver to the Ready folder.
Run: python -m engine new-reel-bg   (the studio starts it for you)
"""
import json
import os
import shutil
import subprocess
import sys
import time

from . import config

DEFAULT_PROMPT = """I have a new reel to edit. It's already imported as project {name} (joined, transcribed and rough-cut),
so don't run 'new': start at step 3 of CLAUDE.md (review the cut), then run 'learned' (what the user changed in past
edits: follow those patterns) and 'style-pick {name}', and do the styling pass (step 4) in the user's style from
lookbook/STYLE.md, timing every effect to the words. B-roll must literally show what's being said: check every clip
with broll-check before using it.
You're running in the background from One Take: the studio is already running, so don't open it, and there's
nobody to answer questions, so make sensible choices yourself. Run every command in the foreground and wait for it
to finish; never start anything in the background. Finish with a short summary for the user (what you cut and styled)."""

FAST = """

Fast mode: the user wants this quick. Make every edit you need, but work efficiently: read lookbook/STYLE.md and
'show' once, combine changes, check at most one still, and only download B-roll if a moment clearly needs it.
Still fix every misheard word (names, brands, numbers): captions must be right."""


def _status(d):
    (config.PROJECTS / ".newreel.json").write_text(json.dumps(d))


def _py(*args, log=None):
    return subprocess.run([sys.executable, "-m", "engine", *args], cwd=config.ROOT,
                          stdout=log or subprocess.DEVNULL, stderr=subprocess.STDOUT if log else subprocess.DEVNULL)


def prompt(name):
    f = config.LOOKBOOK / "new-reel-prompt.md"
    text = f.read_text() if f.exists() else DEFAULT_PROMPT
    text = text.replace("{name}", name)
    return text + (FAST if config.fast() else "")


def run():
    config.PROJECTS.mkdir(exist_ok=True)
    log_path = config.PROJECTS / ".newreel.log"
    drop = [c for c in config.DROP.iterdir() if c.name != ".keep" and not c.name.endswith(".part")] if config.DROP.exists() else []
    if not drop:
        _status({"status": "noclips", "started": int(time.time())})
        return
    auto = bool(os.environ.get("ONETAKE_AUTO_RENDER"))
    _status({"status": "running", "started": int(time.time()), "step": "start", "step_at": int(time.time()),
             "auto_render": auto, "pid": os.getpid()})
    with open(log_path, "w") as log:
        if _py("new", log=log).returncode:
            _status({"status": "failed", "ended": int(time.time())})
            return
    from . import project, variants
    name = project.list_projects()[0]["name"]
    result = "done"
    claude = shutil.which("claude")
    with open(log_path, "a") as log:
        log.write("\n\n")  # Claude's summary starts a new paragraph (the studio shows the last one)
        log.flush()
        ok = False
        if claude:
            cmd = [claude, "-p", prompt(name), "--permission-mode", "acceptEdits",
                   "--allowedTools", "Bash(python3 -m engine:*)", "Bash(python -m engine:*)", "Bash(ls:*)",
                   "Read", "Write", "Edit", "Glob", "Grep"]
            if config.fast():
                cmd[2:2] = ["--model", "sonnet"]
            env = {**os.environ, "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}
            try:
                ok = subprocess.run(cmd, cwd=config.ROOT, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    timeout=3600).returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
        if not ok:  # finish the automatic styling without Claude
            for v in variants.family(name):
                _py("sfx-auto", v, log=log)
                _py("edge-check", v, "--fix", log=log)
            log.write("\n\nClaude couldn't style this one, so One Take made the automatic cut, captions, hook and sounds. "
                      "Open it to review, or use Ask Claude to style it further.\n")
        if auto:
            from . import inbox
            for v in variants.family(name):
                try:
                    inbox.deliver(v)
                except Exception as e:  # noqa: BLE001
                    log.write(f"\ndelivery failed: {e}\n")
                    result = "failed"
    try:
        from . import progress
        progress.finish(result)
    except Exception:  # noqa: BLE001
        _status({"status": result, "ended": int(time.time())})


def use_python():
    """The studio uses this runner on Windows (no bash), when settings say so, or when new-reel.sh is missing."""
    return os.name == "nt" or config.settings().get("newreel_runner") == "python" or not (config.ROOT / "new-reel.sh").exists()


def start(env=None):
    """Start a background new-reel edit the right way for this computer."""
    env = env or os.environ.copy()
    kw = {"cwd": config.ROOT, "env": env, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    if use_python():
        return subprocess.Popen([sys.executable, "-m", "engine", "new-reel-bg"], **kw)
    return subprocess.Popen(["bash", str(config.ROOT / "new-reel.sh")], **kw)
