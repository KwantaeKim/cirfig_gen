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
GENTLE = 45.0                                   # deg: a polyline that turns less than this per vertex is a curve
MAIN_SIZE, SUB_SIZE, SUB_DROP = 20.0, 20.0 * 2 / 3, 1.5
f = lambda v: '%.3f' % v


def palette_table():
    with open(os.path.join(ROOT, 'palette', 'palette.csv'), encoding='utf8') as fh:
        return {r['name']: (r['file'], float(r['width_pt']), float(r['height_pt'])) for r in csv.DictReader(fh)}


def arc_points(cur, rx, ry, rot, large, sweep, x, y, n=12):
    """Points along an SVG elliptical arc from cur to (x, y), as n straight segments (SVG
    implementation notes, endpoint to centre parameterisation)."""
    phi = math.radians(rot)
    cp, sp = math.cos(phi), math.sin(phi)
    x1, y1 = cur
    dx, dy = (x1 - x) / 2, (y1 - y) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(num / den, 0.0)) * (-1 if bool(large) == bool(sweep) else 1)
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x) / 2, sp * cxp + cp * cyp + (y1 + y) / 2
    ang = lambda ux, uy, vx, vy: math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    th1 = ang(1, 0, ux, uy)
    dth = ang(ux, uy, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    pts = []
    for k in range(1, n + 1):
        t = th1 + dth * k / n
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        pts.append((cp * ex - sp * ey + cx, sp * ex + cp * ey + cy))
    pts[-1] = (x, y)
    return pts


def parse_path(d):
    """Absolute SVG path (M L H V Q C A Z, implicit repeats) -> list of (cmd, [points]).
    Arcs (A) are flattened into straight segments."""
    toks = re.findall(r'[MLHVQCAZmlhvqcaz]|-?\d*\.?\d+(?:e-?\d+)?', d)
    out, i, cmd, cur = [], 0, None, (0.0, 0.0)
    need = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'Q': 4, 'C': 6, 'A': 7}
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
        elif cmd == 'A': pts = arc_points(cur, *v); c = 'L'
        else: pts = [(v[k], v[k + 1]) for k in range(0, n, 2)]; c = cmd
        out.append((c, pts)); cur = pts[-1]
        if cmd == 'M': cmd = 'L'                      # implicit lineto after moveto
    return out


class Fig:
    def __init__(self):
        self.els, self.pts, self.pins, self.edges, self.sides = [], [], [], [], []

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


def turn(a, b, c):
    """Change of direction at b on the way a -> b -> c, in degrees (0 to 180)."""
    t = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])
    return abs(math.degrees((t + math.pi) % (2 * math.pi) - math.pi))


def add_sides(fig, segs):
    """Store the straight sides of one symbol path for the wire end caps (rules.md 9).
    Collinear segments merge into one side. Palette circles, rings and arcs are polylines that
    turn a few degrees at every vertex, so a run that meets its neighbours only at such gentle
    turns (or at Bezier curves) is part of a curve and not a side. So is a run shorter than a
    wire with a gentle turn at one end: the last piece of an arc before a cusp or corner."""
    subs = []                                                 # [points, Bezier segment indices, closed]
    for c, pts in segs:
        if c == 'M':
            subs.append([[pts[0]], set(), False])
        elif c == 'Z':
            subs[-1][2] = True
        else:
            for q in (pts[-1:] if c in 'QC' else pts):        # a Bezier counts by its end point only
                last = subs[-1][0][-1]
                if math.hypot(q[0] - last[0], q[1] - last[1]) > 1e-6:
                    if c in 'QC':
                        subs[-1][1].add(len(subs[-1][0]) - 1)
                    subs[-1][0].append(q)
    for pts, bez, closed in subs:
        if closed and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 1e-6:
            pts.append(pts[0])                                # Z draws the closing segment
        m = len(pts) - 1                                      # segment k runs from pts[k] to pts[k + 1]
        if m < 1:
            continue
        def joint(k):                                         # how segment k meets segment k + 1
            a, b = k % m, (k + 1) % m
            if a in bez or b in bez:
                return 'gentle'
            t = turn(pts[a], pts[a + 1], pts[b + 1])
            return 'straight' if t < 1 else 'gentle' if t < GENTLE else 'corner'
        J = [joint(k) for k in range(m if closed else m - 1)]
        if closed:                                            # start the walk just after a corner
            breaks = [k for k in range(m) if J[k] != 'straight']
            if not breaks:
                continue
            order = [(breaks[0] + 1 + k) % m for k in range(m)]
        else:
            order = list(range(m))
        runs = [[order[0]]]
        for a, b in zip(order, order[1:]):
            if J[a] == 'straight':
                runs[-1].append(b)
            else:
                runs.append([b])
        for r in runs:
            if r[0] in bez:
                continue
            ends = [J[(r[0] - 1) % m] if closed or r[0] > 0 else None, J[r[-1]] if closed or r[-1] < m - 1 else None]
            ends = [e for e in ends if e]
            a, b = pts[r[0]], pts[r[-1] + 1]
            if ends and ('corner' not in ends or 'gentle' in ends and math.hypot(b[0] - a[0], b[1] - a[1]) < WIRE_W):
                continue
            fig.sides.append((a, b))


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
            add_sides(fig, segs)
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
    main = float(lab.get('size', MAIN_SIZE))                  # optional per-label size; 20 pt (rules.md 17) by default
    k = main / MAIN_SIZE                                      # subscript size and drop scale with it
    size = lambda kind: main if kind == 'main' else SUB_SIZE * k
    width = sum(face(kk)[0]['glyphs'][ch]['adv'] * size(kk) / face(kk)[1] for ch, kk in runs)
    x = lab['x'] if lab.get('align', 'left') == 'left' else lab['x'] - width
    base = lab['y'] + G['italic']['cap_height'] * main / G['upm_italic'] / 2   # centre the capitals on y
    for ch, kind in runs:
        fc, upm = face(kind)
        g, s = fc['glyphs'][ch], size(kind) / upm
        b = base + (SUB_DROP * k if kind == 'sub' else 0)
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


def end_cap(p, i, wires, fig):
    """Cap of the end p of wire i (rules.md 9). Butt where the wire arrives across a straight
    symbol side and stops inside it: a box side, plate or bar, or a pin on one such as the GND pin.
    Round everywhere else: on another wire, at the end of a lead (most pins), along a lead it
    continues, on a circle, ring or bubble, at a corner, inside a face, or free."""
    if any(j != i and on_segment(p, w[:2], w[2:]) for j, w in enumerate(wires)):
        return 'round'
    x1, y1, x2, y2 = wires[i]
    def lands_on(a, b):
        across = abs((x2 - x1) * (b[1] - a[1]) - (y2 - y1) * (b[0] - a[0])) > 0.02 * math.hypot(x2 - x1, y2 - y1) * math.hypot(b[0] - a[0], b[1] - a[1])
        return across and on_segment(p, a, b) and min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in (a, b)) > 0.01
    return 'butt' if any(lands_on(a, b) for a, b in fig.sides) else 'round'


def place_wire(fig, w, caps):
    """One wire with the given cap at each end. SVG has one linecap per path, so a wire with one
    butt end and one round end is a butt stroke plus a disc of the wire width centred on the round
    end. A round cap is exactly that disc, so the wire still reads as one line."""
    x1, y1, x2, y2 = w
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = (y1 - y2) / length * WIRE_W / 2, (x2 - x1) / length * WIRE_W / 2   # half the width, across the wire
    cap = caps[0] if caps[0] == caps[1] else 'butt'
    fig.path([('M', [(x1, y1)]), ('L', [(x2, y2)])],
             'fill="none" stroke="#000000" stroke-width="%s" stroke-linecap="%s"' % (f(WIRE_W), cap), 0)
    for (x, y), c in zip(((x1, y1), (x2, y2)), caps):
        if c == 'butt':                                       # flush: nothing past the end, half the width across
            fig.extent(x + nx, y + ny); fig.extent(x - nx, y - ny)
        else:                                                 # round: half the width in every direction
            fig.extent(x, y, WIRE_W / 2)
            if cap == 'butt':
                fig.els.append('<circle cx="%s" cy="%s" r="%s" fill="#000000"/>' % (f(x), f(y), f(WIRE_W / 2)))


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
    for sym in spec['symbols']:
        place_symbol(fig, sym, table)
    for x, y in spec['dots']:
        fig.els.append('<circle cx="%s" cy="%s" r="%s" fill="#000000"/>' % (f(x), f(y), f(DOT_D / 2)))
        fig.extent(x, y, DOT_D / 2)
    for lab in spec.get('labels', []):
        place_label(fig, lab, G)
    above, fig.els = fig.els, []                              # the caps need the symbols, but wires are drawn first

    # every wire end must sit on a symbol pin or on another wire, and gets its cap from what it touches
    wires = spec['wires']
    for i, (x1, y1, x2, y2) in enumerate(wires):
        for p in ((x1, y1), (x2, y2)):
            ok = any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for q in fig.pins)
            ok = ok or any(on_segment(p, a, b) for a, b in fig.edges)
            ok = ok or any(j != i and on_segment(p, (w[0], w[1]), (w[2], w[3])) for j, w in enumerate(wires))
            if not ok:
                problems.append('wire end %s is not on a pin or wire' % (tuple(round(v, 3) for v in p),))
        place_wire(fig, wires[i], [end_cap(p, i, wires, fig) for p in ((x1, y1), (x2, y2))])
    fig.els += above

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
    print('%d wires, %d symbols, %d dots, %d labels' % (len(wires), len(spec['symbols']), len(spec['dots']), len(spec.get('labels', []))))
    print('Checks: ' + ('all wire ends on pins or wires' if not problems else '\n  ' + '\n  '.join(problems)))


if __name__ == '__main__':
    main()
