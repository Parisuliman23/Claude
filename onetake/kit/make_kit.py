"""Build the sellable One Take kit from this One Take.

    python3 kit/make_kit.py [OUT_DIR]        (default: ../onetake-kit, next to this folder)

Copies ONLY an allowlist (engine, studio, assets, built-in looks), swaps in the buyer versions of CLAUDE.md,
lookbook/STYLE.md and README, adds the installers, then scans the result for anything personal and refuses to finish
if it finds some. Your own reels, library, settings, style notes, voice and phone-link setup never go in.
Run it again after any improvement: the kit is rebuilt from scratch every time.
"""
import json
import re
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
KIT = SRC / "kit"
OUT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else SRC.parent / "onetake-kit"

# never ship: personal, other creators' styles, or platform-specific helpers
SKIP_ENGINE = {"voicebank.py"}                     # the owner's voice-clone collection
SKIP_LOOK = re.compile(r"^jess_")                  # looks modelled on a named creator's reels
SKIP_CAPTIONS = {"class-serif"}                    # caption style from those reels
ROOT_FILES = ["requirements.txt", "THIRD_PARTY_NOTICES.md", "studio.sh", "open-url.sh"]
KIT_FILES = {"CLAUDE.md": "CLAUDE.md", "STYLE.md": "lookbook/STYLE.md", "README.md": "README.md",
             "LICENSE.txt": "LICENSE.txt", "install.sh": "install.sh", "install.ps1": "install.ps1",
             "Start One Take.command": "Start One Take.command", "Start One Take.bat": "Start One Take.bat"}

# anything matching these in the kit = a leak: the build stops
LEAKS = [r"forttoujours", r"parisuliman", r"tailf69a27", r"swiftpickup", r"inskip", r"kilgore", r"itsmeg",
         r"\bjess_", r"KQeQy4", r"m9E7Agx", r"blZOGC9", r"sk-ant-", r"sk_[0-9a-f]{20,}", r"elevenlabs_key\"\s*:\s*\"\w",
         r"phone_pin\"\s*:\s*\"\d", r"/home/forttoujoursfitness", r"penguin\.tail"]
# applied to engine code while copying: the class-look hooks stay (harmless without those looks) but lose the names
SANITIZE = [(r"jess_", "class_"), (r"Jess Inskip's reels", "a reference creator's reels"),
            (r"Look F, from Jess Inskip's reels", "Look F, a class layout"), (r"(?i)jess inskip", "a reference creator")]
TEXT_EXT = {".py", ".js", ".html", ".css", ".md", ".json", ".txt", ".sh", ".ps1", ".bat", ".command", ".webmanifest"}


def copy_tree(src, dst, keep=lambda p: True):
    for f in src.rglob("*"):
        rel = f.relative_to(src)
        if "__pycache__" in rel.parts or f.name.startswith(".") or not keep(f):
            continue
        t = dst / rel
        if f.is_dir():
            t.mkdir(parents=True, exist_ok=True)
        else:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)


def build():
    if OUT == SRC or SRC in OUT.parents:
        raise SystemExit("Pick an output folder outside this One Take folder.")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy_tree(SRC / "engine", OUT / "engine", lambda f: f.name not in SKIP_ENGINE)
    for f in (OUT / "engine").glob("*.py"):
        t = f.read_text()
        for a, b in SANITIZE:
            t = re.sub(a, b, t)
        f.write_text(t)
    copy_tree(SRC / "app", OUT / "app")
    copy_tree(SRC / "assets", OUT / "assets")
    (OUT / "lookbook" / "looks" / "custom").mkdir(parents=True)
    for f in (SRC / "lookbook" / "looks").glob("*.py"):
        if not SKIP_LOOK.match(f.name):
            shutil.copy2(f, OUT / "lookbook" / "looks" / f.name)
    caps = json.loads((SRC / "lookbook" / "captions.json").read_text())
    if isinstance(caps, list):
        caps = [c for c in caps if c.get("id") not in SKIP_CAPTIONS]
    else:
        key = next(k for k, v in caps.items() if isinstance(v, list))
        caps[key] = [c for c in caps[key] if c.get("id") not in SKIP_CAPTIONS]
    (OUT / "lookbook" / "captions.json").write_text(json.dumps(caps, indent=1))
    shutil.copy2(SRC / "lookbook" / "filters.json", OUT / "lookbook" / "filters.json")
    (OUT / "lookbook" / "style").mkdir()
    (OUT / "lookbook" / "style" / "README.md").write_text(
        "Claude's write-ups of the reference reels you add (Lookbook → Reference reels) go here.\n")
    for f in ROOT_FILES:
        shutil.copy2(SRC / f, OUT / f)
    for src, dst in KIT_FILES.items():
        if (KIT / src).exists():
            (OUT / dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KIT / src, OUT / dst)
    for d in ("drop-in-order", "projects", "library/broll", "library/images", "library/gifs", "library/sounds"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
        (OUT / d / ".keep").write_text("")
    (OUT / ".gitignore").write_text(".venv/\nprojects/*\n!projects/.keep\ndrop-in-order/*\n!drop-in-order/.keep\n"
                                    "library/**/*\n!library/**/.keep\nsettings.json\n__pycache__/\n")
    for f in ("install.sh", "Start One Take.command", "studio.sh", "open-url.sh"):
        if (OUT / f).exists():
            (OUT / f).chmod(0o755)


def scan():
    bad = []
    pats = [re.compile(p, re.I) for p in LEAKS]
    for f in OUT.rglob("*"):
        if f.is_file() and f.suffix.lower() in TEXT_EXT:
            text = f.read_text(errors="ignore")
            for p in pats:
                for m in p.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    bad.append(f"{f.relative_to(OUT)}:{line}: {m.group(0)}")
    return bad


if __name__ == "__main__":
    build()
    leaks = scan()
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
    if leaks:
        print("STOPPED: personal or third-party details found in the kit. Fix these in your One Take, then rebuild:")
        print("\n".join("  " + x for x in leaks[:60]))
        shutil.rmtree(OUT)
        raise SystemExit(1)
    print(f"Kit built: {OUT}  ({size:.1f} MB, {sum(1 for _ in OUT.rglob('*') if _.is_file())} files). Leak scan: clean.")
