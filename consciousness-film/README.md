# Day 0 Until Now

A ~2-minute film about consciousness and the philosophical propositions people
have made about it — from the first light after the Big Bang to a machine
painting these words. Every frame is painted on an HTML canvas by a simulated
bristle brush written in JavaScript (no images, no video assets).

**Watch:** `day-0-until-now.mp4` (1280×720, 30 fps, ambient drone soundtrack).
Or open `index.html` in a browser to watch it render live.

| # | When | Chapter |
|---|------|---------|
| 0 | Day 0 (13.8 billion years ago) | The Beginning |
| 1 | 3.8 billion years ago | The First Flicker — life reaches for light |
| 2 | 540 million years ago | Eyes Open |
| 3 | ~40,000 years ago | A Hand on Stone — cave stencils |
| 4 | ~500 BCE | Heraclitus — everything flows |
| 5 | ~5th c. BCE | The Buddha — no fixed self (ensō) |
| 6 | ~375 BCE | Plato — the cave |
| 7 | ~300 BCE | Zhuangzi — the butterfly dream |
| 8 | 1641 | Descartes — cogito |
| 9 | 1739 | Hume — a bundle of perceptions |
| 10 | 1781 | Kant — the lens of the mind |
| 11 | 1890 | William James — the stream of consciousness |
| 12 | 1974 | Nagel — what is it like to be a bat? |
| 13 | 1995 | Chalmers — the hard problem |
| 14 | 2026 | Now — a machine paints the question |

Lines marked "paraphrase" in the film are summaries of the thinker's position,
not direct quotations.

## Re-rendering

Requires Node, [Playwright](https://playwright.dev) (Chromium) and `ffmpeg`.

```sh
node render.js                       # writes day-0-until-now.mp4
STILLS=300,1200 node render.js       # just save still-300.jpg, still-1200.jpg
```

`renderFrame(i)` is deterministic (seeded RNG per chapter), so every render is
identical.
