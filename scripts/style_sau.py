"""Phân tích SÂU video mẫu (style.py gọi): đồ họa (vị trí/cỡ/màu/thời lượng), zoom trong cảnh, màu video, nhịp dựng,
nhạc nền + BPM + cắt theo nhịp, từng tiếng hiệu ứng âm thanh (loại + gắn với chuyển cảnh/chữ/zoom).
Ghi thêm: ban-do.png (bản đồ nhịp dựng) + bao-cao-mau.md (báo cáo dễ đọc)."""
import subprocess
from pathlib import Path

import numpy as np

W, H = 1080, 1920


def _rgb_frames(src: Path, fps: float, w: int, h: int, t0=0.0, dur=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.3f}"]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(src), "-an", "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8)
    n = len(a) // (w * h * 3)
    return a[: n * w * h * 3].reshape(n, h, w, 3)


def _audio(src: Path, sr=16000, maxsec=180):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(maxsec), "-i", str(src), "-vn", "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", str(sr),
                        "-f", "s16le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0


def _hex(c):
    return "#%02X%02X%02X" % tuple(int(x) for x in c)


def _palette(px: np.ndarray, k=3):
    """k màu chính (k-means đơn giản)"""
    if len(px) < k:
        return []
    px = px.astype(np.float32)
    rng = np.random.default_rng(0)
    cen = px[rng.choice(len(px), k, replace=False)]
    for _ in range(8):
        d = ((px[:, None] - cen[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            if (lab == j).any():
                cen[j] = px[lab == j].mean(0)
    cnt = np.bincount(lab, minlength=k)
    order = np.argsort(-cnt)
    return [(_hex(cen[j]), round(float(cnt[j] / len(px)), 2)) for j in order if cnt[j] > 0]


# ---------- 1. đồ họa / chữ: khung, màu, thời lượng ----------
def graphics(src: Path, events: list, dur: float, limit=40):
    fw, fh = 180, 320
    sc = W / fw
    out = []
    for e in events[:limit]:
        t = e["t"]
        fr = _rgb_frames(src, 10, fw, fh, max(0, t - 0.3), 4.5)
        if len(fr) < 8:
            continue
        before, after = fr[1].astype(np.int16), fr[min(len(fr) - 1, 8)].astype(np.int16)
        diff = np.abs(after - before).mean(-1)
        win = fr[6:min(len(fr), 13)].astype(np.float32).mean(-1)
        steady = win.std(0) < 7 if len(win) >= 3 else np.ones(diff.shape, bool)  # chữ/đồ họa đứng yên, nền thì động
        mask = (diff > 28) & steady
        # bỏ điểm lẻ: chỉ giữ ô 6x6 có đủ điểm
        blk = mask[: fh // 6 * 6, : fw // 6 * 6].reshape(fh // 6, 6, fw // 6, 6).mean((1, 3)) > 0.3
        mask = np.zeros_like(mask)
        mask[: fh // 6 * 6, : fw // 6 * 6] = np.repeat(np.repeat(blk, 6, 0), 6, 1)
        if mask.sum() < 30 or mask.mean() > 0.6:  # quá ít hoặc cả khung đổi (cắt cảnh)
            continue
        rows, cols = np.where(mask.mean(1) > 0.04)[0], np.where(mask.mean(0) > 0.04)[0]
        if not len(rows) or not len(cols):
            continue
        y0, y1, x0, x1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
        pal = _palette(after[y0:y1, x0:x1][mask[y0:y1, x0:x1]].reshape(-1, 3))
        # còn trên màn hình bao lâu: tới lúc vùng đó đổi khác hẳn so với lúc vừa hiện
        ref = after[y0:y1, x0:x1]
        stay = None
        for k in range(9, len(fr)):
            if np.abs(fr[k, y0:y1, x0:x1].astype(np.int16) - ref).mean() > 30:
                stay = round((k - 8) / 10, 1)
                break
        if stay is not None and stay < 0.4:  # đổi liên tục = người/cảnh đang chuyển động, không phải chữ/đồ họa chèn
            continue
        if mask[y0:y1, x0:x1].mean() < 0.12 and (x1 - x0) * (y1 - y0) > 0.5 * fw * fh:  # vùng rộng mà thưa = chuyển động rải rác
            continue
        box = [int(x0 * sc), int(y0 * sc), int((x1 - x0) * sc), int((y1 - y0) * sc)]
        out.append({"t": t, "khung": box, "tamY": round((box[1] + box[3] / 2) / H, 2), "rongTiLe": round(box[2] / W, 2),
                    "mau": [p[0] for p in pal], "tonTai_s": stay if stay is not None else ">4", "_mask": mask})
    return out


def graphics_summary(g: list) -> dict:
    if not g:
        return {}
    ys = [x["tamY"] for x in g]
    ws = [x["rongTiLe"] for x in g]
    stays = [x["tonTai_s"] for x in g if isinstance(x["tonTai_s"], float)]
    cols = {}
    for x in g:
        for c in x["mau"][:2]:
            cols[c] = cols.get(c, 0) + 1
    # gộp màu gần nhau
    merged = []
    for c, n in sorted(cols.items(), key=lambda kv: -kv[1]):
        v = np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)])
        for m in merged:
            if np.abs(m["v"] - v).sum() < 60:
                m["n"] += n
                break
        else:
            merged.append({"v": v, "c": c, "n": n})
    zone = lambda y: "trên" if y < 0.33 else "giữa" if y < 0.66 else "dưới"  # noqa: E731
    zc = {}
    for y in ys:
        zc[zone(y)] = zc.get(zone(y), 0) + 1
    return {"soLan": len(g), "viTriPhoBien": max(zc, key=zc.get), "theoVung": zc,
            "rongTB_tiLe": round(float(np.median(ws)), 2), "tonTaiTB_s": round(float(np.median(stays)), 1) if stays else None,
            "mauChu_va_DoHoa": [m["c"] for m in sorted(merged, key=lambda m: -m["n"])[:5]]}


# ---------- 1b. bố cục: chữ / icon / khung đặt ở đâu, căn thế nào, icon kiểu gì ----------
def _frame_at(src: Path, t: float, w=540, h=960):
    fr = _rgb_frames(src, 1, w, h, max(0.0, t), 0.9)
    return fr[0] if len(fr) else None


def _kind(b):
    x, y, w, h = b
    asp = w / max(1, h)
    if w * h > 0.22 * W * H:
        return "khung"
    if 0.55 <= asp <= 1.8 and w < 0.26 * W and h < 0.16 * H:
        return "icon"
    if asp >= 1.8:
        return "chu"
    return "khoi"


def _icon_info(crop: np.ndarray) -> dict:
    """crop RGB của 1 icon -> nhiều màu / đơn sắc, có nền tròn/vuông phía sau không"""
    px = crop.reshape(-1, 3).astype(np.float32)
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    colorful = sat > 0.35
    hues = []
    if colorful.sum() > 20:
        c = px[colorful]
        r, g, b = c[:, 0], c[:, 1], c[:, 2]
        hue = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) + 360) % 360
        hist = np.histogram(hue, bins=12, range=(0, 360))[0]
        hues = [i for i, n in enumerate(hist) if n > 0.12 * colorful.sum()]
    h, w = crop.shape[:2]
    ring = np.concatenate([crop[int(h * .18):int(h * .25)].reshape(-1, 3), crop[int(h * .75):int(h * .82)].reshape(-1, 3)]).astype(np.float32)
    edge = np.concatenate([crop[:max(1, h // 16)].reshape(-1, 3), crop[-max(1, h // 16):].reshape(-1, 3)]).astype(np.float32)
    badge = ring.std(0).mean() < 22 and np.abs(ring.mean(0) - edge.mean(0)).mean() > 35
    kieu = "emoji/nhiều màu" if len(hues) >= 3 else "1-2 màu" if hues else "đơn sắc (trắng/đen)"
    return {"kieu": kieu, "soTongMau": len(hues), "coNen": bool(badge), "mauChinh": [p[0] for p in _palette(px, 2)]}


def _sobel(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1] = g[2:] - g[:-2]
    return np.hypot(gx, gy)


def _blocks(m, b=6):
    h, w = m.shape[0] // b * b, m.shape[1] // b * b
    return m[:h, :w].reshape(h // b, b, w // b, b).mean((1, 3))


def _close_h(m):
    """lấp khe ngang 1 ô"""
    l = np.zeros_like(m); r = np.zeros_like(m)
    l[:, 1:] = m[:, :-1]
    r[:, :-1] = m[:, 1:]
    return m | (l & r)


def _label(m):
    """gán nhãn vùng liền (4 hướng) -> (lab, danh sách slice); không cần cài scipy"""
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    sls, n = [], 0
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]:
            continue
        n += 1
        st = [(y0, x0)]
        lab[y0, x0] = n
        ys, xs = [y0, y0], [x0, x0]
        while st:
            y, x = st.pop()
            ys[0], ys[1], xs[0], xs[1] = min(ys[0], y), max(ys[1], y), min(xs[0], x), max(xs[1], x)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    st.append((yy, xx))
        sls.append((slice(ys[0], ys[1] + 1), slice(xs[0], xs[1] + 1)))
    return lab, sls


def overlay_mask(src: Path, t: float, cuts=()):
    """vùng chữ/icon/đồ họa CHÈN hiện ra quanh lúc t: nét (cạnh sắc) xuất hiện ĐỨNG YÊN một chỗ sau lúc t mà trước đó
    không có. Nền động / người cử động thì nét không đứng yên; nền tĩnh thì nét có sẵn từ trước -> đều bị loại.
    Trả mask khối 6px trên lưới 180x320 (như graphics)."""
    t0 = max([0.0] + [c + 0.05 for c in cuts if c < t - 0.15])
    t1 = min([t + 1.8] + [c - 0.05 for c in cuts if c > t + 0.15])
    t0 = max(t0, t - 1.0)
    fr = _rgb_frames(src, 10, 360, 640, t0, t1 - t0)
    if len(fr) < 9:
        return None
    g = fr.astype(np.float32).mean(-1)
    Eall = np.stack([_sobel(f) > 45 for f in g])
    k0 = int(round((t - t0) * 10))
    # khung bắt đầu có đồ họa = lúc có nhiều nét MỚI xuất hiện rồi đứng yên nhất
    best, on = -1, None
    for k in range(max(3, k0 - 4), min(len(g) - 4, k0 + 5)):
        sc_ = (Eall[k:k + 4].all(0) & ~Eall[max(0, k - 3):k].any(0)).sum()
        if sc_ > best:
            best, on = sc_, k
    if on is None:
        return None
    pre, post = g[max(0, on - 8):max(0, on - 1)], g[on + 3:on + 13]
    if len(pre) < 3 or len(post) < 4:
        return None
    # nền đổi gần cả khung (đổi cảnh) -> không phải lúc chèn chữ
    chg = _blocks(np.abs(post.mean(0) - pre.mean(0)), 12) > 12
    if chg.mean() > 0.6:
        return None
    pp, pa = Eall[on + 3:on + 13].mean(0), Eall[max(0, on - 8):max(0, on - 1)].mean(0)
    m = (pp > 0.85) & (pa < 0.12)
    b = _blocks(m.astype(np.float32), 6) > 0.08  # ô 6px trên 360 (= 18px trên khung 1080)
    if b.mean() > 0.5:
        return None
    # từng cụm phải hiện RA NHANH (≤ 0.6s, kiểu chữ chèn bật ra) — máy dừng lia / người ngừng cử động thì nét hiện dần
    lab, sls = _label(_close_h(b))
    keep = np.zeros_like(b)
    Eb = np.stack([_blocks(e.astype(np.float32), 6) for e in Eall])
    for i, sl in enumerate(sls, 1):
        reg = (lab[sl] == i) & b[sl]
        r = Eb[:, sl[0], sl[1]][:, reg].mean(1)
        ys_, xs_ = sl
        if (ys_.stop - ys_.start) * (xs_.stop - xs_.start) < 4 or reg.sum() < 3:  # mảnh vụn
            continue
        sb = _sobel(g[min(len(g) - 1, on + 5)])[ys_.start * 6:ys_.stop * 6, xs_.start * 6:xs_.stop * 6]
        if np.percentile(sb, 98) < 180:  # chữ/icon chèn có nét rất sắc (viền, bóng, nền màu); cảnh thật mềm hơn
            continue
        lo_v, hi_v = r[max(0, on - 8):max(1, on - 1)].mean(), r[on + 3:on + 13].mean()
        if hi_v - lo_v < 0.08:
            continue
        nr = (r - lo_v) / (hi_v - lo_v)
        k10 = next((k for k in range(max(0, on - 4), len(nr)) if nr[k] > 0.15), None)
        k90 = next((k for k in range(k10 or 0, len(nr)) if nr[k] > 0.85), None) if k10 is not None else None
        if k10 is None or k90 is None or k90 - k10 > 6:
            continue
        keep[sl] |= reg
    if not keep.any():
        return None
    up = np.zeros_like(m)
    kk = np.repeat(np.repeat(keep, 6, 0), 6, 1)
    up[:kk.shape[0], :kk.shape[1]] = kk
    return keep, m & up


def static_mask(src: Path, dur: float):
    """chữ/logo/huy hiệu đứng yên SUỐT video trong khi nền đổi (tên series, tag góc...)"""
    fr = _rgb_frames(src, max(0.5, 24 / max(1.0, dur)), 180, 320, 0, min(dur, 180))
    if len(fr) < 8:
        return None
    g = fr.astype(np.float32).mean(-1)
    sd = _blocks(g.std(0))
    bg = _blocks(np.abs(np.diff(g, axis=0)).mean(0))
    edge = _blocks(np.median(np.stack([_sobel(x) for x in g[:: max(1, len(g) // 8)]]), 0))
    m = (sd < 6) & (edge > 16)
    if bg.mean() < 4 or m.mean() > 0.4:  # video gần như tĩnh -> không phân biệt được
        return None
    return m


def layout(src: Path, g: list, out: Path, events=None, dur=60.0, cuts=(), limit=40) -> dict:
    from PIL import Image, ImageDraw
    frames = []
    ts = sorted({round(e["t"], 1) for e in (events or [])} | {round(x["t"], 1) for x in g})[:limit]
    sm = static_mask(src, dur)

    def split_icon(px, box):
        """khối chữ có icon dính ở đầu/cuối: các cột của icon cao hơn hẳn chữ -> tách riêng. px = mask nét 360x640,
        box = (y0, y1, x0, x1) trên px. Trả danh sách box."""
        y0, y1, x0, x1 = box
        sub = px[y0:y1, x0:x1]
        if sub.shape[1] < 30 or not sub.any():
            return [box]
        ext = np.zeros(sub.shape[1])
        for c in range(sub.shape[1]):
            r = np.where(sub[:, c])[0]
            if len(r):
                ext[c] = r.max() - r.min() + 1
        # làm mượt: chiều cao lớn nhất trong cửa sổ 5 cột
        sm_ = np.array([ext[max(0, c - 3):c + 4].max() for c in range(len(ext))])
        med = np.median(sm_[sm_ > 0])
        tall = sm_ > 1.3 * med
        out, cut0, cut1 = [], 0, sub.shape[1]
        nz = np.where(sm_ > 0)[0]
        for side in (0, 1):
            cols = list(nz) if side == 0 else list(nz[::-1])
            lim = max(8, int(0.22 * len(cols)))
            st_ = next((i for i, c in enumerate(cols[:lim]) if tall[c]), None)  # icon bắt đầu gần mép
            if st_ is None:
                continue
            run = list(cols[:st_])
            for c in cols[st_:]:
                if tall[c]:
                    run.append(c)
                else:
                    break
            if len(run) >= 6:
                c0, c1 = min(run), max(run) + 1
                rows = np.where(sub[:, c0:c1].any(1))[0]
                h = rows.max() - rows.min() + 1
                if 0.5 <= (c1 - c0) / h <= 1.8 and (c1 - c0) < 0.45 * sub.shape[1]:
                    out.append((y0 + rows.min(), y0 + rows.max() + 1, x0 + c0, x0 + c1))
                    if side == 0:
                        cut0 = c1
                    else:
                        cut1 = c0
        if not out:  # icon nét mờ (không cao hơn chữ): đoạn đầu/cuối tách bởi khe ≥ 5 cột, gần vuông -> icon
            occ = ext > 0
            segs, c = [], 0
            while c < len(occ):
                if occ[c]:
                    e_ = c
                    gap = 0
                    while e_ < len(occ) and gap < 5:
                        gap = gap + 1 if not occ[e_] else 0
                        e_ += 1
                    segs.append((c, e_ - gap))
                    c = e_
                else:
                    c += 1
            if len(segs) >= 2:
                hs = []
                for a_, b_ in segs:
                    r = np.where(sub[:, a_:b_].any(1))[0]
                    hs.append((r.min(), r.max() + 1))
                med_h = np.median([h1 - h0 for h0, h1 in hs[1:-1] or hs])
                n_ = len(segs)
                cands = [(0, 0, 0), (0, 0, 1), (1, n_ - 1, n_ - 1), (1, n_ - 2, n_ - 1)]
                for side, i0, i1 in cands:
                    if i0 < 0 or i1 >= n_ or (i1 - i0 + 1) >= n_:
                        continue
                    a_, b_ = segs[i0][0], segs[i1][1]
                    h0, h1 = min(hs[i][0] for i in range(i0, i1 + 1)), max(hs[i][1] for i in range(i0, i1 + 1))
                    hh, ww = h1 - h0, b_ - a_
                    if 0.75 <= ww / max(1, hh) <= 1.6 and hh >= 0.85 * med_h and ww < 0.3 * sub.shape[1]:
                        out.append((y0 + h0, y0 + h1, x0 + a_, x0 + b_))
                        if side == 0:
                            cut0 = b_
                        else:
                            cut1 = a_
                        break
        if not out:
            return [box]
        rest = sub[:, cut0:cut1]
        rows, cols = np.where(rest)
        if len(rows):
            out.append((y0 + rows.min(), y0 + rows.max() + 1, x0 + cut0 + cols.min(), x0 + cut0 + cols.max() + 1))
        return out

    def comps(mb, t, fixed=False, px=None):
        lab, sls = _label(_close_h(mb))
        sc = W / mb.shape[1]
        res = []
        for sl0 in sls:
            ys, xs = sl0
            if px is not None:
                k = px.shape[1] / mb.shape[1]
                bb = (int(ys.start * k), int(ys.stop * k), int(xs.start * k), int(xs.stop * k))
                r_, c_ = np.where(px[bb[0]:bb[1], bb[2]:bb[3]])
                if len(r_):
                    bb = (bb[0] + r_.min(), bb[0] + r_.max() + 1, bb[2] + c_.min(), bb[2] + c_.max() + 1)
                parts, s2 = split_icon(px, bb), W / px.shape[1]
            else:
                parts, s2 = [(ys.start, ys.stop, xs.start, xs.stop)], sc
            for (a0, a1, b0, b1) in parts:
                bx = [int(b0 * s2), int(a0 * s2), int((b1 - b0) * s2), int((a1 - a0) * s2)]
                if bx[2] * bx[3] < 0.002 * W * H or (bx[2] < 0.04 * W and bx[3] < 0.04 * W):
                    continue
                fill = mb[sl0].mean()
                if fill < 0.25 and bx[2] * bx[3] > 0.05 * W * H:  # vùng rộng mà thưa = nhiễu chuyển động
                    continue
                res.append({"khung": bx, "loai": _kind(bx), **({"coDinh": True} if fixed else {})})
        return res
    fixed = comps(sm, 0, True) if sm is not None else []
    for t in ts:
        r_ = overlay_mask(src, t, cuts)
        if r_ is None:
            continue
        mb, px = r_
        def iou(a, b):
            ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
            return ix * iy / max(1, min(a[2] * a[3], b[2] * b[3]))
        boxes = [x for x in comps(mb, t, px=px) if not any(iou(x["khung"], f["khung"]) > 0.3 for f in fixed)]
        if frames and boxes and t - frames[-1]["t"] < 2.5 and len(boxes) == len(frames[-1]["khoi"]) and \
                all(any(iou(x["khung"], y["khung"]) > 0.7 for y in frames[-1]["khoi"]) for x in boxes):
            continue  # cùng một lần chèn, dò trùng ở 2 mốc gần nhau
        if boxes:
            frames.append({"t": t, "khoi": boxes})
    if not frames and not fixed:
        return {}
    if not frames:
        frames.append({"t": 0.5, "khoi": []})
    allb = [b for f in frames for b in f["khoi"]]
    def rows_of(f):
        """chữ + icon đứng cạnh = 1 hàng (để đo căn lề đúng như mắt thấy)"""
        tb = [list(b["khung"]) for b in f["khoi"] if b["loai"] in ("chu", "khoi")]
        for b in f["khoi"]:
            if b["loai"] != "icon":
                continue
            ic = b["khung"]
            for t in tb:
                vov = min(ic[1] + ic[3], t[1] + t[3]) - max(ic[1], t[1])
                gap = max(t[0] - (ic[0] + ic[2]), ic[0] - (t[0] + t[2]))
                if vov > 0.3 * min(ic[3], t[3]) and gap < 0.12 * W:
                    x0, y0 = min(t[0], ic[0]), min(t[1], ic[1])
                    x1, y1 = max(t[0] + t[2], ic[0] + ic[2]), max(t[1] + t[3], ic[1] + ic[3])
                    t[:] = [x0, y0, x1 - x0, y1 - y0]
                    break
        return tb
    texts = [t for f in frames for t in rows_of(f)] + [b["khung"] for b in fixed if b["loai"] in ("chu", "khoi")]
    # căn lề
    def al(b):
        x, y, w, h = b
        cx = (x + w / 2) / W
        if abs(cx - 0.5) < 0.07:
            return "giua"
        if x / W < 0.2 and cx < 0.5:
            return "trai"
        if (x + w) / W > 0.8 and cx > 0.5:
            return "phai"
        return "lech"
    alc = {}
    for b in texts:
        alc[al(b)] = alc.get(al(b), 0) + 1
    align = max(alc, key=alc.get) if alc else "giua"
    if align == "lech":
        align = max((k for k in alc if k != "lech"), key=alc.get, default="giua")
    side = [b for b in texts if al(b) == align]
    margin = int(np.median([b[0] if align != "phai" else W - b[0] - b[2] for b in side])) if side else 60
    zone = lambda b: "tren" if (b[1] + b[3] / 2) / H < 0.36 else "giua" if (b[1] + b[3] / 2) / H < 0.64 else "duoi"  # noqa: E731
    zc = {}
    for b in texts:
        zc[zone(b)] = zc.get(zone(b), 0) + 1
    # xếp chồng nhiều dòng/khối
    nfix = sum(1 for b in fixed if b["loai"] != "khung")
    per = [sum(1 for b in f["khoi"] if b["loai"] != "khung") + nfix for f in frames]
    gaps, stack = [], {"doc": 0, "ngang": 0}
    for f in frames:
        tb = sorted([b["khung"] for b in f["khoi"] if b["loai"] in ("chu", "khoi")], key=lambda b: b[1])
        for a, b in zip(tb, tb[1:]):
            ov = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
            if ov > 0.3 * min(a[2], b[2]):
                stack["doc"] += 1
                gaps.append(max(0, b[1] - a[1] - a[3]))
            else:
                stack["ngang"] += 1
    # icon cạnh chữ ở phía nào
    pos = {}
    icons = []
    for f in frames:
        tb = [b["khung"] for b in f["khoi"] if b["loai"] in ("chu", "khoi")]
        for b in f["khoi"]:
            if b["loai"] != "icon":
                continue
            ic = b["khung"]
            icons.append((f["t"], ic))
            best, bp = 1e9, "rieng"
            cx, cy = ic[0] + ic[2] / 2, ic[1] + ic[3] / 2
            for t in tb:
                vov = min(ic[1] + ic[3], t[1] + t[3]) - max(ic[1], t[1])
                hov = min(ic[0] + ic[2], t[0] + t[2]) - max(ic[0], t[0])
                if vov > 0.3 * ic[3]:
                    d = t[0] - (ic[0] + ic[2]) if cx < t[0] else ic[0] - (t[0] + t[2])
                    p = "trai" if cx < t[0] else "phai"
                elif hov > 0.3 * ic[2]:
                    d = t[1] - (ic[1] + ic[3]) if cy < t[1] else ic[1] - (t[1] + t[3])
                    p = "tren" if cy < t[1] else "duoi"
                else:
                    continue
                if -20 < d < 0.12 * W and d < best:
                    best, bp = d, p
            pos[bp] = pos.get(bp, 0) + 1
    res = {
        "canLe": align, "canLe_dem": alc, "leNgang_px": margin, "vungChu": max(zc, key=zc.get) if zc else None, "vungChu_dem": zc,
        "soKhoiMotLuc": {"tb": round(float(np.mean(per)), 1), "max": int(max(per))},
        "xepChong": stack, "khoangCachDong_px": int(np.median(gaps)) if gaps else None,
        "coChuTB_px": int(np.median([b[3] for b in texts])) if texts else None,
        "icon": {"soLan": len(icons), "viTriCanhChu": pos, "co_px": int(np.median([i[1][2] for i in icons])) if icons else None},
        "khungHinh": frames[:40], "coDinhSuotVideo": fixed,
        "doTinCay": "cao" if len(frames) >= 6 else "vua" if len(frames) >= 3 else "thap",
    }
    # ảnh: khung hình có vẽ ô (vàng = chữ, xanh lá = icon, xanh dương = khung/khối lớn)
    col = {"chu": (255, 214, 0), "khoi": (255, 140, 0), "icon": (40, 230, 120), "khung": (60, 140, 255)}
    pick = sorted(frames, key=lambda f: -len(f["khoi"]))[:6]
    pick.sort(key=lambda f: f["t"])
    tiles = []
    for f in pick:
        im = _frame_at(src, f["t"] + 0.5, 270, 480)
        if im is None:
            continue
        img = Image.fromarray(im)
        d = ImageDraw.Draw(img)
        k = 270 / W
        for b in f["khoi"] + fixed:
            x, y, w, h = [v * k for v in b["khung"]]
            d.rectangle([x, y, x + w, y + h], outline=col[b["loai"]], width=2)
        d.rectangle([0, 0, 70, 16], fill=(0, 0, 0))
        d.text((4, 2), f"{f['t']:.1f}s", fill=(255, 255, 255))
        tiles.append(img)
    if tiles:
        sheet = Image.new("RGB", (270 * min(3, len(tiles)), 480 * ((len(tiles) + 2) // 3)), (20, 20, 20))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % 3) * 270, (i // 3) * 480))
        sheet.save(out / "bo-cuc_khung.jpg", quality=86)
        res["anhKhung"] = "bo-cuc_khung.jpg (vàng = chữ, cam = khối chữ/hình, xanh lá = icon, xanh dương = khung lớn)"
    # bản đồ nhiệt: hay đặt chữ/icon ở đâu
    gw, gh = 54, 96
    heat = np.zeros((gh, gw), np.float32)
    iheat = np.zeros((gh, gw), np.float32)
    for f in frames:
        for b in f["khoi"]:
            x, y, w, h = b["khung"]
            tgt = iheat if b["loai"] == "icon" else heat
            tgt[int(y / H * gh):int((y + h) / H * gh) + 1, int(x / W * gw):int((x + w) / W * gw) + 1] += 1
    img = np.zeros((gh, gw, 3), np.float32) + 18
    if heat.max() > 0:
        img[..., 0] += heat / heat.max() * 230
        img[..., 1] += heat / heat.max() * 170
    if iheat.max() > 0:
        img[..., 1] += iheat / iheat.max() * 220
    hm = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((270, 480), Image.NEAREST)
    d = ImageDraw.Draw(hm)
    for yy in (160, 320):
        d.line([0, yy, 270, yy], fill=(90, 90, 90))
    for xx in (90, 180):
        d.line([xx, 0, xx, 480], fill=(60, 60, 60))
    hm.save(out / "bo-cuc.png")
    res["banDoNhiet"] = "bo-cuc.png (cam = chữ/khối hay nằm, xanh lá = icon hay nằm; vạch chia 3 phần)"
    # bảng icon cắt ra để xem kiểu icon họ chọn
    crops, infos = [], []
    seen = set()
    for t, ic in icons:
        key = (round(t), ic[0] // 60, ic[1] // 60)
        if key in seen:
            continue
        seen.add(key)
        im = _frame_at(src, t + 0.5)
        if im is None:
            continue
        k = 540 / W
        x, y, w, h = [int(v * k) for v in ic]
        side_ = int(min(w, h) * 1.25)  # ô vuông quanh tâm icon (khung dò hay dư ở 1 phía)
        cx, cy = x + w - min(w, h) // 2 if w > h else x + w // 2, y + h // 2
        c = im[max(0, cy - side_ // 2):cy + side_ // 2, max(0, cx - side_ // 2):cx + side_ // 2]
        if c.size == 0:
            continue
        infos.append({"t": t, **_icon_info(c)})
        crops.append(Image.fromarray(c).resize((128, 128)))
        if len(crops) >= 24:
            break
    if crops:
        sheet = Image.new("RGB", (6 * 136, ((len(crops) + 5) // 6) * 150), (30, 30, 30))
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(crops):
            ox, oy = (i % 6) * 136 + 4, (i // 6) * 150 + 4
            sheet.paste(c, (ox, oy))
            d.text((ox, oy + 130), f"{infos[i]['t']:.1f}s", fill=(200, 200, 200))
        sheet.save(out / "icon-mau.jpg", quality=88)
        kc = {}
        for i in infos:
            kc[i["kieu"]] = kc.get(i["kieu"], 0) + 1
        res["icon"].update({"kieu_dem": kc, "coNen_tiLe": round(sum(i["coNen"] for i in infos) / len(infos), 2),
                            "mau": list(dict.fromkeys(c for i in infos for c in i["mauChinh"]))[:6], "chiTiet": infos,
                            "anh": "icon-mau.jpg (icon cắt từ video mẫu — Claude NHÌN để biết họ dùng emoji, icon nét, icon đặc hay huy hiệu)"})
    return res


# ---------- 2. zoom trong cảnh ----------
def zooms(fr: np.ndarray, cut_times: list, fps=10):
    """zoom giật (punch) / đẩy vào chậm (push) / kéo ra (pull) trong cùng một cảnh"""
    if fr is None or len(fr) < 12:
        return []
    from style import _scale_err
    cutf = set()
    for c in cut_times:
        k = int(round(c * fps))
        cutf.update(range(k - 2, k + 3))
    out = []
    i = 0
    n = len(fr)
    while i < n - 6:
        if i in cutf or i + 1 in cutf:
            i += 1
            continue
        a, b = fr[i], fr[i + 1]
        e1 = _scale_err(a, b, 1.0)
        best = min(((k, _scale_err(a, b, k)) for k in (1.06, 1.1, 1.15, 1.2, 1.3)), key=lambda x: x[1])
        if best[1] < 0.6 * e1 and e1 > 6:
            out.append({"t": round((i + 1) / fps, 1), "kieu": "punch", "scale": best[0]})
            i += 5
            continue
        if i % 5 == 0 and not any(j in cutf for j in range(i, i + 11)) and i + 10 < n:  # chậm: so cách 1 giây
            a2, b2 = fr[i], fr[i + 10]
            e0 = _scale_err(a2, b2, 1.0)
            kin = min(((k, _scale_err(a2, b2, k)) for k in (1.04, 1.08, 1.12)), key=lambda x: x[1])
            kout = min(((k, _scale_err(b2, a2, k)) for k in (1.04, 1.08, 1.12)), key=lambda x: x[1])
            if kin[1] < 0.75 * e0 and kin[1] <= kout[1] and e0 > 4:
                out.append({"t": round(i / fps, 1), "kieu": "push", "scale": kin[0]})
                i += 10
                continue
            if kout[1] < 0.75 * e0 and e0 > 4:
                out.append({"t": round(i / fps, 1), "kieu": "pull", "scale": kout[0]})
                i += 10
                continue
        i += 1
    return out


# ---------- 3. màu video -> gợi ý chỉnh màu ----------
def color_grade(src: Path):
    fr = _rgb_frames(src, 1, 54, 96).astype(np.float32) / 255.0
    if not len(fr):
        return {}
    px = fr.reshape(-1, 3)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0.02, (mx - mn) / np.maximum(mx, 1e-3), 0)
    st = {"doSang": round(float(lum.mean()), 3), "tuongPhan": round(float(lum.std()), 3), "baoHoa": round(float(sat.mean()), 3),
          "am_lanh": round(float((r - b).mean()), 3), "vungToiNhat": round(float(np.percentile(lum, 2)), 3)}
    # quy về thông số chỉnh màu của tool (mốc: video điện thoại bình thường)
    color = {"brightness": int(np.clip(100 + (st["doSang"] - 0.45) * 60, 85, 118)),
             "contrast": int(np.clip(100 + (st["tuongPhan"] - 0.22) * 150, 85, 125)),
             "saturation": int(np.clip(100 + (st["baoHoa"] - 0.30) * 160, 60, 145)),
             "warmth": int(np.clip((st["am_lanh"] - 0.03) * 300, -40, 40))}
    if st["vungToiNhat"] > 0.10:
        color["fade"] = int(np.clip((st["vungToiNhat"] - 0.06) * 250, 0, 45))
    color = {k: v for k, v in color.items() if (k in ("brightness", "contrast", "saturation") and abs(v - 100) >= 3) or
             (k not in ("brightness", "contrast", "saturation") and abs(v) >= 4)}
    return {"thongSo": st, "goiYMau": color}


# ---------- 4. nhạc nền, BPM, cắt theo nhịp ----------
def music(x: np.ndarray, words: list, cut_times: list, sr=16000):
    if len(x) < sr * 4:
        return {}
    hop = 160
    e = np.sqrt((x[: len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1) + 1e-10)  # 10ms
    db = 20 * np.log10(e)
    talk = np.zeros(len(e), bool)
    for w in words:
        talk[int(w["start"] * 100):int(w["end"] * 100) + 1] = True
    gaps = db[~talk] if (~talk).sum() > 50 else db
    speech = db[talk] if talk.sum() > 50 else db
    floor, top = float(np.percentile(gaps, 50)), float(np.percentile(speech, 70))
    has = floor > -42 and (top - floor) < 24
    # BPM: tự tương quan của đường bao nhịp (onset) 60–180 BPM
    on = np.maximum(0, np.diff(db, prepend=db[0]))
    on = on - on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]
    lo, hi = int(100 * 60 / 180), int(100 * 60 / 60)
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = round(6000 / lag)
    strength = float(ac[lag] / (ac[0] + 1e-9))
    res = {"coNhacNen": bool(has), "nenLangDB": round(floor, 1), "chenhLechLoiNoi_vs_nen_dB": round(top - floor, 1)}
    if strength > 0.12:
        res.update(bpm=bpm, doRoNhip=round(strength, 2))
        # pha nhịp: dịch sao cho tổng onset trên các mốc nhịp lớn nhất
        period = lag
        best = max(range(period), key=lambda ph: on[ph::period].sum())
        beats = np.arange(best, len(on), period) / 100.0
        if cut_times:
            d = [float(np.min(np.abs(beats - c))) for c in cut_times]
            res["catTrungNhip_tiLe"] = round(sum(1 for v in d if v < 0.07) / len(d), 2)
        res["_beats"] = [round(float(b), 2) for b in beats[:400]]
    return res


# ---------- 5. hiệu ứng âm thanh: dò + phân loại ----------
def sfx_events(x: np.ndarray, words: list, moments: dict, sr=16000):
    """moments: {"cut": [t...], "chu": [t...], "zoom": [t...]} -> danh sách tiếng sfx + gắn với khoảnh khắc nào"""
    if len(x) < sr * 2:
        return [], {}
    n = 512
    hop = 160
    frames = len(x) // hop - n // hop
    if frames <= 0:
        return [], {}
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(np.stack([x[i * hop:i * hop + n] * win for i in range(frames)]), axis=1))  # (T, 257)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    hf = spec[:, freqs > 2000].sum(1)
    lf = spec[:, freqs < 200].sum(1)
    tot = spec.sum(1) + 1e-9
    flux = np.maximum(0, np.diff(np.log1p(hf), prepend=np.log1p(hf[0])))
    thr = np.percentile(flux, 98.5)
    talk = np.zeros(frames, bool)
    for w in words:
        talk[int(w["start"] * 100):int(w["end"] * 100) + 1] = True
    allm = [(t, k) for k, ts in moments.items() for t in ts]
    out = []
    i = 0
    while i < frames:
        if flux[i] > thr:
            t = i / 100
            near = min(allm, key=lambda m: abs(m[0] - t)) if allm else None
            gan = near[1] if near and abs(near[0] - t) < 0.25 else ""
            if talk[i] and not gan:  # trùng lời nói và không gắn với khoảnh khắc nào -> có thể chỉ là phụ âm
                i += 5
                continue
            seg = tot[i:i + 70]
            pk = seg.max()
            above = np.where(seg > pk * 0.2)[0]
            length = (above.max() + 1) / 100 if len(above) else 0.01
            sp = spec[i:i + max(3, int(length * 100))]
            flat = float(np.exp(np.log(sp + 1e-9).mean()) / (sp.mean() + 1e-9))  # phẳng = tiếng ồn, thấp = có cao độ
            lowr = float(lf[i:i + 20].sum() / tot[i:i + 20].sum())
            cen = (sp * freqs).sum(1) / (sp.sum(1) + 1e-9)
            rising = len(cen) > 20 and cen[-5:].mean() > cen[:5].mean() * 1.5
            if lowr > 0.45:
                loai = "impact" if length < 0.6 else "boom"
            elif length < 0.06:
                loai = "click"
            elif length > 0.5 and rising:
                loai = "riser"
            elif flat > 0.35 and length >= 0.15:
                loai = "whoosh"
            elif flat < 0.15 and length > 0.25:
                loai = "ding"
            else:
                loai = "pop"
            out.append({"t": round(t, 2), "loai": loai, "dai_s": round(length, 2), "gan": gan})
            i += max(15, int(length * 100))
            continue
        i += 1
    summ = {"tong": len(out), "theoLoai": {}, "theoKhoanhKhac": {}}
    for s in out:
        summ["theoLoai"][s["loai"]] = summ["theoLoai"].get(s["loai"], 0) + 1
    for k in moments:
        xs = [s["loai"] for s in out if s["gan"] == k]
        if xs:
            top = max(set(xs), key=xs.count)
            summ["theoKhoanhKhac"][k] = {"loaiHayDung": top, "soLan": len(xs), "tren": len(moments[k]),
                                         "tiLeCoSfx": round(len(xs) / max(1, len(moments[k])), 2)}
    return out, summ


SFX_MAP = {"whoosh": "whoosh", "click": "click", "pop": "pop", "impact": "impact", "boom": "boom", "riser": "riser", "ding": "ding"}


# ---------- 6. nhịp dựng ----------
def pacing(cut_times: list, dur: float, words: list, events: list, graphics_: list):
    edges = [0.0] + sorted(cut_times) + [dur]
    shots = [round(b - a, 2) for a, b in zip(edges, edges[1:]) if b - a > 0.05]
    gaps = [b["start"] - a["end"] for a, b in zip(words, words[1:]) if 0 <= b["start"] - a["end"] < 3]
    first_txt = min([e["t"] for e in events] or [None]) if events else None
    third = dur / 3
    dens = [round(sum(1 for e in events if k * third <= e["t"] < (k + 1) * third) / max(1, third) * 10, 1) for k in range(3)]
    return {"soCanh": len(shots), "doDaiCanh": {"tb": round(float(np.mean(shots)), 2) if shots else dur,
                                                 "ngan": min(shots) if shots else dur, "dai": max(shots) if shots else dur},
            "chuHinhDauTien_s": first_txt, "matDoChuHinh_moi10s_theo3Phan": dens,
            "khoangLangTB_ms": round(float(np.mean(gaps)) * 1000) if gaps else None,
            "catSatLoi": bool(gaps) and float(np.mean(gaps)) < 0.18,
            "hook": f"chữ/hình đầu tiên ở giây {first_txt}" if first_txt is not None else "không có chữ/hình đầu video"}


# ---------- 7. bản đồ nhịp dựng (ảnh) ----------
def timeline_png(path: Path, dur: float, trans: list, graphics_: list, zoom_: list, sfx_: list, words: list, beats: list, events: list):
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in ("arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(f, 15)
            break
        except Exception:
            continue
    font = font or ImageFont.load_default()
    Wd, L = 1800, 150
    rows = ["Lời nói", "Cắt / chuyển", "Chữ & đồ họa", "Zoom", "Âm thanh hiệu ứng", "Nhịp nhạc"]
    rh = 44
    Hd = 40 + rh * len(rows) + 40
    im = Image.new("RGB", (Wd, Hd), (18, 22, 32))
    d = ImageDraw.Draw(im)
    X = lambda t: L + (Wd - L - 20) * t / max(dur, 0.1)  # noqa: E731
    for k, r in enumerate(rows):
        y = 40 + k * rh
        d.rectangle([L, y + 6, Wd - 20, y + rh - 6], fill=(28, 34, 48))
        d.text((10, y + 13), r, fill=(200, 210, 230), font=font)
    for s in range(0, int(dur) + 1, 5 if dur > 30 else 1):
        x = X(s)
        d.line([x, 34, x, Hd - 34], fill=(45, 52, 70))
        d.text((x - 6, Hd - 30), f"{s}s", fill=(140, 150, 170), font=font)
    y = 40
    for w in words:
        d.rectangle([X(w["start"]), y + 14, max(X(w["start"]) + 1, X(w["end"])), y + rh - 14], fill=(90, 110, 140))
    tc = {"cut": (220, 220, 220), "zoom": (236, 72, 153), "fade": (96, 165, 250), "flash": (250, 204, 21), "whip": (14, 165, 233),
          "slide": (20, 184, 166), "up": (34, 197, 94), "zoomin": (219, 39, 119), "blur": (167, 139, 250)}
    y = 40 + rh
    for t in trans:
        x = X(t["t"])
        d.rectangle([x - 2, y + 8, x + 2, y + rh - 8], fill=tc.get(t["kieu"], (200, 200, 200)))
        d.text((x + 4, y + 10), t["kieu"], fill=tc.get(t["kieu"], (200, 200, 200)), font=font)
    y = 40 + rh * 2
    gl = {round(g["t"], 1): g for g in graphics_}
    for e in events:
        g = gl.get(round(e["t"], 1))
        st = g["tonTai_s"] if g and isinstance(g["tonTai_s"], float) else 1.0
        col = tuple(int(g["mau"][0][i:i + 2], 16) for i in (1, 3, 5)) if g and g["mau"] else (120, 200, 255)
        d.rectangle([X(e["t"]), y + 12, max(X(e["t"]) + 3, X(e["t"] + st)), y + rh - 12], fill=col, outline=(255, 255, 255))
    y = 40 + rh * 3
    for z in zoom_:
        x = X(z["t"])
        d.polygon([(x, y + rh - 10), (x - 6, y + 10), (x + 6, y + 10)], fill=(236, 72, 153))
        d.text((x + 6, y + 12), z["kieu"], fill=(236, 72, 153), font=font)
    sc = {"whoosh": (96, 165, 250), "pop": (250, 204, 21), "click": (163, 230, 53), "impact": (248, 113, 113), "boom": (239, 68, 68),
          "riser": (192, 132, 252), "ding": (45, 212, 191)}
    y = 40 + rh * 4
    for s in sfx_:
        x = X(s["t"])
        d.ellipse([x - 5, y + rh / 2 - 5, x + 5, y + rh / 2 + 5], fill=sc.get(s["loai"], (200, 200, 200)))
    lx = Wd - 600
    for k, (n, c) in enumerate(sc.items()):
        d.ellipse([lx + k * 82, 12, lx + k * 82 + 10, 22], fill=c)
        d.text((lx + k * 82 + 14, 8), n, fill=(200, 210, 230), font=font)
    y = 40 + rh * 5
    for b in beats or []:
        if b <= dur:
            x = X(b)
            d.line([x, y + 12, x, y + rh - 12], fill=(120, 130, 150))
    d.text((10, 8), "BẢN ĐỒ NHỊP DỰNG — video mẫu", fill=(255, 230, 120), font=font)
    im.save(path)


# ---------- báo cáo dễ đọc ----------
def report_md(r: dict) -> str:
    L = ["# Phân tích video mẫu (máy đo)\n"]
    p = r.get("nhip") or {}
    if p:
        md = p["matDoChuHinh_moi10s_theo3Phan"]
        L.append(f"**Nhịp dựng:** {p['soCanh']} cảnh, dài trung bình {p['doDaiCanh']['tb']}s (ngắn nhất {p['doDaiCanh']['ngan']}s, dài nhất {p['doDaiCanh']['dai']}s). "
                 f"{p['hook'].capitalize()}. Chữ/hình mỗi 10s: đầu {md[0]} · giữa {md[1]} · cuối {md[2]}. "
                 + (f"Khoảng lặng giữa các câu ~{p['khoangLangTB_ms']} ms" + (" (cắt sát lời)." if p.get('catSatLoi') else ".") if p.get('khoangLangTB_ms') is not None else ""))
    tr = r.get("chuyenCanhTongHop") or {}
    if tr:
        L.append("**Chuyển cảnh:** " + ", ".join(f"{k} ×{v}" for k, v in sorted(tr.items(), key=lambda kv: -kv[1])) + ".")
    g = r.get("doHoaTongHop") or {}
    if g:
        L.append(f"**Chữ & đồ họa:** {g['soLan']} lần, hay đặt ở vùng {g['viTriPhoBien']} ({', '.join(f'{k} {v}' for k, v in g['theoVung'].items())}), rộng ~{int(g['rongTB_tiLe'] * 100)}% khung, "
                 f"ở lại ~{g['tonTaiTB_s']}s. Màu chính: {', '.join(g['mauChu_va_DoHoa'])}.")
    b = r.get("boCuc") or {}
    if b:
        nm = {"giua": "giữa", "trai": "trái", "phai": "phải", "tren": "trên", "duoi": "dưới", "rieng": "đứng riêng"}
        s = (f"**Bố cục:** chữ căn {nm.get(b['canLe'], b['canLe'])}, lề ngang ~{b['leNgang_px']}px" + (f", hay nằm vùng {nm.get(b['vungChu'], b['vungChu'])}" if b.get('vungChu') else "") + "; "
             f"trung bình {b['soKhoiMotLuc']['tb']} khối cùng lúc (nhiều nhất {b['soKhoiMotLuc']['max']})")
        if b.get("khoangCachDong_px") is not None:
            s += f", xếp chồng dọc cách nhau ~{b['khoangCachDong_px']}px"
        ic = b.get("icon") or {}
        if ic.get("soLan"):
            vt = ic.get("viTriCanhChu") or {}
            s += f". Icon: {ic['soLan']} lần, cỡ ~{ic['co_px']}px" + (f", hay đặt {nm.get(max(vt, key=vt.get), '')} chữ" if vt else "")
            if ic.get("kieu_dem"):
                s += ", kiểu " + ", ".join(f"{k} ×{v}" for k, v in ic["kieu_dem"].items())
                if ic.get("coNen_tiLe", 0) >= 0.5:
                    s += ", thường có nền tròn/vuông phía sau"
        if b.get("doTinCay") == "thap":
            s += " (ít mẫu dò được — xem bo-cuc_khung.jpg và ảnh khung hình để chắc)"
        L.append(s + ".")
    z = r.get("zoom") or []
    if z:
        cnt = {}
        for x in z:
            cnt[x["kieu"]] = cnt.get(x["kieu"], 0) + 1
        L.append("**Zoom trong cảnh:** " + ", ".join(f"{ {'punch': 'zoom giật', 'push': 'đẩy vào chậm', 'pull': 'kéo ra'}[k]} ×{v}" for k, v in cnt.items()) + ".")
    m = r.get("mauVideo") or {}
    if m.get("goiYMau"):
        nm = {"brightness": "độ sáng", "contrast": "tương phản", "saturation": "bão hòa", "warmth": "ấm/lạnh", "fade": "nâng vùng tối"}
        gy = ", ".join(f"{nm.get(k, k)} {v}{'%' if k in ('brightness', 'contrast', 'saturation') else ''}" for k, v in m["goiYMau"].items())
        L.append(f"**Màu video:** gợi ý chỉnh màu — {gy}.")
    mu = r.get("nhac") or {}
    if mu:
        s = "**Nhạc nền:** " + ("có" if mu.get("coNhacNen") else "không rõ / không có")
        if mu.get("bpm"):
            s += f", ~{mu['bpm']} BPM"
            if mu.get("catTrungNhip_tiLe") is not None:
                s += f", {int(mu['catTrungNhip_tiLe'] * 100)}% điểm cắt trùng nhịp nhạc"
        L.append(s + ".")
    sf = r.get("sfxTongHop") or {}
    if sf.get("tong"):
        s = f"**Hiệu ứng âm thanh:** {sf['tong']} tiếng — " + ", ".join(f"{k} ×{v}" for k, v in sorted(sf["theoLoai"].items(), key=lambda kv: -kv[1]))
        tk = sf.get("theoKhoanhKhac") or {}
        name = {"cut": "chuyển cảnh", "chu": "chữ/hình hiện", "zoom": "zoom"}
        if tk:
            s += ". " + "; ".join(f"{name.get(k, k)}: hay dùng {v['loaiHayDung']} ({int(v['tiLeCoSfx'] * 100)}% có tiếng)" for k, v in tk.items())
        L.append(s + ".")
    L.append("\n*Số liệu do máy đo, có thể sai vài chỗ — Claude đối chiếu với ảnh khung hình khi rút phong cách.*")
    return "\n\n".join(L)


def deep(src: Path, dur: float, fr, trans: list, events: list, words: list, out: Path) -> dict:
    dur = min(dur, 180)
    cut_times = [t["t"] for t in trans]
    res = {}
    try:
        res["doHoa"] = graphics(src, events, dur)
        res["doHoaTongHop"] = graphics_summary(res["doHoa"])
    except Exception as e:  # noqa
        print("[!] đồ họa:", e)
    try:
        res["boCuc"] = layout(src, res.get("doHoa", []), out, events, dur, cut_times)
    except Exception as e:  # noqa
        print("[!] bố cục:", e)
    for x in res.get("doHoa", []):
        x.pop("_mask", None)
    try:
        res["zoom"] = zooms(fr, cut_times)
    except Exception as e:  # noqa
        print("[!] zoom:", e)
    try:
        res["mauVideo"] = color_grade(src)
    except Exception as e:  # noqa
        print("[!] màu:", e)
    x = None
    try:
        x = _audio(src)
        res["nhac"] = music(x, words, cut_times)
    except Exception as e:  # noqa
        print("[!] nhạc:", e)
    try:
        if x is not None:
            moments = {"cut": cut_times, "chu": [e["t"] for e in events], "zoom": [z["t"] for z in res.get("zoom", [])]}
            res["sfx"], res["sfxTongHop"] = sfx_events(x, words, moments)
    except Exception as e:  # noqa
        print("[!] sfx:", e)
    res["nhip"] = pacing(cut_times, dur, words, events, res.get("doHoa", []))
    try:
        timeline_png(out / "ban-do.png", dur, trans, res.get("doHoa", []), res.get("zoom", []), res.get("sfx", []), words,
                     (res.get("nhac") or {}).get("_beats"), events)
    except Exception as e:  # noqa
        print("[!] bản đồ:", e)
    return res
