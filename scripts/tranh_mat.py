"""Chữ / đồ họa TRÁNH MẶT nhân vật chính.
Dùng _work/mat.json (scripts/mat.py — prepare tự chạy). Với mỗi khối chữ/đồ họa, lấy vùng mặt trong suốt thời gian khối
hiện (đổi giây video xuất -> giây video gốc theo segments; bỏ qua lúc bị ảnh trám che), ước lượng khung của khối, nếu
đè lên mặt thì dời lên TRÊN CÙNG (dưới lề an toàn) hoặc XUỐNG HẲN dưới mặt (trên vùng phụ đề) — chỗ nào gần & đủ chỗ.

  python scripts/tranh_mat.py "<folder>"          # chỉ báo khối nào đè mặt
  python scripts/tranh_mat.py "<folder>" --sua    # tự dời (lưu plan.json, bản cũ ở _work/plan_truoc_tranh_mat.json)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat import zone, STEP  # noqa: E402

DEFAULT_Y = {"chip": 240, "priceHook": 520, "bigQuestion": 620, "checklist": 240, "rangeCard": 280, "cta": 1120, "pip": 260, "text": 700, "sticker": 600,
             "chart": 300, "phrase": 300, "counter": 420, "stamp": 600, "tabs": 260, "tiles": 300, "note": 260, "bubble": 380, "spark": 300, "text3d": 700, "scene": 300, "card3d": 760}
TEXTY = {"text", "chip", "priceHook", "bigQuestion", "checklist", "rangeCard", "cta", "sticker", "pip",
         "phrase", "counter", "stamp", "tabs", "tiles", "note", "bubble", "chart", "text3d", "scene"}
W, H = 1080, 1920


def pres_target(e, face_cy=None):
    """giống presTarget trong remotion/src/Graphics2.tsx: (s, cx, cy, dy) của video chính khi người nói thu nhỏ"""
    m, s = e.get("mode") or "card", e.get("s")
    x = e.get("x")
    if m == "card":
        return (s or 0.5, x * W if x is not None else W / 2, e.get("y") or 1290, 0)
    if m == "corner":
        s = s or 0.3
        return (s, x * W if x is not None else W - 36 - W * s / 2, e.get("y") or 1290, 0)
    if m == "window":
        return (s or 0.64, x * W if x is not None else W / 2, e.get("y") or 1200, 0)
    if m == "split":
        cut = e.get("cut") or 900
        fy = e.get("focusY") or face_cy or 720
        return (1, W / 2, H / 2, max(0, min(cut, cut + (H - cut) * 0.4 - fy)))
    return None


def pres_map(plan, t, z):
    """vùng mặt z (khung gốc) -> vị trí thật trên màn hình khi đang có khối presenter"""
    for e in plan.get("elements") or []:
        if e and e.get("type") == "presenter" and e["start"] <= t < e["end"]:
            tg = pres_target(e, (z[1] + z[3]) / 2)
            if not tg:
                return z
            s, cx, cy, dy = tg
            f = lambda X, Y: (cx + (X - W / 2) * s, cy + (Y - H / 2) * s + dy)  # noqa: E731
            a, b = f(z[0], z[1]), f(z[2], z[3])
            return [a[0], a[1], b[0], b[1]]
    return z
TOP = 150  # lề trên an toàn (thanh trạng thái / tên kênh TikTok)
GAP = 30


def est_h(e, style):
    """ước lượng chiều cao khối (px trên khung 1080x1920)"""
    t = e.get("type")
    sc = e.get("sc") or 1
    if t == "text":
        size = e.get("size") or (style.get("text") or {}).get("size") or 80
        txt = e.get("text") or ""
        width = e.get("width") or 960
        lines = sum(max(1, int(len(ln) * size * 0.55 / width) + 1) for ln in txt.split("\n"))
        return size * 1.3 * lines * sc + 20
    if t == "sticker":
        return (e.get("size") or 150) * sc
    if t == "text3d":
        return (e.get("size") or 140) * 1.6 * max(1, str(e.get("text") or "").count("\n") + 1) * sc
    if t == "card3d":
        w = e.get("w") or 760
        return (e.get("h") or w * (e.get("ratio") or 1.25)) * sc
    if t == "scene":
        rows = e.get("rows") or e.get("items") or []
        n = len(rows.split("|")) if isinstance(rows, str) else len(rows)
        k = e.get("kind") or "intro"
        if k == "stats":
            return (130 + 280 * max(1, -(-n // (1 if n <= 2 else 2)))) * sc
        if k == "compare":
            m = max(len((e.get("a") or {}).get("items") or []), len((e.get("b") or {}).get("items") or []), n)
            return (240 + 80 * m) * sc
        return (140 + 128 * max(1, n)) * sc
    if t == "checklist":
        return (130 + 95 * len(e.get("items") or [])) * sc
    if t == "note":
        return (120 + 78 * len(e.get("items") or [])) * sc
    if t == "phrase":
        z = e.get("size") or 120
        return (z * 1.25 * max(1, str(e.get("big") or "").count("\n") + 1) + (z * 0.5 if e.get("sm") else 0) + (z * 0.55 if e.get("tag") else 0)) * sc
    if t == "counter":
        z = e.get("size") or 230
        return z * (1.05 + (0.28 if e.get("label") else 0) + (0.22 if e.get("note") else 0)) * sc
    if t == "chart":
        return (e.get("height") or 560) * sc
    if t == "stamp":
        return (e.get("size") or 260) * (1.3 if e.get("text") else 1) * sc
    if t == "tabs":
        return (110 + (90 if e.get("title") else 0) + 70) * sc
    if t == "tiles":
        n = len(e.get("items") or [])
        return 220 * max(1, -(-n // max(1, e.get("cols") or min(3, n or 1)))) * sc
    return {"bubble": 170, "chip": 110, "priceHook": 340, "bigQuestion": 280, "rangeCard": 330, "cta": 130, "pip": 700}.get(t, 150) * sc


def box(e, style):
    y = (e.get("y") if e.get("y") is not None else DEFAULT_Y.get(e.get("type"), 600)) + (e.get("dy") or 0)
    h = est_h(e, style)
    if e.get("type") == "stamp":
        s = (e.get("size") or 260) * (e.get("sc") or 1)
        cx = (e.get("x") if e.get("x") is not None else 0.5) * 1080 + (e.get("dx") or 0)
        return [cx - s / 2, y, cx + s / 2, y + h]
    if e.get("type") == "sticker":  # nhãn dán: x, y là tâm
        s = (e.get("size") or 150) * (e.get("sc") or 1)
        cx = (e.get("x") if e.get("x") is not None else 0.5) * 1080 + (e.get("dx") or 0)
        return [cx - s / 2, y - s / 2, cx + s / 2, y + s / 2]
    if e.get("type") == "card3d":  # x, y là tâm
        w = (e.get("w") or 760) * (e.get("sc") or 1)
        yc = (e.get("y") if e.get("y") is not None else 760) + (e.get("dy") or 0)
        cx = (e.get("x") if e.get("x") is not None else 0.5) * (1080 if (e.get("x") or 0) <= 1 else 1) + (e.get("dx") or 0)
        return [cx - w / 2, yc - h / 2, cx + w / 2, yc + h / 2]
    if e.get("type") == "text" and e.get("x") is not None:
        w = (e.get("width") or 960) * (e.get("sc") or 1)
        cx = e["x"] * 1080 + (e.get("dx") or 0)
        return [cx - w / 2, y, cx + w / 2, y + h]
    dx = e.get("dx") or 0
    return [60 + dx, y, 1020 + dx, y + h]


def out2src(segs, t):
    acc = 0.0
    for a, b in segs:
        if t < acc + (b - a):
            return a + (t - acc)
        acc += b - a
    return segs[-1][1] if segs else t


def face_zone(plan, faces, step, s, e, covers):
    """hợp các vùng mặt trong [s, e) của video xuất, bỏ lúc ảnh trám che; None nếu không thấy mặt"""
    segs = [x for x in plan.get("segments") or [] if x[1] - x[0] > 0.05]
    zs, t = [], s
    while t < e:
        if not any(a <= t < b for a, b in covers):
            src = out2src(segs, t) if segs else t
            i = min(len(faces) - 1, max(0, round(src / step)))
            if len(faces[i]) == 5:
                zs.append(pres_map(plan, t, zone(faces[i])))
        t += step / 2
    if not zs:
        return None
    return [min(z[0] for z in zs), min(z[1] for z in zs), max(z[2] for z in zs), max(z[3] for z in zs)]


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def scan(folder: Path, fix=False):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    mp = folder / "_work" / "mat.json"
    try:
        import khung
        if khung.get(folder) != "9:16":  # vùng mặt đo theo khung dọc — khung khác tạm chưa dò
            return plan, [], f"khung {khung.get(folder)}: chưa dò tránh mặt tự động — tự xem vị trí chữ so với mặt (check.jpg)"
    except Exception:
        pass
    if not mp.exists():
        return plan, [], "chưa có _work/mat.json (chạy: python scripts/mat.py \"<folder>\")"
    m = json.loads(mp.read_text(encoding="utf-8"))
    faces, step = m.get("faces") or [], m.get("step", STEP)
    if not faces:
        return plan, [], "không thấy mặt người"
    style = plan.get("style") or {}
    cap = plan.get("captionTop", 1390) if plan.get("captions") else 1760
    els = plan.get("elements") or []
    # chỉ cảnh trám CẢ KHUNG mới che mặt; trám nửa trên/dưới thì người nói vẫn thấy
    _ba = (style.get("broll") or {}).get("area") or "full"
    covers = [(e["start"], e["end"]) for e in els if e and e.get("type") == "broll" and (e.get("area") or _ba) == "full"]
    moved = set()
    out, placed = [], []  # placed: (start, end, box) các khối đã dời, để không chồng lên nhau
    for i, e in enumerate(els):
        if not e or e.get("type") not in TEXTY or e.get("behind") or (isinstance(e.get("z"), (int, float)) and e["z"] < 0):
            continue
        if e.get("type") == "scene" and ((e.get("kind") or "intro") in ("intro", "outro") or e.get("bg") in ("dark", "brand")):
            continue  # cảnh mở/kết phủ cả khung — cố ý che
        z = face_zone(plan, faces, step, e["start"], e["end"], covers)
        b = box(e, style)
        if not z or not hit(b, z):
            continue
        h = b[3] - b[1]
        msg = f"#{i} {e['type']} {e['start']:.1f}–{e['end']:.1f}s đè lên mặt (khối y≈{int(b[1])}–{int(b[3])}, mặt y≈{int(z[1])}–{int(z[3])})"
        if not fix:
            out.append(msg)
            continue
        cands = []
        # vật cản: khối khác hiện cùng lúc (đã dời / không đè mặt) + nhãn ngày
        obs = [bb for (s2, e2, bb) in placed if s2 < e["end"] and e["start"] < e2]
        for j, o in enumerate(els):
            if j == i or not o or o.get("type") in ("audio", "zoom", "sfx", "broll") or not (o["start"] < e["end"] and e["start"] < o["end"]):
                continue
            if o.get("type") == "dayBadge":
                obs.append([40, 120, 1040, 290])
            elif o.get("type") in TEXTY and j not in moved:
                ob = box(o, style)
                if not hit(ob, z):
                    obs.append(ob)

        def slide(y):  # đẩy xuống dưới các vật cản chồng lên [y, y+h]
            for _ in range(20):
                c = [o for o in obs if o[1] < y + h and y < o[3] and o[0] < b[2] and b[0] < o[2]]
                if not c:
                    return y
                y = max(o[3] for o in c) + 20
            return y
        top = slide(TOP)
        if top + h <= z[1] - GAP:
            cands.append(top)
        low = slide(z[3] + GAP)
        if low + h <= cap - 20:
            cands.append(low)
        if not cands:  # không đủ chỗ: thu nhỏ khối cho vừa phía trên / dưới mặt (tối thiểu 60%), không thì chỗ ít đè nhất
            room_top, room_low = z[1] - GAP - top, cap - 20 - low
            k = max(room_top, room_low) / h
            if k >= (0.5 if e.get("type") == "pip" else 0.6) and e.get("type") != "sticker":
                ny = top if room_top >= room_low else low
                e["sc"] = round((e.get("sc") or 1) * k, 2)
                e["org"] = [540, int(round(ny))]  # phóng quanh mép trên-giữa: mép trên giữ nguyên
                e["y"] = int(round(ny))
                e.pop("dy", None)
                placed.append((e["start"], e["end"], [b[0], ny, b[2], ny + h * k]))
                moved.add(i)
                out.append(msg + f" → thu nhỏ {int(k * 100)}% và dời tới y={e['y']}")
                continue
            cands = [top if (z[1] - top) >= (cap - low) else max(low, cap - 20 - h)]
        y0 = b[1]
        ny = min(cands, key=lambda c: abs(c - y0))
        if e.get("type") == "sticker":
            ny += h / 2
        e["y"] = int(round(ny))
        e.pop("dy", None)
        placed.append((e["start"], e["end"], box(e, style)))
        moved.add(i)
        out.append(msg + f" → dời tới y={e['y']}")
    if fix and out:
        work = folder / "_work"
        (work / "plan_truoc_tranh_mat.json").write_text((folder / "plan.json").read_text(encoding="utf-8"), encoding="utf-8")
        (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return plan, out, ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    _, res, note = scan(Path(sys.argv[1]).resolve(), "--sua" in sys.argv)
    if note:
        print("Bỏ qua tránh mặt:", note)
    print("\n".join(res) or "Không có khối nào đè lên mặt.")
