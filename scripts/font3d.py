"""Tạo font cho CHỮ 3D THẬT (khối text3dPro / object3d — remotion/src/Three3D.tsx) từ font @fontsource có sẵn trong node_modules.

Three.js cần font dạng "typeface JSON" (đường nét từng chữ). File này rút đủ chữ tiếng Việt (hoa + thường, mọi dấu), số, dấu câu
từ các bản latin + vietnamese (+ latin-ext) của 1 font @fontsource, ghi ra remotion/src/fonts3d/<tên>.json.

Chạy (máy phát triển, cần: pip install fonttools):
    python scripts/font3d.py be-vietnam-pro 800
    python scripts/font3d.py montserrat 800
    python scripts/font3d.py playfair-display 800 playfair
Thêm font mới -> import file JSON trong Three3D.tsx (FONTS3D) rồi đóng gói lại.
"""
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def chars() -> set:
    base = "aăâbcdđeêghiklmnoôơpqrstuưvxyfjwz"
    out = set()
    for c in base:
        out.add(c)
        if c in "aăâeêioôơuưy":
            for m in "̣̀́̃̉":
                out.add(unicodedata.normalize("NFC", c + m))
    out |= {c.upper() for c in list(out)}
    out |= set("0123456789 .,:;!?-–·%/+&()'\"²₫$@#*")
    return out


def build(pkg: str, weight: str, name: str) -> Path:
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    d = ROOT / "node_modules" / "@fontsource" / pkg / "files"
    fonts = [TTFont(d / f"{pkg}-{s}-{weight}-normal.woff") for s in ("latin", "vietnamese", "latin-ext") if (d / f"{pkg}-{s}-{weight}-normal.woff").exists()]
    if not fonts:
        raise SystemExit(f"Không thấy font {pkg} {weight} trong {d}")

    class Pen(BasePen):
        def __init__(self, gs):
            super().__init__(gs)
            self.o = []

        def _moveTo(self, p):
            self.o += ["m", *p]

        def _lineTo(self, p):
            self.o += ["l", *p]

        def _qCurveToOne(self, a, b):  # three.js: điểm cuối trước, điểm điều khiển sau
            self.o += ["q", *b, *a]

        def _curveToOne(self, a, b, c):
            self.o += ["b", *c, *a, *b]

    glyphs = {}
    for ch in sorted(chars()):
        for ft in fonts:
            cm = ft.getBestCmap()
            if ord(ch) in cm:
                gs = ft.getGlyphSet()
                gn = cm[ord(ch)]
                p = Pen(gs)
                gs[gn].draw(p)
                glyphs[ch] = {"ha": gs[gn].width, "o": " ".join(x if isinstance(x, str) else str(round(x)) for x in p.o)}
                break
    h, hh = fonts[0]["head"], fonts[0]["hhea"]
    data = {"glyphs": glyphs, "familyName": pkg, "ascender": hh.ascent, "descender": hh.descent, "underlinePosition": -100,
            "underlineThickness": 50, "boundingBox": {"yMin": h.yMin, "xMin": h.xMin, "yMax": h.yMax, "xMax": h.xMax},
            "resolution": h.unitsPerEm, "original_font_information": {}}
    out = ROOT / "remotion" / "src" / "fonts3d" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {len(glyphs)} chữ")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "800", sys.argv[3] if len(sys.argv) > 3 else sys.argv[1])
