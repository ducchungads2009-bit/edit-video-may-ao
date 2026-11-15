"""BẢN ĐỒ vị trí / tiện ích cho khối "map": tìm toạ độ + đường đi ô tô, ra sẵn khối để dán vào plan.json.

  python scripts/nho_may.py bando "<folder>" "Vinhomes Ocean Park" "Vinmec Times City" "Aeon Mall Long Biên"
  (hoặc chạy thẳng: python scripts/ban_do.py "<folder>" ...)
Điểm ĐẦU = dự án / căn nhà, các điểm sau = tiện ích. Mỗi điểm viết được:
  "Tên"                              -> tự tìm (OpenStreetMap, ưu tiên Việt Nam)
  "Tên hiển thị|câu tìm kiếm"         -> hiện "Tên hiển thị", tìm bằng câu sau dấu |  (vd "Trường Vinschool|Vinschool Ocean Park Gia Lâm")
  "Tên@21.0035,105.9421"             -> toạ độ có sẵn (lat,lng — lấy từ Google Maps)
  "Tên@https://maps.google.com/…/@21.0,105.9,17z…"  -> lấy toạ độ trong link Google Maps
Không ghi điểm nào -> dùng vị trí người dùng đã chọn sẵn ở trang dự án (vi-tri.json, toạ độ chính xác, khỏi tìm).
Kết quả: _work/ban-do.json (từng điểm: toạ độ, địa chỉ tìm được, phút / km đi ô tô từ điểm đầu) + in khối "map" mẫu.
VÙNG cho khối "mapTour" (bản đồ vệ tinh kể chuyện — vùng tô màu, viền phát sáng):
  python scripts/nho_may.py bando "<folder>" --vung            -> điền ranh giới (geo) + toạ độ nhãn còn thiếu cho mọi khối
                                                                 mapTour trong plan.json (tìm theo "query" / "parts" / "name")
  python scripts/nho_may.py bando "<folder>" --vung "*Việt Nam" "Quân khu 1=Cao Bằng+Bắc Kạn+Lạng Sơn" "Hà Nội"
                                                              -> dựng sẵn khối mapTour (_work/ban-do-vung-khoi.json):
     "*Tên" = viền phát sáng (glow) · "Tên=A+B+C" = 1 vùng gộp nhiều tỉnh · "Tên" = 1 vùng (tỉnh / nước / quần đảo)
  python scripts/nho_may.py bando "<folder>" --vung --csv "assets/so-lieu.csv" ["*Việt Nam"]
                                                              -> BẢN ĐỒ SỐ LIỆU: mỗi dòng "tên vùng, số[, #màu]" -> vùng tô màu
                                                                 theo số + khối cao theo số + chú giải (_work/ban-do-vung-khoi.json)
  Chỗ chỉ tìm được 1 điểm (quần đảo, đảo nhỏ) -> tự vẽ khung bát giác bán kính "radiusKm" (mặc định 35 km).
Cần mạng (chạy trên máy người dùng qua nho_may). KIỂM TRA "full" (địa chỉ tìm được) xem có đúng chỗ không — tên chung chung dễ ra sai.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "_cache" / "ban-do.json"  # dùng chung với giao diện (gui.py /api/geocode, /api/route)
UA = {"User-Agent": "VideoTool/1.0 (trinh dung video tren may)", "Accept-Language": "vi"}  # giống gui.py
_last = [0.0]


def _get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(c):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def geocode(q: str) -> list:
    c = _cache()
    k = "g|" + q.lower()
    if k not in c:
        w = 1.1 - (time.time() - _last[0])  # Nominatim: tối đa 1 lần / giây
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        base = "https://nominatim.openstreetmap.org/search?"
        r = _get(base + urllib.parse.urlencode({"q": q, "format": "jsonv2", "limit": 5, "countrycodes": "vn"})) or \
            _get(base + urllib.parse.urlencode({"q": q, "format": "jsonv2", "limit": 5}))
        c[k] = [{"name": (x.get("name") or x.get("display_name", "").split(",")[0]).strip(), "full": x.get("display_name", ""),
                 "lng": float(x["lon"]), "lat": float(x["lat"])} for x in r]
        _save(c)
    return c[k]


def route(a, b) -> dict:
    c = _cache()
    k = "r|%.5f,%.5f;%.5f,%.5f" % (a[0], a[1], b[0], b[1])
    if k not in c:
        r = _get("https://router.project-osrm.org/route/v1/driving/%.6f,%.6f;%.6f,%.6f?overview=full&geometries=geojson" % (a[0], a[1], b[0], b[1]))
        rt = r["routes"][0]
        pts = rt["geometry"]["coordinates"]
        step = max(1, len(pts) // 300)
        pts = pts[::step] + ([pts[-1]] if (len(pts) - 1) % step else [])
        c[k] = {"coords": [[round(x, 6), round(y, 6)] for x, y in pts], "minutes": max(1, round(rt["duration"] / 60)), "km": round(rt["distance"] / 1000, 1)}
        _save(c)
    return c[k]


def latlng_of(s: str):
    """toạ độ trong chuỗi "21.0035,105.9421" hoặc link Google Maps (…/@lat,lng,… hoặc !3dlat!4dlng) -> (lat, lng) | None"""
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", s) or re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", s) or \
        re.search(r"[?&](?:q|ll|query)=(-?\d+\.\d+),\s*(-?\d+\.\d+)", s) or re.fullmatch(r"\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*", s)
    return (float(m.group(1)), float(m.group(2))) if m else None


def place(arg: str) -> dict:
    name, rest = arg, ""
    if "@" in arg:
        name, rest = arg.split("@", 1)
        ll = latlng_of(rest) or latlng_of("@" + rest)
        if not ll:
            raise ValueError(f"Không đọc được toạ độ trong: {arg}")
        return {"name": name.strip(), "lat": ll[0], "lng": ll[1], "full": "(toạ độ có sẵn)"}
    if "|" in arg:
        name, rest = arg.split("|", 1)
    q = (rest or name).strip()
    r = geocode(q)
    if not r:
        return {"name": name.strip(), "error": f"không tìm thấy “{q}” — thử tên đầy đủ hơn (kèm quận / tỉnh) hoặc dán toạ độ / link Google Maps"}
    x = r[0]
    return {"name": name.strip(), "lat": x["lat"], "lng": x["lng"], "full": x["full"],
            "khac": [y["full"] for y in r[1:3]]}


def run(folder: Path, args: list) -> dict:
    labels = {}
    if not [a for a in args if a.strip()] and (folder / "vi-tri.json").exists():  # vị trí người dùng đã chọn ở trang dự án
        vt = json.loads((folder / "vi-tri.json").read_text(encoding="utf-8")).get("places") or []
        args = [f"{p['name']}@{p['lat']},{p['lng']}" for p in vt]
        labels = {k: p["label"] for k, p in enumerate(vt) if p.get("label")}
    pts = [place(a) for a in args if a.strip()]
    ok = [p for p in pts if "lat" in p]
    if not ok:
        raise SystemExit("Không tìm được điểm nào: " + "; ".join(p.get("error", "") for p in pts))
    home = ok[0]
    paths = []
    for p in ok[1:]:
        try:
            r = route((home["lng"], home["lat"]), (p["lng"], p["lat"]))
            p.update(minutes=r["minutes"], km=r["km"])
            paths.append(r["coords"])
        except Exception as e:  # noqa
            p["routeError"] = str(e)
            paths.append([[home["lng"], home["lat"]], [p["lng"], p["lat"]]])
    res = {"places": pts, "paths": paths}
    out = folder / "_work" / "ban-do.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    el = {"type": "map", "start": 0, "end": round(1.2 + 1.8 * max(1, len(ok) - 1) + 1.0, 1),
          "places": [{"name": p["name"], "lng": p["lng"], "lat": p["lat"],
                      **({"label": labels[pts.index(p)]} if pts.index(p) in labels else {"label": f"{p['minutes']} phút"} if p.get("minutes") else {})} for p in ok],
          "paths": paths, "lineMode": "road", "camera": "zoomin", "sfx": "whoosh"}
    (folder / "_work" / "ban-do-khoi.json").write_text(json.dumps(el, ensure_ascii=False), encoding="utf-8")
    return res


VCACHE = ROOT / "_cache" / "vung.json"  # ranh giới đã tìm (khá nặng, để riêng)


def _r4(c):
    return [_r4(x) for x in c] if isinstance(c, list) and c and isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]


QG_ALIAS = {"việt nam": "Vietnam", "viet nam": "Vietnam", "lào": "Laos", "campuchia": "Cambodia", "thái lan": "Thailand",
            "trung quốc": "China", "nhật bản": "Japan", "hàn quốc": "South Korea", "triều tiên": "North Korea", "mỹ": "United States of America",
            "hoa kỳ": "United States of America", "nga": "Russia", "pháp": "France", "anh": "United Kingdom", "đức": "Germany", "ý": "Italy",
            "úc": "Australia", "ấn độ": "India", "đài loan": "Taiwan", "tây ban nha": "Spain", "bồ đào nha": "Portugal", "hà lan": "Netherlands",
            "thụy sĩ": "Switzerland", "thụy điển": "Sweden", "ai cập": "Egypt", "nam phi": "South Africa", "mông cổ": "Mongolia",
            "ukraina": "Ukraine", "ba lan": "Poland", "thổ nhĩ kỳ": "Turkey", "ả rập xê út": "Saudi Arabia", "đông timor": "Timor-Leste",
            "miến điện": "Myanmar", "phi-líp-pin": "Philippines", "phi líp pin": "Philippines", "in-đô-nê-xi-a": "Indonesia", "ma-lai-xi-a": "Malaysia",
            "xin-ga-po": "Singapore", "bru-nây": "Brunei", "séc": "Czechia", "áo": "Austria", "bỉ": "Belgium", "đan mạch": "Denmark",
            "phần lan": "Finland", "na uy": "Norway", "hy lạp": "Greece", "triều tiên (bắc hàn)": "North Korea"}


def country_geo(q: str):
    """quốc gia -> đường bờ biển + biên giới ĐẤT LIỀN (Natural Earth, public domain; VN/Lào/Campuchia/Thái nét 1:10m).
    OpenStreetMap trả về cả vùng biển lãnh hải -> viền phát sáng nằm ngoài biển, không đẹp."""
    k = q.lower().strip()
    for pre in ("nước ", "quốc gia "):
        if k.startswith(pre):
            k = k[len(pre):]
    try:
        d = json.loads((ROOT / "scripts" / "du-lieu" / "quoc-gia.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    name = QG_ALIAS.get(k) or next((n for n in d if n.lower() == k), None)
    return {"name": q, "full": f"{name} (Natural Earth — đất liền)", "geo": d[name]} if name in d else None


def boundary(q: str) -> dict:
    """ranh giới hành chính (Polygon / MultiPolygon) từ OpenStreetMap; không có vùng -> chỉ toạ độ điểm"""
    cg = country_geo(q)
    if cg:
        g = cg["geo"]
        pts = [p for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]) for p in poly[0]]
        cg["lng"], cg["lat"] = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
        return cg
    try:
        c = json.loads(VCACHE.read_text(encoding="utf-8"))
    except Exception:
        c = {}
    k = q.lower().strip()
    if k not in c:
        base = "https://nominatim.openstreetmap.org/search?"
        res = None
        for cc in ("vn", None):
            w = 1.1 - (time.time() - _last[0])
            if w > 0:
                time.sleep(w)
            _last[0] = time.time()
            prm = {"q": q, "format": "jsonv2", "limit": 6, "polygon_geojson": 1, "polygon_threshold": 0.004}
            if cc:
                prm["countrycodes"] = cc
            r = _get(base + urllib.parse.urlencode(prm), timeout=40) or []
            poly = [x for x in r if (x.get("geojson") or {}).get("type") in ("Polygon", "MultiPolygon")]
            poly.sort(key=lambda x: (x.get("category") != "boundary", -float(x.get("importance") or 0)))
            pick = poly[0] if poly else (r[0] if r else None)
            if pick:
                res = {"name": (pick.get("name") or q), "full": pick.get("display_name", ""), "lng": float(pick["lon"]), "lat": float(pick["lat"])}
                if poly:
                    g = pick["geojson"]
                    res["geo"] = {"type": g["type"], "coordinates": _r4(g["coordinates"])}
                break
        c[k] = res
        VCACHE.parent.mkdir(parents=True, exist_ok=True)
        VCACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return c[k]


def _octagon(lng, lat, km):
    import math
    dy = km / 111.32
    dx = km / (111.32 * max(0.2, math.cos(math.radians(lat))))
    pts = [[round(lng + dx * math.cos(math.pi / 8 + i * math.pi / 4), 4), round(lat + dy * math.sin(math.pi / 8 + i * math.pi / 4), 4)] for i in range(8)]
    return {"type": "Polygon", "coordinates": [pts + [pts[0]]]}


def region_geo(r: dict, log: list):
    """điền r["geo"] (gộp nhiều phần thành MultiPolygon — giữ cả đường ranh giữa các tỉnh)"""
    parts = r.get("parts") or [r.get("query") or r.get("name")]
    polys = []
    for q in [p for p in parts if p]:
        b = boundary(q)
        if b and not b.get("geo") and not q.lower().startswith(("tỉnh", "thành phố", "quần đảo", "huyện", "quận")):
            for pre in ("Tỉnh ", "Thành phố "):  # tên trùng thành phố / phường -> thử tên đầy đủ cấp tỉnh
                b2 = boundary(pre + q)
                if b2 and b2.get("geo"):
                    b = b2
                    break
        if not b:
            log.append(f"[!] không tìm thấy vùng “{q}”")
            continue
        g = b.get("geo") or _octagon(b["lng"], b["lat"], float(r.get("radiusKm") or 35))
        if not b.get("geo"):
            log.append(f"  “{q}”: chỉ có 1 điểm -> khung bát giác {r.get('radiusKm') or 35} km")
        polys += [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        log.append(f"  {q}: {b['full'][:90]}")
    if polys:
        r["geo"] = {"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1 else {"type": "MultiPolygon", "coordinates": polys}


def _center(geo):
    pts = [p for poly in ([geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]) for p in poly[0]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def fill_tour(e: dict, log: list):
    g = e.get("glow")
    if isinstance(g, dict) and not g.get("geo") and (g.get("query") or g.get("parts") or g.get("name")):
        log.append(f"Viền phát sáng: {g.get('name') or g.get('query')}")
        region_geo(g, log)
    for i, r in enumerate(e.get("regions") or []):
        if not r:
            continue
        if not r.get("geo"):
            log.append(f"Vùng #{i + 1} {r.get('name', '')}:")
            region_geo(r, log)
        for t in (r.get("tags") or []) + (r.get("badges") or []):
            if t.get("lng") is None or t.get("lat") is None:
                q = t.get("place") or t.get("query") or (t.get("name") if t in (r.get("tags") or []) else None)  # ảnh chân dung: tên là tên người, không tìm
                hit = geocode(q) if q else []
                if hit:
                    t["lng"], t["lat"] = round(hit[0]["lng"], 5), round(hit[0]["lat"], 5)
                elif r.get("geo"):  # ảnh chân dung không ghi chỗ -> giữa vùng
                    t["lng"], t["lat"] = [round(x, 5) for x in _center(r["geo"])]
                else:
                    log.append(f"  [!] không tìm được toạ độ cho nhãn “{q}”")


def read_csv(path: Path):
    """bảng số liệu (.csv / .tsv): cột 1 = tên vùng, cột 2 = số (vd 12,5 hoặc 12.5), cột 3 (nếu có) = màu -> (regions, tên cột số)"""
    import csv
    txt = path.read_text(encoding="utf-8-sig")
    dl = "\t" if txt.count("\t") > txt.count(",") and txt.count("\t") > txt.count(";") else (";" if txt.count(";") > txt.count(",") else ",")
    rows = [r for r in csv.reader(txt.splitlines(), delimiter=dl) if r and any(x.strip() for x in r)]
    head = None
    def num(x):
        x = x.strip().replace(" ", "")
        if x.count(",") == 1 and x.count(".") == 0:
            x = x.replace(",", ".")
        elif x.count(".") > 1 or (x.count(".") == 1 and x.count(",") == 1):
            x = x.replace(".", "").replace(",", ".")
        return float(x)
    regs = []
    for r in rows:
        if len(r) < 2:
            continue
        try:
            v = num(r[1])
        except ValueError:
            if head is None and not regs:
                head = r[1].strip()
            continue
        reg = {"name": r[0].strip(), "value": v}
        if len(r) > 2 and r[2].strip().startswith("#"):
            reg["color"] = r[2].strip()
        regs.append(reg)
    return regs, head


def vung(folder: Path, args: list) -> list:
    log = []
    csvp = None
    if "--csv" in args:
        i = args.index("--csv")
        csvp = Path(args[i + 1]) if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
        if csvp and not csvp.is_absolute():
            csvp = folder / csvp
    if csvp:
        regs, head = read_csv(csvp)
        e = {"type": "mapTour", "start": 0, "basemap": "dark", "regions": regs, "extrudeBy": "value", "pitch": 50,
             "scale": {"from": "#fde68a", "to": "#b91c1c"}, "legend": {"title": head or csvp.stem, "unit": ""}, "sfx": "whoosh"}
        if args and args[0].startswith("*"):
            e["glow"] = {"name": args[0][1:].strip(), "color": "#d7ff3a"}
        e["end"] = round(2.2 + 2.2 * max(1, len(regs)) + 1.6, 1)
        fill_tour(e, log)
        out = folder / "_work" / "ban-do-vung-khoi.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
        log.append(f"\nBản đồ số liệu ({len(regs)} vùng từ {csvp.name}): {out}")
        return log
    if args:
        e = {"type": "mapTour", "start": 0, "basemap": "sat", "regions": [], "sfx": "whoosh"}
        for a in args:
            a = a.strip()
            if a.startswith("*"):
                e["glow"] = {"name": a[1:].strip(), "color": "#d7ff3a"}
            elif "=" in a:
                nm, ps = a.split("=", 1)
                e["regions"].append({"name": nm.strip(), "parts": [p.strip() for p in ps.split("+") if p.strip()]})
            elif a:
                e["regions"].append({"name": a})
        e["end"] = round(2.2 + 3.2 * max(1, len(e["regions"])) + 1.6, 1)
        fill_tour(e, log)
        out = folder / "_work" / "ban-do-vung-khoi.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
        log.append(f"\nKhối mapTour mẫu (chỉ cần sửa start/end, màu, mốc 'at', nhãn): {out}")
        return log
    pf = folder / "plan.json"
    plan = json.loads(pf.read_text(encoding="utf-8"))
    n = 0
    for e in plan.get("elements") or []:
        if e and e.get("type") == "mapTour":
            n += 1
            fill_tour(e, log)
    if not n:
        log.append("plan.json chưa có khối mapTour nào.")
    else:
        pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        log.append(f"Đã điền ranh giới cho {n} khối mapTour trong plan.json")
    return log


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2 or (len(sys.argv) < 3 and not (Path(sys.argv[1]) / "vi-tri.json").exists()):
        sys.exit(__doc__)
    f = Path(sys.argv[1]).resolve()
    if "--vung" in sys.argv[2:]:
        print("\n".join(vung(f, [a for a in sys.argv[2:] if a != "--vung"])))
        sys.exit(0)
    res = run(f, sys.argv[2:])
    for i, p in enumerate(res["places"]):
        tag = "DỰ ÁN " if i == 0 else f"#{i} "
        if "error" in p:
            print(f"[!] {tag}{p['name']}: {p['error']}")
        else:
            extra = f" — {p['minutes']} phút / {p['km']} km đi ô tô" if p.get("minutes") else ""
            print(f"{tag}{p['name']}: {p['lat']:.5f}, {p['lng']:.5f}{extra}\n    tìm được: {p['full']}")
            if p.get("routeError"):
                print(f"    [!] không tính được đường đi ({p['routeError'][:80]}) — dùng đường thẳng; nên đặt \"lineMode\": \"arc\"")
    print(f"\nĐã lưu {f / '_work' / 'ban-do.json'}")
    print(f"Khối map mẫu (đủ toạ độ + đường đi, chỉ cần sửa start/end): {f / '_work' / 'ban-do-khoi.json'}")
