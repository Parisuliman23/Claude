# Editing style analysis

A study of 10 reference reels (vertical 9:16, ~14.7 minutes total) to capture one editing style: how the animations are timed, why each visual was chosen, and the design system (composition, color, type, objects, motion).

## Folder layout

```
editing-style/
├── README.md                    ← you are here
├── 01-style-guide.md            ← START HERE: the full design system
├── 02-animation-breakdown.md    ← every animation in all 10 videos, in one doc
└── videos/
    ├── 01-launch-behind-the-scenes/
    │   ├── breakdown.md         ← this video's animations: time · said · visual · motion · why
    │   ├── transcript.md        ← timestamped transcript
    │   ├── contact-sheets/      ← 1 frame per second, 24 s per image (000-023s.jpg, 024-047s.jpg…)
    │   └── frame-strips/        ← frame-by-frame studies of key animations
    ├── 02-it-factor/
    ├── 03-top-1-percent-investors/
    ├── 04-3d-world-media-kit/
    ├── 05-modified-dca/
    ├── 06-marriage-rules/
    ├── 07-stocks-will-crash/
    ├── 08-reel-breakdown-b-content/
    ├── 09-should-i-buy-meta/
    └── 10-money-lies-parents-told-you/
```

| File | What's in it |
|---|---|
| [`01-style-guide.md`](01-style-guide.md) | The design system: the three looks, the screen zones, palette with hex values, font pairings, motion specs, a "what to show for what's said" decision table, a beat-sheet template and a build recipe |
| [`02-animation-breakdown.md`](02-animation-breakdown.md) | All 10 per-video breakdowns in one document, plus the 20 frame-level motion measurements |
| `videos/<nn-name>/` | Everything for one video. Videos 04 and 06 have no frame strips: their animations repeat patterns measured in the other videos |

## Videos analysed

| # | Topic | Length | Full-frame changes | Pace | Look |
|---|---|---|---|---|---|
| [01](videos/01-launch-behind-the-scenes/breakdown.md) | Launch behind-the-scenes | 82 s | 1 | 238 wpm | Warm creator |
| [02](videos/02-it-factor/breakdown.md) | The "it" factor | 102 s | 2 | 208 wpm | Warm creator |
| [03](videos/03-top-1-percent-investors/breakdown.md) | What the top 1% do differently | 104 s | 67 | 211 wpm | Cinematic finance |
| [04](videos/04-3d-world-media-kit/breakdown.md) | Media kit as a 3D world | 51 s | 19 | 236 wpm | Cinematic finance / tech |
| [05](videos/05-modified-dca/breakdown.md) | Modified DCA | 71 s | 16 | 265 wpm | Cinematic finance (minimal) |
| [06](videos/06-marriage-rules/breakdown.md) | Marriage rules | 70 s | 0 | 225 wpm | Warm creator (minimal) |
| [07](videos/07-stocks-will-crash/breakdown.md) | Why stocks will crash | 93 s | 44 | 230 wpm | Cinematic finance (news) |
| [08](videos/08-reel-breakdown-b-content/breakdown.md) | Reel breakdown: B content | 149 s | 2 | 215 wpm | Editorial serif |
| [09](videos/09-should-i-buy-meta/breakdown.md) | Should I buy Meta? | 56 s | 15 | 247 wpm | Editorial serif + finance |
| [10](videos/10-money-lies-parents-told-you/breakdown.md) | 4 money lies parents told you | 103 s | 29 | 185 wpm | Skit |

"Full-frame changes" counts hard cuts to a different full-screen image (B-roll, split-screen swaps). It doesn't count graphic overlays or seamless jump cuts.

## Method
- Transcription: Whisper `small.en` (sherpa-onnx), split into ~3–5 s phrases.
- Cut detection: frame-difference + luma-histogram distance at native frame rate.
- Visual inventory: 1 fps timestamped contact sheets of every video.
- Motion timing: frame-by-frame strips around 20 key animations.
- Color: pixel sampling of set, wardrobe and graphic accents.
