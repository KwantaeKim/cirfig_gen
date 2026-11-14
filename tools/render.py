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
The optional "edge_ends": [[x, y], ...] lists the wire ends that land on a straight edge drawn
outside the figure, such as a gate rectangle on the slide. They get a butt cap (rules.md 9).

The optional "rotate": 0, 90, 180 or 270 turns the finished figure clockwise about the origin.
The JSON keeps its unturned coordinates, and the SVG is the turned figure, inserted unturned.
  Wires, dots, edge ends and symbols turn with the figure, and so does a Voltage Node (a ring).
  GND and VDD stay upright. Each is given in the JSON as if upright in the unturned frame,
  with its pin on the wire end or lead. That pin turns, and the symbol is drawn upright about it.
  Voltage Source, Voltage Source H and Voltage Source Inv are replaced by the variant whose +
  points where the turned + points, so the signs stay upright. Current Arrow and Current Arrow H
  turn, because the current turns with the circuit. Symbols with signs, letters or a time axis
  inside (TEXT_SYMBOLS) cannot be turned and are reported.
  Labels stay upright text and their anchor turns. The side of the label that faced the anchor
  keeps facing it: after 180 "left" becomes "right" and back, after 90 a "left" label hangs below
  its anchor and a "right" label stands above it, after 270 the other way round. A label above or
  below its anchor is centred on it across, and its glyph outline ends on it.
All checks run on the turned geometry. Every figure is checked for its supply leads: each one
arrives from the side the upright symbol expects (GND from above, VDD from below). A turned
figure also gets its label boxes checked: each keeps 3 pt from every wire, symbol, dot and other
label (rules.md 24). The box spans the advance widths across and the glyph outlines from top to
bottom. An unturned figure has its labels checked by its layout script, as before.
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
CLEAR = 3.0                                     # pt between a label box and everything else
f = lambda v: '%.3f' % v

# clockwise turns about the origin, in SVG coordinates (y points down)
TURNS = {0: lambda x, y: (x, y), 90: lambda x, y: (-y, x), 180: lambda x, y: (-x, -y), 270: lambda x, y: (y, -x)}
UPRIGHT = {'GND': 'top', 'VDD': 'bottom'}     # supplies that never turn, and their pin side
PLUS = {('Voltage Source', False): (0, -1), ('Voltage Source', True): (0, -1),
        ('Voltage Source Inv', False): (0, 1), ('Voltage Source Inv', True): (0, 1),
        ('Voltage Source H', False): (-1, 0), ('Voltage Source H', True): (1, 0)}   # where the + sign sits
SOURCE_FOR = {(0, -1): ('Voltage Source', False), (0, 1): ('Voltage Source Inv', False),
              (-1, 0): ('Voltage Source H', False), (1, 0): ('Voltage Source H', True)}
TEXT_SYMBOLS = {'Amp', 'Gm', 'Comp', 'FD OpAm', 'Sum', 'DFF', 'DFF QB', 'Clock', 'Pure-Sine', 'Pseudo-Sine',
                'Noise', 'ECG', 'APW', 'Non-Overlap'}


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
        self.strokes, self.discs = [], []                     # symbol ink for the label clearance check

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


def outline(segs, n=8):
    """The straight pieces of one path, with each Bezier sampled into n pieces."""
    out, cur, start = [], None, None
    for c, pts in segs:
        if c == 'M':
            cur = start = pts[0]
        elif c == 'Z':
            if cur and start and cur != start:
                out.append((cur, start))
            cur = start
        elif c == 'L':
            for q in pts:
                out.append((cur, q)); cur = q
        else:
            ctrl = [cur] + pts
            for k in range(1, n + 1):
                t = k / n
                if c == 'Q':
                    q = tuple((1 - t) ** 2 * ctrl[0][i] + 2 * t * (1 - t) * ctrl[1][i] + t * t * ctrl[2][i] for i in (0, 1))
                else:
                    q = tuple((1 - t) ** 3 * ctrl[0][i] + 3 * t * (1 - t) ** 2 * ctrl[1][i]
                              + 3 * t * t * (1 - t) * ctrl[2][i] + t ** 3 * ctrl[3][i] for i in (0, 1))
                out.append((cur, q)); cur = q
    return out


def place_symbol(fig, sym, table, turn=None):
    """Draw one symbol. With turn, every point of it is turned with the figure."""
    fname, w, h = table[sym['type']]
    svg = open(os.path.join(ROOT, 'palette', fname), encoding='utf8').read()
    vx, vy, vw, vh = (float(v) for v in re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', svg).groups())
    sx, sy = w / vw, h / vh
    L, T, flip, rot = sym['left'], sym['top'], sym.get('flip', False), sym.get('rot', 0)
    X = lambda px: L + w - (px - vx) * sx if flip else L + (px - vx) * sx
    Y = lambda py: T + (py - vy) * sy
    # "rot": 90 turns this one symbol a quarter turn clockwise about the centre of its unturned frame (left, top, w, h),
    # for a figure whose transistors lie along a cross-section; the rules forbid this for an ordinary schematic
    assert rot in (0, 90), rot
    if rot:
        cx0, cy0, outer = L + w / 2, T + h / 2, turn
        turn = lambda x, y: (outer or (lambda a, b: (a, b)))(cx0 - (y - cy0), cy0 + (x - cx0))
    P = (lambda px, py: (X(px), Y(py))) if turn is None else (lambda px, py: turn(X(px), Y(py)))
    for m in re.finditer(r'<(path|circle|rect)\b([^>]*)/?>', svg):
        kind, a = m.groups()
        style, sw = style_of(a, sx)
        num = lambda k: float(re.search(r'\b%s="([^"]*)"' % k, a).group(1))
        if kind == 'path':
            segs = [(c, [P(x, y) for x, y in pts]) for c, pts in parse_path(re.search(r'\bd="([^"]*)"', a).group(1))]
            fig.path(segs, style, sw / 2)
            add_sides(fig, segs)
            cap = 'butt' if 'stroke-linecap="butt"' in style else 'round'
            fig.strokes += [(p, q, sw / 2, cap) for p, q in outline(segs)]
            prev = None
            for c, pts in segs:                                   # path vertices and straight edges can be pins
                fig.pins += pts
                if c == 'L' and prev:
                    fig.edges.append((prev, pts[-1]))
                prev = pts[-1] if pts else prev
        elif kind == 'circle':
            (cx, cy), r = P(num('cx'), num('cy')), num('r') * sx
            fig.els.append('<circle cx="%s" cy="%s" r="%s" %s/>' % (f(cx), f(cy), f(r), style))
            fig.extent(cx, cy, r + sw / 2)
            fig.pins += [(cx - r, cy), (cx + r, cy), (cx, cy - r), (cx, cy + r)]
            fig.discs.append((cx, cy, r + sw / 2))
        else:
            if turn is None:
                x0, x1 = sorted((X(num('x')), X(num('x') + num('width'))))
                y0 = Y(num('y'))
                y1 = y0 + num('height') * sy
            else:                                                 # a turned rectangle is still axis aligned
                (ax, ay), (bx, by) = P(num('x'), num('y')), P(num('x') + num('width'), num('y') + num('height'))
                (x0, x1), (y0, y1) = sorted((ax, bx)), sorted((ay, by))
            rx = float((re.search(r'\brx="([^"]*)"', a) or [0, 0])[1]) * sx
            fig.els.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>'
                           % (f(x0), f(y0), f(x1 - x0), f(y1 - y0 if turn else num('height') * sy), f(rx), style))
            fig.extent(x0, y0); fig.extent(x1, y1)
            c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            fig.strokes += [(c[k], c[(k + 1) % 4], sw / 2, 'round') for k in range(4)]


def supply_pin(sym, table):
    """Pin of an upright supply symbol, from its top-left corner: the end of its lead on the pin
    side (VDD stem) or the middle of its bar there (GND)."""
    fname, w, h = table[sym['type']]
    svg = open(os.path.join(ROOT, 'palette', fname), encoding='utf8').read()
    vx, vy, vw, vh = (float(v) for v in re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', svg).groups())
    pts = [((x - vx) * w / vw, (y - vy) * h / vh) for m in re.finditer(r'<path\b[^>]*\bd="([^"]*)"', svg)
           for c, ps in parse_path(m.group(1)) for x, y in ps]
    y = (min if UPRIGHT[sym['type']] == 'top' else max)(p[1] for p in pts)
    xs = [p[0] for p in pts if abs(p[1] - y) < 1e-6]
    x = (min(xs) + max(xs)) / 2
    return (w - x if sym.get('flip', False) else x), y


def label_glyphs(lab, G):
    """The glyph outlines of one label, and its box (x0, x1, y0, y1): the advance widths across,
    as the layout scripts measure them, and the glyph outlines from top to bottom."""
    # main letters: bold italic font; subscripts: the matching upright bold font
    face = lambda kind: (G['italic'], G['upm_italic']) if kind == 'main' else (G['upright'], G['upm_upright'])
    runs = [(ch, kind) for text, kind in lab['runs'] for ch in text]
    main = float(lab.get('size', MAIN_SIZE))                  # optional per-label size; 20 pt (rules.md 17) by default
    k = main / MAIN_SIZE                                      # subscript size and drop scale with it
    size = lambda kind: main if kind == 'main' else SUB_SIZE * k
    width = sum(face(kk)[0]['glyphs'][ch]['adv'] * size(kk) / face(kk)[1] for ch, kk in runs)
    x = lab['x'] if lab.get('align', 'left') == 'left' else lab['x'] - width
    left = x
    base = lab['y'] + G['italic']['cap_height'] * main / G['upm_italic'] / 2   # centre the capitals on y
    glyphs = []
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
            glyphs.append(segs)
        x += g['adv'] * s
    ys = [p[1] for segs in glyphs for c, pts in segs for p in pts] or [lab['y']]
    return glyphs, (left, left + width, min(ys), max(ys))


def place_label(fig, lab, G):
    glyphs, box = label_glyphs(lab, G)
    for segs in glyphs:
        fig.path(segs, 'fill="#000000"', 0)
    return box


def turn_label(lab, G, turn):
    """The label of the turned figure: upright text whose anchor turned with the figure. The side
    that faced the anchor keeps facing it. Text that would run down or up is centred across on the
    anchor and hangs below it or stands above it, with its glyph outline ending on the anchor."""
    _, (x0, x1, top, bottom) = label_glyphs(dict(lab, x=0.0, y=0.0, align='left'), G)
    ax, ay = turn(lab['x'], lab['y'])
    dx, dy = turn(1 if lab.get('align', 'left') == 'left' else -1, 0)   # the way the text runs from its anchor
    if dx:
        return dict(lab, x=ax, y=ay, align='left' if dx > 0 else 'right')
    return dict(lab, x=ax - (x1 - x0) / 2, y=ay - (top if dy > 0 else bottom), align='left')


def side_name(v):
    return ('the right' if v[0] > 0 else 'the left') if abs(v[0]) > abs(v[1]) else ('below' if v[1] > 0 else 'above')


def pt_seg(p, a, b):
    """Distance from point p to segment ab."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0.0 if not (dx or dy) else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def rect_seg(r, a, b):
    """Distance from the box r = (x0, x1, y0, y1) to segment ab, 0 if they touch."""
    x0, x1, y0, y1 = r
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    if inside(a) or inside(b):
        return 0.0
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    side = lambda p, q, s: (q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])
    for k in range(4):
        p, q = c[k], c[(k + 1) % 4]
        if side(a, b, p) * side(a, b, q) <= 0 and side(p, q, a) * side(p, q, b) <= 0:
            return 0.0
    return min([pt_seg(q, a, b) for q in c] + [math.hypot(max(x0 - p[0], 0, p[0] - x1), max(y0 - p[1], 0, p[1] - y1)) for p in (a, b)])


def stroke_gap(r, a, b, half, caps):
    """Distance from the box r to a stroke of half width half along ab. A butt end stops flush
    at its end point, a round end reaches half the width past it."""
    if not half or caps == ('round', 'round'):
        return max(rect_seg(r, a, b) - half, 0.0)
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    nx, ny = (a[1] - b[1]) / L * half, (b[0] - a[0]) / L * half
    c = [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]
    gap = min(rect_seg(r, c[k], c[(k + 1) % 4]) for k in range(4))
    for p, cap in zip((a, b), caps):
        if cap == 'round':
            gap = min(gap, max(math.hypot(max(r[0] - p[0], 0, p[0] - r[1]), max(r[2] - p[1], 0, p[1] - r[3])) - half, 0.0))
    return gap


def label_clearance(boxes, wires, caps, fig, dots):
    """Closest distance from each label box to a wire, symbol, dot or other label (rules.md 24)."""
    out = []
    for i, (name, r) in enumerate(boxes):
        near = [(stroke_gap(r, w[:2], w[2:], WIRE_W / 2, c), 'a wire') for w, c in zip(wires, caps)]
        near += [(stroke_gap(r, a, b, half, (cap, cap)), 'a symbol') for a, b, half, cap in fig.strokes]
        near += [(math.hypot(max(r[0] - cx, 0, cx - r[1]), max(r[2] - cy, 0, cy - r[3])) - rad, 'a symbol')
                 for cx, cy, rad in fig.discs]
        near += [(math.hypot(max(r[0] - x, 0, x - r[1]), max(r[2] - y, 0, y - r[3])) - DOT_D / 2, 'a dot') for x, y in dots]
        near += [(math.hypot(max(r[0] - s[1], 0, s[0] - r[1]), max(r[2] - s[3], 0, s[2] - r[3])), 'label "%s"' % other)
                 for j, (other, s) in enumerate(boxes) if j != i]
        out.append((name,) + min(near) if near else (name, float('inf'), 'nothing'))
    return out


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


def end_cap(p, i, wires, fig, edge_ends):
    """Cap of the end p of wire i (rules.md 9). Butt where the wire arrives across a straight
    symbol side and stops inside it: a box side, plate or bar, or a pin on one such as the GND pin.
    Butt also at a listed edge end, where the wire stops on a straight edge outside the figure.
    Round everywhere else: on another wire, at the end of a lead (most pins), along a lead it
    continues, on a circle, ring or bubble, at a corner, inside a face, or free."""
    if any(j != i and on_segment(p, w[:2], w[2:]) for j, w in enumerate(wires)):
        return 'round'
    if any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for q in edge_ends):
        return 'butt'
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
    rot = spec.get('rotate', 0)
    if rot not in TURNS:
        sys.exit('"rotate" must be 0, 90, 180 or 270, not %r' % (rot,))
    T = TURNS[rot]
    if rot:                                                   # the whole figure turns before anything is checked
        wires = [list(T(w[0], w[1]) + T(w[2], w[3])) for w in spec['wires']]
        dots = [T(x, y) for x, y in spec['dots']]
        edge_ends = [T(x, y) for x, y in spec.get('edge_ends', [])]
    else:
        wires, dots, edge_ends = spec['wires'], spec['dots'], spec.get('edge_ends', [])

    # a diagonal wire is allowed only as half of a cross-coupling X: it must cross another diagonal
    diagonals = [w for w in wires if w[0] != w[2] and w[1] != w[3]]
    for d in diagonals:
        if not any(e is not d and crosses(d, e) for e in diagonals):
            problems.append('diagonal wire %s is not half of a cross-coupling X' % d)
    supplies = []                                             # (symbol, pin, its own edges) of each GND and VDD
    for sym in spec['symbols']:
        kind, n = sym['type'], len(fig.edges)
        if kind in UPRIGHT:                                   # drawn upright, with its pin on the turned pin
            px, py = supply_pin(sym, table)
            pin = T(sym['left'] + px, sym['top'] + py)
            place_symbol(fig, dict(sym, left=pin[0] - px, top=pin[1] - py) if rot else sym, table)
            supplies.append((sym, pin, (n, len(fig.edges))))
        elif not rot:
            place_symbol(fig, sym, table)
        elif (kind, sym.get('flip', False)) in PLUS:          # the source whose + points where the turned + points
            w, h = table[kind][1:]
            (ax, ay), (bx, by) = T(sym['left'], sym['top']), T(sym['left'] + w, sym['top'] + h)
            kind2, flip2 = SOURCE_FOR[T(*PLUS[(kind, sym.get('flip', False))])]
            place_symbol(fig, dict(sym, type=kind2, flip=flip2, left=min(ax, bx), top=min(ay, by)), table)
        else:
            if kind in TEXT_SYMBOLS:
                problems.append('%s (%s) has signs, letters or a time axis inside and cannot be turned' % (sym.get('id', '?'), kind))
            place_symbol(fig, sym, table, T)
    for x, y in dots:
        fig.els.append('<circle cx="%s" cy="%s" r="%s" fill="#000000"/>' % (f(x), f(y), f(DOT_D / 2)))
        fig.extent(x, y, DOT_D / 2)
    boxes = []
    for lab in spec.get('labels', []):
        boxes.append((''.join(text for text, kind in lab['runs']), place_label(fig, turn_label(lab, G, T) if rot else lab, G)))
    above, fig.els = fig.els, []                              # the caps need the symbols, but wires are drawn first

    # every wire end must sit on a symbol pin, on another wire or on a listed edge end outside the
    # figure, and gets its cap from what it touches
    caps = []
    for i, (x1, y1, x2, y2) in enumerate(wires):
        for p in ((x1, y1), (x2, y2)):
            ok = any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for q in fig.pins)
            ok = ok or any(on_segment(p, a, b) for a, b in fig.edges)
            ok = ok or any(j != i and on_segment(p, (w[0], w[1]), (w[2], w[3])) for j, w in enumerate(wires))
            ok = ok or any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for q in edge_ends)
            if not ok:
                problems.append('wire end %s is not on a pin or wire' % (tuple(round(v, 3) for v in p),))
        caps.append(tuple(end_cap(p, i, wires, fig, edge_ends) for p in ((x1, y1), (x2, y2))))
        place_wire(fig, wires[i], list(caps[-1]))
    for q in edge_ends:
        if not any(math.hypot(q[0] - x, q[1] - y) < 0.01 for w in wires for x, y in (w[:2], w[2:])):
            problems.append('edge end %s is not the end of a wire' % (tuple(round(v, 3) for v in q),))
    fig.els += above

    # an upright supply needs its lead from the side it expects: GND from above, VDD from below
    for sym, p, (e0, e1) in supplies:
        want = (0, -1) if UPRIGHT[sym['type']] == 'top' else (0, 1)
        segs = [(w[:2], w[2:]) for w in wires] + [e for k, e in enumerate(fig.edges) if not e0 <= k < e1]
        away = [(q[0] - p[0], q[1] - p[1]) for a, b in segs if on_segment(p, a, b) for q in (a, b)
                if math.hypot(q[0] - p[0], q[1] - p[1]) > 0.01]
        name = '%s %s at %s' % (sym['type'], sym.get('id', ''), tuple(round(v, 3) for v in p))
        if not away:
            problems.append('%s: no wire or lead reaches its pin' % name)
        for v in away:
            if abs(v[0]) > 0.01 or v[1] * want[1] <= 0:
                problems.append('%s: its lead arrives from %s, but the upright symbol needs it from %s'
                                % (name, side_name(v), side_name(want)))
    # a layout script measures its labels in the unturned frame, so a turned figure has them checked here
    clear = label_clearance(boxes, wires, caps, fig, dots) if rot else []
    tight = ['label "%s" is %.2f pt from %s' % (n, d, what) for n, d, what in clear if d < CLEAR - 0.01]

    xs, ys = [p[0] for p in fig.pts], [p[1] for p in fig.pts]
    x0, y0 = min(xs) - MARGIN, min(ys) - MARGIN
    W, H = max(xs) + MARGIN - x0, max(ys) + MARGIN - y0
    if 'frame' in spec:
        # pictures that must align pixel-exactly in PowerPoint share one frame [x, y, w, h], which is the viewBox as is
        fx, fy, fw, fh = spec['frame']
        if x0 < fx - 0.001 or y0 < fy - 0.001 or x0 + W > fx + fw + 0.001 or y0 + H > fy + fh + 0.001:
            problems.append('content %s exceeds the frame %s' % ((round(x0, 3), round(y0, 3), round(W, 3), round(H, 3)), spec['frame']))
        x0, y0, W, H = fx, fy, fw, fh
    out =os.path.splitext(spec_path)[0] + '.svg'
    with open(out, 'w', encoding='utf8') as o:
        o.write('<svg xmlns="http://www.w3.org/2000/svg" width="%spt" height="%spt" viewBox="%s %s %s %s">\n'
                % (f(W), f(H), f(x0), f(y0), f(W), f(H)))
        # wires first, then symbols (their white fills cover wire caps), then dots and labels
        o.write('\n'.join(fig.els) + '\n</svg>\n')
    print('Wrote %s' % os.path.relpath(out))
    print('Size: %.2f x %.2f pt (insert at 100%%, never resize)' % (W, H))
    print('%d wires, %d symbols, %d dots, %d labels' % (len(wires), len(spec['symbols']), len(spec['dots']), len(spec.get('labels', []))))
    landed = 'pins, wires or listed edge ends' if edge_ends else 'pins or wires'
    if rot:
        print('Turned %d degrees clockwise' % rot)
    print('Checks: ' + ('all wire ends on ' + landed if not problems else '\n  ' + '\n  '.join(problems)))
    if clear:
        n, d, what = min(clear, key=lambda c: c[1])
        print('Labels: ' + ('every label at least %g pt from wires, symbols, dots and labels (closest: "%s", %.2f pt from %s)'
                            % (CLEAR, n, d, what) if not tight else '\n  ' + '\n  '.join(tight)))


if __name__ == '__main__':
    main()
