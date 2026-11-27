"""Soát ĐỘ TƯƠNG PHẢN chữ với nền — chữ phải tách biệt, nổi hẳn trên nền video (không hoà vào nền sáng / cùng màu).

  python scripts/tuong_phan.py "<folder>"          -> báo các khối chữ khó đọc (lấy khung video gốc / ảnh trám đúng lúc, đúng chỗ chữ)
  python scripts/tuong_phan.py "<folder>" --sua    -> tự sửa trong plan.json: hơi khó đọc = thêm viền tối (giữ kiểu chữ, màu);
                                                       rất khó đọc = đặt chữ lên nền khối (look "solid", nền tối/sáng mờ, giữ màu chữ)
Cách đo: tỉ lệ tương phản WCAG giữa màu chữ và từng điểm ảnh nền trong vùng chữ (3 thời điểm trong khối).
Chữ có viền tương phản đủ dày, hoặc kiểu có nền khối (solid / highlight / tag…) thì coi là đọc được.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PLATE_LOOKS = {"solid", "highlight", "skew", "tape", "pill2", "dashed", "chat", "box", "gold", "tag"}
NAMED = {"white": "#ffffff", "black": "#000000", "yellow": "#ffff00", "red": "#ff0000"}
SC = 4  # khung lấy mẫu = 1080x1920 / SC


def rgb(c: str):
    c = NAMED.get(str(c).lower().strip(), str(c).strip())
    m = re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", c)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(x * 2 for x in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a: float, b: float) -> float:
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def out_to_src(plan: dict, t: float) -> float:
    segs = plan.get("segments")
    if not segs:
        return t
    acc = 0.0
    for a, b in segs:
        if t < acc + (b - a):
            return a + (t - acc)
        acc += b - a
    return segs[-1][1] - 0.05


def frame(src: Path, t: float, W: int, H: int):
    """khung (PIL, W x H, phủ kín như video dọc) của video / ảnh ở giây t"""
    from PIL import Image
    import io
    if src.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        im = Image.open(src).convert("RGB")
    else:
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", str(src), "-frames:v", "1",
                            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True)
        if r.returncode or not r.stdout:
            return None
        im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    if im.size != (W, H):
        s = max(W / im.width, H / im.height)
        im = im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))))
        l, tp = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((l, tp, l + W, tp + H))
    return im


def is_layer(b: dict) -> bool:
    """khối broll là lớp phủ trong suốt (PNG trong assets/lop/ hoặc đặt z trên ảnh trám)"""
    s = str(b.get("src") or "")
    return s.lower().endswith(".png") and ("assets/lop/" in s or (isinstance(b.get("z"), (int, float)) and b["z"] > 10))


def over(im, png: Path, W: int, H: int):
    """ghép lớp PNG có kênh trong suốt lên khung (đúng vị trí, phủ kín khung)"""
    from PIL import Image
    try:
        lay = Image.open(png).convert("RGBA").resize((W, H))
        return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")
    except Exception:  # noqa
        return im


def text_box(e: dict, size: float, fw: int, fh: int):
    lines = str(e.get("text") or "").split("\n")
    upper = e.get("upper", True)
    chars = max((len(x) for x in lines), default=1)
    w = min(fw - 80, e.get("width") or chars * size * (0.62 if upper else 0.55) + 48)
    h = len(lines) * size * 1.32 + 24
    cx = (e["x"] if isinstance(e.get("x"), (int, float)) else 0.5) * fw
    y = float(e.get("y", 700)) + float(e.get("dy") or 0)
    cx += float(e.get("dx") or 0)
    return max(0, cx - w / 2), max(0, y), min(fw, cx + w / 2), min(fh, y + h)


def check(folder: Path, fix: bool = False) -> list:
    import phongcach
    folder = Path(folder).resolve()
    pf = folder / "plan.json"
    plan = json.loads(pf.read_text(encoding="utf-8"))
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    vid = folder / info.get("video", "")
    st = (phongcach.project_style(folder) or {}).get("style") or {}
    st = phongcach._merge(st, plan.get("style") or {})
    d = st.get("text") or {}
    try:
        import khung
        FW, FH = khung.OUT.get(khung.get(folder), (1080, 1920)) if hasattr(khung, "OUT") else (1080, 1920)
    except Exception:
        FW, FH = 1080, 1920
    W, H = FW // SC, FH // SC
    els = plan.get("elements") or []
    out = []
    for i, e in enumerate(els):
        if not e or e.get("type") != "text" or e.get("hidden") or not str(e.get("text") or "").strip():
            continue
        look = e.get("look") or d.get("look") or "plain"
        if look in PLATE_LOOKS:
            continue
        size = float(e.get("size") or d.get("size") or 80) * float(e.get("sc") or 1)
        col = rgb(e.get("color") or d.get("color") or "#ffffff") or (255, 255, 255)
        stroke = e.get("stroke", d.get("stroke"))
        if stroke is None:
            stroke = round(size / 5) if look == "outline" else round(size / 7) if look == "plain" else 0
        sc = rgb(e.get("strokeColor") or d.get("strokeColor") or ("#000000" if look == "outline" else "#1a1a1a")) or (0, 0, 0)
        Lt = lum(col)
        if stroke >= max(3, size / 14) and ratio(Lt, lum(sc)) >= 4.5:
            continue  # viền tương phản đủ dày -> đọc được trên mọi nền
        x0, y0, x1, y1 = [v / SC for v in text_box(e, size, FW, FH)]
        worst, mean_r = 0.0, 99.0
        for k in (0.2, 0.5, 0.85):
            t = e["start"] + (e["end"] - e["start"]) * k
            act = [b for b in els if b and b.get("type") == "broll" and b.get("src") and b["start"] <= t < b["end"] and not b.get("hidden")]
            lay = [b for b in act if is_layer(b)]  # lớp phủ trong suốt (vd lớp che sáng assets/lop/che-sang.png) — ghép lên nền khi đo
            br = next((b for b in act if not is_layer(b)), None)
            if br and (folder / br["src"]).exists():
                im = frame(folder / br["src"], float(br.get("from") or 0) + (t - br["start"]) * float(br.get("rate") or 1), W, H)
            else:
                im = frame(vid, out_to_src(plan, t), W, H)
            if im is None:
                continue
            for b in lay:
                im = over(im, folder / b["src"], W, H)
            reg = im.crop((int(x0), int(y0), max(int(x0) + 1, int(x1)), max(int(y0) + 1, int(y1))))
            px = list(reg.get_flattened_data() if hasattr(reg, "get_flattened_data") else reg.getdata())
            if not px:
                continue
            rs = [ratio(Lt, lum(p)) for p in px]
            bad = sum(1 for r in rs if r < 2.2) / len(rs)
            worst = max(worst, bad)
            mean_r = min(mean_r, sorted(rs)[len(rs) // 2])
        if worst < 0.3:
            continue
        lvl = "RẤT KHÓ ĐỌC" if worst >= 0.6 else "khó đọc"
        item = {"i": i, "text": str(e.get("text")).replace("\n", " / "), "start": e["start"], "bad": round(worst, 2), "median": round(mean_r, 1), "lvl": lvl}
        if fix:
            light = Lt > 0.35
            if worst >= 0.6:
                e.update(look="solid", bg="#0B0F19D9" if light else "#FFFFFFE6", radius=e.get("radius", 16), stroke=0)
                item["sua"] = "đặt lên nền khối " + ("tối" if light else "sáng") + " (giữ màu chữ)"
            else:
                e.update(stroke=max(4, round(size / 10)), strokeColor="#05070A" if light else "#FFFFFF")
                if look != "neon" and e.get("shadow") in (None, "none", "soft"):
                    e["shadow"] = "hard"
                item["sua"] = "thêm viền " + ("tối" if light else "sáng")
        out.append(item)
    if fix and any("sua" in x for x in out):
        pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    r = check(Path(sys.argv[1]), "--sua" in sys.argv)
    if not r:
        print("Tương phản chữ: ổn — mọi khối chữ đều nổi rõ trên nền.")
    for x in r:
        print(f"[{x['lvl']}] khối #{x['i']} ở {x['start']:.1f}s “{x['text'][:40]}” — {int(x['bad'] * 100)}% vùng chữ gần màu chữ"
              + (f" → đã sửa: {x['sua']}" if x.get("sua") else " → chạy với --sua để tự sửa (hoặc đổi màu / thêm viền / nền khối)"))
