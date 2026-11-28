# One Take Studio

**Film like normal. Claude edits it in your style. You stay in control.**

One Take turns your raw talking clips into an edited reel: it cuts the pauses, flubs and repeated takes, adds
captions, animated graphics timed to your words, B-roll, music and sound effects, then opens a studio where you review
everything live. Nothing renders until you press **Lock in my looks**. Every change you make teaches it your style.

## What you need
- A Mac, Windows PC or Linux computer (8 GB of memory or more recommended)
- A Claude subscription with **Claude Code** (the installer can set it up)
- About 2 GB of free space, plus a few GB per reel while you edit it

## Install (once, ~10 minutes)
**Mac / Linux:** open the One Take folder in Terminal and run:
```
bash install.sh
```
**Windows:** right-click `install.ps1` → **Run with PowerShell**.

The installer adds anything missing (Python, FFmpeg), sets up One Take in its own folder (nothing else on your computer
changes), and offers to install Claude Code.

## Edit your first reel
1. Film your video (vertical, back camera, face a window). Retakes are fine: One Take keeps your best take.
2. Put the clips in the **drop-in-order** folder (they're used in file-name order).
3. Open a terminal in the One Take folder, type `claude`, and say: **I have a new reel to edit**.
4. Claude makes the cut and styles it, then opens the studio in your browser (http://localhost:5178).
5. Review it: bring back any cut, swap any graphic, change captions or music, or ask Claude for changes.
6. Press **Lock in my looks** to render, then download the MP4 (or send it to CapCut as an editable project).

**First time?** Tell Claude: **"interview me about my style"**. It asks a few questions and writes your style rules,
so your very first edit already looks like you. Add reels you love in the studio (Lookbook → Reference reels) and
Claude studies them and learns the techniques.

## Open the studio any time
- **Mac:** double-click **Start One Take.command**
- **Windows:** double-click **One Take Studio** on your desktop
- Start it automatically when you log in: `python3 -m engine autostart on` (Windows: `python -m engine autostart on`)

## Good to know
- **Your style lives in `lookbook/STYLE.md`**: plain-English rules Claude reads before every edit. Edit it any time.
- **B-roll**: add your own clips in the studio (Add media), or add a free Pixabay key there so Claude can find stock
  clips. Claude checks every clip shows what you're saying before it uses it.
- **Lip sync is checked** after every render (picture, voice timing, echo). If a check fails, ask Claude to look.
- **Space**: `python3 -m engine free-space` shows what each reel uses; clear finished reels after you've saved them.
- **Stuck?** Run `python3 -m engine setup`: it checks everything and tells you how to fix it.

One Take Studio is not affiliated with or endorsed by Anthropic, CapCut/ByteDance or Instagram/Meta.
See `THIRD_PARTY_NOTICES.md` for open-source credits and `LICENSE.txt` for your licence.
