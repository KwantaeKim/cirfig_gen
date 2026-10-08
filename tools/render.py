"""Render a circuit layout (JSON) into one SVG, following rules.md.

Usage (from the repository root):
    python3 tools/render.py output/<name>.json

Layout JSON (all numbers in pt, in any frame; the SVG gets a 3 pt margin automatically):
{
  "name": "PMOS-input OTA",
  "symbols": [{"id": "M1", "type": "PMOS", "left": 62.87, "top": 132.75, "flip": false}],
  "wires":   [[x1, y1, x2, y2], ...],
  "dots":    [[x, y], ...],
  "labels":  [{"runs": [["M", "main"], ["1", "sub"]], "x": 104.5, "y": 160.96, "align": "left"}]
}
"type" is a name from palette/palette.csv. "flip" mirrors the symbol horizontally.
A label's "x" is its left edge (align "left") or right edge (align "right"), and "y" is the
line it is vertically centred on.
"""
import csv
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MARGIN = 3.0
WIRE_W = 3.0
DOT_D = 7.09
MAIN_SIZE, SUB_SIZE, SUB_DROP = 20.0, 20.0 * 2 / 3, 1.5
f = lambda v: '%.3f' % v


def palette_table():
    with open(os.path.join(ROOT, 'palette', 'palette.csv'), encoding='utf8') as fh:
        return {r['name']: (r['file'], float(r['width_pt']), float(r['height_pt'])) for r in csv.DictReader(fh)}


def parse_path(d):
    """Absolute SVG path (M L H V Q C Z, implicit repeats) -> list of (cmd, [points])."""
    toks = re.findall(r'[MLHVQCZmlhvqcz]|-?\d*\.?\d+(?:e-?\d+)?', d)
    out, i, cmd, cur = [], 0, None, (0.0, 0.0)
    need = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'Q': 4, 'C': 6}
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            if t.islower():
                raise ValueError('relative path commands are not supported: %s' % t)
            cmd = t; i += 1
            if cmd == 'Z':
                out.append(('Z', [])); continue
        n = need[cmd]
        v = [float(x) for x in toks[i:i + n]]; i += n
        if cmd == 'H': pts = [(v[0], cur[1])]; c = 'L'
        elif cmd == 'V': pts = [(cur[0], v[0])]; c = 'L'
        else: pts = [(v[k], v[k + 1]) for k in range(0, n, 2)]; c = cmd
        out.append((c, pts)); cur = pts[-1]
        if cmd == 'M': cmd = 'L'                      # implicit lineto after moveto
    return out


class Fig:
    def __init__(self):
        self.els, self.pts, self.pins, self.edges = [], [], [], []

    def extent(self, x, y, pad=0.0):
        self.pts += [(x - pad, y - pad), (x + pad, y + pad)]

    def path(self, segs, style, pad):
        d = []
        for c, pts in segs:
            d.append(c + ''.join(' %s %s' % (f(x), f(y)) for x, y in pts))
            for x, y in pts:
                self.extent(x, y, pad)
        self.els.append('<path d="%s" %s/>' % (' '.join(d), style))


def style_of(a, sx):
    get = lambda k: (re.search(r'\b%s="([^"]*)"' % k, a) or [None, None])[1]
    s = 'fill="%s"' % (get('fill') or '#000000')
    sw = 0.0
    if get('stroke') and get('stroke') != 'none':
        sw = float(get('stroke-width') or 1) * sx
        s += ' stroke="%s" stroke-width="%s" stroke-linecap="%s" stroke-linejoin="%s"' % (
            get('stroke'), f(sw), get('stroke-linecap') or 'butt', get('stroke-linejoin') or 'miter')
        if get('stroke-dasharray'):
            s += ' stroke-dasharray="%s"' % ' '.join(f(float(v) * sx) for v in re.split(r'[ ,]+', get('stroke-dasharray').strip()))
    return s, sw


def place_symbol(fig, sym, table):
    fname, w, h = table[sym['type']]
    svg = open(os.path.join(ROOT, 'palette', fname), encoding='utf8').read()
    vx, vy, vw, vh = (float(v) for v in re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', svg).groups())
    sx, sy = w / vw, h / vh
    L, T, flip = sym['left'], sym['top'], sym.get('flip', False)
    X = lambda px: L + w - (px - vx) * sx if flip else L + (px - vx) * sx
    Y = lambda py: T + (py - vy) * sy
    for m in re.finditer(r'<(path|circle|rect)\b([^>]*)/?>', svg):
        kind, a = m.groups()
        style, sw = style_of(a, sx)
        num = lambda k: float(re.search(r'\b%s="([^"]*)"' % k, a).group(1))
        if kind == 'path':
            segs = [(c, [(X(x), Y(y)) for x, y in pts]) for c, pts in parse_path(re.search(r'\bd="([^"]*)"', a).group(1))]
            fig.path(segs, style, sw / 2)
            prev = None
            for c, pts in segs:                                   # path vertices and straight edges can be pins
                fig.pins += pts
                if c == 'L' and prev:
                    fig.edges.append((prev, pts[-1]))
                prev = pts[-1] if pts else prev
        elif kind == 'circle':
            cx, cy, r = X(num('cx')), Y(num('cy')), num('r') * sx
            fig.els.append('<circle cx="%s" cy="%s" r="%s" %s/>' % (f(cx), f(cy), f(r), style))
            fig.extent(cx, cy, r + sw / 2)
            fig.pins += [(cx - r, cy), (cx + r, cy), (cx, cy - r), (cx, cy + r)]
        else:
            x0, x1 = sorted((X(num('x')), X(num('x') + num('width'))))
            y0 = Y(num('y'))
            rx = float((re.search(r'\brx="([^"]*)"', a) or [0, 0])[1]) * sx
            fig.els.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>'
                           % (f(x0), f(y0), f(x1 - x0), f(num('height') * sy), f(rx), style))
            fig.extent(x0, y0); fig.extent(x1, y0 + num('height') * sy)


def place_label(fig, lab, G):
    # main letters: bold italic font; subscripts: the matching upright bold font
    face = lambda kind: (G['italic'], G['upm_italic']) if kind == 'main' else (G['upright'], G['upm_upright'])
    runs = [(ch, kind) for text, kind in lab['runs'] for ch in text]
    size = lambda kind: MAIN_SIZE if kind == 'main' else SUB_SIZE
    width = sum(face(k)[0]['glyphs'][ch]['adv'] * size(k) / face(k)[1] for ch, k in runs)
    x = lab['x'] if lab.get('align', 'left') == 'left' else lab['x'] - width
    base = lab['y'] + G['italic']['cap_height'] * MAIN_SIZE / G['upm_italic'] / 2   # centre the capitals on y
    for ch, kind in runs:
        fc, upm = face(kind)
        g, s = fc['glyphs'][ch], size(kind) / upm
        b = base + (SUB_DROP if kind == 'sub' else 0)
        segs = []
        for c in g['path']:
            if c[0] == 'Z':
                segs.append(('Z', [])); continue
            pts = [(x + s * c[k], b - s * c[k + 1]) for k in range(1, len(c), 2)]
            segs.append((c[0], pts))
        if segs:
            fig.path(segs, 'fill="#000000"', 0)
        x += g['adv'] * s


def on_segment(p, a, b, eps=0.01):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > eps * max(1, math.hypot(bx - ax, by - ay)):
        return False
    return min(ax, bx) - eps <= px <= max(ax, bx) + eps and min(ay, by) - eps <= py <= max(ay, by) + eps


def crosses(a, b):
    """True if wires a and b ([x1, y1, x2, y2]) cross at a point inside both."""
    side = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    p1, p2, q1, q2 = a[:2], a[2:], b[:2], b[2:]
    return side(p1, p2, q1) * side(p1, p2, q2) < 0 and side(q1, q2, p1) * side(q1, q2, p2) < 0


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path, encoding='utf8'))
    table = palette_table()
    glyph_file = os.path.join(HERE, 'glyphs.json')
    if not os.path.exists(glyph_file):
        sys.exit('tools/glyphs.json is missing. Run: python3 tools/make_glyphs.py')
    G = json.load(open(glyph_file))
    fig, problems = Fig(), []

    # a diagonal wire is allowed only as half of a cross-coupling X: it must cross another diagonal
    diagonals = [w for w in spec['wires'] if w[0] != w[2] and w[1] != w[3]]
    for d in diagonals:
        if not any(e is not d and crosses(d, e) for e in diagonals):
            problems.append('diagonal wire %s is not half of a cross-coupling X' % d)
    for x1, y1, x2, y2 in spec['wires']:
        fig.path([('M', [(x1, y1)]), ('L', [(x2, y2)])],
                 'fill="none" stroke="#000000" stroke-width="%s" stroke-linecap="round"' % f(WIRE_W), WIRE_W / 2)
    wire_els = len(fig.els)
    for sym in spec['symbols']:
        place_symbol(fig, sym, table)
    for x, y in spec['dots']:
        fig.els.append('<circle cx="%s" cy="%s" r="%s" fill="#000000"/>' % (f(x), f(y), f(DOT_D / 2)))
        fig.extent(x, y, DOT_D / 2)
    for lab in spec.get('labels', []):
        place_label(fig, lab, G)

    # every wire end must sit on a symbol pin or on another wire
    wires = spec['wires']
    for i, (x1, y1, x2, y2) in enumerate(wires):
        for p in ((x1, y1), (x2, y2)):
            ok = any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for q in fig.pins)
            ok = ok or any(on_segment(p, a, b) for a, b in fig.edges)
            ok = ok or any(j != i and on_segment(p, (w[0], w[1]), (w[2], w[3])) for j, w in enumerate(wires))
            if not ok:
                problems.append('wire end %s is not on a pin or wire' % (tuple(round(v, 3) for v in p),))

    xs, ys = [p[0] for p in fig.pts], [p[1] for p in fig.pts]
    x0, y0 = min(xs) - MARGIN, min(ys) - MARGIN
    W, H = max(xs) + MARGIN - x0, max(ys) + MARGIN - y0
    out = os.path.splitext(spec_path)[0] + '.svg'
    with open(out, 'w', encoding='utf8') as o:
        o.write('<svg xmlns="http://www.w3.org/2000/svg" width="%spt" height="%spt" viewBox="%s %s %s %s">\n'
                % (f(W), f(H), f(x0), f(y0), f(W), f(H)))
        # wires first, then symbols (their white fills cover wire caps), then dots and labels
        o.write('\n'.join(fig.els) + '\n</svg>\n')
    print('Wrote %s' % os.path.relpath(out))
    print('Size: %.2f x %.2f pt (insert at 100%%, never resize)' % (W, H))
    print('%d wires, %d symbols, %d dots, %d labels' % (wire_els, len(spec['symbols']), len(spec['dots']), len(spec.get('labels', []))))
    print('Checks: ' + ('all wire ends on pins or wires' if not problems else '\n  ' + '\n  '.join(problems)))


if __name__ == '__main__':
    main()
