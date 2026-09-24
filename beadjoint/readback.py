"""Read a built TTF back and lay text out with its own metrics and 'kern' table, so the checks run
on what a CAD program or slicer actually gets from the file, not on the source geometry."""
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import Polygon

UNITS = 50


class FontReader:
    def __init__(self, path):
        self.font = TTFont(str(path))
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"].metrics
        self.kern = {}
        if "kern" in self.font:
            for st in self.font["kern"].kernTables:
                self.kern.update(st.kernTable)
        self.pair_subtables = []
        if "GPOS" in self.font:
            for lk in self.font["GPOS"].table.LookupList.Lookup:
                for st in lk.SubTable:
                    if lk.LookupType == 9:
                        st = st.ExtSubTable
                    self.pair_subtables.append(st)
        self._outline = {}

    def pair(self, a, b):
        """Kerning of glyph pair (a, b) in font units: GPOS pair adjustment as a shaper applies it
        (subtables in order; format 1 applies only if the second glyph is listed, format 2 applies
        whenever the first glyph is covered), else the legacy kern table."""
        if not self.pair_subtables:
            return self.kern.get((a, b), 0)
        for st in self.pair_subtables:
            cov = st.Coverage.glyphs
            if a not in cov:
                continue
            if st.Format == 1:
                ps = st.PairSet[cov.index(a)]
                for rec in ps.PairValueRecord:
                    if rec.SecondGlyph == b:
                        return getattr(rec.Value1, "XAdvance", 0) or 0
                continue
            c1 = st.ClassDef1.classDefs.get(a, 0)
            c2 = st.ClassDef2.classDefs.get(b, 0)
            v = st.Class1Record[c1].Class2Record[c2].Value1
            return (getattr(v, "XAdvance", 0) or 0) if v is not None else 0
        return 0

    def outline(self, name):
        """Glyph outline in w, y down, relative to the pen origin."""
        if name not in self._outline:
            pen = RecordingPen()
            self.font.getGlyphSet()[name].draw(pen)
            rings, cur = [], []
            for op, args in pen.value:
                if op == "moveTo":
                    cur = [args[0]]
                elif op == "lineTo":
                    cur.append(args[0])
                elif op in ("closePath", "endPath"):
                    rings.append(cur)
                    cur = []
                else:
                    raise ValueError(f"unexpected segment {op}: outlines are straight lines only")
            # nonzero winding for properly nested contours: apply them largest first, outers added and
            # holes cut, so a letter drawn inside a ring's hole (© ®) survives
            contours = []
            for r in rings:
                p = Polygon([(x / UNITS, 10 - y / UNITS) for x, y in r])
                # font space: clockwise outers; the y flip makes them counter-clockwise here
                contours.append((abs(p.area), p.exterior.is_ccw, Polygon(p.exterior.coords)))
            g = Polygon()
            for _, outer, poly in sorted(contours, key=lambda t: -t[0]):
                g = g.union(poly) if outer else g.difference(poly)
            self._outline[name] = g
        return self._outline[name]

    def layout(self, text):
        """[(char, placed geometry, pen x)] using advances and pair kerning from the file."""
        out, pen, prev = [], 0.0, None
        for ch in text:
            name = self.cmap.get(ord(ch), ".notdef")
            if prev is not None:
                pen += self.pair(prev, name) / UNITS
            geom = self.outline(name)
            if not geom.is_empty:                     # spaces of every kind have no outline
                out.append((ch, affinity.translate(geom, pen), pen))
            pen += self.hmtx[name][0] / UNITS
            prev = name
        return out
