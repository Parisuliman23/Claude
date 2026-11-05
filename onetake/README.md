# One Take Studio: edit your reels with Claude Code, no CapCut grind

**Film once. Claude edits it. You stay in creative control.**

Film like you normally do, drop the clips in a folder, and tell Claude
**"I have a new reel to edit."** Claude cuts out the pauses, "um"s and
retakes, styles the captions, hook and graphics, picks music, and opens a
**studio** in your browser. There you see every edit before anything is
rendered. Bring back any cut, swap any look, or describe something new and
Claude makes three options to choose from.

One click turns it into a finished reel, plus a CapCut layer pack, a carousel,
a story and three trial reels. **One video becomes six pieces of content.**

Everything runs on your own computer. Nothing is uploaded anywhere.

## Who it's for

- **Creators who film on their phone** and lose hours cutting pauses and retakes in CapCut.
- **Coaches, course creators and small-business owners** who need to post consistently but aren't editors.
- **Moms who create content** and want their kids' faces covered automatically when they're in the shot.
- **Anyone already using Claude** who wants AI editing they can *see* before it's final, instead of
  typing a prompt and crossing their fingers.

### Why it's different from "AI edits it for you" tools
- **You see everything before it renders.** The studio previews every cut, caption and look live.
- **Nothing is locked in.** Every cut can come back, and every look, sound and take is swappable.
- **It learns your style.** Your lookbook and style notes grow with every reel.
- **More than one reel.** Carousel, story and trial reels come from the same video.

---

## What you get

**Cut**: your script on one side and the rough cut playing on the other.
- Claude removes pauses, "um"s, false starts and repeated takes.
- "Lines the engine cut" lets you bring any of them back or pick the other take.
- Tap a word to jump there. Select words to cut them; tap a struck word to bring it back.
- CapCut-style timeline: drag a clip's edge, cut before/after the playhead, split, zoom.

**Visuals**: all live, nothing rendered yet.
- 6 caption styles, including single-word, serif accent and box styles. Highlight any word to give it the accent style.
- **Lookbook**: your saved caption styles, hooks and looks, reusable on every reel.
- **Looks**: hook titles, count-up cards, word pops, lower thirds and emoji bursts.
  **Describe your own** by typing or with the 🎤 button. Claude makes **three options** to pick from, and you can ask for changes.
- **Add media**: your GIFs, images and emoji, with in/out animations (slide, spin, pop…). Drag them around on the preview.
- **Cut-away clips**: pick a video and the engine finds its best moment. You can adjust it after.
- **Cover a face**: finds every face, then covers the one you choose with an emoji, a blur, pixelation or your own image, following it across the video.

**Sound**: built-in tracks, or anything you put in `library/sounds` (including songs from your music subscription). Swap with one click.

**Finish**
- **Lock in my looks** renders the MP4.
- **Send to CapCut** gives you video, graphics and captions as separate layers (plus music and an `.srt`), so you can keep editing in CapCut.
- **Save this frame** (or press `S`). Then **Make a carousel** or **Make a story**: Claude writes them from what you said.
- **Make trial reels**: three more versions with a different opening line, length and hook, all in your look.

One video becomes six pieces of content.

---

## One-time setup (Mac)

You need **Claude Code**, **Python 3** and **ffmpeg**. In Terminal:

```bash
# 1. Homebrew (skip if you have it): https://brew.sh
# 2. ffmpeg + python
brew install ffmpeg python

# 3. get this folder (or download the ZIP from GitHub and unzip it)
git clone https://github.com/parisuliman23/claude.git
cd claude/onetake

# 4. Python packages
python3 -m pip install -r requirements.txt

# 5. check everything + make the built-in sounds
python3 -m engine setup
```

The first transcription downloads the speech model (about 500 MB) once.

Windows works too: install Python and ffmpeg (`winget install ffmpeg`), then do the same steps.

## App icons (no Terminal needed)

Run this once from the `onetake` folder:

```bash
bash install-launcher.sh
```

Two apps appear in your launcher (on a Chromebook, in the **Linux apps** folder; right-click to pin to the shelf):
- **One Take – New reel**: Claude edits what's in `drop-in-order` in the background, and the studio opens in
  your browser showing progress until the reel is ready. (To watch Claude work and chat with it, run
  `./new-reel.sh` from a Terminal instead.)
- **One Take Studio**: opens the studio in your browser.

## Every reel

1. Put your clips in **`onetake/drop-in-order/`**. They're used in name order, so `1.mov`, `2.mov`… works.
2. Open Claude Code **in the `onetake` folder** (`cd onetake` then `claude`) and say:
   > I have a new reel to edit

   (or type `/new-reel`).
3. Claude imports, cuts and styles it, then opens the studio at **http://localhost:5178**.
4. Review, tweak, ask Claude for things, then **Lock in my looks**.
5. Grab your files from the Finish tab, or from `projects/<name>/exports/`.

### Asking Claude for things from the studio
Buttons like **Send to Claude**, **Make a carousel** and **Make trial reels** send a request to Claude.
If Claude Code is installed, the studio starts it in the background and pings you
when the result is ready. If a request says *waiting*, tell Claude in your terminal:
> check my studio requests

(or `/studio-requests`).

## Your editing style (built in)

One Take edits in the style captured from 10 reference reels (`lookbook/STYLE.md`, with the full analysis
in `lookbook/style/`): every noun, number and claim gets a visual ON the word it's spoken, text paraphrases
instead of transcribing, and the edit gets out of the way when the moment is personal.

- **Three looks**: warm creator (handwriting + heavy caps, tiny one-word captions beside the face or on the
  chest), editorial serif, and cinematic finance (split screens, receipts, counters, captions on a pill).
- **Graphics for every beat**: typed headlines, handwritten notes with drawn arrows, "KEYWORD =" definition
  cards, running checklists, chapter headers, receipt cards with a highlighter sweep, counters, IF→THEN rule
  cards, name/logo badges, emoji rows, a red ✗, and a "comment KEYWORD" CTA.
- **Motion**: snap pops and hard cuts (no slow fades), typewriter text, slow push-in on screenshots,
  a camera push-in through the hook, and punch-ins at each thought change (Visuals → select a word → ⤢ Punch in).
- **Split screen**: a clip, photo or white panel on top, you below, captions on the seam.

## Teach it your style

- `lookbook/STYLE.md`: write your brand colors, fonts, the kind of hooks you like, and things you never want.
  Claude reads it before every edit and adds to it when you tell it a preference.
- **Save to lookbook** on any look you like to reuse it.
- Add your favorite GIFs, stickers, B-roll and music to `library/`.
- Want a new caption style? Ask Claude to add one to `lookbook/captions.json`.

## Shortcuts

| Key | Does |
|---|---|
| Space | Play / pause |
| Delete | Cut selected words |
| Shift-click | Extend a selection |
| B / Q / W | Split · cut before · cut after playhead |
| S | Save this frame |
| ⌘Z / ⇧⌘Z | Undo / redo |
| ← → | Nudge playhead (hold Shift for 3s) |

## Settings

Create `settings.json` next to this file to change defaults, for example:

```json
{ "whisper_model": "medium.en", "max_gap": 0.3, "music_volume": 0.1, "claude_bridge": "off", "port": 5178 }
```

- `whisper_model`: `small.en` (default) or `medium.en` (more accurate, slower).
- `max_gap`: silences longer than this many seconds get cut.
- `claude_bridge: "off"`: the studio won't start Claude by itself; requests wait for you to say "check my studio requests".

## How it works (for the curious)

- `engine/`: Python. `ingest` (join + transcribe with faster-whisper), `roughcut`, `timeline` (the edit maths),
  `render` (frames with OpenCV/Pillow, encoded with ffmpeg), `analyze` (faces, best B-roll moment),
  `finish` (frames, carousel, story, trial reels, CapCut pack), `server` (the studio), `bridge` (requests to Claude).
- `app/`: the studio, plain HTML/JS. The preview is drawn live from the same rules the renderer uses,
  which is why it's instant and matches the final video.
- `CLAUDE.md`: the playbook Claude follows. It's the "teaching": edit it to change how Claude edits.

Fonts: Montserrat, Playfair Display and Bebas Neue (SIL Open Font License, see `assets/fonts/`).
Emoji: Twemoji by Twitter, CC-BY 4.0 (https://github.com/jdecked/twemoji).
