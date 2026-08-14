# Escape to Scott Lake

A pseudo-3D highway hallucination. You start in **Detroit** or **Chicago** and drive 120 miles
to **Bloomingdale, Michigan**, where Scott Lake and a gassed-up pontoon are waiting. An
unlicensed army of furious toddlers would prefer that you didn't.

Open `index.html` in any browser. No build, no dependencies, no assets — every sprite,
sound and pixel of scenery is generated at runtime.

## Controls

| Key | Action |
| --- | --- |
| `←` `→` / `A` `D` | Steer |
| `↑` / `W` | Gas |
| `↓` / `S` | Brake |
| `Space` | Throw snacks (pacifies a toddler into a butterfly) |
| `Z` | Naptime bomb — pacifies everything on screen |
| `T` | Cycle trip intensity: mild → full melt → **calm mode** |
| `M` | Mute |
| `P` / `Esc` | Pause |

Touch controls appear automatically on coarse-pointer devices.

## Rules of the road

- **Time** is the hard limit. You start with 70 seconds; every 20-mile checkpoint adds 34
  seconds and mends one point of patience.
- **Patience** is your health — four points. Toddlers, LEGO and off-road excursions cost you.
- **Snacks** are ammunition. Juice boxes restock them, coffee buys time and a speed boost,
  pacifiers restore patience.
- Three **MEGA TODDLERS** block the road at miles 30, 62 and 92. Nine snack hits pacifies one.
  You can also thread the shoulder past it, if you like living that way.
- The **trip meter** fills while you hold high speed. A fuller meter means a wilder screen —
  and it never affects the hitboxes, only the hallucination.

## Routes

- **Detroit** — I-94 west through Ann Arbor, Jackson, Battle Creek, Kalamazoo. More debris,
  slower toddlers.
- **Chicago** — I-94 east through Gary, Michigan City, Benton Harbor, Hartford. Cleaner
  pavement, considerably faster babies.

## Accessibility

The default look involves sustained flashing color, hue cycling and screen warp. `T` cycles
to **calm mode**, which keeps the full game but drops the melt, the feedback bloom and the
hue rotation, and flattens the palette. `prefers-reduced-motion` also damps the interface
animations.

## How it works

- **Road** — a segment-based pseudo-3D projection (the classic Out Run technique): each
  segment is projected from camera space to screen space, drawn back-to-front, with hills
  clipping the segments behind them.
- **Sprites** — every toddler, tree, sign and van is a procedural canvas drawing scaled by
  its segment's projection factor.
- **Sky** — a per-frame plasma field computed at 112×72 and stretched over the canvas.
- **Post** — the scene renders to an offscreen canvas, is laid down opaque, re-blitted as
  sine-offset horizontal slices, then screen-composited with a zoomed copy of the previous
  frame for the tunnel smear. Hue drift is a CSS filter on the canvas element.
- **Audio** — WebAudio only: a filtered sawtooth engine tracking speed, a 16th-note pentatonic
  arpeggio with kick and hats, and noise-burst screams.
