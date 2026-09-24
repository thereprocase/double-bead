"""Frodo r2 accent proposals, applied together: before/after sheet and set text at label size.

  A  ģ: U+0123 is g + U+0327 (cedilla) so it took the comma-below branch and fused the comma into
     the g's tail. Route cedilla-on-g to the turned comma above.
  B  breve: half circle (r = 2.4) instead of the square cup.
  C  ring: true circle, same 6w / 2w hole.
  D  ŗ: comma under the stem (x = 1), not under the arch.
  E  ħ đ: stem pokes 2w above a crossing bar (the T-topped ħ read as Cyrillic ћ, đ as a d with a hat).
  F  option: Å with the ring sitting on the A (top -8 instead of -12).
"""
from _lib import *
from beadjoint.charset import full_m, _assemble
import pickle

P = full_p()
FIN = {c: g.geom for c, g in P.items()}
RAW = raw_p()

NEWSHAPES = {
    "breve": S((0, 0, B), (0, 2.5, 2.4), (5, 2.5, 2.4), (5, 0, B)),
    "ring": So((0, 0, 2), (4, 0, 2), (4, 4, 2), (0, 4, 2)),
}
BELOW_X = {"r": 1.0}


def compose2(ch, base_char, ms, bases, anchors=None):
    """marks.compose with fixes A and D (the patch proposed for marks.py)."""
    b = base_char
    if b == "g" and "cedilla" in ms:
        ms = ["commabelow" if m == "cedilla" else m for m in ms]
    if b in BELOW_X and "cedilla" in ms:
        g = bases[b]
        return g | place_below(marks.SHAPES["commabelow"], BELOW_X[b])
    return compose(ch, b, ms, bases, anchors)


def build(ch):
    base, ms = decompose(ch)
    return finish(compose2(ch, base, ms, FIN))


saved = dict(marks.SHAPES)
marks.SHAPES.update(NEWSHAPES)
over = {}
for ch in CHARS:
    dec = decompose(ch)
    if dec and (dec[0] in "gr" and "cedilla" in dec[1] or {"breve", "ring"} & set(dec[1])):
        over[ch] = build(ch)
marks.SHAPES.clear()
marks.SHAPES.update(saved)
over["ħ"] = finish(shift(S((1, -6), (1, 10)) | S((1, 1), (6, 1), (6, 10)), 1.5) | S((0, -3), (5.5, -3)))
over["đ"] = finish(S((6, -6), (6, 10)) | S((6, 1), (1, 1), (1, 9), (6, 9)) | S((3, -3), (9, -3)))
ring_on_a = So((1.5, -7, 2), (5.5, -7, 2), (5.5, -3, 2), (1.5, -3, 2))
aring_attached = finish(RAW["A"] | ring_on_a)

print("changed:", "".join(over))
for c, g in over.items():
    audit(c, g)
audit("Å on A", aring_attached)

# F: mono ĺ with the acute over the mono l's stem (anchor 4.5) fits the cell
M = full_m()
ml = M["l"].geom
mono_lacute = finish(ml | place_above(SHAPES["acute"], 4.5, marks.ABOVE_HIGH))
b = mono_lacute.bounds
print("mono ĺ with anchor 4.5: width", round(b[2] - b[0], 2), "(<= 10 fits)")
audit("mono ĺ", mono_lacute)

# before / after sheet
pairs = {}
for c in "ģăĂğĞŭŬåÅůŮŗħđ":
    pairs[c + " now"] = P[c].geom
    pairs[c + " new"] = over[c]
pairs["Å on A"] = aring_attached
pairs["ĺ mono"] = mono_lacute
sheet(pairs, "final_sheet.png", cols=10, scale=6, cell=(18, 32))
pickle.dump(over, open(fr"{R}\final_over.pkl", "wb"))

rows = [
    ("Latvian", ["Ģīmeņa ķēniņš ļoti gribēja ŗūķīt dzērienu, ģērbies"]),
    ("Turkish / Romanian", ["yağız DOĞU; pițigăiat comandă ĂȘTIA"]),
    ("Czech / Danish", ["kůň, půl, ÚŮ; på Ålborg Ærø"]),
    ("Maltese / Croatian", ["Ħamrun ħobż ħelu; međa Đurđevak đak"]),
    ("Esperanto", ["ĉiuĵaŭde ŝi manĝas ĝis ŬO"]),
]
text(over, rows, "final_text_small.png", scale=3)
text(over, rows, "final_text_big.png", scale=8)
text({}, rows, "final_text_before_small.png", scale=3)
