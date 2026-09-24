"""Monospace composites: same audit (thin, islands, piece gaps)."""
from _lib import *
from beadjoint.charset import full_m
M = full_m()
bad = 0
for c, g in M.items():
    if marks.decompose(c) or c in "đĐÐðħĦŧŦłŁøØæÆœŒŋŊĸıȷĳĲŉſþÞŀĿ":
        r = check_glyph(g.geom)
        gap = min_piece_gap(g.geom)
        if r["thin"] or r["islands"] or (gap is not None and gap < 1.98):
            bad += 1
            print("FAIL", c, r["thin"], r["islands"], gap)
print("mono glyphs", len(M), "fails", bad)
print("missing from mono:", "".join(c for c in CHARS if c not in M))
