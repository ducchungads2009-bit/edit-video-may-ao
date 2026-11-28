"""CẢNH AI — AI tự viết cảnh đồ hoạ động (HTML/SVG/Canvas/WebGL) rồi chèn vào video bằng khối `canhAI`.
Cách làm và thư viện 104 mẫu phong cách lấy từ LumReels (github.com/lumtekvn/lumreels, MIT — canh-ai/LICENSE-LumReels.txt).
Luật viết cảnh: canh-ai/HUONG-DAN.md (đọc HẾT trước khi viết).

Dùng (máy ảo: ./chay.sh canh_ai.py …):
  canh_ai.py ds [--nhom bds|ads|faceless] [--tim "<từ>"]   danh sách mẫu (id, tên, hợp với nội dung gì)
  canh_ai.py xem <id>                                     in bản mô tả mẫu (màu, font, bố cục, nhịp theo giây)
  canh_ai.py san                                          CẢNH DỰNG SẴN (đã viết sẵn, chỉ đổi data): tên, mô tả, trường data
  canh_ai.py moi "<du-an>" <ten> --san <tên cảnh dựng sẵn>  -> chép cảnh dựng sẵn vào dự án
  canh_ai.py moi "<du-an>" <ten> [--mau <id>] [--giay 6] [--nen trong|mau]
        -> tạo <du-an>/canh/<ten>/index.html (khung sẵn đúng luật) + chép bản mô tả mẫu vào MAU.md
  canh_ai.py thu san <tên> [--data '{…}']                  xem thử cảnh dựng sẵn
  canh_ai.py thu "<du-an>" <ten> [--moc 0,1.5,3,4.5] [--data '{"gia":"4 tỷ"}']
        -> chụp các mốc ra <du-an>/canh/<ten>/_thu.jpg để XEM bằng mắt (chạy riêng, không cần dựng video)
  canh_ai.py kiem "<du-an>" [<ten>]                        soát luật + font tiếng Việt của cảnh (soat.py tự gọi)
  canh_ai.py lib                                          dựng lại thư viện cảnh (canh-ai/lib) — cai-may-ao.sh tự gọi
"""
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa
        pass

ROOT = Path(__file__).resolve().parent.parent
CA = ROOT / "canh-ai"
LIB = CA / "lib"
MAU = CA / "mau"
SAN = CA / "san"   # cảnh dựng sẵn (đã viết, dữ liệu đổi qua "data") — canh_ai.py san
NM = ROOT / "node_modules"
SUBSETS = ("latin", "latin-ext", "vietnamese")
# font chỉ dùng trong cảnh AI (mẫu LumReels cần) — ngoài 24 font của tool (remotion/fonts.json)
EXTRA = [("Space Grotesk", "space-grotesk", "sans"), ("Manrope", "manrope", "sans"), ("Space Mono", "space-mono", "mono"),
         ("VT323", "vt323", "mono"), ("IBM Plex Mono", "ibm-plex-mono", "mono"), ("JetBrains Mono", "jetbrains-mono", "mono"),
         ("Alfa Slab One", "alfa-slab-one", "display"), ("Bangers", "bangers", "display"), ("Grenze Gotisch", "grenze-gotisch", "display"),
         ("Mali", "mali", "hand"), ("Lora", "lora", "serif")]
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace",
           "emoji", "math", "inherit", "initial", "unset", "revert"}
BDS = re.compile(r"(bất động sản|(?<!tận )nhà(?! hàng)|căn hộ|biệt thự|villa|vay mua nhà|xây dựng|nội thất|kiến trúc|resort|homestay|môi giới)", re.I)


# ------------------------------------------------------------------ thư viện cảnh (runtime + vendor + font)
def _families():
    out = []
    try:
        for f in json.loads((ROOT / "remotion" / "fonts.json").read_text(encoding="utf-8")):
            out.append((f["family"], f["id"], f.get("kind", "sans")))
    except Exception:  # noqa
        pass
    have = {x[1] for x in out}
    return out + [x for x in EXTRA if x[1] not in have]


def build_lib(quiet=False) -> Path:
    """canh-ai/lib/{runtime,vendor,fonts} — cảnh nạp offline bằng ./lib/..."""
    (LIB / "runtime").mkdir(parents=True, exist_ok=True)
    shutil.copy2(CA / "runtime" / "scene.js", LIB / "runtime" / "scene.js")
    vd = LIB / "vendor"
    vd.mkdir(exist_ok=True)
    for src, name in ((NM / "gsap" / "dist" / "gsap.min.js", "gsap.min.js"), (NM / "three" / "build" / "three.module.js", "three.module.js"),
                      (NM / "three" / "build" / "three.core.js", "three.core.js")):
        if src.exists():
            shutil.copy2(src, vd / name)
    fd = LIB / "fonts"
    (fd / "files").mkdir(parents=True, exist_ok=True)
    css, meta, nfile = [], [], 0
    for fam, fid, kind in _families():
        pdir = NM / "@fontsource" / fid
        if not pdir.exists():
            continue
        weights, italic = set(), set()
        for cf in sorted(pdir.glob("*.css")):
            m = re.fullmatch(r"(\d{3})(-italic)?\.css", cf.name)
            if not m:
                continue
            txt = cf.read_text(encoding="utf-8")
            for blk in re.findall(r"/\*[^*]*\*/\s*@font-face\s*\{[^}]*\}", txt):
                sub = re.search(rf"/\*\s*{re.escape(fid)}-([\w-]+)-\d{{3}}-(normal|italic)\s*\*/", blk)
                if not sub or sub.group(1) not in SUBSETS:
                    continue
                for u in re.findall(r"url\(\./files/([^)]+\.woff2)\)", blk):
                    s = pdir / "files" / u
                    if s.exists():
                        d = fd / "files" / u
                        if not d.exists() or d.stat().st_size != s.stat().st_size:
                            shutil.copy2(s, d)
                            nfile += 1
                blk = re.sub(r",\s*url\(\./files/[^)]+\.woff\)\s*format\('woff'\)", "", blk)
                css.append(blk)
                (italic if m.group(2) else weights).add(int(m.group(1)))
        if weights or italic:
            meta.append({"family": fam, "id": fid, "kind": kind, "weights": sorted(weights), "italic": sorted(italic)})
    (fd / "fonts.css").write_text("/* font có dấu tiếng Việt cho cảnh AI — canh_ai.py lib tự sinh, đừng sửa */\n" + "\n".join(css) + "\n", encoding="utf-8")
    (fd / "fonts.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if not quiet:
        print(f"Thư viện cảnh AI: {LIB} — {len(meta)} họ font, {nfile} file font mới, "
              f"vendor: {', '.join(sorted(p.name for p in vd.iterdir()))}")
    return LIB


def ensure_lib() -> Path:
    if not (LIB / "fonts" / "fonts.json").exists() or not (LIB / "runtime" / "scene.js").exists() or \
            (CA / "runtime" / "scene.js").stat().st_mtime > (LIB / "runtime" / "scene.js").stat().st_mtime:
        build_lib(quiet=True)
    return LIB


def sync_lib(scene_dir: Path, link=True):
    """chép (liên kết cứng) canh-ai/lib vào <cảnh>/lib"""
    ensure_lib()
    for src in LIB.rglob("*"):
        if src.is_dir():
            continue
        dst = Path(scene_dir) / "lib" / src.relative_to(LIB)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if dst.stat().st_size == src.stat().st_size and int(dst.stat().st_mtime) == int(src.stat().st_mtime):
                continue
            dst.unlink()
        try:
            if not link:
                raise OSError
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)


def fonts_meta() -> list:
    ensure_lib()
    try:
        return json.loads((LIB / "fonts" / "fonts.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        return []


# ------------------------------------------------------------------ thư viện mẫu
def catalog() -> list:
    try:
        return json.loads((MAU / "catalog.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        return []


def is_bds(m: dict) -> bool:
    return bool(BDS.search(f"{m.get('genre', '')} {m.get('name', '')}"))


def cmd_ds(args):
    nhom = _opt(args, "--nhom")
    tim = (_opt(args, "--tim") or "").lower()
    rows = catalog()
    if nhom == "bds":
        rows = [m for m in rows if is_bds(m)]
    elif nhom:
        rows = [m for m in rows if m.get("category") == nhom]
    if tim:
        rows = [m for m in rows if tim in json.dumps(m, ensure_ascii=False).lower()]
    for m in rows:
        tag = " [BĐS]" if is_bds(m) else ""
        print(f"{m['id']}  {m['name']}{tag} — {m.get('genre', '')} · độ khó {m.get('difficulty', '?')}/5 · {', '.join(m.get('technique') or [])}")
        if m.get("blurb"):
            print(f"      {m['blurb']}")
    print(f"({len(rows)} mẫu) — xem chi tiết: canh_ai.py xem <id>")


def guidance(mid: str) -> Path:
    mid = str(mid).zfill(3)
    p = MAU / f"{mid}.md"
    if not p.exists():
        sys.exit(f"Không có mẫu {mid} (canh_ai.py ds để xem danh sách)")
    return p


# ------------------------------------------------------------------ tạo cảnh mới
SKELETON = """<!doctype html>
<html lang="vi">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<!-- CẢNH AI: {ten}{mau_note} — luật: canh-ai/HUONG-DAN.md. Mọi khung là hàm thuần của t. -->
<link rel="stylesheet" href="./lib/fonts/fonts.css" />
<script src="./lib/vendor/gsap.min.js"></script>
<script src="./lib/runtime/scene.js"></script>
<style>
  html, body {{ margin:0; width:1080px; height:1920px; overflow:hidden; background:{nen}; }}
  #root {{ position:relative; width:1080px; height:1920px; overflow:hidden; }}
  .tieu-de {{ position:absolute; left:90px; right:90px; top:300px; text-align:center; color:#fff;
             font-family:'Be Vietnam Pro', sans-serif; font-weight:800; font-size:96px; line-height:1.1; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{giay}" data-fps="30" data-width="1080" data-height="1920">
  <div class="tieu-de" id="td"></div>
</div>
<script>
  const D = window.CANH.data;            // dữ liệu từ plan.json (khối canhAI, trường "data")
  const {{ prog, ease, lerp }} = VideoScene;
  VideoScene.define({{
    duration: {giay}, fps: 30, width: 1080, height: 1920,
    setup() {{
      document.getElementById('td').textContent = D.tieuDe || 'Tiêu đề';
    }},
    render(t) {{
      const k = ease.outCubic(prog(t, 0.2, 0.8));
      const td = document.getElementById('td');
      td.style.opacity = k;
      td.style.transform = `translateY(${{lerp(40, 0, k)}}px)`;
    }},
  }});
</script>
</body>
</html>
"""


def _folder(arg: str) -> Path:
    p = Path(arg)
    if not p.exists() and (ROOT / "cho-edit" / arg).exists():
        p = ROOT / "cho-edit" / arg
    if not p.exists():
        sys.exit(f"Không thấy dự án: {arg}")
    return p.resolve()


def cmd_moi(args):
    if len(args) < 2:
        sys.exit(__doc__)
    folder, ten = _folder(args[0]), re.sub(r"[^\w-]+", "-", args[1]).strip("-").lower()
    d = folder / "canh" / ten
    if (d / "index.html").exists():
        sys.exit(f"Đã có cảnh {d / 'index.html'} — sửa thẳng file đó")
    d.mkdir(parents=True, exist_ok=True)
    san = _opt(args, "--san")
    if san:
        src = SAN / san
        if not (src / "index.html").exists():
            sys.exit(f"Không có cảnh dựng sẵn “{san}” (canh_ai.py san để xem danh sách)")
        shutil.copy2(src / "index.html", d / "index.html")
        for f in src.iterdir():
            if f.is_file() and f.name not in ("index.html", "_thu.jpg"):
                shutil.copy2(f, d / f.name)
        sync_lib(d)
        info = next((x for x in san_list() if x["ten"] == san), {})
        print(f"Đã chép cảnh dựng sẵn “{san}” → {d / 'index.html'}")
        print(f"Dữ liệu (data): {info.get('data', '')}")
        print(f'Khối plan.json: {{"type": "canhAI", "start": <giây>, "end": <giây + {info.get("giay", 6)}>, "canh": "canh/{ten}", "data": {{…}}}}')
        return
    mau = _opt(args, "--mau")
    giay = float(_opt(args, "--giay") or 6)
    nen = "transparent" if (_opt(args, "--nen") or "trong") == "trong" else "#000"
    note = ""
    if mau:
        g = guidance(mau)
        shutil.copy2(g, d / "MAU.md")
        m = next((x for x in catalog() if x["id"] == str(mau).zfill(3)), {})
        note = f" · theo mẫu {str(mau).zfill(3)} “{m.get('name', '')}” (MAU.md)"
    (d / "index.html").write_text(SKELETON.format(ten=ten, mau_note=note, nen=nen, giay=f"{giay:g}"), encoding="utf-8")
    sync_lib(d)
    print(f"Đã tạo: {d / 'index.html'}" + (f"\nBản mô tả mẫu: {d / 'MAU.md'} — đọc hết, dựng đúng màu / font / bố cục / nhịp" if mau else ""))
    print(f'Khối plan.json: {{"type": "canhAI", "start": <giây>, "end": <giây + {giay:g}>, "canh": "canh/{ten}", "data": {{…}}}}')


# ------------------------------------------------------------------ soát tĩnh
def lint(scene_dir: Path) -> tuple:
    """(lỗi, cảnh báo, meta) theo canh-ai/HUONG-DAN.md"""
    errors, warns = [], []
    f = scene_dir / "index.html"
    if not f.exists():
        return [f"không có {f}"], [], None
    html = f.read_text(encoding="utf-8", errors="replace")
    remote = re.findall(r"(?:src|href)\s*=\s*[\"']\s*(?:https?:)?//[^\"']+", html, re.I) + \
        re.findall(r"@import\s+url\(\s*[\"']?(?:https?:)?//[^)]+", html, re.I) + re.findall(r"\bfetch\s*\(\s*[\"'`]https?:[^\"'`]+", html, re.I)
    for r in remote:
        errors.append(f"gọi mạng lúc dựng bị cấm: {r[:80]} — tải file về để cạnh index.html")
    if re.search(r"Math\.random\s*\(", html):
        errors.append("dùng Math.random() → mỗi lần dựng một khác; dùng VideoScene.rng(seed) ở setup")
    if re.search(r"Date\.now\s*\(|performance\.now\s*\(|new Date\s*\(\s*\)", html):
        errors.append("dùng đồng hồ thật (Date.now / performance.now) → không tua được; mọi thứ phải tính từ t")
    if re.search(r"requestAnimationFrame\s*\(", html):
        warns.append("có requestAnimationFrame — đừng tự chạy vòng lặp, chỉ vẽ trong render(t)")
    if re.search(r"set(?:Timeout|Interval)\s*\(", html):
        warns.append("có setTimeout/setInterval — chuyển động phải tính từ t, không chạy theo đồng hồ")
    if re.search(r"(?<![-\w])(?:animation|transition)\s*:\s*(?!none)[^;}{]+", html):
        warns.append("có CSS animation / transition — không tua được, khung sẽ lệch; tính trong render(t)")
    if re.search(r"<video[^>]*autoplay", html, re.I):
        errors.append("<video autoplay> không tua được — dùng ảnh hoặc khối broll của tool")
    if not re.search(r"VideoScene\.define\s*\(", html):
        errors.append("thiếu VideoScene.define({ duration, render(t) })")
    if "lib/runtime/scene.js" not in html:
        errors.append('thiếu <script src="./lib/runtime/scene.js">')
    if "lib/fonts/fonts.css" not in html:
        warns.append('thiếu <link rel="stylesheet" href="./lib/fonts/fonts.css"> — chữ sẽ hiện bằng font hệ thống')
    if re.search(r"WebGLRenderer\s*\(", html) and "preserveDrawingBuffer" not in html:
        errors.append("WebGLRenderer thiếu preserveDrawingBuffer: true → khung chụp ra đen")
    meta = None
    root = re.search(r"<div[^>]*id=[\"']root[\"'][^>]*>", html, re.I)
    if root:
        def at(n):
            m = re.search(rf"data-{n}=[\"']([^\"']+)[\"']", root.group(0))
            return m.group(1) if m else None
        try:
            meta = {"duration": float(at("duration") or 0), "width": int(float(at("width") or 1080)), "height": int(float(at("height") or 1920))}
        except ValueError:
            meta = None
    m = re.search(r"VideoScene\.define\s*\(\s*\{[^}]*?duration\s*:\s*([\d.]+)", html, re.S)
    if m:
        meta = meta or {"width": 1080, "height": 1920}
        meta["duration"] = float(m.group(1))
    # font
    have = {f["family"].lower() for f in fonts_meta()}
    used = set()

    def add(lst):
        for x in lst.split(","):
            x = x.strip().strip("\"'").strip()
            if x and not x.startswith("var(") and not re.search(r"[${}]", x):
                used.add(x)
    for m in re.finditer(r"font-family\s*:\s*([^;}{<>\n]+)", html, re.I):
        add(m.group(1))
    for m in re.finditer(r"fontFamily\s*[:=]\s*([\"'`])([^\"'`]+)\1", html):
        add(m.group(2))
    for m in re.finditer(r"(?:\bfont\s*:|\.font\s*=)\s*([^;\n]+)", html):
        v = m.group(1)
        for q in re.finditer(r"([\"'])([A-Za-z][A-Za-z0-9 ]*[A-Za-z0-9])\1", v):
            if re.search(r"\d|\b(px|em)\b", v) and not re.fullmatch(r"(px|em|rem|pt|bold|normal|italic)", q.group(2), re.I):
                used.add(q.group(2).strip())
    bad = sorted(f for f in used if f.lower() not in GENERIC and f.lower() not in have)
    if have:
        for b in bad:
            errors.append(f"font ngoài thư viện: “{b}” — sẽ hiện bằng font hệ thống, mất dấu; chọn font trong canh-ai/HUONG-DAN.md mục 4")
    if re.search(r"₫|&#8363;|&#x20ab;|\\u20ab", html, re.I):
        warns.append("có ký hiệu “₫” — nhiều font vẽ lệch; viết “đ” hoặc “VNĐ”")
    for m in re.finditer(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", html):
        if float(m.group(1)) < 28:
            warns.append(f"font-size {m.group(1)}px < 28px — quá nhỏ trên điện thoại (chữ chính ≥ 40px)")
            break
    return errors, warns, meta


# ------------------------------------------------------------------ chạy trình duyệt (xem thử / kiểm font)
def chrome() -> str:
    for c in (os.environ.get("REMOTION_BROWSER"), os.environ.get("CHROME_PATH")):
        if c and Path(c).exists():
            return c
    try:
        b = (ROOT / ".trinh-duyet").read_text().strip()
        if b and Path(b).exists():
            return b
    except Exception:  # noqa
        pass
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "headless_shell"):
        p = shutil.which(c)
        if p:
            return p
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(c).exists():
            return c
    return ""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _serve(d: Path):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(d)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _chrome(url: str, extra: list, timeout=90):
    b = chrome()
    if not b:
        return None, "không thấy trình duyệt Chrome (chạy ./cai-may-ao.sh)"
    head = "--headless" if "headless_shell" in b or "headless-shell" in b else "--headless=new"
    prof = tempfile.mkdtemp(prefix="canhai-")
    cmd = [b, head, "--no-sandbox", "--disable-gpu-sandbox", "--hide-scrollbars", "--mute-audio", "--no-first-run",
           "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--force-device-scale-factor=1",
           f"--user-data-dir={prof}", "--window-size=1080,1920", "--virtual-time-budget=20000", "--run-all-compositor-stages-before-draw",
           *extra, url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r, None
    except subprocess.TimeoutExpired:
        return None, f"trình duyệt quá {timeout}s"
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def _hash(data: dict = None, **kw) -> str:
    from urllib.parse import quote
    canh = {"data": data or {}, "w": 1080, "h": 1920}
    parts = ["canh=" + quote(json.dumps(canh, ensure_ascii=False))] + [f"{k}={quote(str(v))}" for k, v in kw.items()]
    return "#" + "&".join(parts)


def font_check(scene_dir: Path, times=None, data=None) -> tuple:
    """chạy cảnh trong Chrome, tua vài mốc, bắt chữ hiện bằng font hệ thống / thiếu dấu / quá nhỏ / số viết tay.
    Trả (danh sách vấn đề, lỗi chạy hoặc None)."""
    _, _, meta = lint(scene_dir)
    D = (meta or {}).get("duration") or 6
    times = times or [0, D * 0.25, D * 0.5, D * 0.75, max(0, D - 0.05)]
    sync_lib(scene_dir)
    srv = _serve(scene_dir)
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/index.html" + _hash(data, fontcheck=",".join(f"{t:.2f}" for t in times))
        r, err = _chrome(url, ["--dump-dom"])
    finally:
        srv.shutdown()
    if err:
        return [], err
    m = re.search(r'<script type="application/json" id="__fontreport">(.*?)</script>', r.stdout or "", re.S)
    if not m:
        tail = "\n".join(l for l in (r.stderr or "").splitlines() if "ERROR" in l or "Uncaught" in l)[-400:]
        return [], "cảnh không chạy tới cuối (lỗi JavaScript?) " + tail
    import html as _h
    rep = json.loads(_h.unescape(m.group(1)))
    kinds = {f["family"]: f.get("kind") for f in fonts_meta()}
    out, seen = [], set()
    for i in rep.get("issues") or []:
        if i["kind"] == "_DIGITS":
            if kinds.get(i.get("font")) not in ("script", "hand"):
                continue
            i = {**i, "kind": "FONT_DIGITS", "why": "con số viết bằng font thư pháp / viết tay — khó đọc, đổi sang sans / serif"}
        key = (i["kind"], i.get("text"), i.get("font"), i.get("weight"))
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
    return out, None


VI_KIND = {"FONT_OUTSIDE": "chữ hiện bằng font hệ thống (font không có trong thư viện)",
           "FONT_FALLBACK": "thiếu dấu / font chưa tải", "FONT_WEIGHT": "độ đậm không có (trình duyệt làm đậm giả)",
           "FONT_SMALL": "chữ quá nhỏ", "FONT_DONG": "ký hiệu ₫", "FONT_DIGITS": "số viết bằng font viết tay"}


def check_scene(folder: Path, rel: str, block: dict = None, run_browser=True) -> list:
    """lỗi của 1 cảnh (chuỗi tiếng Việt) — dùng cho soat.py / chat_luong.py"""
    d = (folder / rel).resolve()
    tag = f"cảnh AI “{rel}”"
    if not (d / "index.html").exists():
        return [f"{tag}: không có {rel}/index.html — tạo bằng canh_ai.py moi"]
    errs, warns, meta = lint(d)
    out = [f"{tag}: {e}" for e in errs] + [f"{tag}: (nhắc) {w}" for w in warns]
    if block and meta and meta.get("duration"):
        span = (float(block.get("end", 0)) - float(block.get("start", 0))) * float(block.get("speed") or 1)
        left = meta["duration"] - float(block.get("from") or 0)
        if span > left + 0.1:
            out.append(f"{tag}: khối dài {span:.1f}s nhưng cảnh chỉ còn {left:.1f}s → {span - left:.1f}s cuối đứng hình; "
                       f"tăng duration của cảnh hoặc rút ngắn khối")
    if run_browser and not errs:
        iss, err = font_check(d, data=(block or {}).get("data"))
        if err:
            out.append(f"{tag}: không kiểm được font ({err})")
        for i in iss:
            out.append(f"{tag} giây {i.get('t', 0):.1f}: FONT — {VI_KIND.get(i['kind'], i['kind'])}: “{i.get('text', '')}” "
                       f"({i.get('font', '')} {i.get('weight', '')}{(' — ' + i['why']) if i.get('why') else ''})".replace(" )", ")"))
    return out


def cmd_kiem(args):
    if not args:
        sys.exit(__doc__)
    folder = _folder(args[0])
    plan = {}
    try:
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        pass
    blocks = {e.get("canh"): e for e in plan.get("elements") or [] if e and e.get("type") == "canhAI"}
    names = [f"canh/{args[1]}"] if len(args) > 1 and not args[1].startswith("-") else \
        sorted({*blocks, *(f"canh/{p.name}" for p in (folder / "canh").glob("*") if (p / "index.html").exists())})
    if not names:
        print("Chưa có cảnh AI nào (canh_ai.py moi …)")
        return
    bad = 0
    for n in names:
        r = check_scene(folder, n, blocks.get(n))
        print(f"== {n}: " + ("đạt" if not r else f"{len(r)} vấn đề"))
        for x in r:
            print("- " + x)
        bad += sum(1 for x in r if "(nhắc)" not in x)
    sys.exit(1 if bad else 0)


def cmd_thu(args):
    if len(args) < 2:
        sys.exit(__doc__)
    if args[0] == "san":  # xem thử cảnh dựng sẵn trong kho tool
        folder, d = SAN, SAN / args[1]
    else:
        folder = _folder(args[0])
        d = folder / "canh" / args[1]
    errs, warns, meta = lint(d)
    for e in errs:
        print("LỖI: " + e)
    for w in warns:
        print("nhắc: " + w)
    D = (meta or {}).get("duration") or 6
    moc = _opt(args, "--moc")
    times = [float(x) for x in moc.split(",")] if moc else [round(D * k, 2) for k in (0.08, 0.3, 0.55, 0.8, 0.98)]
    data = json.loads(_opt(args, "--data") or "null") or (None if folder == SAN else _block_data(folder, f"canh/{args[1]}"))
    sync_lib(d)
    srv = _serve(d)
    shots = []
    try:
        for t in times:
            png = Path(tempfile.gettempdir()) / f"canhai_{os.getpid()}_{t:.2f}.png"
            url = f"http://127.0.0.1:{srv.server_address[1]}/index.html" + _hash(data, t=f"{t:.3f}")
            r, err = _chrome(url, [f"--screenshot={png}", "--default-background-color=00000000"])
            if err or not png.exists():
                print(f"[!] không chụp được giây {t}: {err or (r.stderr or '')[-300:]}")
                continue
            shots.append((t, png))
    finally:
        srv.shutdown()
    if not shots:
        sys.exit(1)
    from PIL import Image, ImageDraw
    cw, ch = 360, 640
    sheet = Image.new("RGB", (cw * len(shots), ch + 40), (40, 40, 40))
    chk = Image.new("RGB", (cw, ch), (90, 90, 90))  # ô cờ: thấy được vùng trong suốt
    dr = ImageDraw.Draw(chk)
    for yy in range(0, ch, 40):
        for xx in range(0, cw, 40):
            if (xx // 40 + yy // 40) % 2:
                dr.rectangle([xx, yy, xx + 39, yy + 39], fill=(130, 130, 130))
    for i, (t, png) in enumerate(shots):
        im = Image.open(png).convert("RGBA").resize((cw, ch))
        bg = chk.copy().convert("RGBA")
        bg.alpha_composite(im)
        sheet.paste(bg.convert("RGB"), (i * cw, 40))
        ImageDraw.Draw(sheet).text((i * cw + 10, 10), f"{t:g}s", fill=(255, 220, 120))
        png.unlink(missing_ok=True)
    out = d / "_thu.jpg"
    sheet.save(out, quality=88)
    print(f"Đã chụp {len(shots)} mốc: {out} — MỞ RA XEM (ô cờ xám = vùng trong suốt, video hiện qua)")


def san_list() -> list:
    """đọc dòng chú thích đầu mỗi cảnh dựng sẵn: <!-- CẢNH DỰNG SẴN "<tên>" — mô tả … data: … -->"""
    out = []
    for d in sorted(SAN.glob("*/index.html")):
        html = d.read_text(encoding="utf-8")
        m = re.search(r"<!--\s*CẢNH DỰNG SẴN.*?-->", html, re.S)
        txt = re.sub(r"\s+", " ", m.group(0)[4:-3]) if m else ""
        mo, _, data = txt.partition("data:")
        g = re.search(r"data-duration=\"([\d.]+)\"", html)
        out.append({"ten": d.parent.name, "mo_ta": re.sub(r'^\s*CẢNH DỰNG SẴN "[^"]+"\s*—\s*', "", mo).strip().rstrip("."), "data": data.strip(),
                    "giay": float(g.group(1)) if g else 6})
    return out


def cmd_san(args):
    for x in san_list():
        print(f"- {x['ten']} ({x['giay']:g}s): {x['mo_ta']}\n    data: {x['data']}")
    print('Dùng: canh_ai.py moi "<du-an>" <ten-trong-du-an> --san <tên> · xem thử: canh_ai.py thu san <tên>')


def _block_data(folder: Path, rel: str):
    try:
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        for e in plan.get("elements") or []:
            if e and e.get("type") == "canhAI" and e.get("canh") == rel:
                return e.get("data")
    except Exception:  # noqa
        pass
    return None


def _opt(args, name):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    c, rest = a[0], a[1:]
    if c == "lib":
        build_lib()
    elif c == "ds":
        cmd_ds(rest)
    elif c == "san":
        cmd_san(rest)
    elif c == "xem":
        if not rest:
            sys.exit(__doc__)
        g = guidance(rest[0])
        print(f"# {g}\n")
        print(g.read_text(encoding="utf-8"))
    elif c == "moi":
        cmd_moi(rest)
    elif c == "thu":
        cmd_thu(rest)
    elif c == "kiem":
        cmd_kiem(rest)
    else:
        sys.exit(__doc__)
