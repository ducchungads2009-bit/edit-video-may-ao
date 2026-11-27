"""Tìm & tải ảnh/video minh họa miễn phí từ Pixabay, và ẢNH giấy phép mở từ Openverse (--ov).

Openverse (openverse.org): >800 triệu ảnh Creative Commons / public domain gom từ Wikimedia, Flickr, bảo tàng… — có cả ẢNH
ĐỊA DANH THẬT (Hồ Gươm, cầu Rồng, Landmark 81, phố cổ, tỉnh thành…). Chỉ lấy ảnh được dùng thương mại & chỉnh sửa. PHẢI GHI
NGUỒN (tác giả + giấy phép): tool tự lưu vào assets/stock/_nguon.json, tự chèn dòng chữ nhỏ ở góc ảnh khi xuất (tắt: "credit": false).

1) Tìm, xuất ảnh ghép các lựa chọn để xem:
   python scripts/stock.py search "<folder>" <ten> "<từ khóa TIẾNG ANH>" [--video] [--n 6]
   -> <folder>/assets/stock/_pick_<ten>.jpg  (các ứng viên đánh số 1..n)
2) Tải bản đầy đủ của lựa chọn số k:
   python scripts/stock.py get "<folder>" <ten> <k>
   Openverse: thêm --ov vào lệnh search (chỉ ảnh, từ khoá tiếng Anh hoặc tên địa danh, vd "Hoan Kiem Lake", "Dragon Bridge Da Nang")
   -> <folder>/assets/stock/<ten>.jpg hoặc .mp4  (dùng trong plan.json: "src": "assets/stock/<ten>.jpg")

Ảnh/video Pixabay dùng miễn phí cả cho mục đích thương mại, không bắt buộc ghi nguồn.
"""
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "video-tool/1.0"}


def key():
    k = json.loads((ROOT / "settings.json").read_text(encoding="utf-8")).get("pixabayKey", "")
    if not k:
        sys.exit("Chưa có pixabayKey trong settings.json")
    return k


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def best_video(v: dict) -> dict:
    """Bản lớn nhất nhưng không quá Full HD (4K làm render nặng, dễ lỗi thiếu RAM)."""
    vs = [x for x in (v.get(k) for k in ("large", "medium", "small", "tiny")) if x and x.get("url")]
    ok = [x for x in vs if max(x["width"], x["height"]) <= 1920]
    return max(ok, key=lambda x: x["width"] * x["height"]) if ok else min(vs, key=lambda x: x["width"] * x["height"])


def search(folder: Path, name: str, query: str, video: bool, n: int):
    q = urllib.parse.urlencode({"key": key(), "q": query, "per_page": 30, "safesearch": "true",
                                **({} if video else {"image_type": "photo"})})
    url = f"https://pixabay.com/api/{'videos/' if video else ''}?{q}"
    hits = json.loads(fetch(url)).get("hits", [])
    if not hits:
        print(f"KHÔNG TÌM THẤY: '{query}'. Thử từ khóa tiếng Anh khác, hoặc nhờ người dùng tìm.")
        return

    # ưu tiên ảnh dọc / độ phân giải cao
    def score(h):
        if video:
            v = best_video(h["videos"])
            return (v["height"] >= v["width"], v["width"] * v["height"] >= 1280 * 720)
        return (h["imageHeight"] >= h["imageWidth"], h["imageWidth"] >= 1500)

    hits = sorted(hits, key=score, reverse=True)[:n]
    out = folder / "assets" / "stock"
    out.mkdir(parents=True, exist_ok=True)
    cands = []
    from PIL import Image, ImageDraw

    thumbs = []
    for h in hits:
        if video:
            v = h["videos"]
            best = best_video(v)
            thumb_url = (v.get("small") or v.get("medium") or {}).get("thumbnail") or (v.get("tiny") or {}).get("thumbnail")
            cands.append({"url": best["url"], "ext": ".mp4", "w": best["width"], "h": best["height"],
                          "dur": h.get("duration"), "tags": h.get("tags"), "page": h.get("pageURL")})
        else:
            thumb_url = h.get("webformatURL")
            cands.append({"url": h["largeImageURL"], "ext": ".jpg", "w": h["imageWidth"], "h": h["imageHeight"],
                          "tags": h.get("tags"), "page": h.get("pageURL")})
        try:
            thumbs.append(Image.open(io.BytesIO(fetch(thumb_url))).convert("RGB") if thumb_url else None)
        except Exception:
            thumbs.append(None)

    W, H, top = 320, 180 if video else 240, 30
    sheet = Image.new("RGB", (W * len(cands) + 10 * (len(cands) - 1), H + top + 4), "white")
    d = ImageDraw.Draw(sheet)
    for i, (c, t) in enumerate(zip(cands, thumbs)):
        x = i * (W + 10)
        lab = f"{i + 1}  {c['w']}x{c['h']}" + (f"  {c['dur']}s" if c.get("dur") else "")
        d.text((x + 4, 8), lab, fill="black")
        if t:
            t.thumbnail((W, H))
            sheet.paste(t, (x + (W - t.width) // 2, top + (H - t.height) // 2))
        else:
            d.rectangle([x, top, x + W, top + H], fill="#ccc")
    sheet.save(out / f"_pick_{name}.jpg", quality=85)
    (out / f"_pick_{name}.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ứng viên '{query}' -> {out / f'_pick_{name}.jpg'}")
    for i, c in enumerate(cands):
        print(f"  {i + 1}. {c['w']}x{c['h']} {c.get('dur') or ''} | {c.get('tags')}")


def browse(query: str, video: bool, page: int = 1, per_page: int = 24) -> dict:
    """1 trang kết quả Pixabay (cho trình chỉnh sửa: lưới ảnh nhỏ + nút Xem thêm) -> {total, hits: [...]}"""
    q = urllib.parse.urlencode({"key": key(), "q": query, "per_page": max(3, min(200, per_page)), "page": max(1, page), "safesearch": "true",
                                **({} if video else {"image_type": "photo"})})
    j = json.loads(fetch(f"https://pixabay.com/api/{'videos/' if video else ''}?{q}"))
    out = []
    for h in j.get("hits", []):
        if video:
            v = h["videos"]
            best = best_video(v)
            sm = v.get("tiny") or v.get("small") or {}
            out.append({"id": h["id"], "thumb": (v.get("small") or v.get("medium") or {}).get("thumbnail") or sm.get("thumbnail"),
                        "preview": sm.get("url"), "url": best["url"], "ext": ".mp4", "w": best["width"], "h": best["height"],
                        "dur": h.get("duration"), "tags": h.get("tags")})
        else:
            out.append({"id": h["id"], "thumb": h.get("webformatURL"), "url": h.get("largeImageURL"), "ext": ".jpg",
                        "w": h.get("imageWidth"), "h": h.get("imageHeight"), "tags": h.get("tags")})
    return {"total": j.get("totalHits", 0), "hits": out}


def download(folder: Path, url: str, ext: str, base: str) -> Path:
    out = folder / "assets" / "stock"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{base}{ext}"
    if not dst.exists():
        if not re.match(r"^https://([a-z0-9-]+\.)*pixabay\.com/", url):
            raise ValueError("Chỉ tải từ pixabay.com")
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        tmp.write_bytes(fetch(url))
        tmp.replace(dst)
    return dst


# ---------- OPENVERSE (ảnh Creative Commons / public domain, phải ghi nguồn) ----------
OV = "https://api.openverse.org/v1/images/"
OV_CACHE = ROOT / "_cache" / "openverse.json"


def _ov_get(url: str) -> dict:
    try:
        c = json.loads(OV_CACHE.read_text(encoding="utf-8"))
    except Exception:
        c = {}
    if url in c:
        return c[url]
    try:
        j = json.loads(fetch(url))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError("Openverse đang giới hạn số lần tìm (tìm nhiều quá) — đợi vài phút rồi thử lại")
        raise
    c[url] = j
    if len(c) > 400:  # giữ bộ nhớ đệm gọn
        c = dict(list(c.items())[-300:])
    OV_CACHE.parent.mkdir(parents=True, exist_ok=True)
    OV_CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return j


def _lic(h: dict) -> str:
    l = (h.get("license") or "").lower()
    return "CC0" if l == "cc0" else "Public domain" if l == "pdm" else f"CC {l.upper()} {h.get('license_version') or ''}".strip()


def ov_credit(h: dict) -> str:
    """dòng ghi nguồn ngắn: 'Ảnh: <tác giả> · CC BY 2.0 · Wikimedia'"""
    who = (h.get("creator") or "").strip()[:40]
    src = (h.get("source") or h.get("provider") or "").replace("_", " ").title()
    return " · ".join(x for x in [f"Ảnh: {who}" if who else "Ảnh", _lic(h), src] if x)


def ov_browse(query: str, page: int = 1, per_page: int = 24) -> dict:
    """1 trang kết quả Openverse (ảnh dùng thương mại + chỉnh sửa được) -> {total, hits}"""
    q = urllib.parse.urlencode({"q": query, "page": max(1, page), "page_size": max(3, min(50, per_page)),
                                "license_type": "commercial,modification", "mature": "false"})
    j = _ov_get(OV + "?" + q)
    out = []
    for h in j.get("results", []):
        if not h.get("url"):
            continue
        out.append({"id": h["id"], "thumb": h.get("thumbnail") or h.get("url"), "url": h["url"], "ext": ".jpg",
                    "w": h.get("width") or 0, "h": h.get("height") or 0, "tags": h.get("title") or "", "src": "openverse",
                    "credit": ov_credit(h), "page": h.get("foreign_landing_url")})
    return {"total": j.get("result_count", 0), "hits": out}


def ov_download(folder: Path, ov_id: str, base: str) -> Path:
    """tải ảnh Openverse theo mã (lấy lại thông tin từ Openverse cho chắc) + ghi nguồn vào assets/stock/_nguon.json"""
    if not re.fullmatch(r"[0-9a-f-]{20,40}", ov_id or ""):
        raise ValueError("Mã ảnh Openverse không hợp lệ")
    h = _ov_get(OV + ov_id + "/")
    out = folder / "assets" / "stock"
    out.mkdir(parents=True, exist_ok=True)
    ext = Path(urllib.parse.urlparse(h["url"]).path).suffix.lower()
    ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"
    dst = out / f"{base}{ext}"
    if not dst.exists():
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        tmp.write_bytes(fetch(h["url"]))
        tmp.replace(dst)
    save_credit(folder, dst, ov_credit(h), h)
    return dst


def save_credit(folder: Path, file: Path, credit: str, h: dict = None):
    nf = folder / "assets" / "stock" / "_nguon.json"
    try:
        m = json.loads(nf.read_text(encoding="utf-8"))
    except Exception:
        m = {}
    m[file.relative_to(folder).as_posix()] = {"credit": credit, **({"page": h.get("foreign_landing_url"), "license_url": h.get("license_url"),
                                                                     "title": h.get("title")} if h else {})}
    nf.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def credits(folder: Path) -> dict:
    """{đường dẫn file: dòng ghi nguồn} — render / trình chỉnh sửa tự chèn chữ nhỏ ở góc ảnh"""
    try:
        return {k: v.get("credit", "") for k, v in json.loads((folder / "assets" / "stock" / "_nguon.json").read_text(encoding="utf-8")).items()}
    except Exception:
        return {}


def ov_search(folder: Path, name: str, query: str, n: int):
    """như search() nhưng trên Openverse (ảnh) -> _pick_<ten>.jpg/json"""
    from PIL import Image, ImageDraw
    hits = ov_browse(query, 1, 30)["hits"]
    if not hits:
        print(f"KHÔNG TÌM THẤY trên Openverse: '{query}'. Thử tên tiếng Anh / tên riêng khác.")
        return
    hits = sorted(hits, key=lambda h: ((h["h"] or 0) >= (h["w"] or 1), (h["w"] or 0) >= 1200), reverse=True)[:n]
    out = folder / "assets" / "stock"
    out.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for h in hits:
        try:
            thumbs.append(Image.open(io.BytesIO(fetch(h["thumb"]))).convert("RGB"))
        except Exception:
            thumbs.append(None)
    W, H, top = 320, 240, 30
    sheet = Image.new("RGB", (W * len(hits) + 10 * (len(hits) - 1), H + top + 4), "white")
    d = ImageDraw.Draw(sheet)
    for i, (c, t) in enumerate(zip(hits, thumbs)):
        x = i * (W + 10)
        d.text((x + 4, 8), f"{i + 1}  {c['w']}x{c['h']}", fill="black")
        if t:
            t.thumbnail((W, H))
            sheet.paste(t, (x + (W - t.width) // 2, top + (H - t.height) // 2))
    sheet.save(out / f"_pick_{name}.jpg", quality=85)
    (out / f"_pick_{name}.json").write_text(json.dumps([{**h, "ov": h["id"]} for h in hits], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ứng viên Openverse '{query}' -> {out / f'_pick_{name}.jpg'}")
    for i, c in enumerate(hits):
        print(f"  {i + 1}. {c['w']}x{c['h']} | {c['tags'][:60]} | {c['credit']}")
    print("Ảnh Openverse PHẢI ghi nguồn — tool tự chèn chữ nhỏ ở góc ảnh khi xuất; ghi thêm vào bao-cao.md.")


def get(folder: Path, name: str, k: int):
    out = folder / "assets" / "stock"
    pj = out / f"_pick_{name}.json"
    if not pj.exists():
        sys.exit(f"Chưa tìm '{name}' — chạy lệnh search trước.")
    cands = json.loads(pj.read_text(encoding="utf-8"))
    if not 1 <= k <= len(cands):
        sys.exit(f"Chọn số từ 1 đến {len(cands)}")
    c = cands[k - 1]
    for old in out.glob(f"{name}.*"):  # bỏ lựa chọn cũ (có thể khác đuôi)
        old.unlink()
    if c.get("ov"):  # Openverse: tải theo mã + ghi nguồn
        dst = ov_download(folder, c["ov"], name)
        print(f'Đã tải: {dst}   (dùng: "src": "{dst.relative_to(folder).as_posix()}")  — nguồn: {c.get("credit")}')
        return
    dst = out / f"{name}{c['ext']}"
    dst.write_bytes(fetch(c["url"]))
    rel = dst.relative_to(folder).as_posix()
    print(f'Đã tải: {dst}   (dùng: "src": "{rel}")')


def from_url(folder: Path, name: str, url: str, credit: str = ""):
    """ẢNH DỰ ÁN THẬT từ trang web (trang chủ đầu tư, sàn của chủ đầu tư, báo): tải thẳng 1 link ảnh -> assets/stock/<tên>.<đuôi>.
    Ảnh .webp được đổi sang .jpg. credit (tuỳ chọn) = dòng ghi nguồn tool tự chèn ở góc ảnh (ảnh CC BY...); ảnh phối cảnh của
    chính dự án người dùng đang bán thì không cần."""
    out = folder / "assets" / "stock"
    out.mkdir(parents=True, exist_ok=True)
    if not re.match(r"^https?://", url):
        sys.exit("Link phải bắt đầu bằng http(s)://")
    data = fetch(url)
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    q = urllib.parse.urlparse(url).query.lower()
    if "webp" in q or data[:4] == b"RIFF":
        ext = ".webp"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm"):
        ext = ".jpg"
    for old in out.glob(f"{name}.*"):
        old.unlink()
    dst = out / f"{name}{ext}"
    dst.write_bytes(data)
    if ext == ".webp":
        try:
            im = Image.open(dst).convert("RGB")
            jpg = out / f"{name}.jpg"
            im.save(jpg, quality=94)
            dst.unlink()
            dst = jpg
        except Exception as e:  # noqa
            print("[!] Không đổi được webp -> jpg:", e)
    if credit:
        save_credit(folder, dst, credit)
    try:
        w, h = Image.open(dst).size
        size = f"{w}x{h}"
    except Exception:  # noqa
        size = "?"
    print(f'Đã tải: {dst}   ({size}; dùng: "src": "{dst.relative_to(folder).as_posix()}")')


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    a = sys.argv[1:]
    if len(a) >= 2:
        from tiendo import stop_guard
        stop_guard(Path(a[1]).resolve())
    if len(a) >= 4 and a[0] == "search":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 5
        if "--ov" in a:
            ov_search(Path(a[1]).resolve(), a[2], a[3], n)
        else:
            search(Path(a[1]).resolve(), a[2], a[3], "--video" in a, n)
    elif len(a) >= 4 and a[0] == "get":
        get(Path(a[1]).resolve(), a[2], int(a[3]))
    elif len(a) >= 4 and a[0] == "url":
        from_url(Path(a[1]).resolve(), a[2], a[3], a[a.index("--nguon") + 1] if "--nguon" in a else "")
    else:
        sys.exit(__doc__)
