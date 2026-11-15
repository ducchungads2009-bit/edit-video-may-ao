"""Bảng xem nhanh TƯ LIỆU MINH HỌA người dùng đưa trước (ảnh/video trong <folder>/assets/cua-ban/).

Dùng:  python scripts/tu_lieu.py "<folder>"

Tạo  <folder>/_work/tu-lieu_1.jpg, _2.jpg ... (mỗi ảnh tối đa 20 ô, đánh số #1, #2 ...; video có 3 khung đầu-giữa-cuối)
     <folder>/_work/tu-lieu.json  (số thứ tự, đường dẫn, loại, kích thước, thời lượng)
Claude xem bảng này để biết từng tư liệu là gì, rồi chọn chỗ chèn hợp lý (xem CLAUDE.md, mục "Tư liệu của người dùng").
"""
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic"}
VID_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
CW, CH, LAB, COLS, PER = 300, 300, 46, 5, 20


def frames(video: Path, dur: float, tmp: Path) -> list:
    out = []
    for k, t in enumerate([dur * 0.1, dur * 0.5, max(0.0, dur * 0.9 - 0.1)]):
        f = tmp / f"_f{k}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(f)], capture_output=True)
        if f.exists():
            out.append(f)
    return out


def main(folder: Path):
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    src = folder / "assets" / "cua-ban"
    files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT | VID_EXT) if src.is_dir() else []
    work = folder / "_work"
    work.mkdir(exist_ok=True)
    for old in work.glob("tu-lieu_*.jpg"):
        old.unlink()
    if not files:
        (work / "tu-lieu.json").write_text("[]", encoding="utf-8")
        print("Không có tư liệu trong assets/cua-ban/ — bỏ qua.")
        return
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 18)
            except Exception:
                font = ImageFont.load_default()
    try:  # ghi chú của người dùng cho từng file (giao diện: ô "Ghi chú" dưới mỗi tư liệu)
        notes = json.loads((src / "_ghi-chu.json").read_text(encoding="utf-8"))
    except Exception:
        notes = {}
    items, cells = [], []
    for i, p in enumerate(files, 1):
        rel = p.relative_to(folder).as_posix()
        cell = Image.new("RGB", (CW, CH + LAB), (24, 30, 44))
        d = ImageDraw.Draw(cell)
        info = {"so": i, "src": rel}
        if p.suffix.lower() in VID_EXT:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height:format=duration", "-of", "json", str(p)], capture_output=True, text=True)
            try:
                j = json.loads(r.stdout)
                dur = float(j["format"]["duration"])
                w, h = j["streams"][0]["width"], j["streams"][0]["height"]
            except Exception:
                dur, w, h = 0.0, 0, 0
            info.update(kind="video", durationSec=round(dur, 1), w=w, h=h)
            fs = frames(p, dur, work)
            for k, f in enumerate(fs):  # 3 khung xếp dọc
                im = Image.open(f).convert("RGB")
                im = ImageOps.pad(im, (CW, CH // 3), color=(0, 0, 0))
                cell.paste(im, (0, k * (CH // 3)))
                try:
                    f.unlink()
                except OSError:
                    pass
            tag = f"#{i} VIDEO {dur:.0f}s"
        else:
            try:
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                info.update(kind="image", w=im.width, h=im.height)
                cell.paste(ImageOps.pad(im, (CW, CH), color=(0, 0, 0)), (0, 0))
            except Exception:
                info.update(kind="image", w=0, h=0, loi="không mở được ảnh")
            tag = f"#{i} ẢNH"
        name = p.name if len(p.name) <= 30 else p.name[:27] + "..."
        note = (notes.get(p.name) or "").strip()
        if note:
            info["ghiChu"] = note
            tag += "  ✍ CÓ GHI CHÚ"
        d.text((8, CH + 4), tag, fill=(255, 214, 90), font=font)
        d.text((8, CH + 24), name, fill=(220, 228, 240), font=font)
        items.append(info)
        cells.append(cell)
    pages = [cells[k:k + PER] for k in range(0, len(cells), PER)]
    for n, pg in enumerate(pages, 1):
        rows = (len(pg) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * (CW + 8) + 8, rows * (CH + LAB + 8) + 8), (10, 14, 22))
        for k, c in enumerate(pg):
            sheet.paste(c, (8 + (k % COLS) * (CW + 8), 8 + (k // COLS) * (CH + LAB + 8)))
        sheet.save(work / f"tu-lieu_{n}.jpg", quality=85)
    (work / "tu-lieu.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Xong: {len(items)} tư liệu -> {len(pages)} bảng xem nhanh (_work/tu-lieu_*.jpg)")
    for it in items:  # in ghi chú để Claude đọc ngay
        print(f"  #{it['so']} {Path(it['src']).name}: " + (f"GHI CHÚ CỦA NGƯỜI DÙNG — {it['ghiChu']}" if it.get("ghiChu") else "không ghi chú → tự chọn chỗ"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/tu_lieu.py "<folder>"')
    main(Path(sys.argv[1]).resolve())
