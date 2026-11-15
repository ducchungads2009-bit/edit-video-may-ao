"""PHỤ ĐỀ VẼ BẰNG PYTHON cho bộ dựng nhanh — bắt chước đúng thành phần Captions (remotion/src/Media.tsx):
cùng font (fontsource), cỡ, màu, viền, bóng, từ đang đọc, hiệu ứng nảy (spring y hệt Remotion), xuống dòng cân đối.

Ra: 1 chuỗi ảnh trong suốt (chỉ dải phụ đề) + danh sách thời lượng -> ffmpeg ghép đè lên video.
Hỗ trợ các kiểu: tiktok · outline · karaoke · wordbox · pop · single · minimal. Kiểu 'box' -> supported() = False (dựng bằng Remotion).
"""
import glob
import hashlib
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_CACHE = ROOT / "_cache" / "fonts"
FPS = 30
SUPPORTED = {"tiktok", "outline", "karaoke", "wordbox", "pop", "single", "minimal"}
NAMED = {"white": (255, 255, 255, 255), "black": (0, 0, 0, 255), "transparent": (0, 0, 0, 0), "yellow": (255, 255, 0, 255),
         "red": (255, 0, 0, 255)}


# ---------------------------------------------------------------- tiện ích
def ensure_libs():
    try:
        import fontTools  # noqa
        import brotli  # noqa
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "fonttools", "brotli"], check=True)


def css_color(c, default=(255, 255, 255, 255)):
    if not c:
        return default
    c = str(c).strip().lower()
    if c in NAMED:
        return NAMED[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(x * 2 for x in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) if len(h) == 8 else 255
        return (r, g, b, a)
    m = re.match(r"rgba?\(([^)]+)\)", c)
    if m:
        p = [x.strip() for x in m.group(1).split(",")]
        a = float(p[3]) if len(p) > 3 else 1.0
        return (int(float(p[0])), int(float(p[1])), int(float(p[2])), int(round(a * 255)))
    return default


def spring(frame: float, damping: float, stiffness: float, mass: float = 1.0) -> float:
    """y hệt remotion spring() (from 0 -> 1, vận tốc đầu 0)"""
    if frame <= 0:
        return 0.0
    t = frame / FPS
    w0 = math.sqrt(stiffness / mass)
    z = damping / (2 * math.sqrt(stiffness * mass))
    if z < 1:
        w1 = w0 * math.sqrt(1 - z * z)
        env = math.exp(-z * w0 * t)
        return 1 - env * (math.cos(w1 * t) + (z * w0 / w1) * math.sin(w1 * t))
    return 1 - math.exp(-w0 * t) * (1 + w0 * t)


def clamp01(x):
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------- font
def _fonts_json():
    import json
    try:
        return json.loads((ROOT / "remotion" / "fonts.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        return []


def font_info(name):
    """(id, weights) theo tên font (family hoặc id); không có -> Be Vietnam Pro"""
    L = _fonts_json()
    n = (name or "").strip().lower()
    f = next((x for x in L if x["family"].lower() == n or x["id"] == n), None) or next((x for x in L if x["id"] == "be-vietnam-pro"), None)
    return (f["id"], f.get("weights") or [400, 700, 900]) if f else ("be-vietnam-pro", [400, 700, 900])


def near_weight(ws, want):
    return min(ws, key=lambda w: (abs(w - want), w))


def font_file(fid: str, weight: int) -> Path:
    """gộp các phần (latin, latin-ext, vietnamese) của fontsource thành 1 file .ttf, lưu _cache/fonts"""
    out = FONT_CACHE / f"{fid}-{weight}.ttf"
    if out.exists():
        return out
    ensure_libs()
    from fontTools.merge import Merger
    from fontTools.ttLib import TTFont
    base = ROOT / "node_modules" / "@fontsource" / fid / "files"
    parts = [p for s in ("latin", "latin-ext", "vietnamese") for p in glob.glob(str(base / f"{fid}-{s}-{weight}-normal.woff2"))]
    if not parts:
        raise FileNotFoundError(f"không thấy font {fid} {weight}")
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    tmp = []
    for p in parts:
        t = TTFont(p)
        t.flavor = None
        q = FONT_CACHE / ("_" + Path(p).stem + ".ttf")
        t.save(q)
        tmp.append(str(q))
    for combo in (tmp, [x for x in tmp if "latin-ext" not in x], [tmp[0]]):
        try:
            Merger().merge(combo).save(out)
            break
        except Exception:  # noqa
            continue
    for q in tmp:
        Path(q).unlink(missing_ok=True)
    return out


_FONT_OBJ = {}


def pil_font(path: Path, size: int):
    from PIL import ImageFont
    k = (str(path), size)
    if k not in _FONT_OBJ:
        _FONT_OBJ[k] = ImageFont.truetype(str(path), size)
    return _FONT_OBJ[k]


_METRICS = {}


def vmetrics(path: Path):
    """(ascent, descent) theo đơn vị em, như Chrome dùng (hhea)"""
    if str(path) not in _METRICS:
        from fontTools.ttLib import TTFont
        t = TTFont(str(path))
        upm = t["head"].unitsPerEm
        os2 = t["OS/2"] if "OS/2" in t else None
        if os2 is not None and (os2.fsSelection & (1 << 7)):  # USE_TYPO_METRICS
            a, d = os2.sTypoAscender, -os2.sTypoDescender
        else:
            a, d = t["hhea"].ascent, -t["hhea"].descent
        _METRICS[str(path)] = (a / upm, d / upm)
    return _METRICS[str(path)]


# ---------------------------------------------------------------- cấu hình (giống Media.tsx)
class Cfg:
    def __init__(self, props: dict):
        st = props.get("style") or {}
        c = st.get("captions") or {}
        th = props.get("theme") or {}
        self.preset = c.get("preset") or "tiktok"
        p = self.preset
        self.size = props.get("captionSize") or c.get("size") or (110 if p == "single" else 58 if p == "minimal" else 70)
        up = props.get("captionUpper")
        self.upper = up if up is not None else (c.get("upper") if c.get("upper") is not None else p not in ("minimal", "karaoke"))
        fid, ws = font_info(c.get("font") or st.get("font"))
        self.weight = near_weight(ws, c.get("weight") or (700 if p == "minimal" else 900))
        self.font_path = font_file(fid, self.weight)
        self.color = css_color(c.get("color") or "white")
        dflt_active = th.get("light") if p == "karaoke" else "white" if p == "wordbox" else "#FFE500" if p == "outline" else th.get("gold1")
        self.active = css_color(c.get("active") or dflt_active or "#FFEFB0")
        self.active_bg = css_color(c.get("activeBg") or ("rgba(0,0,0,0.6)" if p == "box" else th.get("mid") or "#2070B8"))
        self.stroke_color = css_color(c.get("strokeColor") or ("#000" if p == "outline" else th.get("dark") or "#0B3570"))
        sz = self.size
        dst = round(sz / 4.5) if p == "outline" else 0 if p in ("minimal", "box", "wordbox") else round(sz / 7)
        self.stroke = c.get("stroke") if c.get("stroke") is not None else dst
        self.anim = c.get("anim") or ("fade" if p == "minimal" else "pop")
        fh = {"9:16": 1920, "4:5": 1350, "1:1": 1080, "16:9": 1080}.get(props.get("format") or "9:16", 1920)
        self.top = props.get("captionTop") if props.get("captionTop") is not None else min(round(1390 * fh / 1920), fh - 200)
        self.frm = props.get("captionsFrom") or 0
        self.x_off = props.get("captionX") or 0
        if p == "minimal":
            self.shadow = (0, 3, 12, (0, 0, 0, 191))
        elif p == "outline":
            self.shadow = (0, 6, 0, (0, 0, 0, 153))
        elif p == "box":
            self.shadow = None
        else:
            self.shadow = (0, 8, 24, (0, 0, 0, 153))


def supported(props: dict) -> bool:
    c = ((props.get("style") or {}).get("captions") or {})
    return (c.get("preset") or "tiktok") in SUPPORTED and not props.get("captionX")


def word_text(w: dict, upper: bool) -> str:
    s = w["w"]
    if upper:
        return s.upper()
    if w.get("keep") or re.search(r"\d", s):
        return s
    return s.lower()


# ---------------------------------------------------------------- 1 khung
def state_at(cfg: Cfg, pages, f: int):
    """mô tả những gì hiện ở khung f (None = không có phụ đề)"""
    t = f / FPS
    if t < cfg.frm:
        return None
    page = next((p for p in pages if p and p[0]["start"] <= t < p[-1]["end"]), None)
    if not page:
        return None
    p = cfg.preset
    if p == "single":
        w = next((x for x in page if x["start"] <= t < x["end"]), None) or next((x for x in reversed(page) if t >= x["start"]), None)
        if not w:
            return None
        page = [w]
    start = page[0]["start"]
    pop = spring(f - start * FPS, 14, 200)
    lin = clamp01((f - start * FPS) / 5)
    q = lambda x: round(x, 3)  # noqa — làm tròn để gộp các khung giống nhau
    box_s = q(0.85 + 0.15 * pop) if cfg.anim == "pop" else 1.0
    box_ty = q((1 - pop) * 40) if cfg.anim == "up" else 0.0
    box_o = q(lin) if cfg.anim in ("fade", "up") else 1.0
    words = []
    for w in page:
        on = w["start"] <= t < w["end"]
        said = t >= w["start"]
        if p == "pop" and not said:
            continue
        wp = spring(f - w["start"] * FPS, 11, 220)
        if p == "karaoke":
            col = "a" if said else "c"
        else:
            col = "a" if on and p != "minimal" else "c"
        if p in ("pop", "single"):
            sc = q(0.4 + 0.6 * wp)
        elif on and p in ("tiktok", "outline"):
            sc = 1.12
        else:
            sc = 1.0
        words.append((word_text(w, cfg.upper), col, sc, bool(on and p == "wordbox")))
    return (box_s, box_ty, box_o, tuple(words))


def _balance(widths, avail):
    """xuống dòng như text-wrap: balance — ít dòng nhất, các dòng dài đều nhau"""
    n = len(widths)
    if sum(widths) <= avail or n <= 1:
        return [list(range(n))]
    lines, cur, cw = 1, 0, 0.0  # số dòng tối thiểu (tham lam)
    for w in widths:
        if cw + w > avail and cw > 0:
            lines += 1
            cw = 0.0
        cw += w
    best = None

    def rec(i, k, acc):
        nonlocal best
        if k == 1:
            seg = list(range(i, n))
            wsum = sum(widths[i:])
            if wsum <= avail or len(seg) == 1:
                cand = acc + [seg]
                mx = max(sum(widths[j] for j in s) for s in cand)
                if best is None or mx < best[0]:
                    best = (mx, cand)
            return
        for j in range(i + 1, n - k + 2):
            seg = list(range(i, j))
            if sum(widths[i:j]) > avail and len(seg) > 1:
                break
            rec(j, k - 1, acc + [seg])

    rec(0, lines, [])
    return best[1] if best else [list(range(n))]


class Painter:
    def __init__(self, cfg: Cfg, width: int):
        self.cfg = cfg
        self.W = width
        self.font = pil_font(cfg.font_path, int(cfg.size))
        a, d = vmetrics(cfg.font_path)
        sz = cfg.size
        self.lh = 1.2 * sz
        self.pad_top = round(sz * 0.08)
        self.box_h = self.lh + self.pad_top
        self.asc = a * sz
        self.baseline = self.pad_top + (self.lh - (a + d) * sz) / 2 + self.asc
        self.margin = 0 if cfg.preset == "single" else round(sz / 5)
        self.avail = width - 40 - 130
        self.band_top = int(cfg.top - 160)
        self.band_h = int(self.box_h * 4 + 320)

    def draw(self, st):
        from PIL import Image
        img = None
        if not st or not st[3]:
            return Image.new("RGBA", (self.W, self.band_h), (0, 0, 0, 0))
        box_s, box_ty, box_o, words = st
        layer, H = self.content(words)
        cfg = self.cfg
        ox, oy = 40 + cfg.x_off, cfg.top - self.band_top
        if abs(box_s - 1) > 1e-4 or box_ty:  # biến đổi cả khung phụ đề quanh tâm vùng chứa
            ccx, ccy = ox + self.avail / 2, oy + H / 2
            s = box_s
            inv = (1 / s, 0, ccx - ccx / s, 0, 1 / s, ccy - (ccy + box_ty) / s)
            layer = layer.transform(layer.size, Image.AFFINE, inv, resample=Image.BICUBIC)
        if box_o < 1:
            layer = layer.copy()
            a = layer.getchannel("A").point(lambda v: int(v * box_o))
            layer.putalpha(a)
        return layer

    def content(self, words):
        """lớp chữ (chưa biến đổi khung) — dùng lại cho các khung có cùng chữ / màu / cỡ"""
        if not hasattr(self, "_cc"):
            self._cc = {}
        if words in self._cc:
            return self._cc[words]
        from PIL import Image, ImageDraw, ImageFilter
        cfg = self.cfg
        f = self.font
        tw = [f.getlength(w[0]) for w in words]
        bw = [tw[i] + (24 if words[i][3] else 0) for i in range(len(words))]  # bề rộng hộp chữ (wordbox có đệm 12px)
        full = [b + 2 * self.margin for b in bw]
        lines = _balance(full, self.avail)
        H = self.box_h * len(lines)
        boxes = []
        for li, ln in enumerate(lines):
            lw = sum(full[i] for i in ln)
            x = (self.avail - lw) / 2
            for i in ln:
                x += self.margin
                boxes.append((i, x, li * self.box_h))
                x += bw[i] + self.margin
        size = (self.W, self.band_h)
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        ox, oy = 40 + cfg.x_off, cfg.top - self.band_top
        shadow = Image.new("RGBA", size, (0, 0, 0, 0)) if cfg.shadow else None
        sd = ImageDraw.Draw(shadow) if shadow else None
        bgl = Image.new("RGBA", size, (0, 0, 0, 0))
        bgd = ImageDraw.Draw(bgl)
        for i, x, y in boxes:
            text, col, sc, wbox = words[i]
            fill = cfg.active if col == "a" else cfg.color
            cx, cy = ox + x + bw[i] / 2, oy + y + self.box_h / 2  # tâm hộp chữ (tâm scale)
            fnt = f if abs(sc - 1) < 1e-3 else pil_font(cfg.font_path, max(1, int(round(cfg.size * sc))))
            sw = int(round(cfg.stroke * sc / 2)) if cfg.stroke else 0
            tx = cx - (tw[i] * sc) / 2
            ty = cy + (self.baseline - self.box_h / 2) * sc  # đường chân chữ
            if wbox:
                hw, hh = bw[i] * sc / 2, self.box_h * sc / 2
                r = 14 * sc
                if shadow:
                    sd.rounded_rectangle([cx - hw, cy - hh + 6, cx + hw, cy + hh + 6], r, fill=(0, 0, 0, 89))
                bgd.rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], r, fill=cfg.active_bg)
            d.text((tx, ty), text, font=fnt, fill=fill, anchor="ls", stroke_width=sw, stroke_fill=cfg.stroke_color)
            if shadow:
                dx, dy, blur, sc_col = cfg.shadow
                sd.text((tx + dx, ty + dy), text, font=fnt, fill=sc_col, anchor="ls", stroke_width=sw, stroke_fill=sc_col)
        if shadow:
            blur = cfg.shadow[2]
            if blur:  # làm mờ ở ảnh thu nhỏ 4 lần (nhanh hơn nhiều, nhìn như nhau)
                bb = shadow.getbbox()
                if bb:
                    m = int(blur * 1.5) + 4
                    x0, y0, x1, y1 = max(0, bb[0] - m), max(0, bb[1] - m), min(size[0], bb[2] + m), min(size[1], bb[3] + m)
                    crop = shadow.crop((x0, y0, x1, y1))
                    q = 4 if blur >= 8 else 1
                    small = crop.resize((max(1, (x1 - x0) // q), max(1, (y1 - y0) // q)), Image.BILINEAR) if q > 1 else crop
                    small = small.filter(ImageFilter.GaussianBlur(blur / 2 / q))
                    crop = small.resize((x1 - x0, y1 - y0), Image.BILINEAR) if q > 1 else small
                    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
                    shadow.paste(crop, (x0, y0))
            base = Image.alpha_composite(shadow, bgl)
        else:
            base = bgl
        layer = Image.alpha_composite(base, layer)
        if len(self._cc) > 400:
            self._cc.clear()
        self._cc[words] = (layer, H)
        return layer, H


def build(props: dict, out_dir: Path, nframes: int, width: int = 1080):
    """vẽ phụ đề cho cả video -> (thư mục ảnh, danh sách [(file, số khung)], band_top). Ảnh giống nhau dùng lại."""
    pages = props.get("captions") or []
    cfg = Cfg(props)
    pt = Painter(cfg, width)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    seq, cache, prev = [], {}, object()
    for f in range(nframes):
        st = state_at(cfg, pages, f)
        if st == prev and seq:
            seq[-1][1] += 1
            continue
        prev = st
        key = hashlib.md5(repr(st).encode()).hexdigest()[:16]
        if key not in cache:
            fn = out_dir / f"{key}.png"
            pt.draw(st).save(fn, compress_level=1)
            cache[key] = fn
        seq.append([cache[key], 1])
    return seq, pt.band_top, pt.band_h


def write_concat(seq, path: Path):
    """danh sách cho ffmpeg concat (thời lượng theo khung 30fps)"""
    L = ["ffconcat version 1.0"]
    for fn, n in seq:
        L.append("file '" + fn.as_posix().replace("'", "'\\''") + "'")
        L.append(f"duration {n / FPS:.6f}")
    if seq:
        L.append("file '" + seq[-1][0].as_posix().replace("'", "'\\''") + "'")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
