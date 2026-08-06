import re
"""Rebuild the YAT monogram as vector outlines.

Strokes are described by their centreline plus a width; this offsets each
centreline into a closed outline so corners are true miters and the leg ends
can be cut horizontally (a stroked path would cut them perpendicular).
"""
import math

CX = 292.0          # every element is symmetric about this axis
VB = (584, 428)


def _unit(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def _side(pts, hw):
    """Offset a polyline by hw (signed), mitering interior vertices."""
    segs = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ux, uy = _unit(ax, ay, bx, by)
        nx, ny = -uy * hw, ux * hw          # left normal, scaled
        segs.append(((ax + nx, ay + ny), (bx + nx, by + ny), (ux, uy)))

    out = [segs[0][0]]
    for (p0, p1, u0), (q0, q1, u1) in zip(segs, segs[1:]):
        # intersect the two offset lines
        d = u0[0] * u1[1] - u0[1] * u1[0]
        if abs(d) < 1e-9:
            out.append(p1)
            continue
        t = ((q0[0] - p0[0]) * u1[1] - (q0[1] - p0[1]) * u1[0]) / d
        out.append((p0[0] + u0[0] * t, p0[1] + u0[1] * t))
    out.append(segs[-1][1])
    return out


def _cut_horizontal(p, q, y):
    """Slide the endpoint along its own edge until it sits on the line y."""
    ux, uy = _unit(p[0], p[1], q[0], q[1])
    if abs(uy) < 1e-9:
        return p
    return (p[0] + ux * (y - p[1]) / uy, y)


def outline(pts, width, cut_start=None, cut_end=None):
    """Closed outline for a stroked polyline, with optional horizontal end cuts."""
    hw = width / 2.0
    left, right = _side(pts, hw), _side(pts, -hw)
    if cut_start is not None:
        left[0] = _cut_horizontal(left[0], left[1], cut_start)
        right[0] = _cut_horizontal(right[0], right[1], cut_start)
    if cut_end is not None:
        left[-1] = _cut_horizontal(left[-1], left[-2], cut_end)
        right[-1] = _cut_horizontal(right[-1], right[-2], cut_end)
    ring = left + right[::-1]
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in ring) + " Z"


def mirror(x):
    return 2 * CX - x


# ---- the W: two splayed outer legs meeting a narrow central peak ----------
W_TOP, W_BOT = 127.0, 396.0
W_WIDTH = 41.0
w_centre = [
    (86.0, W_TOP),      # outer top left
    (210.0, 354.0),     # bottom left vertex (miter carries the point to W_BOT)
    (CX, 225.0),        # central peak (miter carries the tip up to ~185)
    (mirror(210.0), 354.0),
    (mirror(86.0), W_TOP),
]
w_path = outline(w_centre, W_WIDTH, cut_start=W_TOP, cut_end=W_TOP)

# ---- the chevron nested under the peak -----------------------------------
CH_W = 38.0
ch_centre = [(246.0, 396.0), (CX, 311.0), (mirror(246.0), 396.0)]
ch_path = outline(ch_centre, CH_W, cut_start=W_BOT, cut_end=W_BOT)

# ---- the T: crossbar with ends raked parallel to the outer legs -----------
BAR_TOP, BAR_BOT = 62.0, 100.0
rake = (w_centre[1][0] - w_centre[0][0]) / (w_centre[1][1] - w_centre[0][1])
dx = (BAR_BOT - BAR_TOP) * rake
bar = [(99.0, BAR_TOP), (mirror(99.0), BAR_TOP),
       (mirror(99.0) - dx, BAR_BOT), (99.0 + dx, BAR_BOT)]
bar_path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in bar) + " Z"

STEM_W, STEM_BOT = 46.0, 158.0
stem_path = (f"M {CX - STEM_W/2:.1f} {BAR_BOT} L {CX + STEM_W/2:.1f} {BAR_BOT} "
             f"L {CX + STEM_W/2:.1f} {STEM_BOT} L {CX - STEM_W/2:.1f} {STEM_BOT} Z")

ys=[float(v) for v in re.findall(r"-?[\d.]+ (-?[\d.]+)", w_path)]
xs=[float(v) for v in re.findall(r"(-?[\d.]+) -?[\d.]+", w_path)]
cy=[float(v) for v in re.findall(r"-?[\d.]+ (-?[\d.]+)", ch_path)]
print(f"W  peak_tip={min(v for v in ys if v>150):.1f} (want 185)  bottom={max(ys):.1f} (want 396)  outer_x={min(xs):.1f} (want 65)")
print(f"CH apex={min(cy):.1f} (want 268)")
print("W    ", w_path)
print("CHEV ", ch_path)
print("T    ", bar_path + " " + stem_path)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB[0]} {VB[1]}" fill="none">
  <defs>
    <linearGradient id="lg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="var(--accent, #6c5ce7)"/>
      <stop offset="1" stop-color="var(--accent-2, #00d9c0)"/>
    </linearGradient>
  </defs>
  <path d="{bar_path} {stem_path}" fill="url(#lg)"/>
  <path d="{w_path}" fill="#fff"/>
  <path d="{ch_path}" fill="url(#lg)"/>
</svg>'''
open("logo-built.svg", "w").write(svg)
print("\nwrote logo-built.svg")
