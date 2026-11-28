"""BẢN THỬ HYPERFRAMES — dựng video bằng HyperFrames (HeyGen, Apache-2.0) thay cho Remotion, từ cùng plan.json.
Chưa thay render.py: chỉ để so chất lượng / tốc độ / chạy được trên máy ảo hay không.

  python scripts/hf_dung.py "<du-an>" [--chi-tao] [--workers 2] [-o out.mp4]
    -> <du-an>/_hf/ (dự án HyperFrames: index.html + assets) rồi `hyperframes render` ra <du-an>/final-hf.mp4

Khối đã chuyển: video chính (cắt đoạn segments, âm lượng), text (font / cỡ / màu / in hoa / bóng / chuyển sắc grad / hiện mờ hoặc
trượt lên), broll ảnh (phủ kín, lia panFrom→panTo hoặc Ken Burns, mờ vào/ra) và broll video, phụ đề (trang chữ, từ đang đọc đổi màu,
viền), nhạc / khối audio (âm lượng, vuốt đầu cuối), cảnh AI (dựng trước bằng chính HyperFrames ra WebM trong suốt rồi đặt như video).
Chưa chuyển: thẻ đồ hoạ (chip, cta, priceHook…), 3D, bản đồ, chuyển cảnh, hiệu ứng, chỉnh màu, logo, nhạc nhường lời.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
FPS = 30
W, H = 1080, 1920
HF_DIR = ROOT / "_cache" / "hyperframes"   # cài riêng (npm i hyperframes) để không đụng gói của Remotion
DONE = set()
WORKERS = "2"
SKIP = {}


def ensure_hf() -> Path:
    b = HF_DIR / "node_modules" / "hyperframes" / "dist" / "cli.js"
    if not b.exists():
        b = next(iter((HF_DIR / "node_modules" / "hyperframes").glob("bin/*")), None) if (HF_DIR / "node_modules" / "hyperframes").exists() else None
    if not b:
        print("Cài HyperFrames (lần đầu)...", flush=True)
        HF_DIR.mkdir(parents=True, exist_ok=True)
        if not (HF_DIR / "package.json").exists():
            (HF_DIR / "package.json").write_text('{"name":"hf","private":true}', encoding="utf-8")
        subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error", "hyperframes@0.9.104"], cwd=HF_DIR, check=True)
    return HF_DIR / "node_modules" / ".bin" / "hyperframes"


def hf_env() -> dict:
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1", "DO_NOT_TRACK": "1",
           "HYPERFRAMES_RENDER_LOCK": "off", "HYPERFRAMES_NO_AUTO_INSTALL": "1"}
    chs = sorted(Path.home().glob(".cache/chs/*/chrome-headless-shell-linux64/chrome-headless-shell"))
    if chs:  # HyperFrames chụp nhanh hơn hẳn với chrome-headless-shell (BeginFrame)
        env["HYPERFRAMES_BROWSER_PATH"] = str(chs[-1])
        return env
    b = os.environ.get("REMOTION_BROWSER") or ""
    if not b:
        try:
            b = (ROOT / ".trinh-duyet").read_text().strip()
        except Exception:  # noqa
            pass
    if b and Path(b).exists():
        env["HYPERFRAMES_BROWSER_PATH"] = b
    return env


def place(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def esc(t) -> str:
    return html.escape(str(t), quote=True)


def fam(name) -> str:
    return f"'{name}', 'Be Vietnam Pro', sans-serif"


def shadow_css(sh) -> str:
    return {"soft": "0 4px 18px rgba(0,0,0,.45), 0 2px 4px rgba(0,0,0,.35)", "hard": "4px 4px 0 rgba(0,0,0,.6)",
            "glow": "0 0 18px rgba(255,255,255,.6)", "none": "none"}.get(sh or "soft", "0 4px 18px rgba(0,0,0,.45)")


# ------------------------------------------------------------------ cảnh AI -> WebM trong suốt
def render_scene(folder: Path, out_dir: Path, rel: str, data: dict, hf: Path, style: dict = None) -> Path:
    import canh_ai
    import hashlib
    src = (folder / rel).resolve()
    key = hashlib.md5((rel + json.dumps(data or {}, ensure_ascii=False, sort_keys=True)
                       + str((src / "index.html").stat().st_mtime)).encode()).hexdigest()[:8]
    webm = out_dir / "assets" / f"canh_{Path(rel).name}_{key}.webm"
    if webm.exists():
        return webm
    tmp = folder / "_work" / "_hf_canh" / f"{Path(rel).name}_{key}"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp, ignore=shutil.ignore_patterns("lib", "_thu.jpg", "MAU.md"))
    canh_ai.sync_lib(tmp, link=False)
    page = (tmp / "index.html").read_text(encoding="utf-8")
    inject = ("<script>window.CANH_FIXED=" + json.dumps({"data": data or {}, "w": W, "h": H, "style": style or {}}, ensure_ascii=False) + ";</script>"
              + ('<script src="./lib/vendor/gsap.min.js"></script>' if "gsap.min.js" not in page else ""))
    page = page.replace('<script src="./lib/runtime/scene.js">', inject + '<script src="./lib/runtime/scene.js">', 1)
    (tmp / "index.html").write_text(page, encoding="utf-8")
    webm.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r = subprocess.run([str(hf), "render", str(tmp), "--format", "webm", "--quiet", "-o", str(webm), "--workers", WORKERS],
                       env=hf_env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not webm.exists():
        raise RuntimeError(f"Dựng cảnh {rel} lỗi:\n" + (r.stdout + r.stderr)[-1200:])
    print(f"  cảnh AI {rel}: {time.time() - t0:.0f}s", flush=True)
    return webm


# ------------------------------------------------------------------ dựng index.html
def build(folder: Path, hf: Path) -> Path:
    import render as R
    plan = R.build_plan(folder)
    st = plan.get("style") or {}
    tx = st.get("text") or {}
    out = folder / "_hf"
    (out / "assets").mkdir(parents=True, exist_ok=True)
    total = float(plan["durationSec"])
    nodes, tl = [], []
    z = 1

    def asset(rel: str) -> str:
        p = (folder / rel).resolve()
        name = rel.replace("/", "__")
        place(p, out / "assets" / name)
        return "assets/" + name

    # 1. video chính (theo đoạn giữ lại)
    vsrc = asset(plan["videoSrc"])
    vol = float(plan.get("videoVolume", 1) or 0)
    segs = plan.get("segments") or [[0, total]]
    acc = 0.0
    for i, (a, b) in enumerate(segs):
        d = b - a
        snd = f'data-has-audio="true" data-volume="{vol:g}"' if vol > 0 else "muted"
        nodes.append(f'<video id="main{i}" class="clip full" src="{vsrc}" data-start="{acc:.3f}" data-duration="{d:.3f}" '
                     f'data-media-start="{a:.3f}" data-track-index="0" playsinline {snd} style="z-index:{z}"></video>')
        acc += d
    DONE.add("video chính")

    # 2. khối
    for k, e in enumerate(plan.get("elements") or []):
        if not e or e.get("hidden"):
            continue
        t, a, b = e.get("type"), float(e.get("start", 0)), float(e.get("end", 0))
        d = max(0.05, b - a)
        zi = int(e.get("z") or (10 if t in ("broll", "canhAI") else 30)) + 1
        idn = f"e{k}"
        fi, fo = float(e.get("inDur") or e.get("fadeIn") or 0.4), float(e.get("outDur") or e.get("fadeOut") or 0.35)
        if t == "text":
            font = e.get("font") or tx.get("font") or st.get("heading") or st.get("font") or "Be Vietnam Pro"
            size = e.get("size") or tx.get("size") or 80
            wt = e.get("weight") or tx.get("weight") or 800
            color = e.get("color") or tx.get("color") or "#fff"
            up = e.get("upper", tx.get("upper", False))
            sp = e.get("spacing", tx.get("spacing", 0)) or 0
            y = e.get("y", 700)
            grad = e.get("grad")
            css = (f"position:absolute;left:{(W - (e.get('width') or 960)) / 2}px;width:{e.get('width') or 960}px;top:{y}px;"
                   f"text-align:{e.get('align') or 'center'};font-family:{fam(font)};font-size:{size}px;font-weight:{wt};"
                   f"line-height:1.18;letter-spacing:{sp}px;{'text-transform:uppercase;' if up else ''}"
                   f"{'font-style:italic;' if e.get('italic') else ''}z-index:{zi};")
            inner = f'<span class="tx" style="text-shadow:{shadow_css(e.get("shadow") or tx.get("shadow"))};color:{color}">{esc(e.get("text", ""))}</span>'
            if grad:
                g = ",".join(grad)
                inner = (f'<span class="tx" style="background:linear-gradient({e.get("gradAngle", 180)}deg,{g});-webkit-background-clip:text;'
                         f'background-clip:text;color:transparent;filter:drop-shadow(0 4px 10px rgba(0,0,0,.45))">{esc(e.get("text", ""))}</span>')
            nodes.append(f'<div id="{idn}" class="clip" data-start="{a:.3f}" data-duration="{d:.3f}" data-track-index="2" style="{css}">{inner}</div>')
            anim = e.get("anim") or tx.get("anim") or "fade"
            y0 = 30 if anim in ("up", "rise", "maskUp") else 0
            tl.append(f'tl.fromTo("#{idn} .tx",{{opacity:0,y:{y0}}},{{opacity:1,y:0,duration:{min(fi, d / 2):.2f},ease:"power2.out"}},{a:.3f});')
            tl.append(f'tl.to("#{idn} .tx",{{opacity:0,duration:{min(fo, d / 2):.2f},ease:"power1.in"}},{b - min(fo, d / 2):.3f});')
            DONE.add("chữ")
        elif t == "broll" and e.get("src"):
            src = asset(e["src"])
            isvid = re.search(r"\.(mp4|mov|webm|m4v|mkv)$", src, re.I)
            fit = "contain" if e.get("fit") == "contain" else "cover"
            if isvid:
                v = float(e.get("volume") or 0)
                snd = f'data-has-audio="true" data-volume="{v:g}"' if v > 0 else "muted"
                nodes.append(f'<video id="{idn}" class="clip full" src="{src}" data-start="{a:.3f}" data-duration="{d:.3f}" '
                             f'data-media-start="{float(e.get("from") or 0):.3f}" data-track-index="1" playsinline {snd} '
                             f'style="object-fit:{fit};z-index:{zi}"></video>')
            else:
                nodes.append(f'<div id="{idn}" class="clip full" data-start="{a:.3f}" data-duration="{d:.3f}" data-track-index="1" '
                             f'style="z-index:{zi};overflow:hidden"><img class="im" src="{src}" alt="" style="object-fit:{fit}"></div>')
                if e.get("panFrom") is not None and e.get("panTo") is not None:
                    tl.append(f'tl.fromTo("#{idn} .im",{{objectPosition:"{float(e["panFrom"]) * 100:.1f}% 50%"}},'
                              f'{{objectPosition:"{float(e["panTo"]) * 100:.1f}% 50%",duration:{d:.3f},ease:"sine.inOut"}},{a:.3f});')
                elif e.get("kb") is not False:
                    tl.append(f'tl.fromTo("#{idn} .im",{{scale:1}},{{scale:1.08,duration:{d:.3f},ease:"none"}},{a:.3f});')
            if (e.get("transition") or "fade") != "cut":
                tl.append(f'tl.fromTo("#{idn}",{{opacity:0}},{{opacity:1,duration:{min(fi, d / 2):.2f}}},{a:.3f});')
            if (e.get("exit") or "fade") != "cut":
                tl.append(f'tl.to("#{idn}",{{opacity:0,duration:{min(fo, d / 2):.2f}}},{b - min(fo, d / 2):.3f});')
            DONE.add("ảnh / video trám")
        elif t == "canhAI" and e.get("canh"):
            webm = render_scene(folder, out, e["canh"], e.get("data"), hf,
                                {"font": st.get("font"), "heading": st.get("heading") or st.get("font"), "fonts": st.get("fonts"),
                                 "text": st.get("text"), "captions": st.get("captions"), "accent": st.get("accent")})
            rel = "assets/" + webm.name
            sp = float(e.get("speed") or 1)
            nodes.append(f'<video id="{idn}" class="clip full" src="{rel}" data-start="{a:.3f}" data-duration="{d:.3f}" '
                         f'data-media-start="{float(e.get("from") or 0):.3f}" data-playback-rate="{sp:g}" data-track-index="1" muted playsinline '
                         f'style="z-index:{zi};object-fit:cover"></video>')
            cfi, cfo = float(e.get("fadeIn", 0.25)), float(e.get("fadeOut", 0.25))
            if cfi > 0:
                tl.append(f'tl.fromTo("#{idn}",{{opacity:0}},{{opacity:1,duration:{cfi:.2f}}},{a:.3f});')
            if cfo > 0:
                tl.append(f'tl.to("#{idn}",{{opacity:0,duration:{cfo:.2f}}},{b - cfo:.3f});')
            DONE.add("cảnh AI")
        elif t == "audio" and e.get("src"):
            src = asset(e["src"])
            v = float(e.get("volume") if e.get("volume") is not None else 1)
            nodes.append(f'<audio id="{idn}" src="{src}" data-start="{a:.3f}" data-duration="{d:.3f}" data-media-start="{float(e.get("from") or 0):.3f}" '
                         f'data-volume="{v:g}" data-fade-in="{float(e.get("fadeIn") or 0):g}" data-fade-out="{float(e.get("fadeOut") or 0):g}" '
                         f'data-track-index="5"></audio>')
            DONE.add("nhạc / âm thanh")
        else:
            SKIP[t] = SKIP.get(t, 0) + 1
    if plan.get("music") and plan["music"].get("src"):
        src = asset(plan["music"]["src"])
        nodes.append(f'<audio id="nhac" src="{src}" data-start="0" data-duration="{total:.3f}" data-volume="{float(plan["music"].get("volume", 0.15)):g}" '
                     f'data-fade-in="0.5" data-fade-out="1.5" data-track-index="6"></audio>')
        DONE.add("nhạc / âm thanh")

    # 3. phụ đề
    caps = plan.get("captions") if isinstance(plan.get("captions"), list) else []
    if caps:
        c = st.get("captions") or {}
        up = c.get("upper", False)
        top = plan.get("captionTop", 1390)
        css = (f"position:absolute;left:60px;right:60px;top:{top}px;text-align:center;font-family:{fam(c.get('font') or st.get('font') or 'Be Vietnam Pro')};"
               f"font-size:{c.get('size', 56)}px;font-weight:{c.get('weight', 800)};color:{c.get('color', '#fff')};line-height:1.25;z-index:60;")
        stroke = c.get("stroke") or 0
        tsh = f"-webkit-text-stroke:{stroke * 2}px {c.get('strokeColor', '#000')};paint-order:stroke fill;" if stroke else "text-shadow:0 3px 10px rgba(0,0,0,.6);"
        for i, pg in enumerate(caps):
            if not pg:
                continue
            a, b = pg[0]["start"], pg[-1]["end"]
            ws = []
            for j, w in enumerate(pg):
                txt = w["w"] if (up or w.get("keep")) else w["w"].lower()
                ws.append(f'<span class="w" id="c{i}w{j}" style="{tsh}">{esc(txt)}</span>')
                if c.get("active"):
                    tl.append(f'tl.set("#c{i}w{j}",{{color:"{c["active"]}"}},{w["start"]:.3f});tl.set("#c{i}w{j}",{{color:"{c.get("color", "#fff")}"}},{w["end"]:.3f});')
            nodes.append(f'<div id="cap{i}" class="clip" data-start="{a:.3f}" data-duration="{max(0.1, b - a):.3f}" data-track-index="3" '
                         f'style="{css}{"text-transform:uppercase;" if up else ""}">{" ".join(ws)}</div>')
        DONE.add("phụ đề")

    # 4. ghép trang
    import canh_ai
    canh_ai.ensure_lib()
    lib = out / "lib"
    for sub in ("fonts", "vendor"):
        if (lib / sub).exists():
            shutil.rmtree(lib / sub)
    shutil.copytree(canh_ai.LIB / "fonts", lib / "fonts")
    (lib / "vendor").mkdir(parents=True, exist_ok=True)
    shutil.copy2(canh_ai.LIB / "vendor" / "gsap.min.js", lib / "vendor" / "gsap.min.js")
    page = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<link rel="stylesheet" href="lib/fonts/fonts.css">
<script src="lib/vendor/gsap.min.js"></script>
<style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
.full{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover}}
.full .im{{width:100%;height:100%;display:block}}
.w{{display:inline-block;margin:0 .12em}}
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
{chr(10).join(nodes)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
tl.set({{}}, {{}}, {total:.3f});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script>
</body></html>
"""
    (out / "index.html").write_text(page, encoding="utf-8")
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    folder = Path(a[0]).resolve()
    global WORKERS
    if "--workers" in a:
        WORKERS = a[a.index("--workers") + 1]
    hf = ensure_hf()
    t0 = time.time()
    out = build(folder, hf)
    t1 = time.time()
    print(f"Đã tạo dự án HyperFrames: {out}/index.html ({t1 - t0:.0f}s, gồm dựng cảnh AI)")
    print("Đã chuyển: " + ", ".join(sorted(DONE)) + (" · CHƯA chuyển (bỏ qua): " + ", ".join(f"{k}×{v}" for k, v in SKIP.items()) if SKIP else ""))
    if "--chi-tao" in a:
        return
    dst = Path(a[a.index("-o") + 1]) if "-o" in a else folder / "final-hf.mp4"
    r = subprocess.run([str(hf), "render", str(out), "-o", str(dst), "--workers", WORKERS, "--quality", "looks"], env=hf_env())
    if r.returncode:
        sys.exit("HyperFrames dựng lỗi")
    import render as R
    R.chuan_loudness(dst)
    print(f"XONG HyperFrames: {dst} — dựng hình {time.time() - t1:.0f}s (tổng {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
