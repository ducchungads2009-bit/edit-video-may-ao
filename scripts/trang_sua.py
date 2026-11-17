"""Tạo TRANG CHỈNH SỬA cho một dự án (bản máy ảo): video xem thử nhẹ, ảnh từng cảnh, chữ, phụ đề, nhạc, phong cách.

    python3 scripts/trang_sua.py "cho-edit/<du-an>" [--ten "Tên hiện trên trang"]

Ra thư mục <du-an>/_trang-sua/ (index.html + du-lieu.json + preview.mp4 + canh*.jpg) để Claude đăng thành artifact
(publish_files, rồi declare_capabilities db với rule "ban-sua"). Người dùng sửa trên điện thoại, bấm Lưu -> tài liệu
db "ban-sua/hien-tai"; Claude đọc (db_get) rồi chạy ap_ban_sua.py.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_MB = 17  # mỗi file của artifact ≤ 20 MiB (bản 1 file: 10)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def dur_of(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def lines_of(words, gap=0.45, maxw=12):
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["start"] - words[i - 1]["end"] > gap or len(cur) >= maxw):
            out.append(cur); cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [{"t": round(l[0]["start"], 2), "e": round(l[-1]["end"], 2), "text": " ".join(x["w"] for x in l)} for l in out]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    proj = (ROOT / args[0]).resolve() if not Path(args[0]).is_absolute() else Path(args[0])
    ten = args[args.index("--ten") + 1] if "--ten" in args else proj.name
    plan = json.loads((proj / "plan.json").read_text(encoding="utf-8"))
    info = json.loads((proj / "_work/info.json").read_text(encoding="utf-8"))
    final = proj / "final.mp4"
    if not final.exists():
        print("Chưa có final.mp4 — dựng (render.py) trước."); sys.exit(2)
    out = proj / "_trang-sua"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    pv_file = proj / "_work/trang-sua-phien.txt"
    phien = int(pv_file.read_text()) + 1 if pv_file.exists() else 1
    pv_file.write_text(str(phien))

    # video xem thử ≤ MAX_MB
    d = max(1.0, dur_of(final))
    mx = 10 if "--mot-file" in args else MAX_MB
    vb = int(max(250_000, min(1_500_000, mx * 8e6 / d - 96_000)))
    run(["ffmpeg", "-y", "-i", str(final), "-vf", "scale=540:-2", "-c:v", "libx264", "-preset", "veryfast", "-b:v", str(vb),
         "-maxrate", str(int(vb * 1.3)), "-bufsize", str(vb * 2), "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out / "preview.mp4")])

    # cảnh = segments (giây trên video chính); không có segments -> cả video là 1 cảnh
    src = proj / info["video"]
    segs = plan.get("segments") or [[0, info["durationSec"]]]
    words = []
    wf = proj / "_work/words.json"
    if wf.exists():
        words = json.loads(wf.read_text(encoding="utf-8"))
        if isinstance(words, dict):
            words = words.get("words", [])
    nf = proj / "_work/nhan-canh.json"  # Claude ghi tên từng cảnh (vd "Phòng khách") nếu muốn
    nhan = json.loads(nf.read_text(encoding="utf-8")) if nf.exists() else []
    cards = []
    for i, (a, b) in enumerate(segs):
        f = f"canh{i + 1}.jpg"
        run(["ffmpeg", "-y", "-ss", f"{(a + b) / 2:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=180:-2", "-q:v", "5", str(out / f)])
        loi = " ".join(w["w"] for w in words if a - 0.02 <= w["start"] < b)
        lab = nhan[i] if i < len(nhan) and nhan[i] else (loi[:40] + ("…" if len(loi) > 40 else "") if loi else f"Cảnh {i + 1}")
        cards.append({"a": a, "b": b, "thumb": f, "nhan": lab, "loi": loi})

    # phụ đề: từng câu (giây video chính) — sửa câu nào thì thành "fixes"
    phude = lines_of(words) if plan.get("captions") is True and words else []
    if isinstance(plan.get("captions"), list):  # phụ đề sửa tay dạng trang
        phude = [{"t": p[0]["start"], "e": p[-1]["end"], "text": " ".join(w["w"] for w in p)} for p in plan["captions"] if p]

    fixes = [f for f in (plan.get("fixes") or []) if isinstance(f, list) and len(f) == 2]
    for l in phude:  # hiện đúng chữ đang ra màn hình (đã áp fixes), giữ bản máy nghe để áp sửa
        l["goc"] = l["text"]
        for a, b in fixes:
            l["text"] = l["text"].replace(str(a).upper(), str(b).upper())

    nhac_dir = ROOT / "assets-chung/nhac"
    nhac = json.loads((nhac_dir / "danh-sach.json").read_text(encoding="utf-8")) if (nhac_dir / "danh-sach.json").exists() else []
    nhac = [{"file": t.get("file"), "ten": t.get("title"), "mood": t.get("mood")} for t in (nhac if isinstance(nhac, list) else nhac.get("tracks", []))]
    styles = sorted(p.name for p in (ROOT / "phong-cach").iterdir() if p.is_dir() and not p.name.startswith("_"))
    pc = ""
    pf = proj / "phong-cach-tron.json"
    if pf.exists():
        try:
            vals = [v for v in json.loads(pf.read_text(encoding="utf-8")).values() if isinstance(v, str) and v]
            pc = max(set(vals), key=vals.count) if vals else ""
        except Exception:
            pc = ""
    music = plan.get("music") or {}
    data = {"ten": ten, "phienBan": phien, "video": "preview.mp4", "segs": cards, "plan": {k: plan.get(k) for k in ("elements", "music", "captions") if k in plan},
            "phuDe": phude, "nhac": nhac, "phongCach": styles, "phongCachHienTai": pc,
            "nhacHienTai": Path(music.get("src", "")).name if music.get("src") else ""}
    if isinstance(data["plan"].get("captions"), list):
        data["plan"]["captions"] = True
    (out / "du-lieu.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    shutil.copy(ROOT / "scripts/trang_sua.html", out / "index.html")
    # lưu bản gốc lúc tạo trang (để áp bản sửa đúng mốc)
    (proj / "_work/trang-sua-goc.json").write_text(json.dumps({"phien": phien, "segments": segs, "plan": plan}, ensure_ascii=False), encoding="utf-8")
    if "--mot-file" in args:  # 1 file HTML mở được ở mọi nơi (ChatGPT, máy tính) — video + ảnh nhúng sẵn
        import base64
        def durl(f, mime):
            return f"data:{mime};base64," + base64.b64encode((out / f).read_bytes()).decode()
        d1 = dict(data, video=durl("preview.mp4", "video/mp4"), segs=[dict(c, thumb=durl(c["thumb"], "image/jpeg")) for c in cards])
        html = (out / "index.html").read_text(encoding="utf-8")
        inj = "<script>window.__DU_LIEU__=" + json.dumps(d1, ensure_ascii=False).replace("</", "<\\/") + ";</script>"
        html = html.replace("<script>", inj + "\n<script>", 1)
        mf = proj / f"sua-video-{phien}.html"
        mf.write_text(html, encoding="utf-8")
        print(f"Trang sửa 1 file: {mf}  ({mf.stat().st_size / 1e6:.1f} MB)")
    if "--phieu" in args:  # ảnh lưới các cảnh có đánh số — để sửa bằng chat ("bỏ cảnh 3", "đổi cảnh 2 với 5")
        from PIL import Image, ImageDraw, ImageFont
        ims = [Image.open(out / c["thumb"]).convert("RGB") for c in cards]
        if ims:
            w, h = ims[0].size; cols = min(5, len(ims)); rows = (len(ims) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + 6) + 6), "white")
            dr = ImageDraw.Draw(sheet)
            try:
                font = ImageFont.load_default(size=34)
            except TypeError:
                font = ImageFont.load_default()
            for k, im in enumerate(ims):
                x, y = 6 + (k % cols) * (w + 6), 6 + (k // cols) * (h + 6)
                sheet.paste(im.resize((w, h)), (x, y))
                dr.rectangle([x, y, x + 52, y + 44], fill="black")
                dr.text((x + 8, y + 2), str(k + 1), fill="yellow", font=font)
            pf2 = proj / f"phieu-canh-{phien}.jpg"
            sheet.save(pf2, quality=85)
            print(f"Phiếu cảnh: {pf2}")
    files = sorted(p.name for p in out.iterdir())
    mb = sum(p.stat().st_size for p in out.iterdir()) / 1e6
    print(f"Trang chỉnh sửa (bản dựng số {phien}): {out}  ·  {len(files)} file, {mb:.1f} MB")
    print("FILES " + json.dumps(files, ensure_ascii=False))


if __name__ == "__main__":
    main()
