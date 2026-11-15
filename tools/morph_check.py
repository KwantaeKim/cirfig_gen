"""morph_check.py DECK [N ...]   check every slide of DECK, or only slides N (1-based) and the transitions into them
   morph_check.py --cases         run the regression cases listed in output/morph_cases/cases.json

Finds animation that fades lines out and then back in. A fade-out alone or a fade-in alone is fine. The deck is only
read. Exit code 1 when anything is flagged.

Checks
  SWAP        Morph into slide N: an object keeps its name but changes content (a picture with another image), so
              Morph cross-fades it as a whole and every line both versions share dims and comes back.
  CROSS       Morph into slide N: two different objects, one leaving and one arriving, draw the same lines.
  HELD-ENTR   Morph into slide N: slide N-1 showed the object by an entrance effect, so Morph does not hold it still
              even though slide N has the same object.
  BACK-LATER  any transition into slide N: lines that leave at the transition come back later on slide N.
  TEXT        Morph into slide N: a text box keeps its name but changes its text (Morph moves the letters one by one).
  IN-SLIDE    on one slide, lines fade out and the same lines fade in again later (or both fade at the same time).

Model of Morph (learned on the lecture decks, extend it when a new case shows up):
  - An object of slide N-1 pairs with the slide-N object of the same name, else with one of identical content.
  - A paired object with identical content holds still or slides. Every other object fades out (N-1) or in (N).
  - An object that slide N-1 showed by an entrance effect fades out and in even when slide N has it unchanged.
  - Objects that slide N shows by an entrance effect are hidden during the Morph.
  - With any other transition the two slide images are blended, so a line drawn at the same spot on both stays.
Lines are measured on rendered pictures (SVG with QtSvg, PNG/GIF/JPEG with PIL) at 2 px per pt. Shapes, connectors
and text boxes are compared by content (their XML without ids, names and position). Two pictures share a line where
both draw ink of the same colour (white fills and colour changes such as black to grey do not count) along a piece at
least MIN_RUN long (junction dots count, crossings of different lines do not). A same-name swap is also compared in
its sliding frame. On one slide, a dip counts only when every object there together lets the lines dim below 90 %:
objects are placed by their finished motion paths and turned by their spins at each moment.
Regression cases: output/morph_cases/ (lecture slides, git-ignored). Add a case for every new kind of flag or miss.

To fix a flag, edit slide N or later slides, never slide N-1.
Run with /opt/anaconda3/bin/python3 (lxml, numpy, PIL, PyQt5)."""
import sys, os, re, io, json, copy, zipfile, hashlib, posixpath
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
from scipy import ndimage
from lxml import etree
from PIL import Image
from PyQt5.QtGui import QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import QByteArray, QRectF

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
      'asvg': 'http://schemas.microsoft.com/office/drawing/2016/SVG/main',
      'a16': 'http://schemas.microsoft.com/office/drawing/2014/main'}
P, A, RA = '{%s}' % NS['p'], '{%s}' % NS['a'], '{%s}' % NS['r']
EMU = 12700.0
S = 2.0                   # px per pt
INK_ALPHA = 64            # a pixel is ink above this alpha
MIN_PX = 120              # shared lines worth a flag: 30 pt^2 (a 3 pt line, 10 pt long)
MIN_FRAC = 0.05           # ... and at least 5 % of the smaller of the two drawings
CLICK_GAP = 1000.0        # ms between click groups in the slide time line
SKIP_PH = {'sldNum', 'dt', 'ftr'}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])


def xml(raw):
    return etree.fromstring(raw)


# ================================================================ deck
class Deck:
    def __init__(self, path):
        self.path = path
        self.z = zipfile.ZipFile(path)
        self.files = set(self.z.namelist())
        pres = xml(self.z.read('ppt/presentation.xml'))
        sz = pres.find('p:sldSz', NS)
        self.W, self.H = int(sz.get('cx')) / EMU, int(sz.get('cy')) / EMU
        prels = self.rels('ppt/presentation.xml')
        self.slides = [(s.get('id'), prels[s.get(RA + 'id')]) for s in pres.find('p:sldIdLst', NS)]
        self._md5 = {}

    def rels(self, part):
        rp = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
        out = {}
        if rp in self.files:
            for r in xml(self.z.read(rp)):
                t = r.get('Target')
                out[r.get('Id')] = None if r.get('TargetMode') == 'External' else \
                    posixpath.normpath(posixpath.join(posixpath.dirname(part), t))
        return out

    def md5(self, part):
        if part not in self._md5:
            self._md5[part] = hashlib.md5(self.z.read(part)).hexdigest() if part in self.files else 'missing:' + str(part)
        return self._md5[part]


# ================================================================ objects on a slide
class Obj:
    pass


def own_xfrm(el):
    tag = etree.QName(el).localname
    if tag == 'grpSp':
        return el.find('p:grpSpPr/a:xfrm', NS)
    if tag == 'graphicFrame':
        return el.find('p:xfrm', NS)
    return el.find('p:spPr/a:xfrm', NS)


def box_of(el):
    xf = own_xfrm(el)
    if xf is None or xf.find('a:off', NS) is None:
        return None
    o, e = xf.find('a:off', NS), xf.find('a:ext', NS)
    return [int(o.get('x')) / EMU, int(o.get('y')) / EMU, int(e.get('cx')) / EMU, int(e.get('cy')) / EMU]


def signature(el, rels, deck):
    """content of an object without ids, names, creation ids and its own position; media by their bytes"""
    e = copy.deepcopy(el)
    for c in e.iter(P + 'cNvPr'):
        for k in ('id', 'name', 'descr'):
            c.attrib.pop(k, None)
        for x in c.findall('a:extLst', NS):
            c.remove(x)
    for c in list(e.iter('{%s}creationId' % NS['a16'])):
        c.getparent().remove(c)
    for c in e.iter():
        for k, v in list(c.attrib.items()):
            if k.startswith(RA):
                c.set(k, deck.md5(rels[v]) if rels.get(v) else 'ext')
    xf = own_xfrm(e)
    if xf is not None:
        for c in list(xf):
            if etree.QName(c).localname in ('off', 'ext'):
                xf.remove(c)
    return hashlib.md5(etree.tostring(e, method='c14n')).hexdigest()


def objects(deck, part):
    root = xml(deck.z.read(part))
    rels = deck.rels(part)
    out = []
    for el in root.find('p:cSld/p:spTree', NS):
        tag = etree.QName(el).localname
        if tag in ('nvGrpSpPr', 'grpSpPr', 'extLst'):
            continue
        if tag == 'AlternateContent':
            ch = el.find('mc:Choice', NS)
            if ch is None or not len(ch):
                continue
            el = ch[0]
            tag = etree.QName(el).localname
        c = el.find('.//p:cNvPr', NS)
        if c is None:
            continue
        ph = el.find('.//p:nvPr/p:ph', NS)
        if ph is not None and ph.get('type') in SKIP_PH:
            continue
        o = Obj()
        o.el, o.kind, o.id, o.name = el, tag, c.get('id'), c.get('name')
        o.box = box_of(el)
        o.sig = signature(el, rels, deck)
        o.text = ''.join(el.xpath('.//a:t/text()', namespaces=NS))
        o.pics = list(pictures(el, rels, deck))          # (media part, box in pt, crop) of every picture it draws
        o.part = part
        out.append(o)
    return root, out


def pictures(el, rels, deck, tf=None):
    """pictures an object draws, with boxes in slide pt (groups mapped through their child frames)"""
    tag = etree.QName(el).localname
    tf = tf or (lambda b: b)
    if tag == 'pic':
        b = box_of(el)
        blip = el.find('.//asvg:svgBlip', NS)
        if blip is None:
            blip = el.find('.//a:blip', NS)
        if b is not None and blip is not None and rels.get(blip.get(RA + 'embed')):
            sr = el.find('.//a:srcRect', NS)
            crop = tuple(int(sr.get(k, 0)) / 100000.0 for k in ('l', 't', 'r', 'b')) if sr is not None else (0, 0, 0, 0)
            yield rels[blip.get(RA + 'embed')], tf(b), crop
    elif tag == 'grpSp':
        xf = el.find('p:grpSpPr/a:xfrm', NS)
        if xf is None or xf.find('a:chOff', NS) is None:
            return
        o, e = xf.find('a:off', NS), xf.find('a:ext', NS)
        co, ce = xf.find('a:chOff', NS), xf.find('a:chExt', NS)
        ox, oy, ex, ey = [int(v) / EMU for v in (o.get('x'), o.get('y'), e.get('cx'), e.get('cy'))]
        cx, cy, cw, chh = [int(v) / EMU for v in (co.get('x'), co.get('y'), ce.get('cx'), ce.get('cy'))]
        sx, sy = (ex / cw if cw else 1.0), (ey / chh if chh else 1.0)
        inner = lambda b: tf([ox + (b[0] - cx) * sx, oy + (b[1] - cy) * sy, b[2] * sx, b[3] * sy])
        for ch in el:
            yield from pictures(ch, rels, deck, inner)


# ================================================================ ink (rendered pictures)
_ink_cache = {}


def render_mask(deck, media, wpx, hpx):
    key = (deck.md5(media), wpx, hpx)
    if key in _ink_cache:
        return _ink_cache[key]
    m = None
    if media in deck.files and wpx > 0 and hpx > 0:
        data = deck.z.read(media)
        ext = media.rsplit('.', 1)[-1].lower()
        try:
            if ext == 'svg':
                img = QImage(wpx, hpx, QImage.Format_ARGB32)
                img.fill(0)
                p = QPainter(img)
                QSvgRenderer(QByteArray(data)).render(p, QRectF(0, 0, wpx, hpx))
                p.end()
                a = np.frombuffer(img.bits().asstring(img.byteCount()), np.uint8).reshape(hpx, wpx, 4)
                rgb = a[:, :, 2::-1].copy()                                  # Qt stores B, G, R, A
                m = ((a[:, :, 3] > INK_ALPHA) & (rgb.min(axis=2) < 230), rgb)  # white fills are not lines
            elif ext in ('png', 'gif', 'jpg', 'jpeg'):
                im = Image.open(io.BytesIO(data)).convert('RGBA').resize((wpx, hpx))
                a = np.asarray(im)
                m = ((a[:, :, 3] > INK_ALPHA) & (a[:, :, :3].min(axis=2) < 230), a[:, :, :3].copy())
        except Exception:
            m = None
    _ink_cache[key] = m
    return m


def ink(deck, obj, dx=0.0, dy=0.0):
    """list of (x0 px, y0 px, mask, rgb) for the object's pictures, shifted by (dx, dy) pt; None if nothing measurable"""
    out = []
    for media, b, (l, t, r, bt) in obj.pics:
        fw, fh = b[2] / max(1e-6, 1 - l - r), b[3] / max(1e-6, 1 - t - bt)     # the uncropped image
        fx, fy = b[0] - l * fw + dx, b[1] - t * fh + dy
        m = render_mask(deck, media, int(round(fw * S)), int(round(fh * S)))
        if m is None:
            continue
        x0, y0 = int(round(fx * S)), int(round(fy * S))
        cx0, cy0 = int(round((b[0] + dx) * S)) - x0, int(round((b[1] + dy) * S)) - y0
        cx1, cy1 = cx0 + int(round(b[2] * S)), cy0 + int(round(b[3] * S))
        sl = (slice(max(0, cy0), max(0, cy1)), slice(max(0, cx0), max(0, cx1)))
        out.append((x0 + max(0, cx0), y0 + max(0, cy0), m[0][sl], m[1][sl]))
    return out or None


def canvas(deck, parts, rgb=False):
    """union ink of several ink lists on the slide canvas (with the colour last painted, if rgb)"""
    W, H = int(round(deck.W * S)), int(round(deck.H * S))
    c = np.zeros((H, W), bool)
    col = np.zeros((H, W, 3), np.int16) if rgb else None
    for lst in parts:
        for x0, y0, m, k in lst or []:
            xa, ya = max(0, x0), max(0, y0)
            xb, yb = min(W, x0 + m.shape[1]), min(H, y0 + m.shape[0])
            if xb > xa and yb > ya:
                mm = m[ya - y0:yb - y0, xa - x0:xb - x0]
                c[ya:yb, xa:xb] |= mm
                if rgb:
                    col[ya:yb, xa:xb][mm] = k[ya - y0:yb - y0, xa - x0:xb - x0][mm]
    return (c, col) if rgb else c


SAME_COLOUR = 80          # largest channel difference of two inks that count as the same line


MIN_RUN = 6.0             # a shared piece counts when it runs this far (pt): junction dots (7 pt) do, crossings of
                          # 3 pt lines (about 4.5 pt with anti-aliasing) do not


def shared(deck, a, b, minus=None, mask=False):
    """pixels both ink lists draw in the same colour, minus a canvas; returns (count, smaller drawing, bbox in pt)
    and, with mask, the shared pixels and a's colours. The same spot drawn in another colour (black turning grey, an
    icon over a wire) is a change, not a return. Only pieces at least MIN_RUN long count: two different drawings that
    merely cross share a small blob, a line drawn by both shares a long piece."""
    none = (0, 0, None, None, None) if mask else (0, 0, None)
    if not a or not b:
        return none
    (ca, ka), (cb, kb) = canvas(deck, [a], True), canvas(deck, [b], True)
    both = ca & cb & (np.abs(ka - kb).max(axis=2) < SAME_COLOUR)
    if minus is not None:
        both &= ~minus
    if not both.any():
        return none
    lab, k = ndimage.label(both)
    keep = np.zeros(k + 1, bool)
    for j, sl in enumerate(ndimage.find_objects(lab), 1):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) >= MIN_RUN * S:
            keep[j] = True
    both = keep[lab]
    n = int(both.sum())
    if not n:
        return none
    ys, xs = np.nonzero(both)
    out = (n, int(min(ca.sum(), cb.sum())), '(%.0f, %.0f)-(%.0f, %.0f) pt' % (
        xs.min() / S, ys.min() / S, xs.max() / S, ys.max() / S))
    return out + (both, ka) if mask else out


def worth(n, small):
    return n >= MIN_PX and small and n >= MIN_FRAC * small


# ================================================================ timing
def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def timeline(root, W, H):
    """effect events of the main sequence in slide time: dicts with spid, cls, start, end, rep, label, motion end"""
    ev = []
    main = root.find('.//p:cTn[@nodeType="mainSeq"]/p:childTnLst', NS)
    if main is None:
        return ev
    T, click = 0.0, 0
    for gpar in main:
        g = gpar.find('p:cTn', NS)
        auto = g.find('p:stCondLst/p:cond[@evt="onBegin"]', NS) is not None
        if not auto:
            click += 1
        label = 'after the transition' if auto and click == 0 else 'click %d' % click if not auto else 'after click %d' % click
        gend = 0.0
        for ip in g.findall('p:childTnLst/p:par', NS):
            ic = ip.find('p:cTn', NS)
            D = num(ic.find('p:stCondLst/p:cond', NS).get('delay')) if ic.find('p:stCondLst/p:cond', NS) is not None else 0
            for ep in ic.findall('p:childTnLst/p:par', NS):
                ec = ep.find('p:cTn', NS)
                cls = ec.get('presetClass')
                if not cls:
                    continue
                cond = ec.find('p:stCondLst/p:cond', NS)
                d = num(cond.get('delay')) if cond is not None else 0
                rep = ec.get('repeatCount') == 'indefinite'
                durs = [num(c.get('dur')) for c in ec.iter(P + 'cTn') if c is not ec and c.get('dur') not in (None, 'indefinite')]
                dur = max(durs) if durs else 0.0
                tgt = ep.find('.//p:spTgt', NS)
                if tgt is None:
                    continue
                mot = None
                for am in ep.iter(P + 'animMotion'):
                    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*(?:[eE]-?\d+)?', am.get('path', ''))]
                    if len(nums) >= 2:
                        mot = (nums[-2] * W, nums[-1] * H)
                rot = sum(num(ar.get('by')) / 60000.0 for ar in ep.iter(P + 'animRot')) or None   # clockwise deg
                s = T + D + d
                ev.append(dict(spid=tgt.get('spid'), cls=cls, preset=ec.get('presetID'), start=s, end=s + dur,
                               rep=rep, label=label, motion=mot, rot=rot))
                gend = max(gend, D + d + (0 if rep else dur))
        T += gend + CLICK_GAP
    return ev


def vis_events(ev, spid):
    return sorted((e for e in ev if e['spid'] == spid and e['cls'] in ('entr', 'exit')), key=lambda e: e['start'])


def visible_at_start(ev, o):
    v = vis_events(ev, o.id)
    return not v or v[0]['cls'] == 'exit'


def visible_at_end(ev, o):
    v = vis_events(ev, o.id)
    return not v or v[-1]['cls'] == 'entr'


def shift_at(ev, o, t=float('inf')):
    """motion offset (pt) of the object at time t: the end of its last finished path that does not repeat"""
    ms = [e for e in ev if e['spid'] == o.id and e['cls'] == 'path' and e['motion'] and not e['rep'] and e['end'] <= t]
    return max(ms, key=lambda e: e['end'])['motion'] if ms else (0.0, 0.0)


def rot_at(ev, o, t):
    """spin (deg, clockwise) of the object at time t, a running spin counted in proportion"""
    r = 0.0
    for e in ev:
        if e['spid'] == o.id and e['rot'] and not e['rep'] and t > e['start']:
            r += e['rot'] * min(1.0, (t - e['start']) / max(1.0, e['end'] - e['start']))
    return round(r, 1)


def rotate(deck, c, k, centre, deg):
    """turn a canvas (mask, colours) clockwise by deg about centre (pt)"""
    th = np.radians(deg)
    cs, sn = np.cos(th), np.sin(th)
    M = np.array([[cs, -sn], [sn, cs]])                   # output (y, x) -> input (y, x)
    cyx = np.array([centre[1] * S, centre[0] * S])
    off = cyx - M @ cyx
    m = ndimage.affine_transform(c.astype(np.uint8), M, offset=off, order=0) > 0
    rgb = np.stack([ndimage.affine_transform(k[:, :, j], M, offset=off, order=0) for j in range(3)], axis=2)
    return m, rgb


def alpha(ev, o, t):
    a = 1.0 if visible_at_start(ev, o) else 0.0
    for e in vis_events(ev, o.id):
        if t < e['start']:
            break
        dur = max(1.0, e['end'] - e['start'])
        k = 1.0 if (e['preset'] == '1' or t >= e['end']) else (t - e['start']) / dur
        a = k if e['cls'] == 'entr' else 1.0 - k
    return a


# ================================================================ checks
def transition_kind(raw):
    if b'p159:morph' in raw:
        return 'Morph'
    m = re.search(rb'<p:transition[^>]*>\s*<(?:p|p14):(\w+)', raw)
    return m.group(1).decode().capitalize() if m else 'None'


def check_pair(deck, i, cache):
    """slide i-1 -> slide i (0-based)"""
    flags = []
    (_, p0), (_, p1) = deck.slides[i - 1], deck.slides[i]
    r0, o0 = cache(p0)
    r1, o1 = cache(p1)
    ev0, ev1 = timeline(r0, deck.W, deck.H), timeline(r1, deck.W, deck.H)
    kind = transition_kind(deck.z.read(p1))
    end0 = [o for o in o0 if visible_at_end(ev0, o)]
    entered0 = {o.id for o in end0 if vis_events(ev0, o.id)}
    start1 = [o for o in o1 if visible_at_start(ev1, o)]
    later1 = [o for o in o1 if not visible_at_start(ev1, o)]
    pos0 = {o.id: shift_at(ev0, o) for o in end0}
    ink0 = lambda o: ink(deck, o, *pos0[o.id])
    ink1 = lambda o: ink(deck, o)

    held, out, inn, pair = [], [], [], {}
    if kind == 'Morph':
        free = list(start1)
        for o in end0:                                    # by name, identical content first
            c = [n for n in free if n.name == o.name]
            c.sort(key=lambda n: n.sig != o.sig)
            if c:
                pair[o.id] = c[0]
                free.remove(c[0])
        for o in end0:                                    # then by identical content
            if o.id not in pair:
                c = [n for n in free if n.sig == o.sig and n.kind == o.kind]
                if c:
                    pair[o.id] = c[0]
                    free.remove(c[0])
        for o in end0:
            n = pair.get(o.id)
            if n is None:
                out.append(o)
            elif n.sig == o.sig and o.id not in entered0:
                held.append((o, n))
            else:
                out.append(o)
                inn.append(n)
                if n.sig == o.sig:
                    flags.append(('HELD-ENTR', n.name, 'slide %d shows it by an entrance effect, so Morph fades it '
                                  'out and in although slide %d has it unchanged' % (i, i + 1)))
                elif o.kind == n.kind == 'sp' and o.text and n.text and o.text != n.text:
                    flags.append(('TEXT', n.name, 'text "%s" becomes "%s": Morph moves the letters one by one'
                                  % (o.text[:30], n.text[:30])))
        inn += free
        held_ink = canvas(deck, [ink0(o) for o, n in held] + [ink1(n) for o, n in held])
        swaps = {(o.id, pair[o.id].id) for o in out if o.id in pair and pair[o.id].sig != o.sig}
        hits = {}                                         # incoming object -> leaving objects that share its lines
        for o in out:
            a = ink0(o)
            if not a:
                continue
            for n in inn:
                if pair.get(o.id) is n and n.sig == o.sig:
                    continue                              # already reported as HELD-ENTR
                cnt, small, bb = shared(deck, a, ink1(n), held_ink)
                if (o.id, n.id) in swaps and o.box and n.box:
                    # Morph swaps a renamed-image picture inside one frame that slides from the old box to the new
                    # one, so lines at the same place in both frames dim and return even when the frame moves
                    dx, dy = o.box[0] + pos0[o.id][0] - n.box[0], o.box[1] + pos0[o.id][1] - n.box[1]
                    c2, s2, b2 = shared(deck, a, ink(deck, n, dx, dy))
                    if c2 > cnt:
                        cnt, small, bb = c2, s2, b2 + ' (in the sliding frame)'
                if worth(cnt, small):
                    hits.setdefault(n.id, (n, []))[1].append((o, cnt, bb))
        for n, lst in hits.values():
            swap = [h for h in lst if (h[0].id, n.id) in swaps]
            others = ', '.join('"%s"' % o.name for o, c, b in lst if (o.id, n.id) not in swaps)
            area = sum(c for o, c, b in lst) / S / S
            if swap:
                flags.append(('SWAP', n.name, 'same name, another image: %.0f pt^2 of shared lines at %s fade out and '
                              'back in%s' % (area, swap[0][2], ' (also drawn by %s)' % others if others else '')))
            else:
                flags.append(('CROSS', n.name, '%s (slide %d) leaves and "%s" arrives over %.0f pt^2 of the same lines '
                              'at %s' % (others, i, n.name, area, lst[0][2])))
        stay = canvas(deck, [ink0(o) for o, n in held] + [ink1(n) for o, n in held] + [ink1(n) for n in inn])
    else:
        stay = canvas(deck, [ink1(n) for n in start1])
        out = end0
    # lines that leave at the transition and come back later on slide i
    for o in out:
        a = ink0(o)
        for n in later1:
            if a:
                cnt, small, bb = shared(deck, a, ink(deck, n, *shift_at(ev1, n, vis_events(ev1, n.id)[0]['start'])), stay)
                if worth(cnt, small):
                    flags.append(('BACK-LATER', n.name, '"%s" leaves at the %s transition and %.0f pt^2 of its lines at %s '
                                  'come back with "%s" %s' % (o.name, kind, cnt / S / S, bb, n.name,
                                                             vis_events(ev1, n.id)[0]['label'])))
            elif o.kind == n.kind and o.sig == n.sig and o.box == n.box and o.box is not None:
                flags.append(('BACK-LATER', n.name, '"%s" leaves at the %s transition and comes back %s'
                              % (o.name, kind, vis_events(ev1, n.id)[0]['label'])))
    return kind, flags


def check_slide(deck, i, cache):
    """lines that fade out and back in on one slide"""
    flags = []
    root, objs = cache(deck.slides[i][1])
    ev = timeline(root, deck.W, deck.H)
    by = {o.id: o for o in objs}
    exits = [e for e in ev if e['cls'] == 'exit' and e['spid'] in by]
    entrs = [e for e in ev if e['cls'] == 'entr' and e['spid'] in by]
    seen = set()
    canv = {}

    def on_canvas(k, t):
        """the object's ink at time t: moved by its finished motion paths, turned by its spins"""
        sh, rt = shift_at(ev, k, t), rot_at(ev, k, t)
        key = (k.id, sh, rt)
        if key not in canv:
            lk = ink(deck, k, *sh)
            c = canvas(deck, [lk], True) if lk else None
            if c is not None and rt % 360 and k.box:
                c = rotate(deck, c[0], c[1], (k.box[0] + sh[0] + k.box[2] / 2, k.box[1] + sh[1] + k.box[3] / 2), rt)
            canv[key] = c
        return canv[key]

    turning = {e['spid'] for e in ev if e['rot']}

    def dips(M, ref, t0, t1):
        """share of the shared pixels that every object on the slide together lets dim below 90 % and come back"""
        ys, xs = np.nonzero(M)
        if len(xs) > 400:
            pick = np.random.default_rng(0).choice(len(xs), 400, replace=False)
            ys, xs = ys[pick], xs[pick]
        col = ref[ys, xs]
        hit_at = lambda k, t: (lambda c: None if c is None else
                               c[0][ys, xs] & (np.abs(c[1][ys, xs].astype(int) - col).max(axis=1) < SAME_COLOUR))(on_canvas(k, t))
        covers, turners = [], [k for k in objs if k.id in turning]
        for k in objs:
            if k.id not in turning:
                h = hit_at(k, t0)
                if h is not None and h.any():
                    covers.append((k, h))

        def cov(t):
            gap = np.ones(len(xs))
            for k, hit in covers + [(k, hit_at(k, t)) for k in turners]:
                if hit is not None:
                    gap *= np.where(hit, 1 - alpha(ev, k, t), 1.0)
            return 1 - gap
        ts = np.linspace(t0, t1, 60)
        cv = np.array([cov(t) for t in ts])
        ok_out = (cov(t0 - 1) > 0.99) & (cov(t1 + 1) > 0.99)
        bad = ok_out & (cv.min(axis=0) < 0.9)
        if not bad.any():
            return 0.0, None
        j = int(np.argmax(((cv < 0.9) & ok_out).sum(axis=1)))      # the moment most of these lines are dim
        tw = ts[j]
        fading = [k.name for k, h in covers + [(k, hit_at(k, tw)) for k in turners]       # drawn earlier in the
                  if h is not None and (h & bad).any()                                       # window, dimmer now
                  and alpha(ev, k, tw) < max(alpha(ev, k, t) for t in ts[:j + 1]) - 0.05]
        return float(bad.mean()), dict(t=tw, worst=float(cv[:, bad].min()), fading=fading,
                                       box='(%.0f, %.0f)-(%.0f, %.0f) pt' % (xs[bad].min() / S, ys[bad].min() / S,
                                                                            xs[bad].max() / S, ys[bad].max() / S))

    for x in exits:
        a = by[x['spid']]
        for y in entrs:
            b = by[y['spid']]
            if y['end'] < x['start'] or (a.id, b.id) in seen:
                continue                                  # b was fully in before a began to leave
            t0, t1 = min(x['start'], y['start']), max(x['end'], y['end'])
            ia = ink(deck, a, *shift_at(ev, a, x['start']))
            ib = ink(deck, b, *shift_at(ev, b, y['start']))
            if ia and ib:
                cnt, small, bb, M, ref = shared(deck, ia, ib, mask=True)
                if not worth(cnt, small):
                    continue
                share, d = dips(M, ref, t0, t1)
                if share < 0.2:
                    continue
                key = ('in', b.id)                        # one report per object that brings lines back
                if key in seen:
                    continue
                seen.add(key)
                g0 = min(e['start'] for e in ev if e['label'] == y['label'])
                flags.append(('IN-SLIDE', b.name, 'lines at %s dim to %.0f %% %.0f ms into "%s": %s fade(s) before "%s" '
                              'brings them back' % (d['box'], 100 * d['worst'], d['t'] - g0, y['label'],
                                                    ', '.join('"%s"' % n for n in d['fading']) or '"%s"' % a.name,
                                                    b.name)))
            elif a.sig == b.sig and a.box == b.box and a.box is not None:
                ts = np.linspace(t0, t1, 60)
                cov = [1 - (1 - alpha(ev, a, t)) * (1 - alpha(ev, b, t)) for t in ts]
                before = 1 - (1 - alpha(ev, a, t0 - 1)) * (1 - alpha(ev, b, t0 - 1))
                after = 1 - (1 - alpha(ev, a, t1 + 1)) * (1 - alpha(ev, b, t1 + 1))
                if not (before > 0.99 and after > 0.99 and min(cov) < 0.9) or (a.id, b.id) in seen:
                    continue
                seen.add((a.id, b.id))
                flags.append(('IN-SLIDE', b.name, '"%s" leaves (%s) and "%s", the same content at the same place, '
                              'comes back (%s)' % (a.name, x['label'], b.name, y['label'])))
    return flags


def check(path, only=None, quiet=False):
    deck = Deck(path)
    memo = {}
    cache = lambda part: memo.setdefault(part, objects(deck, part))
    result = []
    for i in range(len(deck.slides)):
        if only and (i + 1) not in only:
            continue
        if i > 0:
            kind, fl = check_pair(deck, i, cache)
            result += [(i + 1, 'transition', kind) + f for f in fl]
        result += [(i + 1, 'slide', '') + f for f in check_slide(deck, i, cache)]
    if not quiet:
        print(os.path.basename(path))
        if not result:
            print('  no fade-out-then-fade-in found')
        for n, where, kind, code, name, msg in result:
            head = 's%d > s%d  %s' % (n - 1, n, kind) if where == 'transition' else 's%d' % n
            print('  %-18s %-10s %-14s %s' % (head, code, name, msg))
    return result


def run_cases():
    base = os.path.join(ROOT, 'output', 'morph_cases')
    cases = json.load(open(os.path.join(base, 'cases.json')))
    bad = 0
    for c in cases:
        got = check(os.path.join(base, c['deck']), c.get('slides'), quiet=True)
        found = sorted({(code, name) for n, w, k, code, name, msg in got})
        want = sorted(tuple(x) for x in c['expect'])
        ok = found == want
        bad += not ok
        print('%-4s %-34s %s' % ('ok' if ok else 'FAIL', c['deck'], c.get('note', '')))
        if not ok:
            print('     expected', want)
            print('     found   ', found)
    print('%d of %d cases pass' % (len(cases) - bad, len(cases)))
    return bad


if __name__ == '__main__':
    if sys.argv[1:2] == ['--cases']:
        sys.exit(1 if run_cases() else 0)
    flagged = check(sys.argv[1], {int(v) for v in sys.argv[2:]} or None)
    sys.exit(1 if flagged else 0)
