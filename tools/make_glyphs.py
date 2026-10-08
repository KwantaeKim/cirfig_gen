"""Build tools/glyphs.json, the label letter outlines, from fonts installed on this computer.

    python3 tools/make_glyphs.py                      # pick the best installed font (see rules.md)
    python3 tools/make_glyphs.py <bold-italic> <bold> # use these font files

Main letters come from a Bold Italic font, subscripts from the matching upright Bold font.
Needs fontTools (pip install fonttools). The renderer only reads glyphs.json.
glyphs.json is derived from the chosen font, so it is not committed to the repository.
"""
import glob
import json
import os
import sys
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTCollection, TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
         '+-\u2212=.,()/ ')
# Preference order from rules.md: the first family installed with both styles wins.
FAMILIES = ['Arial Narrow', 'Liberation Sans Narrow', 'Arial', 'Liberation Sans', 'Arimo',
            'Helvetica Neue', 'Helvetica', 'DejaVu Sans Condensed', 'DejaVu Sans']
FONT_DIRS = ['/Library/Fonts', '~/Library/Fonts', '/System/Library/Fonts',
             '/System/Library/Fonts/Supplemental',
             '/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts',
             '/Applications/Microsoft Word.app/Contents/Resources/DFonts',
             'C:/Windows/Fonts', '~/AppData/Local/Microsoft/Windows/Fonts',
             '/usr/share/fonts', '/usr/local/share/fonts', '~/.local/share/fonts', '~/.fonts']


class PathPen(BasePen):
    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.cmds = []

    def _moveTo(self, p):
        self.cmds.append(['M', p[0], p[1]])

    def _lineTo(self, p):
        self.cmds.append(['L', p[0], p[1]])

    def _qCurveToOne(self, p1, p2):
        self.cmds.append(['Q', p1[0], p1[1], p2[0], p2[1]])

    def _curveToOne(self, p1, p2, p3):
        self.cmds.append(['C', p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]])

    def _closePath(self):
        self.cmds.append(['Z'])


def fonts_in(path):
    """(font, index) for a .ttf/.otf file or each face of a .ttc collection."""
    if path.lower().endswith('.ttc'):
        return [(f, i) for i, f in enumerate(TTCollection(path, lazy=True).fonts)]
    return [(TTFont(path, lazy=True), 0)]


def style_name(font):
    name = font['name']
    fam = name.getDebugName(16) or name.getDebugName(1)
    sub = name.getDebugName(17) or name.getDebugName(2)
    return fam, sub


def find_installed():
    found = {}                                             # (family, style) -> (path, index)
    for d in FONT_DIRS:
        for path in glob.glob(os.path.join(os.path.expanduser(d), '**', '*.*'), recursive=True):
            if not path.lower().endswith(('.ttf', '.otf', '.ttc')):
                continue
            try:
                for font, idx in fonts_in(path):
                    fam, sub = style_name(font)
                    if fam in FAMILIES and sub in ('Bold Italic', 'Bold Oblique', 'Bold'):
                        found.setdefault((fam, 'Bold' if sub == 'Bold' else 'Bold Italic'), (path, idx))
            except Exception:
                continue
    for fam in FAMILIES:
        if (fam, 'Bold Italic') in found and (fam, 'Bold') in found:
            return fam, found[(fam, 'Bold Italic')], found[(fam, 'Bold')]
    sys.exit('No suitable font found. Install Liberation Sans Narrow (free) or pass two font files.')


def extract(path, idx=0):
    font = TTCollection(path).fonts[idx] if path.lower().endswith('.ttc') else TTFont(path)
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font['hmtx']
    glyphs = {}
    for ch in CHARS:
        if ord(ch) in cmap:
            pen = PathPen(gs)
            gs[cmap[ord(ch)]].draw(pen)
            glyphs[ch] = {'adv': hmtx[cmap[ord(ch)]][0], 'path': pen.cmds}
    if '\u2212' not in glyphs:
        # No minus sign in the font: use the horizontal bar of its "+" (same width and weight).
        plus = glyphs['+']
        pts = sorted({(c[1], c[2]) for c in plus['path'] if c[0] in 'ML'})
        left, right = sorted(pts[:2], key=lambda p: p[1]), sorted(pts[-2:], key=lambda p: p[1])
        glyphs['\u2212'] = {'adv': plus['adv'], 'path': [
            ['M', left[0][0], left[0][1]], ['L', right[0][0], right[0][1]],
            ['L', right[1][0], right[1][1]], ['L', left[1][0], left[1][1]], ['Z']]}
    fam, sub = style_name(font)
    return font['head'].unitsPerEm, {
        'font': '%s %s' % (fam, sub),
        'cap_height': getattr(font['OS/2'], 'sCapHeight', 0) or int(0.7 * font['head'].unitsPerEm),
        'glyphs': glyphs}


if len(sys.argv) == 3:
    italic_src, upright_src = (sys.argv[1], 0), (sys.argv[2], 0)
else:
    family, italic_src, upright_src = find_installed()
upm_i, italic = extract(*italic_src)
upm_u, upright = extract(*upright_src)
json.dump({'upm_italic': upm_i, 'upm_upright': upm_u, 'italic': italic, 'upright': upright},
          open(os.path.join(HERE, 'glyphs.json'), 'w'))
print('Labels: %s (main letters) and %s (subscripts)' % (italic['font'], upright['font']))
print('From:   %s\n        %s' % (italic_src[0], upright_src[0]))
