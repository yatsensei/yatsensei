"""Generate the YAT monogram used in the nav, the favicon and the app icons.

The letters are described by stroke centrelines plus a width; this offsets each
centreline into a closed outline so corners come out as true miters and the
terminals can be cut horizontally (stroking a path would cut them square to the
stroke instead, which leaves the Y's arms and the A's feet looking sheared).

Run from anywhere:  python3 tools/build-logo.py
Writes tools/logo-yat.svg and rewrites favicon.svg.
"""
import math
import os

BOX_W, BOX_H = 72.0, 100.0   # nominal per-letter box
STROKE = 18.0
HW = STROKE / 2.0
GAP = 15.0                   # gap between letters, measured on their real extents


# --------------------------------------------------------------------------
# outline machinery
# --------------------------------------------------------------------------
def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def _offset(pts, hw):
    """Offset a polyline by hw (signed), mitering interior vertices."""
    segs = []
    for a, b in zip(pts, pts[1:]):
        ux, uy = _unit(a, b)
        nx, ny = -uy * hw, ux * hw
        segs.append(((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (ux, uy)))

    out = [segs[0][0]]
    for (p0, p1, u0), (q0, _q1, u1) in zip(segs, segs[1:]):
        d = u0[0] * u1[1] - u0[1] * u1[0]
        if abs(d) < 1e-9:                      # collinear, nothing to miter
            out.append(p1)
            continue
        t = ((q0[0] - p0[0]) * u1[1] - (q0[1] - p0[1]) * u1[0]) / d
        out.append((p0[0] + u0[0] * t, p0[1] + u0[1] * t))
    out.append(segs[-1][1])
    return out


def _cut(p, q, y):
    """Slide an endpoint along its own edge until it lands on the line y."""
    ux, uy = _unit(p, q)
    if abs(uy) < 1e-9:
        return p
    return (p[0] + ux * (y - p[1]) / uy, y)


def stroke(pts, width=STROKE, cut_start=None, cut_end=None):
    hw = width / 2.0
    left, right = _offset(pts, hw), _offset(pts, -hw)
    if cut_start is not None:
        left[0] = _cut(left[0], left[1], cut_start)
        right[0] = _cut(right[0], right[1], cut_start)
    if cut_end is not None:
        left[-1] = _cut(left[-1], left[-2], cut_end)
        right[-1] = _cut(right[-1], right[-2], cut_end)
    return left + right[::-1]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def half_thickness(dx, dy, hw):
    """Horizontal half-width of a stroke running dx across dy."""
    return hw * math.hypot(dx, dy) / abs(dy)


# --------------------------------------------------------------------------
# letters
# --------------------------------------------------------------------------
def letter_Y():
    """Splayed arms meeting a stem, both arms cut flat across the cap line."""
    junction = 44.0
    arms = stroke([(0.0, 0.0), (BOX_W / 2, junction), (BOX_W, 0.0)],
                  cut_start=0.0, cut_end=0.0)
    stem = rect(BOX_W / 2 - HW, junction, BOX_W / 2 + HW, BOX_H)
    return [arms, stem]


def _apex_for_sharp_tip(dx, base, hw, tip=0.0):
    """Centreline apex whose miter carries the point exactly to y=tip."""
    apex = base / 2
    for _ in range(60):                       # converges in a handful of passes
        apex = tip + half_thickness(dx, base - apex, hw) * (base - apex) / dx
    return apex


def letter_A():
    """Splayed legs to a sharp apex, crossbar set low, feet cut flat."""
    apex = _apex_for_sharp_tip(BOX_W / 2, BOX_H, HW)
    legs = stroke([(0.0, BOX_H), (BOX_W / 2, apex), (BOX_W, BOX_H)],
                  cut_start=BOX_H, cut_end=BOX_H)

    # Span the crossbar to the legs' outer edge at its TOP: lower down the legs
    # are wider still, so both ends stay buried and the join reads clean.
    bar_top, bar_bot = 62.0, 62.0 + STROKE
    t = (bar_top - apex) / (BOX_H - apex)
    centre_x = BOX_W / 2 * (1 - t)
    outer = half_thickness(BOX_W / 2, BOX_H - apex, HW)
    bar = rect(centre_x - outer, bar_top, BOX_W - (centre_x - outer), bar_bot)
    return [legs, bar]


def letter_T():
    return [rect(0.0, 0.0, BOX_W, STROKE),
            rect(BOX_W / 2 - HW, 0.0, BOX_W / 2 + HW, BOX_H)]


# --------------------------------------------------------------------------
# compose
# --------------------------------------------------------------------------
def bbox(groups):
    pts = [p for g in groups for p in g]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def shift(groups, dx, dy=0.0):
    return [[(x + dx, y + dy) for x, y in g] for g in groups]


def compose():
    letters, cursor = [], 0.0
    for build in (letter_Y, letter_A, letter_T):
        g = build()
        x0, _, x1, _ = bbox(g)
        letters.append(shift(g, cursor - x0))       # butt each letter's real edge
        cursor += (x1 - x0) + GAP
    flat = [g for L in letters for g in L]
    x0, y0, x1, y1 = bbox(flat)
    return shift(flat, -x0, -y0), (x1 - x0), (y1 - y0)


def _signed_area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def to_path(poly):
    # Subpaths of one <path> must all wind the same way, or the nonzero fill
    # rule subtracts the overlaps instead of unioning them (a stem would punch
    # a notch out of the arms it joins).
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in poly) + " Z"


shapes, W, H = compose()
D = " ".join(to_path(p) for p in shapes)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}">
  <defs>
    <linearGradient id="yatg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W:.2f}" y2="0">
      <stop offset="0" stop-color="#6c5ce7"/>
      <stop offset="1" stop-color="#00d9c0"/>
    </linearGradient>
  </defs>
  <path d="{D}" fill="url(#yatg)"/>
</svg>'''

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(root, "tools", "logo-yat.svg"), "w").write(svg)

# favicon: same letterforms, fitted into a rounded tile
PAD = 14.0
k = (100 - 2 * PAD) / W
ty = (100 - H * k) / 2
open(os.path.join(root, "favicon.svg"), "w").write(
    f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Akein Tsung">
  <title>Akein Tsung</title>
  <defs>
    <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{PAD:.2f}" y1="0" x2="{100 - PAD:.2f}" y2="0">
      <stop offset="0" stop-color="#6c5ce7"/>
      <stop offset="1" stop-color="#4d9df5"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="22" fill="#0b0e14"/>
  <g transform="translate({PAD:.2f} {ty:.2f}) scale({k:.5f})">
    <path d="{D}" fill="url(#g)"/>
  </g>
</svg>''')

print(f"viewBox 0 0 {W:.2f} {H:.2f}   aspect {W / H:.3f}")
print(f"nav width at 24.3px tall: {24.3 * W / H:.1f}px")
print(D)
