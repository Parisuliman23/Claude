"""Command line: python3 -m engine <command>   (run from the onetake folder)

  setup                     check tools, make built-in sounds
  new [name]                make a project from the clips in drop-in-order/
  open [name]               open the studio in your browser
  show NAME                 print the edit (numbered lines, cut words in [brackets])
  cut NAME A-B              cut words A..B          restore NAME A-B   bring them back
  cut-line NAME L           cut line L              restore-line NAME L
  highlight NAME A-B [--off]
  retext NAME A-B "new words"   fix words the transcript got wrong (captions only)
  set NAME KEY --json VALUE  set a top-level field (caption_style, sound, carousel, trials, story, hook_duration…)
  overlay NAME ID --json {…} change an overlay (merge)    add-overlay NAME --json {…}   remove-overlay NAME ID
  add-broll NAME --json {…}  cut-away / split screen: {"w0","w1","src": video|image|null, "color": "#FFFFFF", "layout": "full"|"split"}
  broll-find "search words" [--n 5]   download free stock clips from Pixabay into library/broll
  broll-starter                       download a starter pack of ~30 money/finance clips
  broll-key KEY                       save your free Pixabay API key (pixabay.com/api/docs)
  sfx-auto NAME [--keep]    give every look, cut-away and punch-in a matching sound effect
  sfx-list                  list sound effects you can use (built-in + library/sfx)
  inbox                     show the phone-upload folders (Google Drive "One Take/Inbox" -> "One Take/Ready")
  remove-captions NAME [--off]  find captions burned into the video and paint them out (or keep them)
  faces NAME                find faces (for Cover a face)
  still NAME SECONDS        render one frame to check a look (projects/NAME/cache/still.png)
  render NAME               lock in: render projects/NAME/exports/reel.mp4
  export NAME capcut-project|carousel|story|trials|capcut|storyboard   (capcut-project = a real CapCut project; capcut = layer pack)
  edge-check NAME [--fix]   find looks hidden by Instagram's buttons/text or off the frame (--fix moves them)
  requests [NAME]           list studio requests waiting for Claude
  request-done NAME ID --note "..." [--options a,b,c] [--failed]
  look-preview LOOK [--params JSON] [--out file.png]
  add-fx NAME --json '{"kind": "whip", "w": 57}'   transition on a word: whip | zoom | flash | shake | glitch | light_leak
  remove-fx NAME ID
  style-pick NAME           which editing style fits this video best (notebook / motion / mix), and why
  study-ref library/references/x.mp4   measure a reference reel (frame sheets, cuts, words, sound) into lookbook/references/
  remaster NAME             rebuild a reel's footage from its original clips with the current colour fix
  phone-link [permanent|changing]   the phone link: a fixed address (Tailscale Funnel, set up with
                            bash setup-phone-link.sh) or the free link that changes on every restart
  autostart on|off          start the studio (and phone link) whenever Linux starts
  restore NAME FILE...      bring back a cleared reel's footage from its clips (in order) or a copy of its
                            old footage; the edit is kept
  logo-find NAME...         download company logos (Wikidata) into library/logos for the logo_row look
  logo-pack [--top N]       download the logos of every NYSE/NASDAQ company (or the N best-known) at once
  free-space [NAME]         how much each reel takes; with NAME, delete that finished reel's big files
                            (clips, footage, renders) once it's saved on the phone. The edit is kept.
  proxy NAME                make the light preview copy the studio plays (smoother on slow computers)
  image-find "apple" [--n 3] [--json '{"type": "vector"}']   images for stickers into library/images (Pixabay)
  variants NAME [STYLE ...] make extra versions of an edit (default: class + the style-pick), each its own project
  list                      list projects
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import config, project


def _rng(s):
    a, _, b = s.partition("-")
    return int(a), int(b or a)


def show(name):
    p = project.load(name)
    from . import timeline
    segs = project.segments(p)
    print(f"{p['title']}  —  {timeline.total(segs):.1f}s after cuts (raw {p['duration']:.1f}s), caption style: {p['caption_style']}")
    for f in p.get("fx", []):
        print(f"  fx {f.get('id')} {f.get('kind')} on word {f.get('w')}")
    if p.get("card_y") is not None:  # notebook layout, worked out from where the face is
        print(f"layout: captions at y {p.get('caption_y')}, notebook cards at y {p['card_y']} (keeps the face clear)")
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
        from . import synth, sfx
        sfx.ensure_builtin()
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
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--keep-drop", action="store_true", help="don't empty drop-in-order/ after importing")
    a = ap.parse_args(argv)
    c, args = a.cmd, a.args
    try:  # a new reel being edited in the background: move its % along
        from . import progress
        progress.for_command(c)
    except Exception:  # noqa: BLE001
        pass

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
    if c == "retext":
        x, y = _rng(args[1])
        project.update(args[0], lambda p: project.replace_words(p, x, y, " ".join(args[2:])))
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
    if c == "variants":  # extra versions of the same cut in other styles (one is always the class style)
        from . import variants
        made = variants.make(args[0], args[1:] or None)
        for v in made:
            print(f"{'Already have' if v.get('existing') else 'Made'} {v['name']}  ({v['style']} style)")
        if made:
            print("Style each one like a normal edit (same words, its own looks), e.g. `show " + made[0]["name"] + "`.")
        return
    if c == "phone-link":  # permanent (Tailscale Funnel) or changing (Cloudflare quick tunnel) phone link
        import secrets
        f = config.ROOT / "settings.json"
        st = json.loads(f.read_text()) if f.exists() else {}
        if args:
            st["phone_link"] = "permanent" if args[0].startswith("perm") else "changing"
            st["phone_access"] = True
            st.setdefault("phone_pin", f"{secrets.randbelow(900000) + 100000}")
            f.write_text(json.dumps(st, indent=1))
        mode = st.get("phone_link", "changing")
        print(f"Phone link: {mode}" + (f"  (PIN {st.get('phone_pin')}, asked once per phone)" if mode == "permanent" else ""))
        if args:
            print("Restart the studio to use it: pkill -f 'engine open'; bash studio.sh")
        return
    if c == "autostart":  # Linux starts -> the studio starts (Chromebook: when you open any Linux app or Terminal)
        unit = Path.home() / ".config" / "systemd" / "user" / "onetake-studio.service"
        if args and args[0] == "off":
            subprocess.run(["systemctl", "--user", "disable", "--now", "onetake-studio.service"], check=False)
            unit.unlink(missing_ok=True)
            print("The studio won't start by itself any more.")
            return
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text(f"""[Unit]
Description=One Take Studio
After=network-online.target

[Service]
WorkingDirectory={config.ROOT}
ExecStart={sys.executable} -m engine open --no-browser
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
""")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        r = subprocess.run(["systemctl", "--user", "enable", "--now", "onetake-studio.service"], capture_output=True, text=True)
        print("The studio now starts whenever Linux starts." if r.returncode == 0 else f"Couldn't turn it on: {r.stderr.strip()}")
        return
    if c == "restore":  # footage cleared/lost: rebuild it from the clips or an old footage copy
        from . import ingest
        ingest.restore(args[0], args[1:])
        return
    if c == "logo-pack":  # every listed company's logo, ahead of time (works by name or ticker)
        from . import logos
        top = None
        if "--top" in args:
            top = int(args[args.index("--top") + 1])
        logos.pack(top)
        return
    if c == "logo-find":  # company logos for the logo_row look
        from . import logos
        for n in args:
            try:
                f = logos.find(n)
                print(f"{n}: {config.rel(f) if f else 'no logo found (the look shows the name instead; or drop a PNG in library/logos/)'}")
            except Exception as e:  # noqa: BLE001
                print(f"{n}: couldn't download ({e}); try again in a minute")
        return
    if c == "free-space":  # a finished reel saved on the phone: give its disk space back
        from . import space
        if not args:
            print(f"Free on this computer: {space.disk_free() / 1e9:.1f} GB")
            for p in project.list_projects():
                q = project.load(p["name"])
                tag = "  (already cleared)" if q.get("archived") else "" if q.get("variant_of") else f"  {space.freeable(p['name']) / 1e9:.2f} GB"
                print(f"  {p['name']}  {p['title']}{tag}")
            return
        print(f"Freed {space.free(args[0]) / 1e9:.2f} GB. Now free: {space.disk_free() / 1e9:.1f} GB")
        return
    if c == "remaster":  # rebuild a reel's footage from its original clips (e.g. after the HDR colour fix)
        from . import ingest
        print("Rebuilt:", ", ".join(ingest.remaster(args[0])))
        return
    if c == "study-ref":  # measure a reference reel (frames, cuts, words, sound) for Claude to learn its style
        from . import reference
        info = reference.study(args[0])
        print(json.dumps(info, indent=1))
        print("Now look at each sheet image, then write lookbook/style/NN-<name>.md and a STYLE.md section (CLAUDE.md, kind reference).")
        return
    if c == "proxy":  # the light preview copy for the studio (normally made at import)
        from . import ingest
        print(ingest.make_proxy(args[0]) or "Couldn't make it.")
        return
    if c == "image-find":  # stickers / illustrations / photos for looks (Pixabay)
        from . import stock
        kind = (json.loads(a.json) if a.json else {}).get("type", "all")
        try:
            got = stock.image_search(" ".join(args), a.n, kind)
        except stock.NoKey as e:
            raise SystemExit(str(e))
        print("\n".join(got) or "Nothing found. Try simpler words.")
        return
    if c == "style-pick":  # which editing style fits this video (notebook / motion / mix)
        from . import stylepick
        p = project.load(args[0])
        r = stylepick.analyze(p)
        project.update(args[0], lambda q: q.update({"style_pick": {"pick": r["pick"], "scores": r["scores"]}}))
        print(f"Best style: {r['pick'].upper()}  (scores: {r['scores']})")
        for line in r["reasons"]:
            print("  -", line)
        print(f"  captions: set {args[0]} caption_style --json '\"{stylepick.STYLE_CAPTIONS[r['pick']]}\"'")
        for k, v in r["moments"].items():
            if v:
                print(f"  {k} words at: {', '.join(map(str, v[:20]))}")
        return
    if c in ("add-fx", "remove-fx"):  # transitions on a word: whip, zoom, flash, shake, glitch, light_leak
        from . import fx as _fx

        def fn(p):
            if c == "add-fx":
                f = json.loads(a.json)
                if f.get("kind") not in _fx.KINDS:
                    raise SystemExit(f"kind must be one of: {', '.join(_fx.KINDS)}")
                f.setdefault("id", project.new_id("f"))
                p.setdefault("fx", []).append(f)
                print("Added effect", f["id"])
            else:
                p["fx"] = [f for f in p.get("fx", []) if f.get("id") != args[1]]
                print("Removed", args[1])
            p["edit_rev"] = p.get("edit_rev", 0) + 1
        project.update(args[0], fn)
        return
    if c in ("overlay", "add-overlay", "remove-overlay"):
        def fn(p):
            if c == "add-overlay":
                ov = json.loads(a.json)
                ov.setdefault("id", project.new_id())
                for k, d in (("x", 0.5), ("y", 0.4), ("scale", 1.0 if ov.get("kind") == "look" else 0.45),
                             ("anim_in", "snap"), ("anim_out", "none"), ("min_dur", 1.2)):
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
    if c in ("broll-find", "broll-starter", "broll-key"):
        from . import stock
        try:
            if c == "broll-key":
                stock.save_key(args[0])
                print("Saved. (It stays on this computer, in settings.json.)")
                return
            got = stock.search(" ".join(args), a.n) if c == "broll-find" else \
                stock.starter_pack(progress=lambda x: print(f"\r  {x * 100:.0f}%", end="", flush=True))
        except stock.NoKey as e:
            raise SystemExit(str(e) + "  Or: python3 -m engine broll-key YOUR_KEY")
        print("\n".join(got) or "Nothing found. Try other words.")
        return
    if c in ("sfx-auto", "sfx-list"):
        from . import sfx
        if c == "sfx-list":
            for x in sfx.library():
                print(f"{x['path']}  ({x['dur']}s, {x['source']})  {x['tags']}")
            return
        p = project.update(args[0], lambda q: (sfx.auto(q, replace=not a.keep), q.update({"edit_rev": q.get("edit_rev", 0) + 1})))
        print(f"{len(p['sfx'])} sound effects placed.")
        return
    if c == "edge-check":
        from . import finish
        if a.fix:
            p = project.update(args[0], lambda q: (finish.fix_edges(q), q.update({"edit_rev": q.get("edit_rev", 0) + 1})))
        flags = finish.edge_check(project.load(args[0]))
        for f in flags:
            print(f"  {f['id']} {f['name']} at {f['at']}s: {f['issue']}")
        print("All looks are in the safe area." if not flags else f"{len(flags)} look(s) may be partly hidden.")
        return
    if c == "inbox":
        from . import inbox
        inbox.ensure()
        print(json.dumps(inbox.status(), indent=1))
        return
    if c == "add-broll":
        b = json.loads(a.json)
        b.setdefault("id", project.new_id("b"))
        b.setdefault("w1", b["w0"])
        b.setdefault("clip_start", 0)
        b.setdefault("layout", "full")
        if b.get("src") and config.absolute(b["src"]).suffix.lower() in config.VIDEO_EXT and "clip_start" not in json.loads(a.json):
            from . import analyze
            p0 = project.load(args[0])
            sp = project.timeline.range_out(p0["words"], project.segments(p0), b["w0"], b["w1"])
            b["clip_start"] = analyze.best_moment(config.absolute(b["src"]), (sp[1] - sp[0]) if sp else 3)
        project.update(args[0], lambda p: (p.setdefault("broll", []).append(b), p.update({"edit_rev": p.get("edit_rev", 0) + 1})))
        print("Added cut-away", b["id"])
        return
    if c == "remove-captions":
        from . import analyze
        nm = args[0]
        if a.off:
            project.update(nm, lambda p: (p.setdefault("burned_captions", {}).update({"remove": False}),
                                          p.update({"edit_rev": p.get("edit_rev", 0) + 1})))
            print("Keeping the video's own captions.")
            return
        p = project.load(nm)
        scan = analyze.scan_burned_text(config.absolute(p["source"]))
        if not scan["band"]:
            print("No burned-in captions found.")
            return

        def fn(q):
            q["burned_captions"] = {"remove": True, **scan}
            q["caption_y"] = round(min(0.85, max(0.15, (scan["band"][0] + scan["band"][1]) / 2)), 3)
            q["edit_rev"] = q.get("edit_rev", 0) + 1
        project.update(nm, fn)
        print(f"Found captions in {scan['coverage'] * 100:.0f}% of the video (band {scan['band']}). "
              f"They'll be painted out; your captions moved to y={min(0.85, (scan['band'][0] + scan['band'][1]) / 2):.2f}.")
        return
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
        from . import finish
        phone = finish.phone_copy(out, out.with_name("reel_phone.mp4"))
        cov = finish.cover(args[0])
        project.update(args[0], lambda q: (q.update({"render": {"status": "done", "file": config.rel(out), "edit_rev": edit_rev,
                                                                "phone": config.rel(phone)}}),
                                           q.setdefault("exports", {}).update({"cover": cov} if cov else {})))
        print(f"\nSaved {out}")
        return
    if c == "export":
        from . import finish
        kind = args[1]
        prog = lambda x: print(f"\r  {kind} {x * 100:.0f}%", end="", flush=True)
        res = {"carousel": lambda: finish.carousel(args[0]), "story": lambda: finish.story(args[0]),
               "trials": lambda: finish.trials(args[0], progress=prog),
               "capcut": lambda: finish.capcut(args[0], progress=prog),
               "storyboard": lambda: finish.storyboard(args[0], progress=prog),
               "capcut-project": lambda: __import__("engine.capcut_draft", fromlist=["x"]).build(args[0], progress=prog)}[kind]()
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
