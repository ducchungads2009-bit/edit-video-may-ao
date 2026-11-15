"""Phân tích VIDEO MẪU (phong cách) của một dự án — máy tự chạy, không tốn quota.

Dùng:  python scripts/style.py "<folder>"

Video mẫu đặt trong <folder>/_mau/ (giao diện: thẻ "Video mẫu"). Tạo <folder>/_mau/_phan-tich/:
  khung_XX.jpg   lưới khung hình MỖI GIÂY, có mốc giây ở góc (mỗi ảnh 30 ô = 30 giây; tối đa 3 phút đầu)
  phan-tich.json thời lượng, kích thước, điểm cắt cảnh, độ dài cảnh trung bình, độ to âm thanh theo từng giây
  loi-noi.txt    lời nói trong video mẫu (nhận giọng tiếng Việt), mốc giây ở đầu dòng
  hieu-ung_XX.jpg  chuỗi 6 khung liền nhau (0,1s/khung) ở những lúc CHỮ/HÌNH xuất hiện -> thấy kiểu hiện chữ, hiệu ứng
  chu_XX.jpg     khung hình nét (sau khi chữ hiện xong) -> nhận font, màu, viền, bóng, nền chữ
  phan-tich.json còn có: suKien (lúc chữ/hình xuất hiện + vùng), phuDe (vị trí phụ đề ước tính), flash, nhịp
Claude xem các file này để dựng video của dự án theo cùng phong cách (xem CLAUDE.md, mục "Video mẫu").
"""
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import VIDEO_EXT, footage_sheets, probe, readable, run, scene_cuts, transcribe  # noqa: E402

MAX_SEC = 180
FPS_A = 10      # khung/giây khi dò sự kiện
GW, GH = 72, 128  # khung xám thu nhỏ để dò


def gray_frames(video: Path):
    """khung xám thu nhỏ 10 khung/giây -> mảng numpy (n, GH, GW)."""
    import numpy as np
    import subprocess
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(MAX_SEC), "-i", str(video), "-vf",
                        f"fps={FPS_A},scale={GW}:{GH}:force_original_aspect_ratio=disable,format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (GW * GH)
    return a[: n * GW * GH].reshape(n, GH, GW).astype(np.int16)


def detect_events(fr, cuts):
    """lúc chữ/đồ họa/hình chèn xuất hiện: một VÙNG khung đổi mạnh nhưng không phải cắt cảnh."""
    import numpy as np
    if len(fr) < 3:
        return [], {}, 0
    bands = 8
    d = np.abs(np.diff(fr, axis=0))  # (n-1, GH, GW)
    glob = d.mean(axis=(1, 2))
    per = d.reshape(len(d), bands, GH // bands, GW).mean(axis=(2, 3))  # (n-1, bands)
    near_cut = np.zeros(len(d), bool)
    for c in cuts:
        k = int(round(c * FPS_A))
        near_cut[max(0, k - 2):k + 2] = True
    thr = np.maximum(np.minimum(np.median(per, axis=0), np.median(per)) * 4, 7.0)
    ev = []
    for i in range(len(d)):
        if near_cut[i] or glob[i] > 28:
            continue
        hit = np.where(per[i] > thr)[0]
        if len(hit) and len(hit) <= 5:  # đổi cục bộ (không cả khung)
            b = int(hit[np.argmax(per[i][hit])])
            ev.append({"t": round((i + 1) / FPS_A, 2), "band": b, "score": float(per[i][hit].max())})
    merged = []
    for e in ev:  # gộp sự kiện sát nhau cùng vùng
        if merged and e["t"] - merged[-1]["t"] < 0.45 and abs(e["band"] - merged[-1]["band"]) <= 1:
            if e["score"] > merged[-1]["score"]:
                merged[-1]["score"] = e["score"]
            continue
        merged.append(e)
    # vùng có sự kiện dày đặc, nhịp đều (≥ 0,6 lần/giây) ở nửa dưới -> phụ đề
    dur = len(fr) / FPS_A
    cnt = [sum(1 for e in merged if e["band"] == b) for b in range(bands)]
    pair = max(range(4, bands - 1), key=lambda b: cnt[b] + cnt[b + 1])
    rate = (cnt[pair] + cnt[pair + 1]) / max(1.0, dur)
    cap = {"goiY": f"có thể có phụ đề quanh y≈{int((pair + 1) / bands * 1920)}px/1920" if rate >= 0.6 else "ít đổi ở nửa dưới — có thể không có phụ đề",
           "demSuKienTheoVung_0tren_7duoi": cnt,
           "luuY": "chỉ là ước tính (tay/người cử động cũng tính) — xác nhận bằng khung_XX.jpg / chu_XX.jpg"}
    # chớp sáng: độ sáng tăng vọt rồi giảm lại trong ≤ 0,4s
    br = fr.mean(axis=(1, 2))
    flashes = [round(i / FPS_A, 2) for i in range(1, len(br) - 4)
               if br[i] - br[i - 1] > 35 and br[i] - br[min(len(br) - 1, i + 4)] > 25]
    return merged, cap, flashes


def _frames30(video: Path, t0: float, dur: float, w=90, h=160):
    import numpy as np
    import subprocess
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{max(0, t0):.3f}", "-t", f"{dur:.3f}", "-i", str(video), "-an",
                        "-vf", f"fps=30,scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = len(a) // (w * h)
    return a[: n * w * h].reshape(n, h, w).astype(np.float32)


def _scale_err(a, b, k):
    """sai khác giữa b và a phóng to k lần (cắt giữa) -> để nhận zoom"""
    import numpy as np
    h, w = a.shape
    ch, cw = int(h / k), int(w / k)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    crop = a[y0:y0 + ch, x0:x0 + cw]
    yi = (np.arange(h) * ch / h).astype(int)
    xi = (np.arange(w) * cw / w).astype(int)
    return float(np.abs(crop[yi][:, xi] - b).mean())


def _shift(a, b):
    """dịch chuyển (dx, dy) giữa 2 khung bằng tương quan pha"""
    import numpy as np
    F = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(b - b.mean()))
    r = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    h, w = a.shape
    return (x if x < w / 2 else x - w), (y if y < h / 2 else y - h)


def _sharp(a):
    import numpy as np
    return float(np.var(a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]))


def diff_cuts(fr):
    """điểm đổi cảnh đột ngột từ khung xám 10/giây (bắt cả cắt giữa 2 cảnh giống nhau mà bộ dò thường bỏ sót)"""
    import numpy as np
    if fr is None or len(fr) < 10:
        return []
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    out = []
    for i in range(len(d)):
        loc = np.median(d[max(0, i - 15):i + 15])
        if d[i] > max(18.0, 3.5 * loc) and d[i] >= d[max(0, i - 2):i + 3].max():
            t = round((i + 1) / FPS_A, 2)
            if not out or t - out[-1] > 0.5:
                out.append(t)
    return out


def _prof_dx(a, b):
    """dịch ngang giữa 2 khung theo đường bao cột (chịu được nhòe chuyển động)"""
    import numpy as np
    pa, pb = a.mean(0), b.mean(0)
    pa, pb = pa - pa.mean(), pb - pb.mean()
    c = np.correlate(pb, pa, "full")
    return int(c.argmax() - (len(pa) - 1))


def gradual_candidates(fr, cuts):
    """chuyển cảnh từ từ (mờ chồng, lia, trượt...) mà dò cắt cảnh thường bỏ sót: khung trước–sau 0,5s khác hẳn nhưng từng bước đổi ít"""
    import numpy as np
    if len(fr) < 8:
        return []
    out = []
    step = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    for i in range(len(fr) - 5):
        big = np.abs(fr[i + 5] - fr[i]).mean()
        if big > 30 and step[i:i + 5].max() < 26:
            t = round((i + 2.5) / FPS_A, 2)
            if all(abs(t - c) > 0.6 for c in list(cuts) + out):
                out.append(t)
    return out


def classify_transitions(src: Path, cuts: list, out_dir: Path, limit_sheets=8):
    """nhận dạng kiểu từng chuyển cảnh: cut | zoom (zoom cut) | fade | flash | whip | slide | up | zoomin | blur"""
    import numpy as np
    res = []
    for t in cuts[:80]:
        f = _frames30(src, t - 0.4, 0.8)
        if len(f) < 12:
            continue
        d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
        pk = int(d.argmax())
        br = f.mean(axis=(1, 2))
        kind = "cut"
        pre, post = f[max(0, pk - 3)], f[min(len(f) - 1, pk + 4)]
        if br[max(0, pk - 2):pk + 4].max() - max(br[0], br[-1]) > 35:
            kind = "flash"
        else:
            hot = int((d > 0.4 * d.max()).sum())
            if hot <= 2:  # đổi trong 1 khung
                a, b = f[max(0, pk)], f[min(len(f) - 1, pk + 1)]
                errs = {k: _scale_err(a, b, k) for k in (1.0, 1.06, 1.1, 1.15, 1.2, 1.3)}
                kbest = min(errs, key=errs.get)
                kind = "zoom" if kbest > 1.0 and errs[kbest] < 0.6 * errs[1.0] else "cut"
            else:
                lo, hi = max(0, pk - 3), min(len(f) - 1, pk + 3)
                dxs = [_prof_dx(f[i], f[i + 1]) for i in range(lo, hi)]
                dys = [_prof_dx(f[i].T, f[i + 1].T) for i in range(lo, hi)]
                sh = [_sharp(f[i]) for i in range(lo, hi + 1)]
                edge = 0.5 * (sh[0] + sh[-1]) + 1e-6
                blur_drop = min(sh) / edge
                sc = []
                for i in range(lo, hi):
                    e = {k: _scale_err(f[i], f[i + 1], k) for k in (1.0, 1.05, 1.1, 1.15, 1.2)}
                    sc.append(min(e, key=e.get))
                big_dx = max(abs(x) for x in dxs) if dxs else 0
                big_dy = max(abs(x) for x in dys) if dys else 0
                if big_dx >= 8 and big_dx >= big_dy * 0.8:
                    kind = "whip" if blur_drop < 0.2 else "slide"
                elif big_dy >= 12:
                    kind = "up"
                elif sum(1 for k in sc if k > 1.0) >= 2:
                    kind = "zoomin"
                elif blur_drop < 0.25:
                    kind = "blur"
                else:
                    kind = "fade"
        res.append({"t": round(t, 2), "kieu": kind})
    # ảnh chuỗi khung quanh vài điểm chuyển (ưu tiên kiểu khác "cut")
    try:
        from PIL import Image, ImageDraw
        for old in out_dir.glob("chuyen-canh_*.jpg"):
            old.unlink()
        pick = sorted(res, key=lambda r: (r["kieu"] == "cut", r["t"]))[:limit_sheets]
        pick.sort(key=lambda r: r["t"])
        tmp = out_dir / "_cc.jpg"
        strips = []
        for r in pick:
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, r['t'] - 0.2):.2f}", "-i", str(src), "-t", "0.4",
                 "-vf", "fps=15,scale=200:-2,tile=6x1", "-frames:v", "1", "-q:v", "3", str(tmp)])
            if tmp.exists():
                strips.append((r, Image.open(tmp).convert("RGB").copy()))
                tmp.unlink()
        for i in range(0, len(strips), 2):
            part = strips[i:i + 2]
            w = max(im.width for _, im in part)
            sheet = Image.new("RGB", (w, sum(im.height + 30 for _, im in part)), (20, 20, 28))
            dr = ImageDraw.Draw(sheet)
            y = 0
            for r, im in part:
                dr.text((8, y + 8), f"{r['t']:.1f}s - may doan: {r['kieu']} - 6 khung, moi khung 1/15s", fill=(255, 230, 120))
                sheet.paste(im, (0, y + 30))
                y += im.height + 30
            sheet.save(out_dir / f"chuyen-canh_{i // 2 + 1:02d}.jpg", quality=85)
    except Exception as e:  # noqa
        print("[!] Không tạo được ảnh chuyển cảnh:", e)
    return res


def sfx_usage(src: Path, moments: list, dur: float) -> dict:
    """có dùng hiệu ứng âm thanh không: tiếng cao tần bật lên đột ngột ngay lúc chuyển cảnh / chữ hiện"""
    import numpy as np
    import subprocess
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(min(dur, MAX_SEC)), "-i", str(src), "-vn", "-ac", "1",
                        "-ar", "16000", "-af", "aresample=async=1:first_pts=0,highpass=f=2500", "-f", "s16le", "-"], capture_output=True)
    x = np.abs(np.frombuffer(r.stdout, np.int16).astype(np.float32))
    if len(x) < 16000:
        return {}
    hop = 160  # 10 ms
    e = x[: len(x) // hop * hop].reshape(-1, hop).mean(1)
    flux = np.maximum(0, np.diff(e, prepend=e[0]))
    thr = np.percentile(flux, 99)  # bật lên mạnh hơn 99% thời gian còn lại

    def rate(ts):
        h = 0
        for t in ts:
            i = int(t * 100)
            w = flux[max(0, i - 25):i + 25]
            if len(w) and w.max() > thr:
                h += 1
        return h, h / max(1, len(ts))
    hit, r_ev = rate(moments)
    rnd = np.random.default_rng(1).uniform(0.5, len(e) / 100 - 0.5, 200)
    _, r_rand = rate(list(rnd))
    ratio = max(0.0, (r_ev - r_rand) / max(1e-6, 1 - r_rand))  # trừ phần "trùng hợp ngẫu nhiên"
    return {"tiLe": round(ratio, 2), "soLan": hit, "tren": len(moments),
            "mucDo": "nhieu" if ratio > 0.55 else "vua" if ratio > 0.25 else "it",
            "ghiChu": "tỉ lệ khoảnh khắc (chuyển cảnh/chữ hiện) có tiếng 'bụp/vụt' bật lên — ước tính"}


def burst_sheets(src: Path, out: Path, events: list, cap: dict, limit=14):
    """chuỗi khung liền nhau quanh mỗi sự kiện (không tính phụ đề), 2 sự kiện / ảnh; + khung nét để nhận font."""
    from PIL import Image, ImageDraw
    for old in list(out.glob("hieu-ung_*.jpg")) + list(out.glob("chu_*.jpg")):
        old.unlink()
    pool = events
    pool = sorted(pool, key=lambda e: -e["score"])
    pick = []
    for e in pool:  # trải đều, cách nhau ≥ 1,5s; luôn lấy sự kiện trong 3s đầu (hook)
        if all(abs(e["t"] - p["t"]) >= 1.5 for p in pick):
            pick.append(e)
        if len(pick) >= limit:
            break
    hook = [e for e in pool if e["t"] < 3]
    if hook and not any(p["t"] < 3 for p in pick):
        pick[-1:] = [hook[0]]
    pick.sort(key=lambda e: e["t"])
    strips = []
    tmp = out / "_strip.jpg"
    for e in pick:
        t0 = max(0.0, e["t"] - 0.15)
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.2f}", "-i", str(src), "-t", "0.7", "-vf",
             "fps=10,scale=240:-2,tile=6x1", "-frames:v", "1", "-q:v", "3", str(tmp)])
        if tmp.exists():
            im = Image.open(tmp).convert("RGB")
            strips.append((e, im.copy()))
            tmp.unlink()
    vung = ["tren cung", "tren", "tren", "giua", "giua", "duoi", "duoi", "duoi cung"]
    k = 0
    for i in range(0, len(strips), 2):
        part = strips[i:i + 2]
        w = max(im.width for _, im in part)
        h = sum(im.height + 34 for _, im in part)
        sheet = Image.new("RGB", (w, h), (20, 20, 28))
        dr = ImageDraw.Draw(sheet)
        y = 0
        for e, im in part:
            dr.text((8, y + 8), f"{e['t']:.1f}s - vung {vung[e['band']]} - 6 khung, moi khung 0,1s ->", fill=(255, 230, 120))
            sheet.paste(im, (0, y + 34))
            y += im.height + 34
        k += 1
        sheet.save(out / f"hieu-ung_{k:02d}.jpg", quality=85)
    # khung nét sau khi chữ hiện xong (0,6s sau sự kiện), 3 khung / ảnh
    stills = []
    for e in pick[:9]:
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{e['t'] + 0.6:.2f}", "-i", str(src), "-frames:v", "1",
             "-vf", "scale=540:-2", "-q:v", "2", str(tmp)])
        if tmp.exists():
            stills.append((e, Image.open(tmp).convert("RGB").copy()))
            tmp.unlink()
    for i in range(0, len(stills), 3):
        part = stills[i:i + 3]
        sheet = Image.new("RGB", (sum(im.width for _, im in part), max(im.height for _, im in part) + 30), (20, 20, 28))
        dr = ImageDraw.Draw(sheet)
        x = 0
        for e, im in part:
            dr.text((x + 8, 8), f"{e['t'] + 0.6:.1f}s", fill=(255, 230, 120))
            sheet.paste(im, (x, 30))
            x += im.width
        sheet.save(out / f"chu_{i // 3 + 1:02d}.jpg", quality=88)
    return pick


def find_ref(folder: Path):
    d = folder / "_mau"
    if not d.is_dir():
        return None
    vids = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)
    return vids[0] if vids else None


def loudness(video: Path, dur: float) -> list:
    """Độ to (dB) trung bình từng giây — để thấy có nhạc nền liên tục hay chỉ có giọng, có khoảng lặng không."""
    r = run(["ffmpeg", "-hide_banner", "-t", str(min(dur, MAX_SEC)), "-i", str(video), "-vn", "-af",
             "asetnsamples=48000,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
             "-ar", "48000", "-f", "null", "-"])
    vals = [float(m) if m not in ("-inf", "inf") else -90.0
            for m in re.findall(r"RMS_level=(-?[\d.]+|-?inf)", r.stderr)]
    return [round(v, 1) for v in vals]


TR_NAME = {"cut": "cắt thẳng", "zoom": "zoom cut", "fade": "mờ chồng", "flash": "chớp sáng", "whip": "lia nhanh",
           "slide": "đẩy ngang", "up": "đẩy lên", "zoomin": "zoom xuyên", "blur": "nhòe chồng"}


def goi_y(st: dict) -> dict:
    """máy tự gợi ý một số thành phần phong cách (Claude bổ sung/sửa khi rút phong cách)"""
    tp, style, plan = {}, {}, {}
    tr = st.get("chuyenCanhTongHop") or {}
    tot = sum(tr.values())
    if tot:
        main_k = max(tr, key=tr.get)
        others = {k: v for k, v in tr.items() if k != "cut"}
        if main_k == "cut" and others and sum(others.values()) >= 0.3 * tot:
            main_k = max(others, key=others.get)
        plan["transition"] = "auto" if main_k == "cut" and tr.get("zoom") else main_k
        if tr.get("flash", 0) >= max(2, 0.3 * tot):
            plan["cutFx"] = "flash"
        tp["chuyencanh"] = ", ".join(f"{TR_NAME.get(k, k)} ×{v}" for k, v in sorted(tr.items(), key=lambda x: -x[1]))
    sfx = st.get("amThanhHieuUng") or {}
    if sfx.get("mucDo"):
        style["sfx"] = {"density": sfx["mucDo"], "joins": sfx["mucDo"] != "it"}
        tp["amthanh"] = {"nhieu": "hiệu ứng âm thanh dày (gần như mỗi lần chuyển/chữ hiện)", "vua": "hiệu ứng âm thanh vừa phải",
                         "it": "ít hiệu ứng âm thanh"}[sfx["mucDo"]]
    pace = {"doDaiCanhTB": st.get("doDaiCanhTrungBinh"), "catMoi10s": st.get("catMoi10Giay"),
            "chuHinhMoi10s": st.get("soSuKienMoi10Giay"), "tocDoNoi": st.get("tocDoNoi_chuMoiPhut")}
    style["pace"] = {k: v for k, v in pace.items() if v is not None}
    tp["nhip"] = f"cảnh dài ~{pace['doDaiCanhTB']}s, ~{pace['chuHinhMoi10s']} lần chữ/hình hiện mỗi 10s"
    eff = {}
    if st.get("chopSang"):
        eff["flash"] = len(st["chopSang"])
    zs = st.get("zoom") or []
    if zs:
        per10 = len(zs) / max(1.0, min(st.get("durationSec", 60), MAX_SEC)) * 10
        eff["zoom"] = "nhiều" if per10 > 1.5 else "vừa" if per10 > 0.5 else "ít"
        kinds = [z["kieu"] for z in zs]
        eff["zoomStyle"] = {"punch": "punch", "push": "in", "pull": "out"}[max(set(kinds), key=kinds.count)]
    if eff:
        style["effects"] = eff
        parts = []
        if eff.get("zoom"):
            parts.append(f"zoom {eff['zoom']} ({ {'punch': 'giật', 'in': 'đẩy vào', 'out': 'kéo ra'}[eff['zoomStyle']]})")
        if eff.get("flash"):
            parts.append(f"{eff['flash']} lần chớp sáng")
        tp["hieuung"] = ", ".join(parts)
    # màu video
    gm = (st.get("mauVideo") or {}).get("goiYMau")
    if gm:
        plan["color"] = gm
        tp["mau"] = ", ".join(x for x in [
            gm.get("brightness", 100) > 102 and "sáng", gm.get("brightness", 100) < 98 and "tối",
            gm.get("saturation", 100) > 104 and "rực", gm.get("saturation", 100) < 96 and "nhạt màu",
            gm.get("contrast", 100) > 104 and "tương phản cao", gm.get("contrast", 100) < 96 and "dịu",
            gm.get("warmth", 0) > 3 and "ấm", gm.get("warmth", 0) < -3 and "lạnh", gm.get("fade") and "kiểu phim (nâng tối)"] if x) or "màu tự nhiên"
    # âm thanh: loại tiếng hay dùng ở từng khoảnh khắc -> bảng tự gán
    sf = st.get("sfxTongHop") or {}
    tk = sf.get("theoKhoanhKhac") or {}
    if tk:
        from style_sau import SFX_MAP
        mp = {{"cut": "cut", "chu": "text", "zoom": "zoom"}[k]: SFX_MAP.get(v["loaiHayDung"], "pop") for k, v in tk.items() if v["tiLeCoSfx"] >= 0.25}
        if mp:
            style.setdefault("sfx", {})["map"] = mp
            if "cut" in mp:
                style["sfx"]["joins"] = True
        rate = max(v["tiLeCoSfx"] for v in tk.values())
        style.setdefault("sfx", {})["density"] = "nhieu" if rate > 0.6 else "vua" if rate > 0.3 else "it"
        name = {"cut": "chuyển cảnh", "text": "chữ hiện", "zoom": "zoom"}
        tp["amthanh"] = ", ".join(f"{name[k]} → {v}" for k, v in mp.items()) or tp.get("amthanh", "")
    mu = st.get("nhac") or {}
    if mu.get("bpm"):
        style.setdefault("pace", {})["bpm"] = mu["bpm"]
        if mu.get("catTrungNhip_tiLe") is not None:
            style["pace"]["catTheoNhip"] = mu["catTrungNhip_tiLe"]
    if mu.get("coNhacNen"):
        tp["amthanh"] = (tp.get("amthanh", "") + ("; " if tp.get("amthanh") else "") + f"có nhạc nền{' ~' + str(mu['bpm']) + ' BPM' if mu.get('bpm') else ''}").strip()
    # đồ họa
    g = st.get("doHoaTongHop") or {}
    if g:
        style["graphics"] = {"viTri": g["viTriPhoBien"], "rong": g["rongTB_tiLe"], "tonTai": g["tonTaiTB_s"], "mau": g["mauChu_va_DoHoa"]}
        tp["dohoa"] = f"hay đặt vùng {g['viTriPhoBien']}, rộng ~{int(g['rongTB_tiLe'] * 100)}%, ở lại ~{g['tonTaiTB_s']}s"
    b = st.get("boCuc") or {}
    if b and b.get("doTinCay") != "thap":
        AL = {"giua": "center", "trai": "left", "phai": "right"}
        ZN = {"tren": "top", "giua": "middle", "duoi": "bottom"}
        IP = {"trai": "left", "phai": "right", "tren": "above", "duoi": "below", "rieng": "none"}
        lay = {"align": AL.get(b["canLe"], "center"), "marginX": b["leNgang_px"], "textZone": ZN.get(b.get("vungChu"), "middle"),
               "maxBlocks": b["soKhoiMotLuc"]["max"]}
        if b.get("khoangCachDong_px") is not None:
            lay["stackGap"] = b["khoangCachDong_px"]
        ic = b.get("icon") or {}
        vt = ic.get("viTriCanhChu") or {}
        if vt:
            lay["iconPos"] = IP[max(vt, key=vt.get)]
        style["layout"] = lay
        VN = {"giua": "giữa", "trai": "trái", "phai": "phải", "tren": "trên", "duoi": "dưới", "rieng": "riêng"}
        tp["bocuc"] = f"chữ căn {VN.get(b['canLe'], b['canLe'])}, vùng {VN.get(b.get('vungChu'), '?')}, tối đa {lay['maxBlocks']} khối" + \
            (f", icon {VN.get(max(vt, key=vt.get))} chữ" if vt else "")
        if ic.get("soLan"):
            kd = ic.get("kieu_dem") or {}
            emo = kd.get("emoji/nhiều màu", 0)
            icons = {"kind": "emoji" if kd and emo >= 0.5 * sum(kd.values()) else "lucide", "size": ic.get("co_px")}
            if ic.get("coNen_tiLe") is not None:
                icons["bg"] = "circle" if ic["coNen_tiLe"] >= 0.5 else "none"
            style["icons"] = icons
            tp["icon"] = f"{'emoji' if icons['kind'] == 'emoji' else 'icon nét/đặc'}, cỡ ~{ic.get('co_px')}px" + \
                (", có nền phía sau" if icons.get("bg") == "circle" else "") + " — Claude xem icon-mau.jpg để chọn bộ icon tương tự"
    nh = st.get("nhip") or {}
    if nh:
        style.setdefault("pace", {}).update({"hookChuDauTien": nh.get("chuHinhDauTien_s"), "catSatLoi": nh.get("catSatLoi"),
                                             "matDo3Phan": nh.get("matDoChuHinh_moi10s_theo3Phan")})
        tp["nhip"] = f"cảnh ~{nh['doDaiCanh']['tb']}s" + (", cắt sát lời" if nh.get("catSatLoi") else "") + \
            (f", cắt theo nhịp nhạc {int(mu['catTrungNhip_tiLe'] * 100)}%" if mu.get("catTrungNhip_tiLe") else "")
    return {"style": style, "plan": plan, "thanhPhan": tp, "may": True}


def main(folder: Path):
    ref = find_ref(folder)
    if not ref:
        sys.exit("Chưa có video mẫu trong _mau/ — kéo video mẫu vào thẻ 'Video mẫu' của dự án.")
    out = folder / "_mau" / "_phan-tich"
    out.mkdir(parents=True, exist_ok=True)
    info = probe(ref)
    dur = info["durationSec"]
    print(f"Video mẫu: {ref.name} — {dur}s {info['width']}x{info['height']}")
    src = ref
    if dur > MAX_SEC:  # chỉ phân tích 3 phút đầu
        src = out / "_cat.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-t", str(MAX_SEC), "-i", str(ref), "-c", "copy", str(src)])
    for old in out.glob("khung_*.jpg"):
        old.unlink()
    print("Tạo lưới khung hình mỗi giây...")
    sheets = footage_sheets(src, out, step=1, cols=10, rows=3)
    for p in sheets:  # footage_XX.jpg -> khung_XX.jpg
        p.replace(out / p.name.replace("footage_", "khung_"))
    (out / "footage.txt").unlink(missing_ok=True)
    print("Dò điểm cắt cảnh...")
    cuts = scene_cuts(src)
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [min(dur, MAX_SEC)]) if b - a > 0.05]
    print("Dò lúc chữ/hình xuất hiện, phụ đề, chớp sáng...")
    try:
        fr = gray_frames(src)
        events, cap, flashes = detect_events(fr, cuts)
        picked = burst_sheets(src, out, events, cap)
    except Exception as e:  # noqa
        print("[!] Không dò được hiệu ứng:", e)
        fr, events, cap, flashes, picked = None, [], {}, [], []
    print("Nhận dạng kiểu chuyển cảnh...")
    trans = []
    try:
        dc = diff_cuts(fr)
        base = sorted(dc + [c for c in cuts if all(abs(c - x) > 0.5 for x in dc)])
        allc = sorted(set(base) | set(gradual_candidates(fr, base) if fr is not None else []))
        trans = classify_transitions(src, allc, out)
    except Exception as e:  # noqa
        print("[!] Không nhận dạng được chuyển cảnh:", e)
    try:
        sfxu = sfx_usage(src, [r["t"] for r in trans] + [e["t"] for e in events][:120], dur)
    except Exception as e:  # noqa
        sfxu = {}
    print("Đo âm lượng...")
    loud = loudness(src, dur)
    print("Nhận lời nói...")
    wav = out / "_a.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "16000", str(wav)])
    try:
        words = transcribe(wav)
    except Exception as e:  # noqa
        words = []
        print("[!] Không nhận được lời nói:", e)
    wav.unlink(missing_ok=True)
    (out / "loi-noi.txt").write_text(readable(words) if words else "(không nhận được lời nói)", encoding="utf-8")
    talk = sum(1 for w in words) / max(1.0, min(dur, MAX_SEC)) * 60
    print("Phân tích sâu: đồ họa, zoom, màu, nhạc/nhịp, hiệu ứng âm thanh...")
    try:
        from style_sau import deep, report_md
        sau = deep(src, dur, fr, trans, events, words, out)
    except Exception as e:  # noqa
        print("[!] Không phân tích sâu được:", e)
        sau = {}
    if trans:  # số cảnh theo mọi điểm chuyển đã dò (chính xác hơn bộ dò cắt cảnh thường)
        cuts = sorted(t["t"] for t in trans)
        shots = [b - a for a, b in zip([0.0] + cuts, cuts + [min(dur, MAX_SEC)]) if b - a > 0.05]
    stats = {
        "file": ref.name, "durationSec": dur, "width": info["width"], "height": info["height"],
        "phanTichToiDa": MAX_SEC, "soCanh": len(shots), "diemCat": cuts,
        "doDaiCanhTrungBinh": round(sum(shots) / len(shots), 2) if shots else dur,
        "catMoi10Giay": round(len(cuts) / max(1.0, min(dur, MAX_SEC)) * 10, 2),
        "tocDoNoi_chuMoiPhut": round(talk), "amLuongTungGiay_dB": loud,
        "suKien": [{"t": e["t"], "vung": e["band"]} for e in events][:300],
        "suKien_ghiChu": "lúc một vùng khung đổi mạnh mà không cắt cảnh (chữ/đồ họa/hình chèn hiện ra). vung 0 = trên cùng … 7 = dưới cùng",
        "soSuKienMoi10Giay": round(len(events) / max(1.0, min(dur, MAX_SEC)) * 10, 2),
        "suKienDaChup": [e["t"] for e in picked],
        "phuDe": cap, "chopSang": flashes,
        "chuyenCanh": trans,
        "chuyenCanhTongHop": {k: sum(1 for r in trans if r["kieu"] == k) for k in sorted({r["kieu"] for r in trans})},
        "chuyenCanh_ghiChu": "máy đoán kiểu từng chuyển cảnh: cut (cắt thẳng) | zoom (zoom cut) | fade (mờ chồng) | flash (chớp) | whip (lia nhanh) | slide (đẩy ngang) | up (đẩy lên) | zoomin (zoom xuyên) | blur (nhòe). Xác nhận bằng chuyen-canh_XX.jpg",
        "amThanhHieuUng": sfxu,
        "fontMau": "phong-cach/_font-mau.jpg (bảng các font có sẵn để so)",
        **{k: v for k, v in sau.items() if not k.startswith("_")},
        "banDo": "ban-do.png (bản đồ nhịp dựng: lời nói, chuyển cảnh, chữ/đồ họa, zoom, sfx, nhịp nhạc)",
        "ghiChu": "Âm lượng gần như không đổi (cả lúc ngừng nói) → có nhạc nền liên tục; tụt sâu (< -45 dB) → khoảng lặng.",
    }
    if isinstance(stats.get("nhac"), dict):
        stats["nhac"].pop("_beats", None)
    stats["goiY"] = goi_y(stats)
    (out / "phan-tich.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        (out / "bao-cao-mau.md").write_text(report_md(stats), encoding="utf-8")
    except Exception as e:  # noqa
        print("[!] báo cáo:", e)
    if src != ref:
        src.unlink(missing_ok=True)
    print(f"Xong: {len(shots)} cảnh (trung bình {stats['doDaiCanhTrungBinh']}s/cảnh), {len(words)} chữ, "
          f"{len(sheets)} ảnh khung hình -> {out}")


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/style.py "<folder>"')
    from tiendo import wrap
    _f = Path(sys.argv[1]).resolve()
    _r = find_ref(_f)
    try:
        _vs = min(MAX_SEC, probe(_r)["durationSec"]) if _r else 0
    except Exception:
        _vs = 60
    wrap(_f, "style", _vs, main, _f, msg="Đang phân tích video mẫu")
