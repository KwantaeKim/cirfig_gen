# Instructions for coding agents

This repository draws analog circuit schematics as single SVG files for slides.
When the user asks for a circuit, follow this workflow.

## Workflow

0. First time only: if `tools/glyphs.json` does not exist, build it from the fonts installed
   on this computer with `python3 tools/make_glyphs.py`. It needs fontTools: if it is missing,
   ask the user before running `pip install fonttools`. Tell the user which font was chosen.
   If it is not Arial Narrow or Liberation Sans Narrow, suggest installing Liberation Sans
   Narrow (free) and running the script again.
1. Read `rules.md`. Every rule there is mandatory.
2. Pick symbols from `palette/palette.csv`. Use each at exactly its `width_pt` × `height_pt`.
3. Work out every pin from the symbol SVG in `palette/`:
   pin = (left + x × scale, top + y × scale), where (x, y) is the end of the lead in the SVG
   and scale = `width_pt` / SVG viewBox width. For a flipped symbol, the x offset becomes
   `width_pt` − x × scale. The pins of the most common symbols are listed below.
4. Write the layout to `output/<name>.json` (format below). Choose coordinates so that every
   wire end lands exactly on a pin or another wire.
5. Render and check it, running from the repository root:
   `python3 tools/render.py "output/<name>.json"`
   It writes `output/<name>.svg`, prints the size in pt, and lists any wire end that misses a
   pin or wire. Fix every reported problem and render again.
6. Make a PNG preview and look at it. On macOS:
   `qlmanage -t -s 1200 -o output "output/<name>.svg"`, or use `rsvg-convert` if available.
   Check the rules a renderer cannot check: label placement, overlaps, crossings and
   overall readability.
7. Report to the user: the SVG path, its exact size in pt, the topology (which transistor does
   what, input polarity), and the check results. Tell them to insert it at 100% and never
   resize it.

When editing an existing figure, change its JSON and render again. Say whether the size
changed: if it did not, the user can use PowerPoint's Change Picture. If it did, they must
delete the old picture and insert the new one.

Do not edit `palette/` or `rules.md` unless the user asks. Never commit `tools/glyphs.json`,
because it is derived from a font whose licence may not allow redistribution.

## Layout JSON

```json
{
  "name": "PMOS-input Current-Mirror OTA",
  "symbols": [{"id": "M1", "type": "PMOS", "left": 122.8699, "top": 185.9232, "flip": false}],
  "wires":   [[160.0, 170.1733, 160.0, 188.1733]],
  "dots":    [[220.0, 170.1733]],
  "labels":  [{"runs": [["M", "main"], ["1", "sub"]], "x": 164.5, "y": 214.1319, "align": "left"}]
}
```

- `type` is a `name` from `palette/palette.csv`. `flip` mirrors the symbol horizontally.
- `wires` are `[x1, y1, x2, y2]`, horizontal or vertical. The only diagonals are the two
  crossing wires of a cross-coupled pair (see `references/`).
- A label's `x` is its left edge (`"align": "left"`) or right edge (`"align": "right"`), and
  `y` is the line it is vertically centred on. `"main"` runs are italic, `"sub"` runs are
  upright subscripts. Use "−" (U+2212) for minus.
- The frame is arbitrary. The renderer adds the 3 pt margin.
- Generated figures go in `output/`.

## Common pins

Offsets in pt from the symbol's top-left corner, unflipped. For a flipped symbol use
x' = width − x.

| Symbol         | Size (pt)      | Pins |
|----------------|----------------|------|
| NMOS           | 39.40 × 56.60  | gate (2.251, 28.296), drain (37.149, 2.252), source (37.149, 54.348) |
| PMOS           | 39.38 × 56.56  | gate (2.250, 28.209), source (37.130, 2.250), drain (37.130, 54.310) |
| Current Source | 35.14 × 35.14  | top (17.570, 2.250), bottom (17.570, 32.890) |
| Voltage Source | 35.14 × 35.14  | + top (17.570, 2.250), − bottom (17.570, 32.890). DC source, + on top |
| Voltage Source H | 35.14 × 35.14 | + left (2.250, 17.570), − right (32.890, 17.570). The same source lying down; flip it to put + on the right |
| Voltage Source Inv | 35.14 × 35.14 | − top (17.570, 2.250), + bottom (17.570, 32.890). The upright source with − on top, since symbols cannot be flipped vertically |
| Diode H        | 47.92 × 27.04  | anode left (4.000, 13.533), cathode right (43.920, 13.533). The Diode lying down, pointing right. Flip it to point left |
| VDD            | 22.90 × 16.70  | pin (11.447, 14.905), the bottom of the stem |
| GND            | 14.80 × 14.60  | pin (7.400, 1.799), the middle of the top bar |
| Voltage Node   | 12.60 × 12.60  | centre (6.300, 6.300). A wire ends on the ring's centre line, 4.053 from the centre. The ring's outer edge is 5.551 from the centre. |

NMOS and PMOS gates are on the left and the drain/source leads on the right. Flip a
transistor to put its gate on the right. The PMOS gate pin is the left edge of its bubble.
