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
7. Each VDD and GND pin gets its own VDD or GND symbol. Never join supply pins with a shared
   rail and a junction dot.
8. A VDD symbol sits directly on the transistor pin it supplies, with no wire in between: the
   bottom of its stem is the pin. A GND symbol hangs on a 13.5 pt vertical wire below its
   pin. A symbol with horizontal leads (a capacitor or resistor) reaches its supply through a
   wire that bends once and runs 13.5 pt to the VDD or GND symbol.

## Wires

9. A wire is a straight, solid black (#000000), 3.00 pt line with no arrowheads. Each end gets
   its cap from what it touches:

   | The end touches | Cap |
   |-----------------|-----|
   | A straight edge: the side of a rectangle, plate or bar, or a pin that sits on one, such as the GND pin | Butt, flush with the edge |
   | A straight edge outside the figure, listed in the JSON | Butt, flush with the edge |
   | Another wire (a corner or T) or a dot | Round |
   | The free end of a lead: the transistor, capacitor, resistor and VDD pins | Round |
   | A circle or ring: a source, the PMOS bubble, a Voltage Node | Round |
   | The inside of a face, short of its edge, or nothing (a free end) | Round |

   Either way, the visible end sits exactly where the wire must stop. A butt end keeps its
   endpoint on the edge. A round cap reaches half the stroke width (1.5 pt) past the endpoint, so
   a round end that must stop at a given point has its endpoint pulled back by 1.5 pt. On a pin
   or another wire the endpoint stays on it (rule 11), because the cap then lies over the joint.
   `tools/render.py` picks each cap.
10. Wires are horizontal or vertical only, with one exception: the cross-coupling of a
    cross-coupled pair is a symmetric X. Each side leaves its node on a horizontal wire, runs
    diagonally across the centre line to the other device's gate wire, and the two diagonals
    cross once, with no dot.
11. Every wire end lands exactly on a pin or on another wire, with no gap, overshoot or
    misalignment.
12. A wire never passes through a symbol or a label.
13. Avoid wire crossings. If one is unavoidable, it gets no dot.
14. The common node of a differential pair (the tail) is one horizontal wire that ends
    directly on both source pins, with no vertical wire between it and either pin.

## Junctions and terminals

15. A junction dot is a filled black circle, 7.09 pt in diameter, centred on the point. Put one
    wherever three or more wires meet. No dot at a simple bend.
16. Every external input, output or bias terminal ends in a Voltage Node whose ring touches
    the wire end.

## Labels

17. Labels are 20 pt, black. Main letters are Bold Italic.
18. Subscripts and superscripts are upright Bold of the same family, 13.3 pt (2/3 of 20 pt),
    with their baseline 1.5 pt below the main letter's baseline, starting right after the main
    letter. Example: an italic "V" followed by an upright subscript "IN+".
19. Use the first font family in this list that is installed with both Bold Italic and Bold:
    1. Arial Narrow (the reference design)
    2. Liberation Sans Narrow (free, same character widths as Arial Narrow)
    3. Arial, Liberation Sans or Arimo (wider)
    4. Helvetica Neue, Helvetica, DejaVu Sans Condensed or DejaVu Sans

    `tools/make_glyphs.py` applies this order. Tell the user which font was used. If only a
    family from groups 3 or 4 is installed, suggest installing Liberation Sans Narrow.
20. Use a real minus sign "−", not a hyphen.
21. Labels are drawn as glyph outlines inside the SVG, so they look the same everywhere.
22. Device labels (M1, M2, …) go beside the drain/source lead on the side away from the gate,
    vertically centred on the gate line, with a 3 pt gap between the label and the lead.
    Never place a device label by the gate wire or an input pin.
23. Signal labels (VIN+, VOUT, IREF, …) go beside their terminal on the outer side, vertically
    centred on the wire, with a 3 pt gap between the label and the terminal.
24. A label never overlaps a wire, dot, symbol or another label.

## Placement

25. A resistor in parallel with a current source (a Norton equivalent) sits straight under the
    source, in the same column. The node between them is a junction, and the output wire runs
    from it to the terminal.
26. A source or resistor standing between the output row and GND sits in the middle of that
    height, with an equal wire above and below it (13.5 pt each, as the GND wire of rule 8).
27. Circuits shown side by side or on consecutive slides share the output row and the GND
    level. Their figures share one vertical frame, so they line up when placed at the same y.
28. When a lead is too short for a Current Arrow and its 3 pt gaps, the arrow goes beside the
    device body, with its label on the outer side of the arrow.
