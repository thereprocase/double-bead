# FDM two-bead font — reproducible specification

Everything needed to regenerate the glyphs, the three settings, and the checks.
Coordinates are in extrusion widths (w). Y points down.

## 1. Units and guides

```
w            = extrusion width (e.g. 0.42 mm on a 0.4 nozzle)
ASC, XH, BASE, DESC = -4, 0, 10, 14      # guide lines (y, down)
lowercase    : body y ∈ [0,10], ascenders to -4, descenders to 14
figures      : y ∈ [-4,10]
font units   : 1w = 50 u, UPM 1000, Y_font = (10 - y) * 50
               → baseline 0, x-height 500, ascender 700, descender -200
physical     : em size = 20 * w   (0.42 mm → 8.4 mm em, ≈ 23.8 pt)
```

## 2. Slicer model (Arachne, PrusaSlicer/Orca derivation)

```
mb     = min_bead_width / w                   # default 0.85 (of nozzle); treat as 0.85w
split  = 2*mb - 1                             # odd → even threshold  (0.70)
add    = mb                                   # even → odd threshold  (0.85)
beads(T) = n + [ (T - n) >= (n odd ? split : add) ],  n = floor(T)
bands  : 2 beads T ∈ [2mb, 2+add) = [1.70, 2.85)
         3 beads      [2.85, 3.70)
         4 beads      [3.70, 4.85)
```

At T = 2w every stroke is the outer-wall loop passing itself: no inner wall, no gap fill.

## 3. Local-thickness algebra (stroke = 2w)

Local thickness = diameter of the largest inscribed circle.

```
straight                                   2.00
L corner, outer R2 centred on inner vertex 2.00
L corner, square outer                     8 - 4√2                (= 2.34)
L corner, outer R2 + inner fillet ρ        2 + ρ(√2 - 1)          (ρ=0.5 → 2.21)
T junction                                 2.50
crossing at included angle φ               2 / cos(φ/2)           (90° → 2.83, 74° → 2.50)
acute bend, centreline radius r            measured; r ≥ 0.8 keeps < 2.85, r = 2 → 2.00
```

## 4. Rules

```
R1  stroke width                = 2w      (floor 2*mb; never below)
R2  local max thickness         < 2.85w   (point maxima at crossings allowed; 2.83 accepted)
R3  counters / apertures        ≥ 2w      (notch tips at acute joins may fill)
R4  right-angle corners         centreline fillet r=1 → outer R2, inner sharp
R5  acute bends                 centreline fillet r ∈ [0.8, 1.0]; r=2 for constant thickness
R6  convex corners              ≥ R0.5w   (soft-square filter, §6)
R7  free ends                   R1 ball; stem ends on a guide line stay flat (softened by R6)
R8  diagonals                   measured perpendicular, not on the grid
R9  letter gap (true distance)  ≥ 2w
R10 all geometry in w           slicer profile ships with the font (mb, XY comp = 0)
```

## 5. Primitives

```
D(c, r)                disk
Rect(x0,y0,x1,y1)      axis-aligned box
S[p0, p1^r, ..., pn]   stroke: centreline polyline, each interior vertex filleted with
                       centreline radius r (default 1; ^0 = sharp mitre), then
                       buffer(radius 1, cap = flat, join = mitre)
                       ● on an endpoint adds D(endpoint, 1)
S°[...]                closed stroke, all vertices filleted
∪, −                   union, difference

fillet at vertex P between A and B, radius r:
    u = (A-P)/|A-P|, v = (B-P)/|B-P|, θ = acos(u·v)
    t = r / tan(θ/2)                  # tangent length
    C = P + r/sin(θ/2) * (u+v)/|u+v|  # arc centre
    replace P with arc from P+u·t to P+v·t about C

solve(build):          find vy by bisection on [9.5, 16] such that max_y(build(vy)) = 10
                       (bend vertices are placed so the filleted curve lands on the baseline)
```

## 6. Finishing filter

```
soft(g) = (g ⊖ 0.5) ⊕ 0.5        # morphological opening, r = 0.5w
```
Applied to every glyph in every set. Leaves balls and R ≥ 0.5 corners untouched.

## 7. Proportional glyphs (set P)

```
a  S[(1,1)●,(6,1),(6,10)] ∪ S[(6,5),(1,5),(1,9),(6,9)]
b  S[(1,-4),(1,10)] ∪ S[(1,1),(6,1),(6,9),(1,9)]
c  S[(6,1)●,(1,1),(1,9),(6,9)●]
d  S[(6,-4),(6,10)] ∪ S[(6,1),(1,1),(1,9),(6,9)]
e  S[(1,5),(6,5),(6,1),(1,1),(1,9),(6,9)●]
f  S[(2.5,10),(2.5,-3),(5.5,-3)●] ∪ S[(0,1),(6,1)]
g  S[(6,0),(6,13),(1,13)●] ∪ S[(6,1),(1,1),(1,9),(6,9)]
h  S[(1,-4),(1,10)] ∪ S[(1,1),(6,1),(6,10)]
i  S[(1,0),(1,10)] ∪ D((1,-3),1)
j  S[(4,0),(4,13),(1,13)●] ∪ D((4,-3),1)
k  S[(1,-4),(1,10)] ∪ S[(6,1)●,(2.5,6),(6.5,9)●]
l  S[(1,-4),(1,9),(3,9)●]
m  S[(1,10),(1,1)^0,(9,1),(9,10)] ∪ S[(5,1),(5,10)]
n  S[(1,10),(1,1)^0,(6,1),(6,10)]
o  S°[(1,1),(6,1),(6,9),(1,9)]
p  S[(1,0),(1,14)] ∪ S[(1,1),(6,1),(6,9),(1,9)]
q  S[(6,0),(6,14)] ∪ S[(6,1),(1,1),(1,9),(6,9)]
r  S[(1,10),(1,1)^0,(6,1),(6,3)●]
s  S[(6,1)●,(1,1),(1,5),(6,5),(6,9),(1,9)●]
t  S[(2.5,-3),(2.5,9),(5.5,9)●] ∪ S[(0,1),(6,1)]
u  S[(1,0),(1,9),(6,9)] ∪ S[(6,0),(6,10)]
v  solve(vy ↦ S[(1,1)●,(4,vy),(7,1)●])
w  solve(vy ↦ S[(1,1)●,(3.125,vy),(5.25,3.5),(7.375,vy),(9.5,1)●])
x  S[(1,1)●,(7,9)●] ∪ S[(7,1)●,(1,9)●]
y  S[(7,1)●,(2.2,13)●] ∪ S[(0.8,1)●,(4.6,7)]
z  S[(0,1),(6.3,1)^0.8,(0.7,9)^0.8,(7,9)]

0  S°[(1,-3),(6,-3),(6,9),(1,9)]
1  S[(1,-3)●,(4,-3),(4,10)]
2  S[(1,-3)●,(6,-3),(6,3),(1,3),(1,9)^0,(7,9)]
3  S[(1,-3)●,(6,-3),(6,9),(1,9)●] ∪ S[(2,3)●,(6,3)]
4  S[(1,-4),(1,3),(6,3)] ∪ S[(6,-4),(6,10)]
5  S[(7,-3),(1,-3)^0,(1,3)^0,(6,3),(6,9),(1,9)●]
6  S[(6,-3)●,(1,-3),(1,9),(6,9),(6,3),(1,3)]
7  S[(0,-3),(6.4,-3)^2,(3.4,9)●]
8  S°[(1,-3),(6,-3),(6,9),(1,9)] ∪ S[(1,3),(6,3)]
9  rotate(6, 180°, about (3.5, 3))
```

## 8. Monospace glyphs (set M)

Regular glyphs are widened by stretching only the counter zone, so stems stay 2w:

```
widen(x) = x                    x ≤ 2
           2 + (x - 2) * 5/3    2 < x < 5
           x + 2                x ≥ 5
M[c] = widen(P[c])   for c in a b c d e g h n o p q s u 0 2 3 4 5 6 8 9
M[m] = P[m]
```

Rebuilt or re-armed glyphs:

```
i  S[(2,1)●,(4.5,1)^0,(4.5,9)] ∪ S[(1,9),(8,9)] ∪ D((4.5,-3),1)
l  S[(2,-3)●,(4.5,-3)^0,(4.5,9),(8,9)●]
j  S[(3,1)●,(6,1)^0,(6,13),(1,13)●] ∪ D((6,-3),1)
f  S[(3.5,10),(3.5,-3),(8,-3)●] ∪ S[(0.5,1),(8.5,1)]
t  S[(3.5,-3),(3.5,9),(8,9)●] ∪ S[(0.5,1),(8.5,1)]
r  S[(2.5,10),(2.5,1)^0,(8,1),(8,3)●] ∪ S[(0.5,9),(5.5,9)]
k  S[(1,-4),(1,10)] ∪ S[(8,1)●,(2.5,6),(8.5,9)●]
v  solve(vy ↦ S[(1,1)●,(4.5,vy),(8,1)●])
w  solve(vy ↦ S[(1,1)●,(3,vy)^0.9,(5,3.5)^0.9,(7,vy)^0.9,(9,1)●])
x  S[(1,1)●,(8,9)●] ∪ S[(8,1)●,(1,9)●]
y  S[(8,1)●,(2.6,13)●] ∪ S[(0.8,1)●,(5.2,7)]
z  S[(0,1),(8.3,1)^0.8,(0.7,9)^0.8,(9,9)]
1  S[(1.5,-3)●,(4.5,-3),(4.5,9)] ∪ S[(1,9),(8,9)]
7  S[(0,-3),(8.4,-3)^2,(4.6,9)●]
```

Tabular "1" for the mixed setting (7w wide, fits the 9w figure cell):

```
1ₜ S[(1,-3)●,(3.5,-3),(3.5,9)] ∪ S[(0.5,9),(6.5,9)]
```

## 9. Settings

```
T      = 2.4     # optical target gap = stem-to-stem gap
DEPTH  = 3.0     # scanline cap = T + DEPTH
GAPMIN = 2.0     # hard true-distance floor (R9)
WORD   = 5.5     # ink-to-ink word space
CELL_M = 12      # monospace advance  (= width(m) 10 + GAPMIN)
CELL_F = 9       # tabular figure advance (= 7 + GAPMIN)
```

Optical pair offset (origin of B relative to origin of A):

```
band = [-4,10] if A or B is a figure else [0,10]
y_i  = 101 evenly spaced scanlines in band
R_A(y), L_B(y) = rightmost / leftmost ink on scanline (undefined if none)

gap_i(dx) = dx + L_B(y_i) - R_A(y_i)
ĝ_i(dx)   = min(gap_i, T+DEPTH),  or T+DEPTH where undefined
off(A,B)  = root of mean_i ĝ_i(dx) = T       # monotone in dx; bisection on [0,30]
off(A,B) ← min dx' ≥ off(A,B) with dist(A, B + dx') ≥ GAPMIN
```

Kerned setting (set P):

```
x_B = x_A + off(A,B)
after a space: place next ink edge WORD past the previous ink edge
```

Tabular setting (set M):

```
glyph k in line: origin = k*CELL_M + (CELL_M - bboxW)/2 - bbox_minx
space = one empty cell
```

Mixed setting (letters from P, figures from P with 1 → 1ₜ):

```
figure run d0..dn:  cell_origin(k,d) = k*CELL_F + (CELL_F - bboxW(d))/2 - bbox_minx(d)
  run start after letter L:  run0 = x_L + off(L, d0) - cell_origin(0, d0)
  run start after space/BOL: run0 = current edge
  figure k at run0 + cell_origin(k, dk)
letter after figure d:       x = x_d + off(d, letter)
```

## 10. Font-file mapping (kerned set)

```
inkgap(A,B) = off(A,B) - maxx(A) + minx(B)
lsb(n) = rsb(n) = inkgap(n,n) / 2
lsb(X) = inkgap(n, X) - rsb(n)
rsb(X) = inkgap(X, n) - lsb(n)
advance(X) = lsb(X) + bboxW(X) + rsb(X)
kern(A,B)  = inkgap(A,B) - rsb(A) - lsb(B)      # drop |kern| < 0.1w
```

Monospace font: every advance = CELL_M, glyph centred. Tabular figures: advance = CELL_F, kerning disabled between figures.

## 11. Verification

```
raster at 40 px/w
thickness(g)  = 2 * max(EDT(g)) / 40                      require ≤ 2.85 (2.83 at crossings)
thin(g)       = pieces of g − ((g ⊖ 0.98) ⊕ 0.98), eroded 0.03, area > 0.5   require none
tight(g)      = pieces of ((g ⊕ 0.98) ⊖ 0.98) − g, same filter                 informational
line check    = dist(neighbour_i, neighbour_i+1) ≥ 1.98 for every set line
```

Note: opening at exactly r = 1 deletes exact-2w strokes; the check radius must sit below 1.

Reference results: P max 2.83 (f, t crossings), all others ≤ 2.76; M max 2.83; no thin pieces; no neighbour gaps under 2w in any setting.

## 12. Not yet defined

Uppercase and punctuation. Extension rules: capitals use the figure height (y ∈ [-4,10]) and the 5-band stack 2-4-2-4-2; every new glyph passes §11 before joining a set; monospace capitals must fit width ≤ 10.
