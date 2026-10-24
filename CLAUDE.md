@AGENTS.md

# Working preferences for this repository

These complement `AGENTS.md` and apply to every reply and every file written here.

## Writing style

- Do not use a hyphen or dash to connect sentences or phrases. Use a period, comma or
  conjunction instead. Joining nouns with a hyphen is fine: "cross-coupled pair",
  "current-mirror load".
- Do not use a semicolon to connect sentences or phrases. Inside code it is fine.
- Write "layout" as one word, also as a verb: "layout the differential pair".
- No slogans, taglines or catchy headlines, anywhere: not on figures or plots, and not in the
  README, docstrings, commit messages or replies. State what a thing does in plain words
  ("renders one SVG per circuit"), never sell it ("pixel-perfect schematics in seconds").
- Never invent a title. Figures and plots have no title, and a headline exists only when I
  ask for one and give its wording.

## Files

- Change an existing text file (Markdown, JSON, Python) with the Edit or Write tool, never by
  rewriting it from Bash with `sed -i`, a heredoc or a script. A Bash rewrite bypasses the
  editor, and a file open in VS Code then reports "The content of the file is newer". The one
  exception is a build script in `output/build/` regenerating its own `output/<name>.json`.
- Keep temporary files inside this project, in `output/build/`, never in a system temp folder.
- A file I edited by hand is the master. If `output/<name>.json` changed since its build
  script last wrote it, read it first and carry my edits into `output/build/<name>.py`
  before rerunning the script, so they are not overwritten.
- Never open PowerPoint or any other application that holds a deck. The decks in `output/`
  are edited in parallel. Work on files only and render previews to PNG.

## Slides and figures

- Labeled boxes are not a visualization and are not allowed: no icon plus number plus
  caption tiles, no cards holding facts, no process flows drawn as chains of rounded text
  blocks. Even when a spec asks for them, turn the spec into a drawing.
- Draw the mechanism, not the verdict. Show what actually happens in the circuit or system,
  such as the real waveform, the current path, or the node that moves. A badge or a word
  that only states the outcome is too simplified.
- Test: hide all text. The slide must still tell the story. Text is only a short label of
  one to three words on the picture.
- No explanatory phrases on the picture. If a label needs a verb, replace it with a visual
  and put the explanation in the speaker notes.
- On a plot, mark the key point with a dot, a dotted guide line and a short label. Extend a
  projection far enough that the key point is visible.
- Physics must be right. Simplify, but never draw something false. When the physics of a
  picture is unclear, state it in one sentence before drawing.

## Working together

- Work incrementally. One change per round, with a preview.
- Once a figure is approved, freeze it. Later requests change only what they name.
- When a direction is rejected, revert it fully and try a different idea, not a variation
  of the same one.
