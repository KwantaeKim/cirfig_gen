"""Build docs/palette.png, the sheet of every palette symbol shown in the README.

    /opt/anaconda3/bin/python3 docs/palette.py      # any Python with Pillow

Writes docs/palette.json with every symbol of palette/palette.csv at its palette size on a
grid, each named below in the label style of the figures, renders docs/palette.svg through
tools/render.py and rasterizes it to docs/palette.png on a white background with qlmanage
and Pillow. Run it again after a palette change.
"""
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.dont_write_bytecode = True                    # no tools/__pycache__ from the import below
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import render                                     # noqa: E402, the renderer measures the labels

COLS = 7
CELL_W = 122.0          # pt, wider than the widest symbol (Noise, 93.84 pt) and the longest name
GAP = 8.0               # pt from the symbol band down to the name
ROW_GAP = 20.0          # pt from the name down to the next symbol band
SIZE = 18.0             # the label's main size. The name is a 'sub' run: upright bold at 2/3 of it
CLEAR = 3.0             # pt kept between every label box and everything else (rules.md 24)
PIXELS = 2000           # qlmanage thumbnail size


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'palette', 'palette.csv'), encoding='utf8')))
    G = json.load(open(os.path.join(ROOT, 'tools', 'glyphs.json'), encoding='utf8'))
    measure = lambda name: render.label_glyphs({'runs': [[name, 'sub']], 'size': SIZE, 'x': 0.0, 'y': 0.0, 'align': 'left'}, G)[1]
    band_h = max(float(r['height_pt']) for r in rows)
    name_h = max(measure(r['name'])[3] - measure(r['name'])[2] for r in rows)
    row_h = band_h + GAP + name_h + ROW_GAP

    symbols, labels, boxes = [], [], []
    for i, r in enumerate(rows):
        col, row = i % COLS, i // COLS
        w, h = float(r['width_pt']), float(r['height_pt'])
        cx, band_top = col * CELL_W + CELL_W / 2, row * row_h
        left, top = cx - w / 2, band_top + (band_h - h) / 2
        symbols.append({'id': r['name'], 'type': r['name'], 'left': round(left, 4), 'top': round(top, 4), 'flip': False})
        boxes.append(('symbol ' + r['name'], (left, left + w, top, top + h)))
        x0, x1, y0, y1 = measure(r['name'])
        lab = {'runs': [[r['name'], 'sub']], 'size': SIZE, 'x': round(cx - (x1 - x0) / 2, 4),
               'y': round(band_top + band_h + GAP - y0, 4), 'align': 'left'}
        labels.append(lab)
        bx0, bx1, by0, by1 = render.label_glyphs(lab, G)[1]
        boxes.append(('label ' + r['name'], (bx0, bx1, by0, by1)))

    # every label box keeps CLEAR from every symbol box and every other label box
    gap = lambda a, b: max(max(a[0] - b[1], b[0] - a[1], 0.0), max(a[2] - b[3], b[2] - a[3], 0.0))
    worst = None
    for n1, b1 in boxes:
        if not n1.startswith('label'):
            continue
        for n2, b2 in boxes:
            if n2 == n1:
                continue
            d = gap(b1, b2)
            if worst is None or d < worst[0]:
                worst = (d, n1, n2)
    print('Closest label: "%s" is %.2f pt from %s' % (worst[1], worst[0], worst[2]))
    if worst[0] < CLEAR:
        sys.exit('A label is closer than %g pt. Widen CELL_W or the gaps.' % CLEAR)

    spec = {'name': 'Palette', 'symbols': symbols, 'wires': [], 'dots': [], 'labels': labels}
    spec_path = os.path.join(HERE, 'palette.json')
    with open(spec_path, 'w', encoding='utf8') as fh:
        json.dump(spec, fh, indent=1)
    print('Wrote docs/palette.json: %d symbols on %d columns' % (len(symbols), COLS))

    out = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'render.py'), spec_path],
                         capture_output=True, text=True, cwd=ROOT)
    print(out.stdout.strip())
    # VDD and GND stand alone on the sheet, so the renderer reports that nothing reaches their
    # pins. That report is expected here. Any other report is a problem.
    reports = out.stdout.split('Checks:', 1)[-1].strip().splitlines()
    unexpected = [r for r in reports if r.strip() and 'no wire or lead reaches its pin' not in r and 'all wire ends' not in r]
    if out.returncode or unexpected:
        sys.exit(out.stderr.strip() or 'The renderer reported a problem.')

    # qlmanage draws a square thumbnail and crops anything outside it, so it gets a temporary
    # copy whose viewBox is padded to a square. It draws on a transparent background, so Pillow
    # crops the padding away and lays the sheet on white.
    import re
    from PIL import Image
    svg = os.path.join(HERE, 'palette.svg')
    text = open(svg, encoding='utf8').read()
    W, H, x0, y0 = (float(v) for v in re.match(r'<svg[^>]*width="([\d.]+)pt" height="([\d.]+)pt" viewBox="([-\d.]+) ([-\d.]+)', text).groups())
    S = max(W, H)
    square = os.path.join(HERE, 'palette_square.svg')
    with open(square, 'w', encoding='utf8') as fh:
        fh.write(re.sub(r'width="[\d.]+pt" height="[\d.]+pt" viewBox="[^"]*"',
                        'width="%spt" height="%spt" viewBox="%s %s %s %s"' % (S, S, x0, y0, S, S), text, count=1))
    subprocess.run(['qlmanage', '-t', '-s', str(PIXELS), '-o', HERE, square], check=True, capture_output=True)
    thumb = square + '.png'
    im = Image.open(thumb).convert('RGBA')
    im = im.crop((0, 0, round(im.width * W / S), round(im.height * H / S)))
    white = Image.new('RGBA', im.size, (255, 255, 255, 255))
    white.alpha_composite(im)
    png = os.path.join(HERE, 'palette.png')
    white.convert('RGB').save(png, optimize=True)
    os.remove(thumb)
    os.remove(square)
    print('Wrote docs/palette.png: %d x %d px' % im.size)


if __name__ == '__main__':
    main()
