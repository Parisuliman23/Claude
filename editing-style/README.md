# Editing style analysis

A study of 10 reference reels (vertical 9:16, ~14.7 minutes total) to capture one editing style: how the animations are timed, why each visual was chosen, and the design system (composition, color, type, objects, motion).

| File | What's in it |
|---|---|
| [`01-STYLE-GUIDE.md`](01-STYLE-GUIDE.md) | **Start here.** The design system: the three looks, the screen zones, palette with hex values, font pairings, motion specs, a "what to show for what's said" decision table, a beat-sheet template and a build recipe |
| [`02-animation-breakdown.md`](02-animation-breakdown.md) | Every graphic in all 10 videos: timestamp, what was being said, what appeared, how it moved, and why. Ends with 20 frame-level motion measurements |
| [`transcripts/`](transcripts/) | Timestamped transcripts of all 10 videos |
| [`frame-strips/`](frame-strips/) | 20 frame-by-frame contact strips of the key animations (read left→right, top→bottom; every 2nd–4th frame) |

## Videos analysed

| # | Topic | Length | Full-frame changes | Pace | Look |
|---|---|---|---|---|---|
| 01 | Launch behind-the-scenes | 82 s | 1 | 238 wpm | Warm creator |
| 02 | The "it" factor | 102 s | 2 | 208 wpm | Warm creator |
| 03 | What the top 1% do differently | 104 s | 67 | 211 wpm | Cinematic finance |
| 04 | Media kit as a 3D world | 51 s | 19 | 236 wpm | Cinematic finance / tech |
| 05 | Modified DCA | 71 s | 16 | 265 wpm | Cinematic finance (minimal) |
| 06 | Marriage rules | 70 s | 0 | 225 wpm | Warm creator (minimal) |
| 07 | Why stocks will crash | 93 s | 44 | 230 wpm | Cinematic finance (news) |
| 08 | Reel breakdown: B content | 149 s | 2 | 215 wpm | Editorial serif |
| 09 | Should I buy Meta? | 56 s | 15 | 247 wpm | Editorial serif + finance |
| 10 | 4 money lies parents told you | 103 s | 29 | 185 wpm | Skit |

"Full-frame changes" counts hard cuts to a different full-screen image (B-roll, split-screen swaps). It doesn't count graphic overlays or seamless jump cuts.

## Method
- Transcription: Whisper `small.en` (sherpa-onnx), split into ~3–5 s phrases.
- Cut detection: frame-difference + luma-histogram distance at native frame rate.
- Visual inventory: 1 fps timestamped contact sheets of every video.
- Motion timing: frame-by-frame strips around 20 key animations.
- Color: pixel sampling of set, wardrobe and graphic accents.
