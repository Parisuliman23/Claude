# B-roll that shows what's said (practice run on the TSMC reel, Nov 22 2026)

The user: "don't just put up random construction videos… choose more specific videos and images related to the topic."

## What went wrong (TSMC reel, graded shot by shot)
| Said | Clip used | Really shows | Grade | Should have been |
|---|---|---|---|---|
| "TSMC are the ones manufacturing the chips" | robotic-arm-factory-12041 | a worker under heavy machinery (looks like construction) | ❌ | a photo of a TSMC fab (commons-find "TSMC fab"), a wafer close-up, the TSMC logo on a white panel |
| "TSMC operates … a semiconductor foundry" | silicon-wafer-clean-room-worker-267359 | a textile-style production line | ❌ | TSMC fab photo / clean-room photo (Commons), or the term on a white panel |
| "somebody's gotta make them" | silicon-wafer-clean-room-worker-271463 | women on a textile-style line | ⚠️ generic | same as above |
| "guess which AI application wins" | slot-machine-casino-spinning-38388 | a blurry car dashboard | ❌ | a real slot machine / roulette, or a "?" panel with AI app logos |
| "extreme precision" | microscope-laboratory-precision | a biology lab | ⚠️ | a wafer / chip macro shot, or ASML machine photo |
| "AI" (in the list) | KUKA robot arms | robots | ⚠️ | data-center / GPU photo |
| "cars" | modern-car-driving-road-52943 | empty street, car tiny | ⚠️ | modern-car-driving-road-184734 (car clearly visible) |
| "NVIDIA designed… chips" | chip close-ups | chips | ✅ | (an NVIDIA GPU photo would be even better) |
| "AI supply chain" / "high demand compute" | data-center-server-room | servers | ✅ | |
| "$80,000" | money bundles | money | ✅ | |

## Root cause
Clips were named after the SEARCH WORDS, Pixabay returned off-topic clips, and later picks trusted the filename.
Fixed: new downloads are named `pixabay-<id>.mp4`, and `library/broll/index.json` says what each clip REALLY shows.

## The rules (follow on every reel)
1. **Pick by what's on screen, never by filename**: `python3 -m engine broll-index "words"` searches the checked
   descriptions. A clip marked `avoid`, or whose `not_for` matches, is never used.
2. **Every new clip is looked at before use** (`broll-check`), then described (`broll-describe FILE --json '{"shows": …}'`).
   If it doesn't clearly show the words, don't place it.
3. **Specific beats generic.** Named company → its logo (`logo_row`), a real photo of its HQ/fab/product
   (`commons-find "TSMC fab"`), or its stock chart. Named person → their photo + name label. A number → a counter.
   Generic stock footage only for metaphors and feelings ("panic", "a plan").
4. **Never "close enough"**: no random factory, construction, office or crowd shots for a specific claim. If nothing
   specific exists, use a white panel with the key words, a logo or a chart instead of a vague clip.
5. **Industry words**: chips / semiconductors / foundry / wafers → chip or wafer macro shots, a fab or clean-room
   PHOTO, never a generic production line. AI → data centers / GPUs / servers, not industrial robots.

## Order of choice (user, Nov 22 2026)
1. **The exact thing** if we have it or can get it (TSMC's own fab photo, Jensen Huang's photo, the NVDA chart): search
   `broll-index "TSMC"` and `commons-find "TSMC fab"` first.
2. Otherwise the **same category** (another chipmaker's fab, any data center…), as below.
3. Otherwise a panel with the words, a logo or a chart. Never a vague clip.

## Same CATEGORY is enough when the exact thing isn't available
"It doesn't have to be the exact TSMC factory, another chipmaker's factory is fine, just keep it similar."
| They say… | Show |
|---|---|
| a chipmaker (TSMC, Intel fabs, Samsung…) / "manufacture the chips" / foundry | any chip fab, clean room, wafer, lithography machine |
| AI | AI factories / data centers / GPU racks |
| compute | servers, GPUs, data-center racks |
| data center | a data center |
| a price, a run-up, a crash, "investors love this stock" | a real chart: `price-fetch TICKER 1y` + `stock_chart` |
| cars / phones / electronics | that product clearly in shot |
