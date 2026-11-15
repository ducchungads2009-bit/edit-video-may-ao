"""BỘ DỰNG NHANH — chỉ dựng (bằng Remotion) những khúc có chữ / khối / ảnh trám / zoom / chuyển cảnh;
phần còn lại ffmpeg lấy thẳng từ video gốc (giữ đúng cắt đoạn, phóng 108% của zoom cut, màu), phụ đề vẽ bằng Python
(phude_nhanh.py, giống hệt kiểu phụ đề của tool), tiếng lấy từ Remotion (chỉ dựng tiếng, không chụp hình) -> ghép 1 lần.

Máy yếu (2 nhân, Mac Intel...) nhanh hơn rõ rệt; video càng ít đồ hoạ càng nhanh. Không dùng được (kiểu phụ đề 'box',
khung người nói, logo thương hiệu, khung hình đặc biệt...) hoặc đồ hoạ chiếm gần hết video -> render.py dựng như cũ.
"""
import json
import math
import subprocess
import time
from pathlib import Path

FPS = 30
TR = 6           # khung mờ chồng ở điểm nối (giống EditPlan.tsx)
OVERLAP = {"fade", "whip", "slide", "up", "zoomin", "blur"}
PAD = 3          # khung đệm hai đầu khúc phức tạp
MERGE = 20       # khúc thường ngắn hơn ~0,7s kẹp giữa 2 khúc phức tạp -> dựng luôn bằng Remotion (đỡ vụn)
NO_VISUAL = {"audio", "sfx", "beauty"}


# ---------------------------------------------------------------- điểm nối (port từ EditPlan.tsx)
def _join_key(b, a):
    return f"{round(b * 100) / 100:g}>{round(a * 100) / 100:g}"


def join_type(segs, i, default, over, clips, style):
    b, a2 = segs[i][1], segs[i + 1][0]
    o = None
    if over:
        o = over.get(_join_key(b, a2))
        if not o:
            for k, v in over.items():
                try:
                    kb, ka = (float(x) for x in k.split(">"))
                except ValueError:
                    continue
                if abs(kb - b) < 0.011 and abs(ka - a2) < 0.011:
                    o = v
                    break
    want = o if o and o != "auto" else default
    if abs(a2 - b) < 0.05:
        return "cut"
    if want != "auto":
        return want

    def clip_of(t):
        for n, c in enumerate(clips or []):
            if c.get("start", 0) - 0.05 <= t < c.get("end", 0) + 0.05:
                return n
        return -1
    if (((style or {}).get("effects") or {}).get("zoomEase")) == "smooth":
        return "fade"
    c1, c2 = clip_of(b), clip_of(a2)
    return "zoom" if c1 >= 0 and c1 == c2 and abs(a2 - b) < 25 else "fade"


def seg_layout(props):
    """[(a, b, from, len, scale, type_sau)] theo khung xuất"""
    segs = props.get("segments")
    if not segs:
        return None
    d = props.get("transition") or "auto"
    types = [join_type(segs, i, d, props.get("joinFx"), props.get("clipBounds"), props.get("style")) for i in range(len(segs) - 1)]
    scales, out, acc = [], [], 0.0
    for i, (a, b) in enumerate(segs):
        scales.append((1.08 if scales[i - 1] == 1 else 1) if i and types[i - 1] == "zoom" else 1)
        fr = round(acc * FPS)
        acc += b - a
        to = round(acc * FPS)
        out.append((a, b, fr, max(1, to - fr), scales[i], types[i] if i < len(types) else None))
    return out


def _seg_identity(x):
    if not x:
        return True
    return (x.get("s", 1) in (1, None) and not x.get("dx") and not x.get("dy") and not x.get("rot") and not x.get("flip")
            and not any(x.get("crop") or []) and not x.get("round"))


# ---------------------------------------------------------------- màu (port CSS filter + ColorOverlay sang ffmpeg)
def color_filters(c, W, H, work: Path):
    """trả (chuỗi filter ffmpeg | '', [ảnh phủ thêm], lý do không làm được | None)"""
    if not c:
        return "", [], None
    if c.get("tint") and (c.get("tintAmount") or 0) > 0:
        return "", [], "màu phủ (tint)"
    b, k, s = (c.get("brightness") or 100) / 100, (c.get("contrast") or 100) / 100, (c.get("saturation") or 100) / 100
    h, sp = c.get("hue") or 0, (c.get("sepia") or 0) / 100
    f = []
    if abs(b - 1) > 1e-6 or abs(k - 1) > 1e-6:
        f.append(f"lutrgb=r='clip((val*{b:.6f}-128)*{k:.6f}+128,0,255)':g='clip((val*{b:.6f}-128)*{k:.6f}+128,0,255)'"
                 f":b='clip((val*{b:.6f}-128)*{k:.6f}+128,0,255)'")
    if abs(s - 1) > 1e-6:
        m = [0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s,
             0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s,
             0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s]
        f.append("colorchannelmixer=" + ":".join(f"{n}={v:.6f}" for n, v in zip(["rr", "rg", "rb", "gr", "gg", "gb", "br", "bg", "bb"], m)))
    if sp > 0:
        a = 1 - sp
        m = [0.393 + 0.607 * a, 0.769 - 0.769 * a, 0.189 - 0.189 * a,
             0.349 - 0.349 * a, 0.686 + 0.314 * a, 0.168 - 0.168 * a,
             0.272 - 0.272 * a, 0.534 - 0.534 * a, 0.131 + 0.869 * a]
        f.append("colorchannelmixer=" + ":".join(f"{n}={v:.6f}" for n, v in zip(["rr", "rg", "rb", "gr", "gg", "gb", "br", "bg", "bb"], m)))
    if h:
        r = math.radians(h)
        co, si = math.cos(r), math.sin(r)
        m = [0.213 + co * 0.787 - si * 0.213, 0.715 - co * 0.715 - si * 0.715, 0.072 - co * 0.072 + si * 0.928,
             0.213 - co * 0.213 + si * 0.143, 0.715 + co * 0.285 + si * 0.140, 0.072 - co * 0.072 - si * 0.283,
             0.213 - co * 0.213 - si * 0.787, 0.715 - co * 0.715 + si * 0.715, 0.072 + co * 0.928 + si * 0.072]
        f.append("colorchannelmixer=" + ":".join(f"{n}={v:.6f}" for n, v in zip(["rr", "rg", "rb", "gr", "gg", "gb", "br", "bg", "bb"], m)))
    # lớp phủ: fade (lighten rgb(70,70,78)), warmth (soft-light) — tính theo từng kênh -> bảng tra
    fd, w = c.get("fade") or 0, c.get("warmth") or 0
    if fd > 0:
        o = min(1, fd / 100) * 0.9
        cc = (70, 70, 78)
        f.append("lutrgb=" + ":".join(f"{ch}='val+(max(val,{v})-val)*{o:.4f}'" for ch, v in zip("rgb", cc)))
    if w:
        o = min(1, abs(w) / 100) * 0.7
        cc = (255, 150, 40) if w > 0 else (40, 130, 255)
        ex = []
        for ch, v in zip("rgb", cc):
            cs = v / 255
            # W3C soft-light: B=nền (val/255), S=lớp
            if cs <= 0.5:
                e = f"(val/255-(1-2*{cs:.5f})*(val/255)*(1-val/255))"
            else:
                e = (f"(val/255+(2*{cs:.5f}-1)*(if(lte(val/255,0.25),((16*val/255-12)*val/255+4)*val/255,sqrt(val/255))-val/255))")
            ex.append(f"{ch}='clip(255*((1-{o:.4f})*val/255+{o:.4f}*{e}),0,255)'")
        f.append("lutrgb=" + ":".join(ex))
    imgs = []
    v = c.get("vignette") or 0
    if v > 0:
        from PIL import Image
        import numpy as np
        a = min(1, v / 100) * 0.85
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # radial-gradient(ellipse at center ...) mặc định farthest-corner: bán kính elip = cạnh/2 * sqrt(2)
        rx, ry = W / 2 * math.sqrt(2), H / 2 * math.sqrt(2)
        d = np.sqrt(((xx - W / 2) / rx) ** 2 + ((yy - H / 2) / ry) ** 2)
        al = np.clip((d - 0.45) / 0.55, 0, 1) * a * 255
        im = np.zeros((H, W, 4), np.uint8)
        im[..., 3] = al.astype(np.uint8)
        p = work / "_nhanh_vignette.png"
        Image.fromarray(im, "RGBA").save(p)
        imgs.append(p)
    return ",".join(f), imgs, None


# ---------------------------------------------------------------- lập kế hoạch
def plan(props: dict, W: int, H: int):
    """-> (dict kế hoạch | None, lý do). Kế hoạch: N, pieces [(kind, f0, f1)], seglay"""
    import phude_nhanh
    st = props.get("style") or {}
    why = []
    if props.get("template") != "review":
        why.append("mẫu cũ")
    if props.get("captions") and not phude_nhanh.supported(props):
        why.append("kiểu phụ đề này")
    if st.get("presenter") or st.get("backdrop"):
        why.append("khung người nói / nền vẽ của phong cách")
    if props.get("mainXf") and not _seg_identity(props.get("mainXf")):
        why.append("khung hình video chính")
    for k, label in (("brandMark", "logo thương hiệu"), ("keepBand", "giữ dải chữ"), ("shots", "đổi cỡ cảnh tự động")):
        if props.get(k):
            why.append(label)
    if (props.get("mainFit") or "cover") != "cover":
        why.append("khung video khác tỉ lệ")
    if (st.get("frame") or {}) and (st.get("frame") or {}).get("type") not in (None, "none"):
        why.append("khung viền của phong cách")
    if why:
        return None, ", ".join(why)
    N = max(1, round(float(props.get("durationSec") or 0) * FPS))
    cx = bytearray(N)

    def mark(f0, f1):
        f0, f1 = max(0, int(f0)), min(N, int(f1))
        if f1 > f0:
            cx[f0:f1] = b"\x01" * (f1 - f0)
    for e in props.get("elements") or []:
        if not e or e.get("hidden") or e.get("type") in NO_VISUAL or float(e.get("end", 0)) <= float(e.get("start", 0)):
            continue
        mark(math.floor(float(e["start"]) * FPS) - PAD, math.ceil(float(e["end"]) * FPS) + PAD)
    lay = seg_layout(props)
    segxf = props.get("segXf") or {}
    segcurve = props.get("segCurve") or {}

    def seg_opt(m, a):
        for k, v in (m or {}).items():
            try:
                if abs(float(k) - a) < 0.011:
                    return v
            except ValueError:
                pass
        return None
    if lay:
        for (a, b, fr, ln, sc, nxt) in lay:
            if not _seg_identity(seg_opt(segxf, a)) or seg_opt(segcurve, a):
                mark(fr - PAD, fr + ln + PAD)
            if nxt in OVERLAP or nxt == "flash":
                mark(fr + ln - TR - PAD - (10 if nxt == "flash" else 0), fr + ln + TR + PAD + (10 if nxt == "flash" else 0))
    elif not _seg_identity(seg_opt(segxf, 0)):
        mark(0, N)
    cfx = props.get("cutFx") or "none"
    if "flash" in cfx or "bump" in cfx:
        for c in props.get("cuts") or []:
            t = c if isinstance(c, (int, float)) else (c.get("t") if isinstance(c, dict) else None)
            if t is not None:
                mark(t * FPS - 12, t * FPS + 14)
    # che mờ (biển số...): theo giây video gốc -> khung xuất
    blurs = [b for b in props.get("blurs") or [] if b and not b.get("off") and b.get("track")]
    if blurs:
        rngs = [(b["track"][0][0] - 0.3, b["track"][-1][0] + 0.3) for b in blurs]
        for f in range(N):
            t = src_time(lay, f)
            if t is not None and any(r0 <= t <= r1 for r0, r1 in rngs):
                cx[f] = 1
    # phần kéo dài quá cuối video chính (nhạc / khối dài hơn video -> đứng hình khung cuối): dựng bằng Remotion
    tf = props.get("tailFrom")
    if tf:
        mark(float(tf) * FPS - PAD, N)
    if lay:
        end_main = lay[-1][2] + lay[-1][3]
        if end_main < N:
            mark(end_main - PAD, N)
    # khúc thường quá ngắn kẹp giữa -> gộp vào phức tạp
    runs = _runs(cx)
    for kind, f0, f1 in runs:
        if kind == 0 and f1 - f0 < MERGE and f0 > 0 and f1 < N:
            cx[f0:f1] = b"\x01" * (f1 - f0)
    runs = _runs(cx)
    # khúc thường không được vắt qua điểm nối có chuyển cảnh chồng (đã đánh dấu) — điểm nối cut/zoom thì tách khúc tại đó
    pieces = []
    for kind, f0, f1 in runs:
        if kind == 1 or not lay:
            pieces.append(("R" if kind else "S", f0, f1))
            continue
        cuts = sorted({fr for (_, _, fr, _, _, _) in lay if f0 < fr < f1})
        edges = [f0, *cuts, f1]
        for x0, x1 in zip(edges, edges[1:]):
            pieces.append(("S", x0, x1))
    frac = sum(f1 - f0 for k, f0, f1 in pieces if k == "R") / N
    return {"N": N, "pieces": pieces, "lay": lay, "frac": frac}, None


def _runs(cx):
    out, n = [], len(cx)
    i = 0
    while i < n:
        j = i
        while j < n and cx[j] == cx[i]:
            j += 1
        out.append((cx[i], i, j))
        i = j
    return out


def src_time(lay, f):
    """khung xuất f -> giây trong video chính (theo đoạn giữ lại)"""
    if not lay:
        return f / FPS
    for (a, b, fr, ln, sc, nxt) in lay:
        if fr <= f < fr + ln:
            return (round(a * FPS) + (f - fr)) / FPS
    return None


def seg_of(lay, f):
    for item in lay or []:
        if item[2] <= f < item[2] + item[3]:
            return item
    return None


# ---------------------------------------------------------------- dựng
def run(folder: Path, props: dict, W: int, H: int, out: Path, remotion_fn, render_flags, scale_flags, tien=None, k=1.0):
    """dựng nhanh; trả True nếu xong (False = không dùng được, để render.py dựng như cũ)"""
    import phude_nhanh
    from hw import venc, encoder
    work = folder / "_work"
    P, why = plan(props, W, H)
    if not P:
        print(f"Dựng nhanh: không áp dụng ({why}) — dựng như thường.", flush=True)
        return False
    if P["frac"] > 0.75:
        print(f"Dựng nhanh: đồ hoạ chiếm {P['frac'] * 100:.0f}% video — dựng như thường.", flush=True)
        return False
    cf, cimgs, cwhy = color_filters(props.get("color"), W, H, work)
    if cwhy:
        print(f"Dựng nhanh: không áp dụng ({cwhy}) — dựng như thường.", flush=True)
        return False
    t0 = time.time()
    N, pieces, lay = P["N"], P["pieces"], P["lay"]
    ow, oh = int(round(W * k / 2) * 2), int(round(H * k / 2) * 2)
    print(f"Dựng nhanh: {sum(1 for p in pieces if p[0] == 'R')} khúc có đồ hoạ = {P['frac'] * 100:.0f}% video dựng bằng Remotion, "
          f"còn lại lấy thẳng video gốc.", flush=True)
    main_src = Path(props["_jobDir"]) / Path(props["videoSrc"]).name
    bundle = props.get("_bundle")
    steps = 4
    # phụ đề vẽ bằng Python — chạy song song (luồng riêng) trong lúc Remotion dựng khúc đồ hoạ
    cap_th, cap_res, cap_list = None, {}, None
    if props.get("captions"):
        import threading
        phude_nhanh.Cfg(props)  # chuẩn bị font trước (lỗi thì báo ngay)

        def _caps():
            t2 = time.time()
            try:
                cap_res["v"] = phude_nhanh.build(props, work / "_nhanh_cap", N, W)
                print(f"   phụ đề ({len({str(x[0]) for x in cap_res['v'][0]})} ảnh): {time.time() - t2:.0f}s", flush=True)
            except Exception as e:  # noqa
                cap_res["err"] = e
        cap_th = threading.Thread(target=_caps, daemon=True)
        cap_th.start()
    # 1) tiếng: Remotion chỉ dựng tiếng (không chụp khung)
    import os
    keep = os.environ.get("NHANH_GIU") == "1"  # (thử nghiệm) dùng lại tiếng / khúc đã dựng lần trước
    aud = work / "_nhanh_audio.wav"
    pfile = work / "props.json"
    if tien:
        tien.update(0.01, "Dựng tiếng")
    t1 = time.time()
    if not (keep and aud.exists()):
        aud.unlink(missing_ok=True)
        remotion_fn(["render", bundle, "audio", str(aud), f"--props={pfile}", "--codec=wav", "--log=error"], tien, (0.01, 0.06))
    print(f"   tiếng: {time.time() - t1:.0f}s", flush=True)
    # 2) khúc có đồ hoạ: 1 lần Remotion, phụ đề tắt (vẽ bằng Python ở bước 3)
    rr = [[f0, f1] for kind, f0, f1 in pieces if kind == "R"]
    part = work / "_nhanh_part.mp4"
    t1 = time.time()
    if not (keep and part.exists()):
        part.unlink(missing_ok=True)
    if rr and not part.exists():
        pp = dict(props)
        pp["captions"] = None
        pp["__ranges"] = rr
        if (pp.get("color") or {}).get("vignette"):
            pp["color"] = {**pp["color"], "vignette": 0}
        pf2 = work / "props_nhanh.json"
        pf2.write_text(json.dumps(pp, ensure_ascii=False), encoding="utf-8")
        remotion_fn(["render", bundle, "partial", str(part), f"--props={pf2}", "--muted", *render_flags, *scale_flags], tien, (0.06, 0.80))
        print(f"   khúc đồ hoạ ({sum(b - a for a, b in rr)} khung): {time.time() - t1:.0f}s", flush=True)
    # 3) phụ đề: vẽ song song lúc Remotion dựng khúc đồ hoạ (đã khởi động ở trên)
    if cap_th:
        if tien:
            tien.update(0.81, "Vẽ phụ đề")
        cap_th.join()
        if cap_res.get("err"):
            raise cap_res["err"]
        seq, band_top, band_h = cap_res["v"]
        cap_list = work / "_nhanh_cap.txt"
        phude_nhanh.write_concat(seq, cap_list)
    # 4) ghép
    if tien:
        tien.update(0.84, "Ghép video")
    inputs, chains, labels, vg_uses = [], [], [], []
    cum = 0
    base_vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,crop={W}:{H},setsar=1"
    for kind, f0, f1 in pieces:
        n = f1 - f0
        idx = len(inputs) // 4
        if kind == "R":
            ss = cum / FPS
            cum += n
            inputs += ["-ss", f"{max(0.0, ss - 0.25 / FPS):.6f}", "-i", str(part)]
            chains.append(f"[{idx}:v]fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,scale={W}:{H},setsar=1,format=yuv420p[p{idx}]")
        else:
            sg = seg_of(lay, f0) if lay else None
            sc = sg[4] if sg else 1
            ts = src_time(lay, f0)
            inputs += ["-ss", f"{max(0.0, ts - 0.25 / FPS):.6f}", "-i", str(main_src)]
            vf = [f"fps={FPS}", f"trim=end_frame={n}", "setpts=PTS-STARTPTS", base_vf]
            if abs(sc - 1) > 1e-6:  # zoom cut: phóng quanh 50% 38%
                cw, ch = W / sc, H / sc
                vf.append(f"crop={cw:.3f}:{ch:.3f}:{(W - cw) * 0.5:.3f}:{(H - ch) * 0.38:.3f},scale={W}:{H}:flags=bicubic,setsar=1")
            if cf:
                vf.append(cf)
            vf.append("format=yuv420p")
            chains.append(f"[{idx}:v]" + ",".join(vf) + f"[p{idx}]")
        labels.append(f"[p{idx}]")
    fc = chains + ["".join(labels) + f"concat=n={len(labels)}:v=1:a=0[base]"]
    cur = "base"
    nin = len(inputs) // 4
    if cimgs:  # vệt tối 4 góc (vignette): phủ cả video 1 lần (khúc Remotion đã dựng không có vignette)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(cimgs[0])]
        fc.append(f"[{nin}:v]format=rgba[vg]")
        fc.append(f"[{cur}][vg]overlay=0:0:shortest=1:format=auto[vvg]")
        cur = "vvg"
        nin += 1
    if cap_list:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(cap_list)]
        ci = nin
        nin += 1
        fc.append(f"[{ci}:v]fps={FPS},format=rgba[cap]")
        fc.append(f"[{cur}][cap]overlay=0:{band_top}:eof_action=pass:format=auto[vcap]")
        cur = "vcap"
    if abs(k - 1) > 1e-6:
        fc.append(f"[{cur}]scale={ow}:{oh}:flags=bicubic[vout]")
    else:
        fc.append(f"[{cur}]null[vout]")
    inputs += ["-i", str(aud)]
    ai = nin
    tmp = work / "_nhanh_out.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{ai}:a",
           *venc(), "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{N / FPS:.6f}", "-movflags", "+faststart", str(tmp)]
    t1 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"   ghép: {time.time() - t1:.0f}s", flush=True)
    if r.returncode and encoder() != "libx264":
        cmd2 = [x for x in cmd]
        v = venc()
        j = cmd2.index(v[0])
        cmd2[j:j + len(v)] = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", "30", "-pix_fmt", "yuv420p"]
        r = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not tmp.exists():
        print("[!] Dựng nhanh: ghép lỗi —", (r.stderr or "")[-1500:], flush=True)
        return False
    tmp.replace(out)
    if not keep:
        for p in (part, aud, work / "props_nhanh.json"):
            p.unlink(missing_ok=True)
    print(f"Dựng nhanh xong trong {time.time() - t0:.0f}s.", flush=True)
    return True
