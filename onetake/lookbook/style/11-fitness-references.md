# Fitness / workout reels: 3 references (Nov 23 2026)

The user sent 3 gym reels as "references of editing for fitness videos". No talking, music only.

## What they do
- **Full-screen 9:16 footage**, filmed portrait, wide enough to see the whole body + the weight.
- **Long holds**: one exercise per clip, 3-7 s, so full reps show (ref 1: 0.9-3 s cuts incl. detail shots; ref 2: 2-7 s; ref 3: 3.5-4 s).
  Cuts land on the music, never mid-rep.
- **Detail shots** between sets (ref 1): feet/stance from above ("point toe outward"), hand on the pin/handle. Short, 1-2 s.
- **Text is small and clean**: white, soft shadow, NO boxes/pills.
  - Title at the top: bold caps "LEG DAY" + a small italic script line under it ("quad focus"), stays on the whole reel (ref 2).
  - One short line per exercise in the middle/lower-middle: name + weight ("squat with 140kg", "bulgarian with 80kg") (ref 3),
    or a tip ("point toe outward") / goal ("how to build volume") (ref 1).
  - Optional small muscle-diagram sticker above the head showing which muscle works (ref 1).
- No filter, no zoom effects, no transitions: hard cuts.
- Music only (gym audio off), loud and steady.

## How One Take does it
- Workout reels aren't talking reels: build them as a beat-cut montage (projects/workout-legday/build2.py + beat.py).
- Music: `library/sounds/gym-trap-140 (made by Claude).m4a` (140 BPM, 2-bar build then a drop at 3.43 s). Cut on bar lines
  (1 bar = 1.714 s; mostly 2-bar holds = 3.43 s), frame-exact so cuts never drift off the beat.
- Landscape clips: fill the frame as much as possible (scaled to ~1060 px tall over a blurred copy). Tell the user to film
  workouts **portrait** next time so they're truly full-screen.
- Text: Montserrat Black caps + Playfair italic script, white with shadow. Ask for weights if the user wants "with 100kg" lines.
