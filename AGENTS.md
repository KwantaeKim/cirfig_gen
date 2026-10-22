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
4. Write the layout to `output/<name>.json` (format below). Compute the coordinates in a
   short Python script instead of typing them: place each symbol by the point its lead must
   reach, derive every pin from the offsets below, and let the wires follow from the pins.
   Keep the script as `output/build/<name>.py` and make later edits there, then rerun it.
5. Render and check it, running from the repository root:
   `python3 tools/render.py "output/<name>.json"`
   It writes `output/<name>.svg`, prints the size in pt, and lists any wire end that misses a
   pin or wire. Fix every reported problem and render again.
6. Make a PNG preview and look at it. On macOS:
   `qlmanage -t -s 1200 -o output "output/<name>.svg"`, then rename the result from
   `<name>.svg.png` to `<name>.png`. `qlmanage` draws a square thumbnail and crops a figure
   that is wider than tall, so preview a wide figure from a temporary copy whose viewBox is
   padded to a square. `rsvg-convert -z 2.5 -b white` has neither problem if it is installed.
   Make a second, cropped preview of any dense area: a 3 pt gap is invisible at full view.
   Then go through the checklist under Quality control below.
7. Report to the user: the SVG path, its exact size in pt, the topology (which transistor does
   what, input polarity), and the check results, including every wire crossing and every
   place where a rule could not be met. Tell them to insert it at 100% and never resize it.
   A 16:9 slide is 960 × 540 pt. If the figure is wider than about 900 pt or taller than
   about 450 pt, say that it will not fit at 100% and offer a tighter layout.

When editing an existing figure, change its JSON and render again. Say whether the size
changed: if it did not, the user can use PowerPoint's Change Picture. If it did, they must
delete the old picture and insert the new one. Once the user has approved a figure, its
coordinates are frozen. A later request moves only the part it names, and everything else
keeps its exact position so that Change Picture keeps working.

Do not edit `palette/` or `rules.md` unless the user asks. Never commit `tools/glyphs.json`,
because it is derived from a font whose licence may not allow redistribution.

## Plots

`references/plots/` holds the reference plots, one folder per plot with its script and data.
They are the golden standard for the look of every graph. When the user asks for a plot,
open the closest reference, reuse its `apply_style` and `style_axis`, and keep the shared
look exactly: Arial Narrow bold labels, navy, red `#C80000` and black lines, 0.3 pt grid on
major and minor ticks, engineering tick labels through `EngFormatter`, a 4 in wide figure
saved as PNG at 300 dpi with `bbox_inches="tight"`. Every script runs on its own with
`--out fig.png` and reads its data from its own folder.

The references are examples of style, not a catalogue of allowed plots. A slide on any
topic can get a plot: an SRAM read margin against supply, a PLL phase-noise spectrum, an
LDO load-transient waveform, a mirror's output current against output voltage. Compute the
curves from the physics or from data the user gives, choose the reference whose kind of
plot is closest (a waveform, a spectrum, a Bode plot, a corner sweep, a sketch without
axes), and draw the new plot in that style. Never refuse a plot because no reference shows
that circuit.

| Folder       | Script           | What it shows |
|--------------|------------------|---------------|
| `SQNR/`      | `SQNR.py`        | Two panels, 4 × 3 in: transient waveform over an FFT spectrum, 0.7 pt lines, navy `#1A2258` and red, black and red. The reference for any waveform or spectrum |
| `SC_filter/` | `sc_filt.py`     | One panel, 3 × 3 in, log frequency axis: black 1 pt theory curve, navy `#0000C8` 0.7 pt and red 0.5 pt dashed simulated curves. The reference for any transfer function or Bode magnitude plot |
| `SC_filter/` | `sc_filt_rc.py`  | Same frame, simulated SC filter (navy 1 pt) against its RC prototype (black 1 pt dashed), no tick marks. `--band hf` or `lf` picks the data file and the capacitor |
| `resistor_corners/` | `resistor_corners.py` | 4 × 3 in, linear axes: three 1.5 pt corner lines with a marker on every point (navy diamond, black square, red triangle), 12 pt axis labels, no tick marks, no legend. The reference for any corner or sweep plot with few points |
| `sample_hold/` | `sample_hold.py` | `--fig sh` and `th`: 4 × 3 in waveform drawings with the axes off, a 1.5 pt arrow as the time axis, a navy 1.2 pt clock below the signal, the input as a 1 pt black dotted sine and the held output as 1.5 pt segments. `--fig sinc` (4 × 3 in, linear) and `sinc_log` (3 × 3 in): the zero-order-hold roll-off as a 1.5 pt black line with gray dotted guides and 8 pt labels in rounded white boxes. The reference for any waveform sketch without axes and for annotated theory curves |
| `pole_zero/` | `pole_zero.py`   | s-plane 4 × 3 in and z-plane 4 × 4 in with the region of convergence shaded. Origin axes as 1 pt black lines, no tick labels, red "x" poles, white-filled blue circles for zeros, 14 pt axis labels, 10 pt legend in a black-edged box. Poles and zeros are given as `--poles=-1+2j,-1-2j` |
| `biquad/` | `biquad.py` | `--fig q`, `step`, `family`: 4 × 3 in comparisons of second-order and sixth-order low-pass filters, 1.5 pt lines in gray tones or 1 pt lines in black, red and navy, 12 pt axis labels, the corner frequency named in a rounded white box (8 pt), 10 pt or 8 pt legend. `--fig lpf`, `hpf`, `bpf`, `notch`: one biquad response each at 6 × 4 in as a 2 pt blue line, the one reference wider than 4 in. The reference for any theory curve comparison with a legend |
| `phase_margin/` | `phase_margin.py` | 4 × 3 in, linear axes: phase margin against damping factor, exact as a 2 pt black line, the 100 ζ rule as a 1.5 pt gray dashed line, 0.8 pt dashed guides at ζ = 0.707 and 65.5° named in rounded boxes, 12 pt labels, no legend |
| `stability/` | `stability.py` | Two stacked panels, 4 × 4 in, 12 pt labels, no tick marks. `--fig bode`: loop gain over loop phase, black 1.5 pt, 0.8 pt dashed guides at the gain crossover, at −180° and at the phase there, phase ticks at −180, −90, 0. `--fig pm`: closed-loop magnitude over step response for Q = 2 (dashed) and Q = 0.5 (solid), 12 pt tick labels, 10 pt legends. The reference for any Bode pair |

Keep the plot script in `output/build/` like the layout scripts. On this computer
`/usr/bin/python3` has neither matplotlib nor pandas, so run plot scripts with
`/opt/anaconda3/bin/python3`.

Every time a plot is delivered, tell the user: paste the PNG into PowerPoint, then set its
width to 16 cm with the aspect ratio locked. That size is part of the standard. A 4 in wide
figure shown at 16 cm is enlarged about 1.6 times, so the slide shows the 0.7 pt lines at
about 1.1 pt and the 10 pt text at about 16 pt. Resizing is fine as long as the line widths
and font sizes that appear on the slide stay at those values.

The rule behind the number is 4 cm of slide width per inch of `figsize` width. A few
references are not 4 in wide and keep the 10 pt font, so they go on the slide at a
different width: the 3 in plots (`sc_filt.py`, `sc_filt_rc.py`, `sample_hold.py --fig
sinc_log`) at 12 cm and the 6 in biquad responses (`biquad.py --fig lpf`, `hpf`, `bpf`,
`notch`) at 24 cm. Tell the user the width that goes with the figure you deliver. For a
new plot, prefer a 4 in wide figure and 16 cm. If another width W in inches is needed,
either paste it at 4 × W cm, or keep 16 cm and scale the line widths to 0.7 × W/4 pt and
the font size to 10 × W/4 pt so that the slide shows the same sizes.

## Quality control

The renderer only checks that wire ends land on pins or wires. Everything else is on you.

- Netlist first. Before placing anything, write the netlist in your reply: every device with
  its gate, drain and source nets, every terminal, and the input polarity. Build the wires from
  it. After rendering, read the preview back against the netlist device by device. Nothing
  else catches a wrong topology.
- Ask once when the request leaves a real choice, such as the input device type, the number
  of stages, or single-ended against differential. Offer two or three options with a
  recommended default, then proceed. Do not ask about things the rules already decide.
- Every SVG in `output/` comes out of `tools/render.py`. Never hand-write an SVG, never edit
  one, and never patch a coordinate in it. Fix the JSON and render again.
- Dots: one exactly where three or more wires or pins meet, and nowhere else. Count them in
  the preview and make sure none sits on a crossing or a bend.
- Labels: the renderer does not check overlaps. Compute each label's width the way
  `render.py` does (the glyphs' `adv` × size / upm from `tools/glyphs.json`), have the script
  print the label boxes, and keep 3 pt between each box and every wire, symbol and other
  label.
- Supplies and tails follow rules 8 and 14 exactly: VDD directly on the pin, GND on a 13.5 pt
  wire, and one horizontal tail wire that ends on both source pins.
- Match `references/`. Before a new layout, open the closest figure there and reuse its
  spacings: device pitch, wire length between stacked devices, label gaps. Figures that go
  into one deck share the same spacings.
- Fit the slide. The reference figures are 180 to 465 pt wide. When a circuit would need more
  than about 900 pt, choose a tighter layout before drawing it in full (one representative
  cell, fewer stages, folded routing) and say what you left out.
- Tidy output. `output/` holds `<name>.json`, `<name>.svg` and `<name>.png` per figure, plus
  `output/build/` for the scripts. Delete crops, `.svg.png` duplicates, QA iterations and
  any fallback drawings before reporting.

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
| Current Arrow  | 14.10 × 26.00  | no pins. A free-standing arrow pointing down (3 pt shaft, filled head as on the Summer), placed beside a wire with a 3 pt gap to mark a current direction. It is never part of a wire |
| Current Arrow H | 26.00 × 14.10 | no pins. The same arrow pointing right; flip it to point left |
| NPN            | 42.00 × 53.40  | base (3.999, 26.700), collector top (38.001, 4.003), emitter bottom (38.001, 49.397) |
| PNP            | 42.01 × 53.36  | base (3.999, 26.671), emitter top (38.010, 4.000), collector bottom (38.010, 49.344) |
| VDD            | 22.90 × 16.70  | pin (11.447, 14.905), the bottom of the stem |
| GND            | 14.80 × 14.60  | pin (7.400, 1.799), the middle of the top bar |
| Voltage Node   | 12.60 × 12.60  | centre (6.300, 6.300). A wire ends on the ring's centre line, 4.053 from the centre. The ring's outer edge is 5.551 from the centre. |

NMOS and PMOS gates are on the left and the drain/source leads on the right. Flip a
transistor to put its gate on the right. The PMOS gate pin is the left edge of its bubble.
