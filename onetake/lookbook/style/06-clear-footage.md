# Clear, real-looking footage without filters

Studied from 5 reels by a creator the user admires (same Samsung phone, no filters). Measured at 720 px wide
(`python3 -m engine footage-check`):

| | his reels | the user's indoor clip |
|---|---|---|
| brightness | ~117 | ~118 (same) |
| contrast | 61–69 | 39 (flat) |
| fine detail | 300–600 | 50 (soft) |
| HDR video | off | on |

His videos were posted at 720p and only 1–2.4 Mbps on Instagram, so the clarity is not from the file or an edit:
it's how they're **filmed**.

## What he does
1. **Daylight on the face.** Next to big windows or outside in open shade/sun, the light coming from the front or
   side of the face. Light is what makes a phone video sharp: in dim rooms the phone smooths away noise and detail.
2. **A background with depth and texture.** Streets, a lit room, windows, shelves, a studio wall with wood slats,
   a few metres behind him. Never a plain wall right behind the head (flat, nothing for the camera to resolve).
3. **The back (main) camera,** held at chest height or set on a tripod a little below the eyes. Much sharper than
   the selfie camera.
4. **HDR video off**, plain FHD/4K. Instagram shows standard video truer than HDR.
5. A clip-on mic (clear sound makes the whole video feel higher quality).

## The user's camera checklist (Samsung)
- Camera → Settings → Advanced video options → **HDR10+ video: OFF**.
- Video size **4K 30** if there's room on the phone (sharper even after Instagram), else **FHD 30**.
- **Back camera**, lens wiped. Face a window or film outside in open shade.
- Space behind you: a room, plants, shelves, a street; not a wall close behind.
- Tap your face on screen to focus; if skin looks shiny/white, drag the brightness sun down a touch.

One Take never adds a filter by default; `footage-check` runs at every import and says what to change next time.
