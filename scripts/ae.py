"""Hiệu ứng kiểu After Effects — tự đặt & bắt nhịp.

  python scripts/ae.py tu-gan "<folder>" [--it|--nhieu] [--ghi-de]
      Tự đặt lớp hiệu ứng phủ (overlay) vào chỗ hợp: light leak ở hook 3s đầu, film burn / light leak ở điểm nối khác cảnh,
      lấp lánh / pháo giấy ở kêu gọi cuối, lens flare ở con số lớn. Theo style.effects.overlay của phong cách
      ("không" = tắt; danh sách kiểu ưa dùng, vd ["bokeh", "particles"]). Khối tự đặt có "auto": "ae" — chạy lại sẽ thay.
      --ghi-de: xoá cả overlay người dùng tự thêm trước khi đặt lại (mặc định giữ).
  python scripts/ae.py bat-nhip "<folder>" [--sai 0.15]
      Dời điểm bắt đầu các khối hình (zoom, overlay, shape, fx, chữ, nhãn dán, 3D, cảnh) tới NHỊP NHẠC gần nhất (lệch ≤ --sai giây,
      giữ nguyên độ dài). Nhịp lấy từ plan.beats, chưa có thì dò từ plan.music (scripts/nhip.py) và lưu vào plan.beats.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SNAP_TYPES = {"zoom", "overlay", "shape", "fx", "text", "sticker", "text3d", "text3dPro", "object3d", "card3d", "scene", "phrase", "counter", "stamp", "chip", "bigQuestion"}


def _joins(plan):
    segs = [s for s in plan.get("segments") or [] if s[1] - s[0] > 0.05]
    out, acc = [], 0.0
    for i, (a, b) in enumerate(segs[:-1]):
        acc += b - a
        nxt = segs[i + 1][0]
        out.append((acc, abs(nxt - b) > 1.0))  # (giây xuất, khác cảnh/nhảy xa)
    return out


def _dur(plan, folder):
    segs = [s for s in plan.get("segments") or [] if s[1] - s[0] > 0.05]
    if segs:
        return sum(b - a for a, b in segs)
    try:
        return float(json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8")).get("durationSec") or 0)
    except Exception:  # noqa: BLE001
        return max([e.get("end", 0) for e in plan.get("elements") or [] if e] + [0])


def style_of(folder: Path, plan: dict) -> dict:
    try:
        from phongcach import apply as apply_style
        return apply_style(folder, json.loads(json.dumps(plan))).get("style") or {}
    except Exception:  # noqa: BLE001
        return plan.get("style") or {}


def tu_gan(folder: Path, dens="vua", overwrite=False):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    plan, msg = tu_gan_plan(plan, style_of(folder, plan), _dur(plan, folder), dens, overwrite)
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(msg)


def tu_gan_plan(plan: dict, st: dict, total: float, dens="vua", overwrite=False):
    """-> (plan, câu báo)"""
    eff = st.get("effects") or {}
    pref = eff.get("overlay")
    els = [e for e in plan.get("elements") or [] if e]
    els = [e for e in els if not (e.get("type") == "overlay" and (e.get("auto") == "ae" or overwrite))]
    if pref in ("không", "khong", "none", False, 0):
        plan["elements"] = els
        return plan, "Phong cách không dùng lớp hiệu ứng phủ — đã bỏ các overlay tự đặt."
    kinds = pref if isinstance(pref, list) and pref else None
    if isinstance(pref, str) and pref in ("ít", "it"):
        dens = "it"
    elif isinstance(pref, str) and pref in ("nhiều", "nhieu"):
        dens = "nhieu"
    chill = (eff.get("zoomEase") == "smooth") or (st.get("backdrop") or {}).get("type") == "ink"
    news = st.get("skin") in ("news", "info")
    has = lambda a, b: any(e.get("type") == "overlay" and e["start"] < b and e["end"] > a for e in els)  # noqa: E731
    add = []

    def put(kind, a, b, **kw):
        a, b = max(0.0, a), min(total or b, b)
        if b - a < 0.4 or has(a, b) or any(x["start"] < b and x["end"] > a for x in add):
            return
        add.append({"type": "overlay", "kind": kind, "start": round(a, 2), "end": round(b, 2), "auto": "ae", **kw})

    pick = lambda opts: next((k for k in (kinds or []) if k in opts), opts[0])  # noqa: E731
    # 1) hook
    if not news:
        put(pick(["bokeh", "particles"] if chill else ["lightleak", "flare", "rays"]), 0, 2.6 if dens != "nhieu" else 3.2, amount=55 if chill else 70)
    # 2) điểm nối khác cảnh
    lim = {"it": 1, "vua": 3, "nhieu": 99}[dens]
    gap = {"it": 20, "vua": 9, "nhieu": 5}[dens]
    last = -99
    n = 0
    for t, far in _joins(plan):
        if n >= lim or not (far or dens == "nhieu") or t - last < gap or t < 4 or (total and t > total - 2):
            continue
        if chill:
            put(pick(["lightleak", "bokeh"]), t - 0.5, t + 0.9, amount=45)
        elif not news:
            put(pick(["filmburn", "lightleak"]), t - 0.45, t + 0.65, amount=80)
        last, n = t, n + 1
    # 3) con số lớn
    if dens != "it" and not news:
        for e in els:
            if e.get("type") in ("priceHook", "text3d", "counter") or (e.get("type") == "scene" and e.get("kind") in ("pricetable", "stats")):
                put("flare", e["start"], min(e["end"], e["start"] + 2.5), amount=60)
                break
    # 4) kêu gọi cuối
    cta = [e for e in els if e.get("type") == "cta" or (e.get("type") == "scene" and e.get("kind") == "outro")]
    if cta:
        c = cta[-1]
        txt = " ".join(str(c.get(k, "")) for k in ("text", "title", "sub")).lower()
        kind = "confetti" if re.search(r"chúc mừng|quà|tặng|ưu đãi|khuyến mãi|giveaway|trúng", txt) else pick(["sparkle", "particles"])
        put(kind, c["start"], min(c["end"], c["start"] + 3.5), amount=70)
    plan["elements"] = els + add
    return plan, f"Đã đặt {len(add)} lớp hiệu ứng phủ" + (": " + ", ".join(f"{x['kind']} {x['start']:.1f}s" for x in add) if add else "")


def bat_nhip(folder: Path, tol=0.15):
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    beats = plan.get("beats") or []
    if not beats:
        m = plan.get("music") or {}
        src = m.get("src")
        if not src or not (folder / src).is_file():
            print("Không có nhạc nền (plan.music) và chưa có plan.beats — bỏ qua bắt nhịp.")
            return 0
        import nhip
        tempo, beats = nhip.beats_on_video(str(folder / src), float(m.get("from") or 0), _dur(plan, folder) + 1)
        plan["beats"] = beats
        print(f"Nhịp nhạc: {tempo} BPM, {len(beats)} nhịp")
    moved = snap_plan(plan, beats, tol)
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Bắt nhịp: dời {moved} khối về nhịp nhạc (lệch ≤ {tol}s).")
    return moved


def snap_plan(plan: dict, beats: list, tol=0.15) -> int:
    import bisect
    moved = 0
    for e in plan.get("elements") or []:
        if not e or e.get("type") not in SNAP_TYPES or e.get("locked"):
            continue
        s = float(e["start"])
        i = bisect.bisect_left(beats, s)
        cand = [beats[j] for j in (i - 1, i) if 0 <= j < len(beats)]
        if not cand:
            continue
        b = min(cand, key=lambda x: abs(x - s))
        d = b - s
        if 0.005 < abs(d) <= tol:
            e["start"] = round(b, 3)
            e["end"] = round(float(e["end"]) + d, 3)
            if e.get("type") == "checklist":
                for it in e.get("items") or []:
                    it["at"] = round(it["at"] + d, 3)
            moved += 1
    return moved


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    f = Path(a[1]).resolve()
    try:
        from tiendo import stop_guard
        stop_guard(f)
    except ImportError:
        pass
    if a[0] == "tu-gan":
        tu_gan(f, "it" if "--it" in a else "nhieu" if "--nhieu" in a else "vua", "--ghi-de" in a)
    elif a[0] == "bat-nhip":
        bat_nhip(f, float(a[a.index("--sai") + 1]) if "--sai" in a else 0.15)
    else:
        sys.exit(__doc__)
