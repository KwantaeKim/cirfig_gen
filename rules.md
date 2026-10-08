# Drawing rules

Every circuit figure must follow these rules. Positions and sizes are in points (pt).

## Output

1. One circuit is one SVG file. Symbols, wires, junction dots, terminals and labels all live
   inside that file.
2. The SVG's `width` and `height` are in pt, and 1 viewBox unit = 1 pt.
3. Leave a 3 pt margin around the drawing, including line caps and label glyphs.

## Symbols

4. Use only the symbols in `palette/`, each at the size listed in `palette/palette.csv`.
   Never resize a symbol.
5. Every symbol's main line is 3.00 pt at its palette size, the same as a wire.
6. A horizontal flip is allowed. Never rotate a transistor, because rotation swaps drain and
   source.
7. Each VDD and GND pin gets its own VDD or GND symbol with its own short wire. Never join
   supply pins with a shared rail and a junction dot.

## Wires

8. A wire is a straight, solid black (#000000), 3.00 pt line with round caps and no arrowheads.
9. Wires are horizontal or vertical only.
10. Every wire end lands exactly on a pin or on another wire, with no gap, overshoot or
    misalignment.
11. A wire never passes through a symbol or a label.
12. Avoid wire crossings. If one is unavoidable, it gets no dot.

## Junctions and terminals

13. A junction dot is a filled black circle, 7.09 pt in diameter, centred on the point. Put one
    wherever three or more wires meet. No dot at a simple bend.
14. Every external input, output or bias terminal ends in a Voltage Node whose ring touches
    the wire end.

## Labels

15. Labels are 20 pt, black. Main letters are Bold Italic.
16. Subscripts and superscripts are upright Bold of the same family, 13.3 pt (2/3 of 20 pt),
    with their baseline 1.5 pt below the main letter's baseline, starting right after the main
    letter. Example: an italic "V" followed by an upright subscript "IN+".
17. Use the first font family in this list that is installed with both Bold Italic and Bold:
    1. Arial Narrow (the reference design)
    2. Liberation Sans Narrow (free, same character widths as Arial Narrow)
    3. Arial, Liberation Sans or Arimo (wider)
    4. Helvetica Neue, Helvetica, DejaVu Sans Condensed or DejaVu Sans

    `tools/make_glyphs.py` applies this order. Tell the user which font was used. If only a
    family from groups 3 or 4 is installed, suggest installing Liberation Sans Narrow.
18. Use a real minus sign "−", not a hyphen.
19. Labels are drawn as glyph outlines inside the SVG, so they look the same everywhere.
20. Device labels (M1, M2, …) go beside the drain/source lead on the side away from the gate,
    vertically centred on the gate line, with a 3 pt gap between the label and the lead.
    Never place a device label by the gate wire or an input pin.
21. Signal labels (VIN+, VOUT, IREF, …) go beside their terminal on the outer side, vertically
    centred on the wire, with a 3 pt gap between the label and the terminal.
22. A label never overlaps a wire, dot, symbol or another label.
