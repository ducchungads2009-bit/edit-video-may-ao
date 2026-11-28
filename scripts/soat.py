"""Soát nhanh plan.json bằng chữ (không dựng hình, chạy < 1 giây) — thay cho chụp khung kiểm tra.
Liệt kê lỗi dễ sót khi xem video: thiếu file, khối nằm ngoài video, quá nhiều chữ cùng lúc, chữ đè vùng phụ đề,
chữ hiện đúng điểm nối, khoảng trống dài không có minh họa; in toàn bộ chữ trên màn hình để soát chính tả / số liệu.
  python scripts/soat.py "<folder>"
"""
import json
import sys
from pathlib import Path

TEXTY = {"text", "chip", "priceHook", "bigQuestion", "checklist", "rangeCard", "cta", "phrase", "counter", "stamp", "tabs", "tiles", "note", "bubble", "chart", "text3d", "text3dPro", "scene"}


def words_of(e):
    t = e.get("type")
    if t == "checklist":
        return [e.get("title", "")] + [it.get("text", "") for it in e.get("items") or []]
    if t == "priceHook":
        return [e.get("price", ""), e.get("sub", "")]
    if t == "rangeCard":
        return [e.get("label", ""), e.get("value", ""), e.get("note", "")]
    if t == "phrase":
        return [e.get("sm", ""), str(e.get("big", "")).replace("**", "").replace("__", ""), e.get("tag", "")]
    if t == "counter":
        return [e.get("label", ""), f"{e.get('prefix', '')}{e.get('to', '')} {e.get('suffix', '')}".strip(), e.get("note", "")]
    if t == "chart":
        return [e.get("title", ""), str(e.get("data", "")) if not isinstance(e.get("data"), list) else ", ".join(f"{x.get('label')}: {x.get('value')}" for x in e["data"]), e.get("source", "")]
    if t in ("tabs", "tiles", "note"):
        its = [it if isinstance(it, str) else it.get("text", "") for it in e.get("items") or []]
        nts = [it.get("note", "") for it in e.get("items") or [] if isinstance(it, dict)]
        return [e.get("title", "")] + its + nts
    if t == "scene":
        rows = e.get("rows") or e.get("items") or []
        if isinstance(rows, str):
            rows = [r for r in rows.replace("\n", "|").split("|")]
        rs = [r if isinstance(r, str) else " ".join(str(r.get(k, "")) for k in ("label", "text", "value", "dist", "a", "b", "note") if r.get(k)) for r in rows]
        ab = []
        for k in ("a", "b"):
            if isinstance(e.get(k), dict):
                ab += [e[k].get("name", ""), e[k].get("value", "")] + [str(x if isinstance(x, str) else x.get("text", "")) for x in e[k].get("items") or []]
        return [e.get("kicker", ""), e.get("title", ""), e.get("sub", ""), e.get("handle", "")] + rs + ab
    if t == "shape":
        return [e.get("text", "")]
    return [e.get("text") or e.get("label") or ""]


def main(folder: Path):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    info = {}
    for p in (folder / "_work" / "info.json", folder / "info.json"):
        if p.exists():
            info = json.loads(p.read_text(encoding="utf-8"))
            break
    try:  # khung hình (khung.json): chiều cao lớp đồ hoạ 1920 / 1350 / 1080 / 608
        import khung
        FH = khung.height(khung.get(folder))
    except Exception:
        FH = 1920
    segs = [s for s in plan.get("segments") or [] if s[1] - s[0] > 0.05]
    total = sum(b - a for a, b in segs) if segs else float(info.get("durationSec") or 0) or None
    joins, acc = [], 0.0
    for a, b in segs[:-1]:
        acc += b - a
        joins.append(acc)
    els = [e for e in plan.get("elements") or [] if e]
    loi, chu = [], []
    for i, e in enumerate(els):
        tag = f"#{i} {e.get('type')} {e.get('start', 0):.1f}–{e.get('end', 0):.1f}s"
        if e.get("end", 0) <= e.get("start", 0):
            loi.append(f"{tag}: kết thúc ≤ bắt đầu")
        if total and e.get("end", 0) > total + 0.05 and not plan.get("tail"):
            loi.append(f"{tag}: kéo quá cuối video ({total:.1f}s) — video sẽ tự dài thêm {e.get('end', 0) - total:.1f}s, ĐỨNG HÌNH khung cuối. Cố ý (voice dài hơn) thì bỏ qua; không thì dời/cắt khối")
        src = e.get("src")
        if src and not (folder / src).exists():
            loi.append(f"{tag}: thiếu file {src}")
        if isinstance(e.get("y"), (int, float)) and e.get("type") != "zoom" and e["y"] > 1 and e["y"] > FH - 40:
            loi.append(f"{tag}: y={e['y']} nằm ngoài khung (khung cao {FH}px)")
        if e.get("type") in TEXTY or e.get("type") == "sticker":
            for j in joins:
                if abs(e.get("start", 0) - j) < 0.2:
                    loi.append(f"{tag}: hiện đúng điểm nối {j:.1f}s (dời ra ≥ 0,2s)")
        cap_top = plan.get("captionTop", round(1390 * FH / 1920))
        if plan.get("captions") and e.get("type") == "text" and e.get("y") is not None and abs(e["y"] + (e.get("dy") or 0) - cap_top) < 140:
            loi.append(f"{tag}: chữ nằm sát vùng phụ đề (y≈{e['y']}, phụ đề {cap_top})")
        if e.get("type") in TEXTY:
            for w in words_of(e):
                if w and w.strip():
                    chu.append(f"{e.get('start', 0):6.1f}s  {w.strip()}")
        if e.get("type") == "canhAI" and isinstance(e.get("data"), dict):  # chữ đưa vào cảnh AI
            for k, v in e["data"].items():
                if isinstance(v, str) and v.strip() and k not in ("che", "giaoDien", "mau", "nen", "font") and not v.startswith("#"):
                    chu.append(f"{e.get('start', 0):6.1f}s  [cảnh AI {k}] {v.strip()}")
    # nhiều chữ cùng lúc
    pts = sorted({round(e.get("start", 0), 2) for e in els})
    for t in pts:
        n = [e for e in els if e.get("type") in TEXTY | {"sticker"} and e.get("start", 0) <= t + 0.01 < e.get("end", 0)]
        if len(n) > 3:
            loi.append(f"{t:.1f}s: {len(n)} khối chữ cùng lúc (nên ≤ 3)")
    # người nói thu nhỏ (presenter): khối không được bật ra lúc đang thu (che mặt / trễ nhịp), nền không được trống
    for q in [e for e in els if e.get("type") == "presenter" and (e.get("mode") or "card") != "full"]:
        tag = f"người nói {q.get('mode', 'card')} {q['start']:.1f}–{q['end']:.1f}s"
        ind = q.get("inDur", 0.4)
        inside = [e for e in els if e.get("type") in TEXTY | {"sticker", "spark", "pip", "map"} and e.get("start", 0) < q["end"] and e.get("end", 0) > q["start"]]
        for e in inside:
            if q["start"] - 0.05 < e.get("start", 0) < q["start"] + ind - 0.02:
                loi.append(f"{tag}: khối {e.get('type')} hiện lúc người nói còn đang thu nhỏ ({e['start']:.2f}s) — dời ≥ {q['start'] + ind:.2f}s")
        t, step = q["start"] + ind, 0.25
        empty = 0.0
        while t < q["end"]:
            if not any(e.get("start", 0) <= t < e.get("end", 0) for e in inside):
                empty += step
                if empty >= 1.5:
                    loi.append(f"{tag}: nền trống ~{empty:.1f}s quanh {t:.1f}s (lúc người nói thu nhỏ nên luôn có đồ họa)")
                    break
            else:
                empty = 0.0
            t += step
    # nhãn: in hoa, ngắn
    for i, e in enumerate(els):
        lab = e.get("tag") if e.get("type") == "phrase" else None
        if lab and len(lab.split()) > 4:
            loi.append(f"#{i} phrase {e.get('start', 0):.1f}s: hộp chữ '{lab}' dài {len(lab.split())} từ — nên 1–3 từ, rút từ khóa thay vì chép nguyên câu")
    # khoảng trống minh họa
    if total:
        vis = sorted((e["start"], e["end"]) for e in els if e.get("type") not in ("audio", "dayBadge", "zoom"))
        cur = 0.0
        for a, b in vis:
            if a - cur > 10:
                loi.append(f"{cur:.1f}–{a:.1f}s: {a - cur:.0f}s không có minh họa/đồ họa")
            cur = max(cur, b)
        if total - cur > 10:
            loi.append(f"{cur:.1f}–{total:.1f}s: {total - cur:.0f}s cuối không có minh họa/đồ họa")
        if not any(e.get("start", 99) < 3 for e in els if e.get("type") in TEXTY):
            loi.append("3 giây đầu chưa có chữ hook")
    try:  # mật độ tiếng hiệu ứng (người xem dễ thấy "lạm dụng")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import sfx as sfxmod
        ev = sfxmod.events(plan)
        dur_ = total or max([e.get("end", 0) for e in els] or [60])
        gap, per = sfxmod.BUDGET["vua"]
        if len(ev) > dur_ / per + 1:
            loi.append(f"{len(ev)} tiếng hiệu ứng trong {dur_:.0f}s (~1 tiếng / {dur_ / max(1, len(ev)):.1f}s) — dày quá, nên ≤ {int(dur_ / per + 0.5)}"
                       f"  → python scripts/sfx.py giam \"<folder>\"")
        close = [f"{a[0]:.1f}s/{b[0]:.1f}s" for a, b in zip(ev, ev[1:]) if b[0] - a[0] < 0.8 and a[2] != "item" and b[2] != "item"]
        if close:
            loi.append(f"tiếng hiệu ứng sát nhau (< 0,8s): {', '.join(close[:6])}{' …' if len(close) > 6 else ''}")
        nb = sum(1 for x in ev if x[4] == "bell")
        if nb > 1:
            loi.append(f"chuông 'bell' dùng {nb} lần — chỉ nên 1 lần ở kêu gọi cuối")
    except Exception as e:  # noqa
        loi.append(f"(không kiểm tra được mật độ âm thanh: {e})")
    try:  # chữ đè mặt nhân vật
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from tranh_mat import scan
        _, fm, note = scan(folder)
        loi += [x + "  → sửa: python scripts/tranh_mat.py \"<folder>\" --sua" for x in fm]
    except Exception as e:  # noqa
        loi.append(f"(không kiểm tra được chữ đè mặt: {e})")
    try:  # chữ hoà vào nền (độ tương phản) — đo trên khung video thật đúng lúc, đúng chỗ chữ
        from tuong_phan import check as tp_check
        for x in tp_check(folder):
            loi.append(f"{x['start']:.1f}s chữ “{x['text'][:30]}” {x['lvl'].upper()} — hoà vào nền ({int(x['bad'] * 100)}% vùng chữ gần màu chữ)"
                       "  → sửa: python scripts/tuong_phan.py \"<folder>\" --sua")
    except Exception as e:  # noqa
        loi.append(f"(không kiểm tra được độ tương phản chữ: {e})")
    try:  # cổng chất lượng chung cho mọi AI / mọi phong cách (huong-dan/chat-luong.md)
        from chat_luong import check as cl_check
        loi += ["CHUẨN: " + x for x in cl_check(folder, plan)]
    except Exception as e:  # noqa
        loi.append(f"(không chạy được cổng chất lượng: {e})")
    print("== Lỗi / cần xem ==")
    print("\n".join("- " + x for x in dict.fromkeys(loi)) or "- không thấy lỗi")
    print("\n== Chữ trên màn hình (soát chính tả, dấu, số liệu so với brief) ==")
    print("\n".join(chu) or "(không có)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/soat.py "<folder>"')
    from tiendo import stop_guard
    stop_guard(Path(sys.argv[1]).resolve())
    main(Path(sys.argv[1]).resolve())
