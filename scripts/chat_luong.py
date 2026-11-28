"""CỔNG CHẤT LƯỢNG — soát plan.json theo CHUẨN CHUNG cho mọi AI (Claude, ChatGPT, Codex) và MỌI phong cách.
soat.py tự gọi; chạy riêng: python scripts/chat_luong.py "<folder>"
Bắt các lỗi làm video "khác tay": lệch phong cách (font / kiểu hộp chữ ngoài bộ), ảnh thu nhỏ / đóng khung, ảnh tĩnh quá lâu,
ảnh độ phân giải thấp, chữ ghi nguồn giữa màn hình, thiếu nhạc nền, ảnh lặp sát nhau, brief cần ảnh dự án mà toàn ảnh stock,
script tự viết trong _work để dựng hình, font thiếu dấu tiếng Việt (kiem_font.py), cảnh AI sai luật / lỗi font (canh_ai.py). Chuẩn đầy đủ: huong-dan/chat-luong.md (máy ảo: CHAT-LUONG.md).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PLATE = {"solid", "highlight", "skew", "tape", "pill2", "dashed", "chat", "box", "gold", "tag"}
IMG = re.compile(r"\.(jpe?g|png|webp|avif|bmp)$", re.I)
CREDIT = re.compile(r"(wikimedia|wikipedia|cc[ -]?by|cc0|creative commons|unsplash|pixabay|openverse|nguồn:|ảnh:|photo:|©|bản quyền ảnh|·\s*vinhomes market)", re.I)
NEED_REAL = re.compile(r"(hình ảnh (về )?dự án|ảnh (về )?dự án|ảnh thật|phối cảnh|tìm (hình|ảnh)|minh hoạ dự án|minh họa dự án)", re.I)


def _style(folder: Path) -> dict:
    try:
        import phongcach
        ps = phongcach.project_style(folder)
        return (ps or {}).get("style") or {}
    except Exception:  # noqa
        return {}


def _img_size(p: Path):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:  # noqa
        return None


def _is_stock_generic(folder: Path, src: str) -> bool:
    """ảnh/video lấy từ Pixabay (cảnh chung chung) — dựa vào _pick_<tên>.json của lần tải"""
    p = folder / src
    if not src.startswith("assets/stock/"):
        return False
    pj = p.parent / f"_pick_{p.stem}.json"
    try:
        return "pixabay" in pj.read_text(encoding="utf-8").lower()
    except Exception:  # noqa
        return False


def check(folder: Path, plan: dict = None) -> list:
    folder = Path(folder)
    plan = plan or json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    els = [e for e in plan.get("elements") or [] if e]
    st = _style(folder)
    out = []

    # 1. LỆCH PHONG CÁCH — chữ phải theo bộ đã chọn (để trống font/look là phong cách tự áp)
    if st:
        allowed = {str(x).lower() for x in [st.get("font"), st.get("heading"), (st.get("text") or {}).get("font"),
                                             (st.get("captions") or {}).get("font"), *(st.get("fonts") or [])] if x}
        st_look = (st.get("text") or {}).get("look") or "clean"
        st_plate = st_look in PLATE or bool(set(st.get("looks") or []) & PLATE)
        bad_font, bad_look = {}, []
        for i, e in enumerate(els):
            if e.get("type") != "text":
                continue
            f = e.get("font")
            if f and allowed and f.lower() not in allowed:
                bad_font.setdefault(f, []).append(f"{e.get('start', 0):.1f}s")
            lk = e.get("look")
            if lk and lk in PLATE and not st_plate and lk not in (st.get("looks") or []):
                bad_look.append(f"#{i} {e.get('start', 0):.1f}s ({lk})")
        for f, ts in bad_font.items():
            out.append(f"LỆCH PHONG CÁCH: font “{f}” ở {', '.join(ts[:5])}{' …' if len(ts) > 5 else ''} không thuộc bộ "
                       f"({', '.join(sorted(allowed))}) — bỏ trường font để phong cách tự áp, hoặc dùng font của bộ")
        if bad_look:
            out.append(f"LỆCH PHONG CÁCH: chữ đặt trong hộp ({', '.join(bad_look[:4])}{' …' if len(bad_look) > 4 else ''}) trong khi bộ dùng "
                       f"chữ trơn “{st_look}” — bỏ trường look; nền sáng thì dùng lớp che sáng (assets-chung/lop/che-sang.png) hoặc dời chữ")

    # 2. ẢNH MINH HOẠ — phủ kín, có chuyển động, đủ nét, không lặp sát
    brolls = [e for e in els if e.get("type") == "broll" and e.get("src") and "assets/lop/" not in e["src"]]
    seen = {}
    for e in sorted(brolls, key=lambda x: x.get("start", 0)):
        src, a, b = e["src"], e.get("start", 0), e.get("end", 0)
        tag = f"ảnh {Path(src).name} {a:.1f}–{b:.1f}s"
        full = (e.get("area") or (st.get("broll") or {}).get("area") or "full") == "full"
        if IMG.search(src):
            if e.get("fit") in ("contain", "blur") and full:
                out.append(f"{tag}: ảnh không phủ kín (fit {e['fit']}) — dùng fit cover + panFrom/panTo (chuẩn mục 3)")
            moving = (e.get("panFrom") is not None and e.get("panTo") is not None) or (e.get("panYFrom") is not None and e.get("panYTo") is not None)
            kb_off = e.get("kb") is False or (st.get("broll") or {}).get("kenburns") is False
            if b - a > 6.05:
                out.append(f"{tag}: một ảnh tĩnh {b - a:.1f}s (> 6s) — chia thành 2–3 ảnh hoặc vùng lia khác nhau")
            if kb_off and not moving:
                out.append(f"{tag}: ảnh đứng yên (tắt Ken Burns, không lia) — thêm panFrom/panTo")
            sz = _img_size(folder / src)
            if sz and full:
                w, h = sz
                if h < 1080:
                    out.append(f"{tag}: ảnh gốc chỉ {w}×{h} — phủ kín khung dọc sẽ mờ; tìm bản lớn hơn (cao ≥ 1300px) hoặc dùng video stock")
                if abs(w / h - 1080 / 1920) < 0.01 and src.startswith(("assets/canh-quan", "assets/_khung", "assets/frames")):
                    out.append(f"{tag}: ảnh đã bị dựng sẵn thành khung dọc bằng script riêng — dùng ảnh gốc, để tool phủ kín + lia")
        if src in seen and a - seen[src] < 20 and not e.get("cropS"):
            out.append(f"{tag}: lặp lại ảnh đã dùng ở {seen[src]:.1f}s (cách < 20s) — đổi ảnh hoặc thêm cropS + lia vùng khác")
        seen.setdefault(src, a)

    # 3. CHỮ GHI NGUỒN GIỮA MÀN HÌNH
    for e in els:
        if e.get("type") == "text" and CREDIT.search(str(e.get("text", ""))):
            out.append(f"{e.get('start', 0):.1f}s: khối chữ “{str(e['text'])[:40]}” là dòng ghi nguồn — xoá; ảnh CC để tool tự chèn ở góc "
                       f"(_nguon.json), ảnh dự án ghi link trong bao-cao.md")

    # 4. NHẠC NỀN
    has_music = bool(plan.get("music")) or any(e.get("type") == "audio" and (e.get("bgm") or "nhac" in str(e.get("src", ""))) for e in els)
    mode = ""
    try:
        mode = json.loads((folder / "nhac.json").read_text(encoding="utf-8")).get("mode", "")
    except Exception:  # noqa
        pass
    if not has_music and mode != "khong" and not plan.get("dungNhip"):
        out.append("chưa có nhạc nền — thêm theo phong cách (chuẩn mục 5); người dùng không muốn nhạc thì nhac.json {\"mode\": \"khong\"}")

    # 5. BRIEF CẦN ẢNH DỰ ÁN MÀ TOÀN STOCK CHUNG CHUNG
    brief = ""
    for n in ("brief.txt", "brief.md"):
        if (folder / n).exists():
            brief = (folder / n).read_text(encoding="utf-8", errors="ignore")
    if brief and NEED_REAL.search(brief) and brolls:
        gen = [e for e in brolls if _is_stock_generic(folder, e["src"])]
        if len(gen) >= max(2, 0.6 * len(brolls)):
            out.append(f"brief cần ẢNH THẬT của dự án nhưng {len(gen)}/{len(brolls)} ảnh trám là stock Pixabay chung chung — tìm ảnh "
                       f"phối cảnh / tiện ích của dự án trên web và tải bằng stock.py url (chuẩn mục 2)")

    # 6. FONT TIẾNG VIỆT — mở file font kiểm từng ký tự (kiem_font.py)
    try:
        import kiem_font
        out += kiem_font.check(folder, plan)
    except Exception as ex:  # noqa
        out.append(f"không kiểm được font ({ex})")

    # 7. CẢNH AI — luật viết cảnh + chạy thử trong Chrome bắt chữ mất dấu (canh_ai.py, canh-ai/HUONG-DAN.md)
    for e in els:
        if e.get("type") == "canhAI" and not e.get("hidden"):
            if not e.get("canh"):
                out.append(f"khối canhAI {e.get('start', 0):.1f}s thiếu trường canh (thư mục cảnh, vd canh/gia-ban)")
                continue
            try:
                import canh_ai
                out += [x for x in canh_ai.check_scene(folder, e["canh"], e) if "(nhắc)" not in x]
            except Exception as ex:  # noqa
                out.append(f"không soát được cảnh AI {e['canh']} ({ex})")

    # 8. SCRIPT TỰ VIẾT ĐỂ DỰNG HÌNH
    work = folder / "_work"
    if work.exists():
        for py in sorted(work.glob("*.py")):
            try:
                s = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa
                continue
            if re.search(r"(filter_complex|concat=|Image\.new|\.paste\(|overlay=|elements\s*=|plan\.json)", s):
                out.append(f"_work/{py.name}: script tự viết có ghép / dựng hình / sinh plan — chuẩn mục 1 cấm; làm lại bằng công cụ của tool")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = check(Path(sys.argv[1]).resolve())
    print("== Cổng chất lượng ==")
    print("\n".join("- " + x for x in r) or "- đạt")
