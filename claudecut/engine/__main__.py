"""Command line: python3 -m engine <command>   (run from the claudecut folder)

  setup                     check tools, make built-in sounds
  new [name]                make a project from the clips in drop-in-order/
  open [name]               open the studio in your browser
  show NAME                 print the edit (numbered lines, cut words in [brackets])
  cut NAME A-B              cut words A..B          restore NAME A-B   bring them back
  cut-line NAME L           cut line L              restore-line NAME L
  highlight NAME A-B [--off]
  set NAME KEY --json VALUE  set a top-level field (caption_style, sound, carousel, trials, story, hook_duration…)
  overlay NAME ID --json {…} change an overlay (merge)    add-overlay NAME --json {…}   remove-overlay NAME ID
  faces NAME                find faces (for Cover a face)
  still NAME SECONDS        render one frame to check a look (projects/NAME/cache/still.png)
  render NAME               lock in: render projects/NAME/exports/reel.mp4
  export NAME carousel|story|trials|capcut
  requests [NAME]           list studio requests waiting for Claude
  request-done NAME ID --note "..." [--options a,b,c] [--failed]
  look-preview LOOK [--params JSON] [--out file.png]
  list                      list projects
"""
import argparse
import json
import shutil
import subprocess
import sys

from . import config, project


def _rng(s):
    a, _, b = s.partition("-")
    return int(a), int(b or a)


def show(name):
    p = project.load(name)
    from . import timeline
    segs = project.segments(p)
    print(f"{p['title']}  —  {timeline.total(segs):.1f}s after cuts (raw {p['duration']:.1f}s), caption style: {p['caption_style']}")
    for l in project.lines(p):
        ws = []
        for i in range(l["w0"], l["w1"] + 1):
            w = p["words"][i]
            t = w["t"] + ("*" if w.get("hl") else "")
            ws.append(f"[{t}]" if w.get("cut") else t)
        tag = " (CUT)" if l["cut"] else ""
        print(f"L{l['id']:>3} w{l['w0']}-{l['w1']} @{p['words'][l['w0']]['s']:.1f}s{tag}: {' '.join(ws)}")
    if p.get("overlays"):
        print("\nOverlays:")
        for o in p["overlays"]:
            what = o.get("look") or o.get("src") or o.get("emoji")
            print(f"  {o['id']} {o['kind']}:{what} words {o['w0']}-{o.get('w1', o['w0'])} {o.get('role', '')} {json.dumps(o.get('params', {}))[:80]}")
    for b in p.get("broll", []):
        print(f"  b-roll {b['src']} over words {b['w0']}-{b['w1']} from {b.get('clip_start', 0)}s")
    print(f"\nSound: {p.get('sound', {}).get('src')}")


def set_cut(name, a, b, val):
    def fn(p):
        for i in range(a, b + 1):
            p["words"][i]["cut"] = val
            if val:
                p["words"][i]["why"] = "claude"
        p["edit_rev"] = p.get("edit_rev", 0) + 1
    project.update(name, fn)


def line_range(name, l):
    p = project.load(name)
    for x in project.lines(p):
        if x["id"] == l:
            return x["w0"], x["w1"]
    raise SystemExit(f"no line {l}")


def setup():
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"✗ {tool} is missing — install it (Mac: brew install ffmpeg)")
            ok = False
    for mod in ("faster_whisper", "cv2", "PIL", "numpy"):
        try:
            __import__(mod)
        except ImportError:
            print(f"✗ Python package {mod} missing — run: python3 -m pip install -r requirements.txt")
            ok = False
    if ok:
        from . import synth
        made = synth.make_all()
        if made:
            print("Made built-in sounds:", ", ".join(made))
        from . import bridge
        print("✓ Ready." + ("" if bridge.claude_bin() else "  (Tip: install Claude Code so the studio can send requests to Claude.)"))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m engine", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--options", default="")
    ap.add_argument("--failed", action="store_true")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--json", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--keep-drop", action="store_true", help="don't empty drop-in-order/ after importing")
    a = ap.parse_args(argv)
    c, args = a.cmd, a.args

    if c == "setup":
        sys.exit(0 if setup() else 1)
    if c == "new":
        from . import ingest
        name = ingest.new(args[0] if args else None, move=not a.keep_drop)
        print(f"\nNext: review with `python3 -m engine show {name}`, then `python3 -m engine open {name}`")
        return
    if c in ("open", "serve"):
        from . import server
        server.serve(args[0] if args else None, open_browser=not a.no_browser)
        return
    if c == "list":
        for p in project.list_projects():
            print(f"{p['name']}  ({(p['duration'] or 0):.0f}s raw)  render: {p['render']}")
        return
    if c == "show":
        return show(args[0])
    if c in ("cut", "restore"):
        x, y = _rng(args[1])
        set_cut(args[0], x, y, c == "cut")
        return show(args[0])
    if c in ("cut-line", "restore-line"):
        x, y = line_range(args[0], int(args[1]))
        set_cut(args[0], x, y, c == "cut-line")
        return show(args[0])
    if c == "highlight":
        x, y = _rng(args[1])

        def fn(p):
            for i in range(x, y + 1):
                p["words"][i]["hl"] = not a.off
            p["edit_rev"] = p.get("edit_rev", 0) + 1
        project.update(args[0], fn)
        return show(args[0])
    if c == "set":
        key, val = args[1], json.loads(a.json)

        def fn(p):
            p[key] = val
            p["edit_rev"] = p.get("edit_rev", 0) + 1
        project.update(args[0], fn)
        print(f"Set {key}.")
        return
    if c in ("overlay", "add-overlay", "remove-overlay"):
        def fn(p):
            if c == "add-overlay":
                ov = json.loads(a.json)
                ov.setdefault("id", project.new_id())
                for k, d in (("x", 0.5), ("y", 0.4), ("scale", 1.0 if ov.get("kind") == "look" else 0.45),
                             ("anim_in", "pop"), ("anim_out", "fade"), ("min_dur", 1.2)):
                    ov.setdefault(k, d)
                ov.setdefault("w1", ov["w0"])
                p["overlays"].append(ov)
                print("Added overlay", ov["id"])
            else:
                o = next((o for o in p["overlays"] if o["id"] == args[1]), None)
                if not o:
                    raise SystemExit(f"no overlay {args[1]}")
                if c == "remove-overlay":
                    p["overlays"].remove(o)
                else:
                    upd = json.loads(a.json)
                    if "params" in upd:
                        o.setdefault("params", {}).update(upd.pop("params"))
                    o.update(upd)
            p["edit_rev"] = p.get("edit_rev", 0) + 1
        project.update(args[0], fn)
        return show(args[0])
    if c == "faces":
        from . import analyze
        p = project.load(args[0])
        res = analyze.detect_faces(config.absolute(p["source"]), project.pdir(args[0]) / "cache" / "faces")
        project.update(args[0], lambda q: q.setdefault("faces", {}).update({"detected": res}))
        for f in res:
            print(f"{f['id']}: seen {f['seen']}s, thumbnail {f['thumb']}")
        return
    if c == "still":
        from . import render
        out = project.pdir(args[0]) / "cache" / "still.png"
        out.parent.mkdir(exist_ok=True)
        render.still(args[0], float(args[1]), out)
        print("Saved", out)
        return
    if c == "render":
        from . import render
        edit_rev = project.load(args[0]).get("edit_rev", 0)
        out = render.render(args[0], progress=lambda x: print(f"\r  rendering {x * 100:.0f}%", end="", flush=True))
        project.update(args[0], lambda q: q.update({"render": {"status": "done", "file": config.rel(out), "edit_rev": edit_rev}}))
        print(f"\nSaved {out}")
        return
    if c == "export":
        from . import finish
        kind = args[1]
        prog = lambda x: print(f"\r  {kind} {x * 100:.0f}%", end="", flush=True)
        res = {"carousel": lambda: finish.carousel(args[0]), "story": lambda: finish.story(args[0]),
               "trials": lambda: finish.trials(args[0], progress=prog),
               "capcut": lambda: finish.capcut(args[0], progress=prog)}[kind]()
        print("\n" + json.dumps(res, indent=1))
        return
    if c == "requests":
        names = args or [p["name"] for p in project.list_projects()]
        n = 0
        for nm in names:
            for r in project.load(nm).get("requests", []):
                if r.get("status") in ("waiting", "running"):
                    n += 1
                    print(f"[{nm}] {r['id']} ({r['status']}) {json.dumps({k: v for k, v in r.items() if k not in ('id', 'status', 'created')})}")
        if not n:
            print("No open requests.")
        return
    if c == "request-done":
        nm, rid = args[0], args[1]

        def fn(p):
            for r in p.get("requests", []):
                if r["id"] == rid:
                    r["status"] = "failed" if a.failed else "done"
                    r["note"] = a.note
                    if a.options:
                        r["options"] = [o.strip() for o in a.options.split(",") if o.strip()]
        project.update(nm, fn)
        print("Marked", rid, "failed" if a.failed else "done")
        return
    if c == "look-preview":
        from . import looks
        out = a.out or str(config.ROOT / "projects" / f"_preview_{args[0]}.png")
        looks.still(args[0], json.loads(a.params), out)
        print("Preview saved to", out)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
