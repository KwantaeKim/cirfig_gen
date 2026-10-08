# <img src="https://raw.githubusercontent.com/KwantaeKim/KwantaeKim.github.io/main/favicon-rounded.png" height="40" align="top" alt=""> cirfig_gen

Clean analog circuit schematics for slides, drawn by a coding agent.

You describe a circuit in plain words. Claude Code or Codex lays it out from a fixed palette
of symbols, checks it against the drawing rules, and gives you one SVG file to drop into
PowerPoint, Keynote or any slide tool.

![PMOS-input current-mirror OTA](output/PMOS-input%20Current-Mirror%20OTA.png)

## Why one SVG per circuit

If a schematic is built from separate pictures and lines in PowerPoint, the PDF export shifts
every object by its own small amount, up to about 0.4 pt. Wires and symbol leads then no longer
line up. A single SVG per circuit keeps every line exactly aligned, on screen and in the PDF.

## How to use

1. Clone the repository and open the folder in Claude Code or Codex:

   ```
   git clone https://github.com/KwantaeKim/cirfig_gen.git
   cd cirfig_gen
   claude        # or: codex
   ```

2. Ask for a circuit, for example:

   > Draw a PMOS-input current-mirror OTA.

   > Draw an NMOS current mirror with a reference current source and an output terminal.

   The agent picks up its instructions from `AGENTS.md` by itself. You don't need to open any
   other file. It saves `output/<name>.svg` with a PNG preview, and tells you the exact size.

3. Insert the SVG into your slide (drag it in, or **Insert → Pictures → Picture from File**).
   Check that its size matches the reported width × height, then only move it.
   **Never resize it.** Resizing scales every line width.

4. To change something, ask the agent ("move the M5 label", "add a cascode", "make it
   narrower"). It updates the figure and tells you whether the size changed:
   - Same size: right-click the picture → **Change Picture**. It keeps its place.
   - Size changed: delete the old picture and insert the new one. (Change Picture would
     stretch it to the old size and change the line widths.)

If a figure is too big for your slide, ask for a tighter layout instead of scaling it down.

## What's in the repository

| Path                  | Contents |
|-----------------------|----------|
| `AGENTS.md`           | Instructions the agent follows (`CLAUDE.md` points to it) |
| `rules.md`            | Drawing rules every figure must follow |
| `palette/`            | The 49 symbol SVGs |
| `palette/palette.csv` | Each symbol's size on the slide and its line widths |
| `tools/render.py`     | Turns a layout (JSON) into one SVG and checks it |
| `tools/make_glyphs.py`| Builds the label letter outlines from a font on your computer |
| `output/`             | Generated figures: SVG, PNG preview and the editable JSON layout |

## Fonts

No font is included. On first use, the agent runs `tools/make_glyphs.py`, which picks the best
font installed on your computer and saves its letter outlines to `tools/glyphs.json`:

1. **Arial Narrow**, the reference design. It comes with Microsoft Office.
2. **Liberation Sans Narrow**, free, with the same character widths as Arial Narrow.
3. Wider fallbacks: Arial, Liberation Sans, Arimo, Helvetica, DejaVu Sans.

Main letters use the Bold Italic style and subscripts the upright Bold style. The labels are
drawn as outlines inside each SVG, so a figure looks the same on every computer once it's made.

To choose the fonts yourself:

```
python3 tools/make_glyphs.py <bold-italic font file> <bold font file>
```

`tools/glyphs.json` is derived from your fonts, so it isn't committed (see `.gitignore`).

## Requirements

- Python 3. The renderer uses only the standard library.
- `fonttools` (`pip install fonttools`), once, for `tools/make_glyphs.py`.
- Arial Narrow or Liberation Sans Narrow installed, for the intended look.
- A PNG previewer for the agent to look at its work: `qlmanage` (built into macOS) or
  `rsvg-convert`.

## License

MIT. See [LICENSE](LICENSE).
