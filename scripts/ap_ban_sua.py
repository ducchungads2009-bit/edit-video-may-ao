"""Áp phần người dùng sửa trên TRANG CHỈNH SỬA vào plan.json (bản máy ảo).

    python3 scripts/ap_ban_sua.py "cho-edit/<du-an>" ban-sua.json

ban-sua.json = dữ liệu tài liệu db "ban-sua/hien-tai" của trang (Claude đọc bằng db_get rồi ghi ra file).
Làm: đổi cảnh (bỏ / thứ tự / thu – nới), dời mọi khối theo cảnh mới, sửa chữ / xoá / thêm, sửa phụ đề (thành fixes),
đổi nhạc, đổi phong cách. In "GHI CHÚ:" để Claude tự xử lý phần còn lại. Bản plan cũ cất ở _work/plan-truoc-sua-<n>.json.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def to_src(segs, t):
    acc = 0.0
    for a, b in segs:
        if t <= acc + (b - a) + 1e-6:
            return a + (t - acc)
        acc += b - a
    return segs[-1][1] if segs else t


def to_out(segs, t):
    acc = 0.0
    for a, b in segs:
        if a - 1e-3 <= t <= b + 1e-3:
            return acc + (t - a)
        acc += b - a
    return None


def remap(segs_old, segs_new, t, snap=False):
    """mốc video xuất cũ -> mới (qua giây video chính); rơi vào đoạn bị bỏ -> None (snap: dời tới đầu đoạn kế)"""
    s = to_src(segs_old, t)
    o = to_out(segs_new, s)
    if o is None and snap:
        acc, best = 0.0, None
        for a, b in segs_new:
            if a >= s and best is None:
                best = acc
            acc += b - a
        o = best
    return None if o is None else round(o, 2)


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    proj = (ROOT / sys.argv[1]).resolve()
    sua = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if "data" in sua and isinstance(sua["data"], dict) and "canh" in sua["data"]:
        sua = sua["data"]
    goc = json.loads((proj / "_work/trang-sua-goc.json").read_text(encoding="utf-8"))
    if sua.get("phienBan") != goc["phien"]:
        print(f"⚠️ Bản sửa thuộc bản dựng số {sua.get('phienBan')}, trang hiện là số {goc['phien']} — vẫn áp, kiểm tra kỹ.")
    plan = json.loads((proj / "plan.json").read_text(encoding="utf-8"))
    shutil.copy(proj / "plan.json", proj / f"_work/plan-truoc-sua-{goc['phien']}.json")
    log = []
    segs_old = goc["segments"]

    # 1) cảnh
    canh = sua.get("canh") or []
    segs_new = [[round(float(c["a"]), 2), round(float(c["b"]), 2)] for c in canh if float(c["b"]) - float(c["a"]) >= 0.3]
    if not segs_new:
        segs_new = segs_old
    changed_segs = segs_new != segs_old
    if changed_segs:
        bo = sua.get("canhBo") or []
        order = [c.get("goc") for c in canh]
        log.append(f"cảnh: {len(segs_old)} → {len(segs_new)}" + (f" (bỏ cảnh {', '.join(map(str, bo))})" if bo else "")
                   + (" · đổi thứ tự" if order != sorted(order) else "") + " · thu/nới mép nếu có")

    # 2) khối chữ / đồ hoạ: lấy danh sách trang trả về (đã gồm sửa / xoá / thêm), các khối không sửa được trên trang giữ nguyên
    els_old = plan.get("elements") or []
    chu = sua.get("chu")
    if isinstance(chu, list):
        els, nsua, nxoa, nmoi = [], 0, 0, 0
        for e in chu:
            g, xoa, moi = e.pop("goc", None), e.pop("xoa", False), e.pop("moi", False)
            if xoa:
                nxoa += 1; continue
            if moi:
                nmoi += 1
            elif g is not None and g < len(els_old) and e != els_old[g]:
                nsua += 1
            els.append(e)
        if nsua or nxoa or nmoi:
            log.append(f"chữ: sửa {nsua}, xoá {nxoa}, thêm {nmoi}")
    else:
        els = list(els_old)

    # 3) dời mốc theo cảnh mới
    if changed_segs:
        total = sum(b - a for a, b in segs_new)
        kept = []
        for e in els:
            if e.get("type") == "dayBadge" or (e.get("start", 0) <= 0.05 and e.get("end", 0) >= sum(b - a for a, b in segs_old) - 0.3):
                kept.append({**e, "start": 0, "end": round(total, 2)}); continue  # khối suốt video
            s = remap(segs_old, segs_new, e["start"], snap=True)
            en = remap(segs_old, segs_new, e["end"])
            if s is None:
                continue
            if en is None or en <= s:
                en = min(total, s + max(1.5, e["end"] - e["start"]))
            ne = {**e, "start": s, "end": round(min(total, en), 2)}
            if isinstance(e.get("items"), list):
                ne["items"] = [{**it, "at": remap(segs_old, segs_new, it["at"], snap=True) or s} if isinstance(it, dict) and "at" in it else it for it in e["items"]]
            kept.append(ne)
        dropped = len(els) - len(kept)
        if dropped:
            log.append(f"bỏ {dropped} khối nằm trong cảnh đã bỏ")
        els = kept
    plan["segments"] = segs_new
    plan["elements"] = els

    # 4) phụ đề -> fixes
    pd = [x for x in (sua.get("phuDe") or []) if x.get("moi", "").strip() and x.get("moi") != x.get("cu")]
    if pd:
        # sửa cả câu: đặt TRƯỚC các fixes cũ (áp lên đúng câu máy nghe, chưa bị fixes khác đổi)
        plan["fixes"] = [[(x.get("goc") or x["cu"]).upper(), x["moi"].strip().upper()] for x in pd] + (plan.get("fixes") or [])
        log.append(f"phụ đề: sửa {len(pd)} câu")

    # 5) nhạc
    if "nhac" in sua:
        bgm_free = [e for e in plan["elements"] if not (e.get("type") == "audio" and e.get("bgm") and not e.get("voice"))]
        if sua["nhac"] is None:
            if plan.get("music") or len(bgm_free) != len(plan["elements"]):
                plan.pop("music", None); plan["elements"] = bgm_free; log.append("nhạc: tắt")
        else:
            f = Path(sua["nhac"]).name
            cur = Path((plan.get("music") or {}).get("src", "")).name
            vol = float(sua.get("amLuongNhac") or 0.5)
            if f != cur or abs(vol - float((plan.get("music") or {}).get("volume", -1))) > 0.01:
                src = ROOT / "assets-chung/nhac" / f
                if src.exists():
                    (proj / "assets/nhac").mkdir(parents=True, exist_ok=True)
                    shutil.copy(src, proj / "assets/nhac" / f)
                    plan["music"] = {"src": f"assets/nhac/{f}", "volume": vol}
                    plan["elements"] = bgm_free
                    log.append(f"nhạc: {f} · {round(vol * 100)}%")
                else:
                    log.append(f"⚠️ không thấy file nhạc {f}")

    (proj / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    # 6) phong cách
    pc = (sua.get("phongCach") or "").strip()
    if pc:
        cur = ""
        pf = proj / "phong-cach-tron.json"
        if pf.exists():
            vals = [v for v in json.loads(pf.read_text(encoding="utf-8")).values() if isinstance(v, str)]
            cur = max(set(vals), key=vals.count) if vals else ""
        if pc != cur:
            subprocess.run([sys.executable, str(ROOT / "scripts/phongcach.py"), "chon", str(proj), pc], check=False)
            log.append(f"phong cách: {pc}")

    print("ĐÃ ÁP: " + ("; ".join(log) if log else "không có thay đổi"))
    if (sua.get("ghiChu") or "").strip():
        print("GHI CHÚ: " + sua["ghiChu"].strip())


if __name__ == "__main__":
    main()
