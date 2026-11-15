# One Take: handoff (everything so far)

This file sums up the long cloud chat ("Claude reel editing in Capcut") that built One Take, so a new Claude session
on the Chromebook can carry on without it. Read it together with `CLAUDE.md` (how to edit reels) and
`lookbook/STYLE.md` (the user's taste). Last updated: Nov 15, 2026.

## Who the user is and how to talk to them
- A finance creator on Instagram (stocks, debt, investing). Not technical: plain words, short steps, no jargon.
- Works on an **Asus Chromebook** (Linux/"penguin", little memory and disk) and a **Samsung phone** (often from the
  phone, through the phone link). Sends photos/screenshots of the screen.
- Wants Claude to **do things, not explain them**. Prefers one clear instruction at a time.
- **Not selling One Take** ("I'm not ready to sell it yet"): no pricing, landing pages or sales prep.
- Never put the phone-link PIN or private details in GitHub.

## Setup facts
- One Take lives at `~/Claude/onetake` (git repo `Parisuliman23/Claude`, folder `onetake/`). Work happens on branch
  `claude/reel-editing-capcut-nyvace`, merged into `main` by pull request. To update the Chromebook copy: pull `main`
  (or copy the changed files) and **keep** `projects/`, `library/`, `settings.json`, `lookbook/STYLE.md`,
  `lookbook/saved.json`. Then restart the studio.
- Studio: `bash ~/Claude/onetake/studio.sh` → http://100.115.92.26:5178 on the Chromebook. It also starts by itself
  (`python3 -m engine autostart on`, a systemd user service).
- **Permanent phone link**: https://penguin.tailf69a27.ts.net (Tailscale Funnel; `/phone` = upload/download page).
  Asks a PIN once per phone (the PIN is in `settings.json`, never commit it). Works only while the Chromebook is on,
  plugged in, awake (lid-closed "stay awake" is set) and the studio is running.
- Remote control: `cd ~/Claude/onetake && claude remote-control` in a Terminal tab kept open (minimised). The user
  then chats with the Chromebook from claude.ai/code or the Claude phone app (session "onetake · penguin").
- If the Chromebook freezes or videos stop playing: it's out of memory. Fix = right-click Terminal → Shut down Linux,
  reopen (the studio auto-starts). Do one heavy job at a time; tell the user to close extra tabs and `/clear` long
  Claude chats.
- Disk is small (2–5 GB free). A new reel needs ~4 GB while it's made. `python3 -m engine free-space` + the studio's
  🧹 Free up button (only after a complete render is saved on the phone).

## Reels right now
- `20261103-171957` "5 checks before you buy a stock": rendered (1:11), carousel + story. Its original clips were
  not kept, so it can't be remastered; the old-footage copy is in Google Drive "One Take/Originals" if ever needed
  (`restore-footage NAME FILE`).
- `20261111-153844` (+ `-class` version): rendered; needs a proper title. Remastered with the new colours: press
  Lock in my looks again to render them with it.

## The user's preferences (also in lookbook/STYLE.md; keep both in sync)
- **Colour: keep the footage exactly like the phone shows it. No filter by default** ("Original"). Never "fix" flat
  footage with a filter. Filter options stay available if they ask.
- **Split screen instead of covering the face**: big graphics / B-roll in the top half, the user below.
- **Reference structure** (`lookbook/style/05-split-screen-reference.md`): split screen as the main beat, top clip
  changing every 1.5–3 s, small boxed captions on the seam, highlighted screenshots, card-over-blur cut-aways, lists
  above the head, people named → photo + name label, company names → logos, held hook title over quick cuts,
  "Comment WORD" + "+follow" ending, something new every 1–3 s.
- **Company names → logos pop in on each name** (`logo_row`; logos by name or ticker).
- **Captions**: they like **Cinematic · pill** (small white words in a dark rounded box, 2–3 words) and the
  **Class · serif** typed fragments; asked how to set a default (Ask Claude + "Make this my default").
- **Hook**: the **Typed headline** look (big white caps + handwritten line), ideally over full-screen B-roll.
- **Look F "Class" (Jess Inskip style)** is a favourite: every edit also gets a `-class` version.
- Primary styles: Look D Notebook / Look E Motion (style-pick decides). Sound effects sparse.
- Footage quality: film with **HDR off**, back camera, UHD 30 in good light (FHD in dim light), face a window, space
  behind them. `footage-check` gives tips after every import; pass them on.

## What was built / fixed (newest first)
- **Phone studio laid out like CapCut**: dark editor, top bar ✕ · undo/redo · Ask Claude · Export, big preview,
  timeline, bottom icon bar Edit · Cut · Visuals · Sound · Finish; each section opens as a slide-up sheet; Edit selects
  the clip and the bar becomes Done · Split · Delete · Cut before · Cut after. Desktop layout unchanged.
- **HDR colours matched to the phone**: `ingest.TONEMAP` = 203-nit reference white + hable + gentle RGB desaturation,
  checked against a screenshot of the user's own clip in the Samsung gallery (old 100-nit version was ~25% too bright
  and orange). Earlier fixes still stand: HDR detection with the rotation tag, BT.709 tags on every export, the
  preview showing the filter. Existing reels need `remaster` to get new colours.
- **Lighter renders** (encoder ~430 → ~270 MB via `config.x264_light()`), **lighter previews** (looks drawn one at a
  time, small caches), request progress counts from when the phone sees it, stuck requests marked "stopped" at
  studio start.
- **Timeline touch like CapCut**: no page zoom, no accidental cuts, wide handles that snap to the playhead, two-finger
  pinch zooms the timeline.
- **Home page buttons fixed** (Delete / Free up / phone card), **Filter on/off compare button** on the preview.
- **Footage check** (`engine/quality.py`, `footage-check`), studied a creator with the same phone: clarity comes from
  light, background depth, back camera, HDR off. Guide: `lookbook/style/06-clear-footage.md`.
- **More B-roll**: Pexels (`broll-key --pexels KEY`), Internet Archive public-domain footage (`archive-find`,
  `archive-preview`, `archive-clip`), `broll-check` contact sheets. **Real stock charts**: `price-fetch TICKER RANGE`
  + `stock_chart` look.
- **Logos**: `logo_row` look, `logo-find`, `logo-pack` (~2,000 NYSE/NASDAQ name logos from Wikidata), `logo-import`
  (~5,100 ticker icons from github.com/davidepalazzo/ticker-logos). Not logostream.dev (its terms forbid bulk saving).
- **Card-over-blur cut-away layout** (`"layout": "card"`), split-screen reference style written up.
- **Permanent phone link** (Tailscale) + autostart; phone page upload/download; 🧹 Free up space; `restore-footage`;
  carousel/story re-grab frames after remaster; remaster hides stale trial reels.
- Earlier: notebook (Look D), motion graphics (Look E), class style (Look F) with versions, CapCut-style timeline,
  sync effects to words, full studio on the phone, phone uploads.

## Ideas the user agreed to but not built yet
1. **Full-screen "app" mode**: make the studio installable (web app manifest + icon) so it opens from the phone's
   home screen without the browser bars.
2. **CapCut-style option rows**: tapping a tool opens a row of options instead of a long panel, e.g. Visuals → Text ·
   Captions · Stickers · Effects · B-roll · Charts; Sound → Music · Sound effects · Voice volume; Edit → Split ·
   Delete · Speed · Volume.
3. Optional: a launcher icon that starts `claude remote-control` with one click.

## Lessons (avoid repeating these mistakes)
- Check colour against what the **phone shows** (a screenshot from the gallery), not against another conversion.
- Test phone layouts in an emulated phone (Playwright `devices['Galaxy S9+']`) before shipping.
- Chromebook = ~1 GB for Linux: never hold many full-size frames, keep caches small, one heavy job at a time.
- Name new CLI commands carefully: `restore` already means "bring back cut words".
- Free up only after a complete render exists, and say clearly that it deletes the Chromebook copy.
