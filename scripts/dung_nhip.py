"""DỰNG THEO NHỊP NHẠC — tự cắt cảnh sao cho mỗi lần đổi cảnh rơi đúng nhịp nhạc (trailer, đoạn mở đầu, video không lời).

  python scripts/dung_nhip.py "<folder>"                     # theo dung-nhip.json (hoặc cả video)
  python scripts/dung_nhip.py "<folder>" --tu 0 --den 12     # chỉ đoạn 0–12s của video xuất
      --mat-do auto|1|2|4      số nhịp mỗi cảnh (auto: đoạn nhạc mạnh cắt dày, đoạn nhẹ cắt thưa)
      --nguon video|tu-lieu|tat-ca   lấy cảnh từ video chính / tư liệu (assets) / cả hai (mặc định tat-ca)
      --hieu-ung khong|it|vua|nhieu  zoom giật / chớp ở nhịp mạnh (mặc định vua)
      --che-do tu-dong|canh|khoi     canh = cắt chính video chính (segments, chỉ khi cả video & không có lời nói);
                                     khoi = các khối video trám đè lên đoạn đó (giữ tiếng gốc / lời nói)
      --kieu auto|trailer|nang-dong|sang-trong|chia-khung|glitch|chill|mau:<bộ phong cách>   kiểu dựng nhịp (auto: chọn theo nhạc)
      --cam-giac em|vua|manh   ép cảm giác bài (mặc định tự nhận: êm = cắt theo câu nhạc + mờ chồng dài; mạnh = cắt theo phách)
      --phuong-an <số>         số phương án (giữ nguyên số = ra đúng kết quả cũ; bỏ trống = phương án mới mỗi lần)
      --xem                    chỉ in kế hoạch, không ghi plan.json
  python scripts/dung_nhip.py ds                             # danh sách kiểu dựng nhịp (có sẵn + học từ mẫu)
  python scripts/dung_nhip.py hoc "<folder có _mau>"          # học kiểu nhịp từ video mẫu -> _mau/phong-cach.json "beatStyle"

Ghi vào plan.json: beats (nếu chưa có), beatEdit {on, from, to, ...} (trong đoạn này không phát tiếng hiệu ứng),
các khối "beatCut": true (cảnh) và "beatFx": true (hiệu ứng) — chạy lại sẽ thay các khối cũ của đoạn đó.
Bản cũ lưu ở _work/plan_truoc_nhip.json.
"""
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nhip  # noqa: E402

VID = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
IMG = (".jpg", ".jpeg", ".png", ".webp")
AUD = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")


def rj(p: Path, d=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return d


def probe_dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def scene_cuts(p: Path, cache: Path) -> list:
    """điểm chuyển cảnh trong 1 file video (ffmpeg scene), có nhớ đệm"""
    c = rj(cache, {}) or {}
    key = f"{p.name}|{p.stat().st_size}|{int(p.stat().st_mtime)}"
    if key in c:
        return c[key]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-an", "-vf", "scale=160:-2,select='gt(scene,0.32)',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    cuts = sorted({round(float(m), 2) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)})
    c[key] = cuts
    try:
        cache.write_text(json.dumps(c), encoding="utf-8")
    except Exception:
        pass
    return cuts


def music_of(folder: Path, plan: dict, total: float, plan_only: bool = False):
    """nguồn nhạc nền -> (đường dẫn, from trong file, giây bắt đầu trên video xuất, giây kết thúc, rate)
    plan_only: chỉ tính nhạc đã nằm trong plan (không lấy nhac.* rời)"""
    m = plan.get("music") or {}
    if m.get("src") and (folder / m["src"]).is_file():
        return folder / m["src"], float(m.get("from") or 0), 0.0, total, float(m.get("rate") or 1)
    auds = [e for e in plan.get("elements") or [] if e and e.get("type") == "audio" and e.get("src") and (folder / e["src"]).is_file()]
    auds.sort(key=lambda e: (not e.get("bgm"), not e.get("loop"), -(e["end"] - e["start"])))
    if auds and auds[0]["end"] - auds[0]["start"] >= 4:
        e = auds[0]
        return folder / e["src"], float(e.get("from") or 0), float(e["start"]), float(e["end"]), float(e.get("rate") or 1)
    if plan_only:
        return None
    for p in sorted(folder.glob("nhac.*")):
        if p.suffix.lower() in AUD:
            return p, 0.0, 0.0, total, 1.0
    return None


def beats_for(folder: Path, plan: dict, total: float):
    """nhịp (giây video xuất) + độ mạnh từng nhịp (0–1) + tempo; đặc điểm bài ở beats_for.info {perc, rms}"""
    beats_for.info = {}
    mu = music_of(folder, plan, total)
    if not mu:
        return [], [], 0.0
    src, frm, st, en, rate = mu
    rate = max(0.1, rate)
    span = (min(en, total or en) - st) * rate
    tempo, bv = nhip.beats_on_video(str(src), frm, span)
    if not bv:
        return [], [], tempo
    y = nhip._audio(str(src))
    env = nhip.onset_env(y)
    fps = nhip.SR / nhip.HOP
    ylen = max(1.0, len(y) / nhip.SR)
    out, stren = [], []
    for b in bv:
        tf = (frm + b) % ylen
        i = int(tf * fps)
        w = env[max(0, i - 2): i + 3]
        out.append(round(st + b / rate, 2))
        stren.append(float(w.max()) if len(w) else 0.0)
    mx = max(stren) or 1
    # đặc điểm bài: độ "giật" (nhịp trống rõ hay êm), độ to từng nhịp (để tìm đoạn / cao trào)
    import numpy as np
    raw = np.array(stren)
    perc = float(np.median(raw) / (float(env.mean()) + 1e-6)) if len(raw) else 2.0
    rms, att, crest = [], [], []
    hop = int(0.01 * nhip.SR)
    for b in bv:
        i0 = int(((frm + b) % ylen) * nhip.SR)
        w = y[i0: i0 + int(0.35 * nhip.SR)]
        rms.append(float(np.sqrt((w ** 2).mean())) if len(w) else 0.0)
        # độ "gắt" của tiếng ở nhịp: thời gian lên đỉnh (trống: < 25ms, piano / pad: > 60ms) và đỉnh / nền
        z = y[max(0, i0 - int(0.06 * nhip.SR)): i0 + int(0.25 * nhip.SR)]
        if len(z) > hop * 8:
            r = np.sqrt(np.convolve(z ** 2, np.ones(hop) / hop, mode="valid")[::hop])
            pk = int(np.argmax(r))
            lo = int(np.argmin(r[: pk + 1])) if pk > 0 else 0
            att.append((pk - lo) * 10)
            crest.append(float(r.max() / (np.median(r) + 1e-6)))
    beats_for.info = {"perc": perc, "rms": rms, "att": float(np.median(att)) if att else 50.0, "crest": float(np.median(crest)) if crest else 2.0}
    return out, [x / mx for x in stren], tempo


def shot_pool(folder: Path, info: dict, nguon: str, work: Path):
    """các cảnh dùng được: {src, a, b, img, key}"""
    pool = []
    cache = work / "canh-nhip.json"
    if nguon in ("video", "tat-ca") and info.get("video") and (folder / info["video"]).is_file():
        v = folder / info["video"]
        d = float(info.get("durationSec") or probe_dur(v))
        cuts = [0.0] + [c for c in scene_cuts(v, cache) if 0.3 < c < d - 0.3] + [d]
        # cảnh quá dài (quay một mạch) -> chia nhỏ 4s để có nhiều góc khác nhau
        for a, b in zip(cuts, cuts[1:]):
            x = a
            while b - x > 0.7:
                y = min(b, x + 4.0)
                if b - y < 1.0:
                    y = b
                pool.append({"src": info["video"], "a": x, "b": y, "img": False, "key": f"v{a:.1f}"})
                x = y
    if nguon in ("tu-lieu", "tat-ca"):
        skip = {"_xu-ly", "giong-doc", "nhac", "sfx", "_pick"}
        for p in sorted((folder / "assets").rglob("*")) if (folder / "assets").exists() else []:
            if not p.is_file() or any(s in p.parts for s in skip) or p.name.startswith(("_", ".")):
                continue
            rel = p.relative_to(folder).as_posix()
            if p.suffix.lower() in IMG:
                pool.append({"src": rel, "a": 0.0, "b": 99.0, "img": True, "key": rel})
            elif p.suffix.lower() in VID:
                d = probe_dur(p)
                cuts = [0.0] + [c for c in scene_cuts(p, cache) if 0.3 < c < d - 0.3] + [d]
                for a, b in zip(cuts, cuts[1:]):
                    if b - a > 0.6:
                        pool.append({"src": rel, "a": a, "b": b, "img": False, "key": f"{rel}@{a:.1f}"})
    return pool


# ---------------------------------------------------------------- KIỂU DỰNG NHỊP
# ramp: số nhịp mỗi cảnh ở đầu / giữa / cuối đoạn (ở ~120 BPM) · trans: tỉ lệ kiểu chuyển giữa các cảnh
# kb: đẩy chậm vào cảnh · zoom: tỉ lệ nhịp mạnh có zoom giật · pulse: khung nảy theo nhịp (0–100) · flash: số lần chớp sáng
# strong: hiệu ứng ở nhịp mạnh (glitch | rgb | shake) + strongFrac · blackGap: giây màn đen chen giữa cảnh ở phần đầu
# bars: viền đen kiểu phim · overlay: lớp phủ (lightleak | grain | dust | filmburn) · frames: start (Khung nhịp mở đầu) |
# sections (Dải chéo ở chỗ chuyển đoạn) · color: chỉnh màu (chỉ áp khi dựng theo nhịp CẢ video) · endBlack: kết bằng màn đen
KIEU = {
    "trailer": {"ten": "Trailer điện ảnh", "moTa": "mở chậm có màn đen chen giữa, dồn dập về cao trào, viền phim, chớp trắng",
                "ramp": [4, 2, 1], "trans": {"cut": 0.75, "fade": 0.25}, "kb": True, "zoom": 0.12, "pulse": 0, "flash": 3,
                "blackGap": 0.18, "bars": True, "overlay": None, "endBlack": True, "color": {"contrast": 110, "saturation": 92, "fade": 8}},
    "nang-dong": {"ten": "Năng động TikTok", "moTa": "cắt mỗi nhịp, zoom giật + rung ở nhịp mạnh, lia nhanh",
                  "ramp": [1, 1, 1], "trans": {"cut": 0.55, "whip": 0.25, "zoom": 0.2}, "kb": False, "zoom": 0.35, "pulse": 45,
                  "flash": 1, "strong": "shake", "strongFrac": 0.12},
    "sang-trong": {"ten": "Sang trọng", "moTa": "2–4 nhịp mỗi cảnh, đẩy chậm vào cảnh, mờ chồng, ánh sáng loé, màu ấm",
                   "ramp": [4, 2, 2], "trans": {"fade": 0.6, "cut": 0.4}, "kb": True, "zoom": 0, "pulse": 0, "flash": 0,
                   "overlay": "lightleak", "color": {"warmth": 12, "contrast": 104, "saturation": 104}},
    "chia-khung": {"ten": "Chia khung montage", "moTa": "mở bằng Khung nhịp, Dải chéo ở chỗ chuyển đoạn, cắt gọn theo nhịp",
                   "ramp": [2, 2, 1], "trans": {"cut": 0.8, "slide": 0.2}, "kb": True, "zoom": 0.1, "pulse": 0, "flash": 1,
                   "frames": "start+sections"},
    "glitch": {"ten": "Glitch công nghệ", "moTa": "cắt cực nhanh ở đoạn mạnh, nhiễu hình / tách màu ở nhịp mạnh",
               "ramp": [2, 1, 1], "trans": {"cut": 0.85, "zoom": 0.15}, "kb": False, "zoom": 0.2, "pulse": 30, "flash": 2,
               "strong": "glitch", "strongFrac": 0.25, "color": {"contrast": 112, "saturation": 110}},
    "chill": {"ten": "Chill nhẹ nhàng", "moTa": "cắt thưa, mờ chồng mềm, hạt phim, màu nhạt",
              "ramp": [4, 4, 4], "trans": {"fade": 0.8, "cut": 0.2}, "kb": True, "zoom": 0, "pulse": 0, "flash": 0,
              "overlay": "grain", "color": {"saturation": 88, "fade": 14, "warmth": 6}},
}
TRANS_IN = {"cut": "cut", "fade": "fade", "whip": "whip", "zoom": "zoom", "slide": "slide", "up": "up", "flash": "cut", "blur": "fade", "zoomin": "zoom"}
TRANS_JOIN = {"cut": "cut", "fade": "fade", "whip": "whip", "zoom": "zoomin", "slide": "slide", "up": "up", "flash": "flash", "blur": "blur", "zoomin": "zoomin"}


def kieu_tu_mau():
    """các kiểu nhịp học từ video mẫu, lưu trong bộ phong cách (phong-cach/<bộ>/phong-cach.json "beatStyle")"""
    out = {}
    root = Path(__file__).resolve().parent.parent / "phong-cach"
    for f in sorted(root.glob("*/phong-cach.json")) if root.exists() else []:
        j = rj(f, {}) or {}
        bsy = (j.get("style") or {}).get("beat") or j.get("beatStyle")
        if isinstance(bsy, dict) and bsy.get("ramp"):  # chỉ kiểu HỌC từ mẫu (bộ "Nhịp · …" tạo sẵn trỏ tới kiểu có sẵn)
            out["mau:" + f.parent.name] = {**bsy, "ten": "Từ mẫu: " + (j.get("ten") or f.parent.name)}
    return out


def ds_kieu():
    return {**KIEU, **kieu_tu_mau()}


def hoc(pt: dict) -> dict:
    """phân tích video mẫu (phan-tich.json của style.py) -> kiểu dựng nhịp"""
    mu = pt.get("nhac") or {}
    bpm = float(mu.get("bpm") or 120)
    g = 60 / max(60, min(200, bpm))
    nh = pt.get("nhip") or {}
    tb = (nh.get("doDaiCanh") or {}).get("tb") or pt.get("doDaiCanhTrungBinh") or 1.0
    k = max(1, round(float(tb) / g))
    m3 = nh.get("matDoChuHinh_moi10s_theo3Phan") or []
    if isinstance(m3, list) and len(m3) == 3 and max(m3) > 0:  # phần nào dày chữ/hình hơn thì cắt dày hơn
        mx = max(m3)
        ramp = [max(1, round(k * (1.5 - 0.7 * x / mx))) for x in m3]
    else:
        ramp = [k, k, max(1, k - 1)]
    ramp = [round(r * 0.5 / g) or 1 for r in ramp]  # quy về ~120 BPM như các kiểu có sẵn
    tr = pt.get("chuyenCanhTongHop") or {}
    tot = sum(tr.values()) or 1
    trans = {kk: round(v / tot, 2) for kk, v in tr.items() if kk in TRANS_IN} or {"cut": 1.0}
    dur = max(1.0, float(pt.get("durationSec") or 30))
    zs = pt.get("zoom") or []
    zf = min(0.5, len(zs) / dur * 10 / 6)
    fl = pt.get("chopSang") or []
    out = {"moTa": f"học từ mẫu: cảnh ~{float(tb):.1f}s (~{k} nhịp ở {bpm:.0f} BPM), cắt trùng nhịp {int((mu.get('catTrungNhip_tiLe') or 0) * 100)}%",
           "ramp": ramp, "trans": trans, "kb": any(z.get("kieu") == "push" for z in zs), "zoom": round(zf, 2), "pulse": 0,
           "flash": min(4, len(fl)), "bpm": bpm}
    gm = (pt.get("mauVideo") or {}).get("goiYMau")
    if gm:
        out["color"] = gm
    return out


def kieu_du_an(folder: Path):
    """kiểu nhịp theo PHONG CÁCH dự án đã chọn (thành phần "Nhịp dựng" của bộ phong cách: style.beat)"""
    try:
        import phongcach  # noqa
        ps = phongcach.project_style(Path(folder)) or {}
        b = (ps.get("style") or {}).get("beat")
        if isinstance(b, dict):
            if b.get("preset") in KIEU:
                return b["preset"], KIEU[b["preset"]]
            if b.get("ramp"):
                src = (ps.get("nguon") or {}).get("nhip") or "mẫu"
                return "mau:" + str(src), {**b, "ten": "Từ phong cách: " + str(src)}
    except Exception:  # noqa
        pass
    return None


def chon_kieu(name: str, tempo: float, stren: list, rnd, feel: str = None, folder: Path = None) -> tuple:
    """kiểu theo tên; "auto" = theo phong cách dự án (nếu bộ có kiểu nhịp) rồi mới chọn theo nhạc (tempo, độ mạnh, cao trào)"""
    ks = ds_kieu()
    if name and name != "auto" and name in ks:
        return name, ks[name]
    if folder is not None:
        kd = kieu_du_an(folder)
        if kd:
            return kd
    n = len(stren)
    mean = sum(stren) / n if n else 0.5
    a3 = stren[: n // 3] or [mean]
    c3 = stren[-(n // 3):] or [mean]
    build = (sum(c3) / len(c3)) / max(0.05, sum(a3) / len(a3))
    if feel == "em" or (not feel and tempo and tempo < 95):
        cand = ["sang-trong", "chill"] + (["trailer"] if build > 1.3 else [])
    elif feel == "vua" or (not feel and tempo < 118):
        cand = ["sang-trong", "chia-khung"] + (["trailer"] if build > 1.3 else [])
    else:
        cand = ["nang-dong", "chia-khung"] + (["glitch"] if tempo > 128 else [])
        if build > 1.3:
            cand = ["trailer"] + cand
    k = cand[0] if rnd.random() < 0.6 else rnd.choice(cand)
    return k, ks[k]


def nhac_info(bs: list, stren: list, tempo: float, info: dict) -> dict:
    """CẢM GIÁC BÀI + CẤU TRÚC: feel em | vua | manh, phách mạnh (đầu ô nhịp), chỗ chuyển đoạn / cao trào (drop), độ to từng nhịp"""
    n = len(bs)
    perc = float(info.get("perc") or 2.0)
    rms = list(info.get("rms") or [])[:n]
    rms += [rms[-1] if rms else 0.1] * (n - len(rms))
    mr = max(rms) or 1
    en = [r / mr for r in rms]
    # phách mạnh: pha (0–3) có tổng độ mạnh lớn nhất -> nhịp 1 của mỗi ô 4/4
    ph = max(range(4), key=lambda k: sum(stren[i] for i in range(k, n, 4))) if n >= 8 else 0
    # độ to trung bình theo từng ô nhịp (4 phách), so 2 ô liền nhau -> chỗ chuyển đoạn; tăng mạnh -> cao trào (drop)
    bars = list(range(ph, n, 4))
    be = [sum(en[i:i + 4]) / max(1, len(en[i:i + 4])) for i in bars]
    sec, drop = set(), set()
    for j in range(2, len(bars)):
        prev = (be[j - 1] + be[j - 2]) / 2
        if prev <= 0:
            continue
        r = be[j] / prev
        if r > 1.45 or r < 0.62:
            sec.add(bars[j])
        if r > 1.7 and be[j] > 0.55:
            drop.add(bars[j])
    att = float(info.get("att") or 50.0)    # ms lên đỉnh ở nhịp
    crest = float(info.get("crest") or 2.0)  # đỉnh / nền quanh nhịp
    tp = tempo or 110
    if att >= 60 or crest < 1.5 or (tp < 92 and (att >= 35 or crest < 2.2)):
        feel = "em"
    elif att <= 30 and crest >= 2.4 and tp >= 105:
        feel = "manh"
    else:
        feel = "vua"
    return {"feel": feel, "perc": round(perc, 2), "att": round(att), "crest": round(crest, 2), "phase": ph, "sec": sec, "drop": drop, "en": en,
            "g": sorted(y - x for x, y in zip(bs, bs[1:]))[max(0, (n - 1) // 2)] if n > 1 else 0.5}


FEEL_NAME = {"em": "êm (ballad / piano / acoustic)", "vua": "vừa (pop / nhịp đều)", "manh": "mạnh (EDM / trống dồn)"}


def plan_cuts_nhac(bs: list, stren: list, A: float, B: float, mat: str, K: dict, M: dict, rnd) -> list:
    """LƯỚI CẮT THEO DÒNG NHẠC: nhạc êm cắt ở đầu ô nhịp / câu nhạc (2–4 ô), nhạc vừa cắt theo ô hoặc nửa ô,
    nhạc mạnh cắt theo phách — đoạn nhỏ cắt thưa, đoạn to cắt dày, cao trào cắt dồn; luôn cắt ở chỗ chuyển đoạn.
    Trả [(giây cắt, mức: 3 chuyển đoạn | 2 đầu ô | 1 nửa ô | 0 phách thường)]"""
    idx = [i for i, b in enumerate(bs) if A + 0.05 < b < B - 0.2]
    if not idx:
        return [(A, 3), (B, 3)]
    ph, sec, drop, en = M["phase"], M["sec"], M["drop"], M["en"]

    def lv(i):
        return 3 if i in sec or i in drop else 2 if (i - ph) % 4 == 0 else 1 if (i - ph) % 2 == 0 else 0
    ramp = K.get("ramp") or [2, 2, 1]
    sf = sum(ramp) / len(ramp) / 2  # kiểu dựng: >1 cắt thưa hơn, <1 dày hơn
    feel = M["feel"]

    def want(i):  # số phách mong muốn cho cảnh bắt đầu ở phách i
        e = en[i] if i < len(en) else 0.5
        if mat in ("1", "2", "4"):
            return int(mat)
        if feel == "em":
            L = 8 if e < 0.6 else 4
        elif feel == "vua":
            L = 4 if e < 0.45 else 2
        else:
            L = 2 if e < 0.4 else 1
        u = (bs[i] - A) / max(0.1, B - A)
        r = ramp[0] if u < 1 / 3 else ramp[1] if u < 2 / 3 else ramp[-1]
        L = L * (r / max(0.5, sum(ramp) / len(ramp))) * max(0.5, min(2.0, sf))
        if feel == "em":
            L = max(4, L)  # nhạc êm: tối thiểu 1 ô nhịp mỗi cảnh
        return max(1, int(round(L)))
    minlv = {"em": 2, "vua": 1, "manh": 0}[feel] if mat == "auto" else 0
    cuts = [(A, 3)]
    pos = {i: k for k, i in enumerate(idx)}
    k = 0
    cur = idx[0] - 1
    while True:
        L = want(max(0, cur))
        tgt = cur + L
        # chuyển đoạn / cao trào ở giữa cảnh hiện tại -> cắt ngay đó (nếu cảnh đã đủ 1 ô)
        forced = next((i for i in idx if cur + min(4, L) <= i < tgt and lv(i) == 3), None)
        if forced is not None:
            nxt = forced
        else:
            win = [i for i in idx if abs(i - tgt) <= (2 if feel == "em" else 1) and i > cur and lv(i) >= minlv]
            if not win:
                win = [i for i in idx if i >= tgt and lv(i) >= minlv][:1] or [i for i in idx if i >= tgt][:1]
            if not win:
                break
            nxt = max(win, key=lambda i: (lv(i), -abs(i - tgt), rnd.random() * 0.01))
        cuts.append((bs[nxt], lv(nxt)))
        cur = nxt
        if pos.get(nxt, len(idx)) >= len(idx) - 1:
            break
        k += 1
        if k > 4000:
            break
    out = [c for c in cuts if c[0] < B - 0.2]
    clean = [out[0]]
    for c in out[1:]:
        if c[0] - clean[-1][0] >= 0.22:
            clean.append(c)
    return clean + [(B, 3)]


def plan_cuts(bs: list, stren: list, A: float, B: float, mat: str, ramp=None, rnd=None):
    """các mốc cắt trên video xuất (bắt đầu A, kết thúc B, ở giữa rơi đúng nhịp).
    ramp = [số nhịp mỗi cảnh ở đầu, giữa, cuối đoạn] (theo kiểu dựng nhịp; tính ở ~120 BPM, tự quy theo tempo bài)."""
    idx = [i for i, b in enumerate(bs) if A + 0.05 < b < B - 0.2]
    if not idx:
        return [A, B]
    gaps = sorted(b - a for a, b in zip(bs, bs[1:])) or [0.5]
    g = gaps[len(gaps) // 2]
    k120 = 0.5 / max(0.2, g)  # nhịp nhanh hơn 120 BPM -> mỗi cảnh nhiều nhịp hơn (giữ thời lượng cảnh tương đương)
    ramp = ramp or [2, 2, 1]

    def base_at(t):
        u = (t - A) / max(0.1, B - A)
        r = ramp[0] if u < 1 / 3 else ramp[1] if u < 2 / 3 else ramp[-1]
        return max(1, round(r * k120))
    if mat in ("1", "2", "4"):
        base_at = (lambda m: (lambda t: m))(int(mat))  # noqa: E731
    q = sorted(stren[i] for i in idx)
    hi = q[int(len(q) * 0.7)] if q else 1
    lo = q[int(len(q) * 0.25)] if q else 0
    out = [A]
    k = max(0, base_at(A) - 1)  # cảnh đầu cũng dài đủ số nhịp (đầu đoạn A thường là 1 nhịp)
    while k < len(idx):
        i = idx[k]
        out.append(bs[i])
        base = base_at(bs[i])
        n = base
        if mat == "auto":
            s = sum(stren[j] for j in idx[k:k + base]) / max(1, len(idx[k:k + base]))
            n = max(1, base // 2) if s >= hi else base * 2 if s <= lo and base <= 2 else base
            if rnd and n > 1 and rnd.random() < 0.15:  # thỉnh thoảng đổi nhịp cho đỡ đều
                n += rnd.choice((-1, 1))
        k += max(1, n)
    out = [x for x in out if x < B - 0.2]
    clean = [out[0]]
    for x in out[1:]:
        if x - clean[-1] >= 0.22:
            clean.append(x)
    return clean + [B]


def assign(cuts: list, pool: list, seed: int = 7):
    """ghép cảnh vào từng ô thời gian: luân phiên nguồn, không lặp cảnh liền nhau, lấy phần giữa cảnh"""
    rnd = random.Random(seed)
    used = {}
    shots = []
    last_key = None
    order = pool[:]
    rnd.shuffle(order)
    for a, b in zip(cuts, cuts[1:]):
        L = b - a
        cand = [s for s in order if s["key"] != last_key and (s["img"] or (s["b"] - s["a"]) - used.get(id(s), 0) >= L + 0.2)]
        if not cand:
            cand = [s for s in order if s["key"] != last_key] or order
        cand.sort(key=lambda s: (used.get(("n", id(s)), 0), -((s["b"] - s["a"]) - used.get(id(s), 0))))
        s = cand[0]
        if s["img"]:
            frm = 0.0
        else:
            room = (s["b"] - s["a"]) - L
            u = used.get(id(s), 0)
            frm = s["a"] + (min(room, max(0.15, room * 0.35)) if u == 0 else min(room, u)) if room > 0 else s["a"]
            used[id(s)] = (frm - s["a"]) + L + 0.1
        used[("n", id(s))] = used.get(("n", id(s)), 0) + 1
        shots.append({"start": round(a, 2), "end": round(b, 2), "src": s["src"], "from": round(max(0.0, frm), 2), "img": s["img"]})
        last_key = s["key"]
        order.append(order.pop(order.index(s)))  # cảnh vừa dùng xuống cuối hàng
    return shots


def build(folder: Path, plan: dict, opts: dict = None):
    """tính lại plan dựng theo nhịp (không ghi file). opts: tu, den, mat_do, nguon, hieu_ung, che_do.
    Trả (plan mới, các dòng báo cáo)."""
    import copy
    opts = opts or {}
    folder = Path(folder)
    plan = copy.deepcopy(plan) if plan else {"template": "review", "captions": False, "elements": []}
    plan.setdefault("elements", [])
    work = folder / "_work"
    info = rj(work / "info.json", {}) or {}
    cfg = rj(folder / "dung-nhip.json", {}) or {}
    pbe = plan.get("beatEdit") or {}
    if pbe.get("mode") == "canh" or pbe.get("baseSeg"):  # lần trước đã cắt video chính theo nhịp -> bỏ để cắt lại từ đầu
        for k in ("segments", "joinFx", "transition"):
            plan.pop(k, None)
    segs = plan.get("segments")
    total = sum(b - a for a, b in segs) if segs else float(info.get("durationSec") or 0)
    A0 = float(opts.get("tu", cfg.get("from", 0)) or 0)
    # nhạc đã chọn (dung-nhip.json "music" / nhac.*) mà plan chưa có -> thêm khối nhạc nền (bắt buộc có nhạc để dựng theo nhịp)
    if not music_of(folder, plan, total, plan_only=True):
        cand = cfg.get("music") if cfg.get("music") and (folder / cfg["music"]).is_file() else None
        if not cand:
            cand = next((p.name for p in sorted(folder.glob("nhac.*")) if p.suffix.lower() in AUD), None)
        if cand:
            md = probe_dur(folder / cand)
            words0 = rj(work / "words.json", []) or []
            talk0 = bool(words0) and plan.get("videoVolume", 1) > 0 and info.get("mode") != "voice"
            intro = cfg.get("range") == "intro" and opts.get("den") is None
            end = A0 + md
            if intro:
                end = min(end, A0 + float(cfg.get("introSec") or 10) + 1.5)
            elif total and not (cfg.get("range") == "all" and not talk0):
                end = min(end, total)
            plan["elements"].append({"type": "audio", "src": cand, "start": round(A0, 2), "end": round(end, 2), "bgm": True,
                                     "volume": 0.25 if talk0 and not intro else 0.85, "fadeIn": 0.2, "fadeOut": 1.5})
    mu = music_of(folder, plan, total)
    if mu and mu[3] > total and not segs:
        total = max(total, mu[3])
    A = A0
    if opts.get("den") is None and cfg.get("range") == "intro":
        B = A + float(cfg.get("introSec") or 10)
    else:
        B = float(opts.get("den") if opts.get("den") is not None else (cfg.get("to") or total) or total)
    B = min(B, total) if total else B
    if mu:  # không dựng quá chỗ hết nhạc
        B = min(B, mu[3])
    mat = str(opts.get("mat_do") or cfg.get("density", "auto"))
    nguon = opts.get("nguon") or cfg.get("source", "tat-ca")
    hu = opts.get("hieu_ung") or cfg.get("fx", "vua")
    mode = opts.get("che_do") or cfg.get("mode", "tu-dong")
    rep = []

    bs, stren, tempo = beats_for(folder, plan, total)
    minfo = dict(getattr(beats_for, "info", {}) or {})
    if not bs:
        bs = plan.get("beats") or []
        stren = [0.5] * len(bs)
    if not bs:
        raise RuntimeError("Chưa có nhạc nền — dựng theo nhịp BẮT BUỘC chọn nhạc trước (ô 🎵 Dựng theo nhịp nhạc: tìm nhạc / tải nhạc lên; hoặc thêm khối nhạc trong trình chỉnh sửa).")
    pool = shot_pool(folder, info, nguon, work)
    if not pool:
        raise RuntimeError("Không có cảnh nào để dựng (video chính / tư liệu trong assets/).")
    # nhịp thưa / hết ở cuối đoạn: nối thêm nhịp theo chu kỳ trung bình
    gaps = sorted(y - x for x, y in zip(bs, bs[1:])) or [0.5]
    g = gaps[len(gaps) // 2]
    while bs and bs[-1] + g < B:
        bs.append(round(bs[-1] + g, 2))
        stren.append(0.3)
    seed = int(opts.get("seed") or random.randrange(1, 10 ** 6))
    rnd = random.Random(seed)
    M = nhac_info(bs, stren, tempo, minfo)  # cảm giác bài (êm / vừa / mạnh) + phách mạnh + chỗ chuyển đoạn / cao trào
    feel = opts.get("cam_giac") or cfg.get("feel") or M["feel"]
    M["feel"] = feel if feel in FEEL_NAME else M["feel"]
    feel = M["feel"]
    kname, K = chon_kieu(opts.get("kieu") or cfg.get("style") or "auto", tempo, stren, rnd, feel, folder)
    mul = {"khong": 0, "it": 0.6, "vua": 1.0, "nhieu": 1.5}.get(hu, 1.0)  # mức hiệu ứng nhân với độ "đậm" của kiểu
    fxk = {"em": 0.0, "vua": 0.5, "manh": 1.0}[feel]  # nhạc êm: không zoom giật / rung / chớp — chỉ chuyển mềm
    cutsL = plan_cuts_nhac(bs, stren, A, B, mat, K, M, rnd)
    cuts = [c for c, _ in cutsL]
    clv = {round(c, 2): lv for c, lv in cutsL}
    g = M["g"]
    soft = round(min(1.4, max(0.5, 1.6 * g)), 2) if feel == "em" else round(min(0.7, max(0.3, 0.9 * g)), 2)  # thời lượng mờ chồng
    shots = assign(cuts, pool, seed)
    words = rj(work / "words.json", []) or []
    talk = any(A - 0.1 <= (w.get("start", 0) if isinstance(w, dict) else 0) <= B for w in words) and plan.get("videoVolume", 1) > 0 and info.get("mode") != "voice"
    whole = A <= 0.05 and B >= min(total, mu[3] if mu else total) - 0.3  # cả video (hoặc tới hết nhạc)
    only_main = all(s["src"] == info.get("video") for s in shots)
    base_seg = False
    if mode == "tu-dong":
        mode = "canh" if whole and only_main and not talk and not segs else "khoi"
        if mode == "canh" and (feel == "em" or "fade" in (K.get("trans") or {})):
            # cần mờ chồng dài -> dùng khối trám (chuyển mềm được), video chính chỉ làm nền, cắt cho vừa bài nhạc
            mode, base_seg = "khoi", True
            plan["segments"] = [[0.0, round(min(float(info.get("durationSec") or B), B - A + 0.0), 2)]]
            plan["videoVolume"] = 0
    rep.append(f"Kiểu: {K['ten']} · nhạc {FEEL_NAME[feel]} · {len(bs)} nhịp ({tempo:.0f} BPM) · đoạn {A:.2f}–{B:.2f}s · {len(shots)} cảnh · "
               f"{'cắt video chính' if mode == 'canh' else 'khối trám'} · phương án #{seed}")
    rep.append({"em": f"Cắt ở đầu ô nhịp / câu nhạc, mờ chồng {soft}s, không hiệu ứng giật", "vua": "Cắt theo ô / nửa ô nhịp, mờ chồng ở chỗ chuyển đoạn",
                "manh": "Cắt theo phách, dồn ở cao trào, hiệu ứng ở nhịp mạnh"}[feel] + (f" · {len(M['sec'])} chỗ chuyển đoạn, {len(M['drop'])} cao trào" if M["sec"] else ""))
    for s in shots:
        rep.append(f"  [{s['start']:6.2f}–{s['end']:6.2f}] {s['src']}" + ("" if s["img"] else f" từ {s['from']:.2f}s"))
    plan["elements"] = [e for e in plan["elements"] if not (e and (e.get("beatCut") or e.get("beatFx")) and e["start"] < B - 0.01 and e["end"] > A + 0.01)]
    tw = K.get("trans") or {"cut": 1}

    def pick_tr():
        r, acc = rnd.random() * sum(tw.values()), 0.0
        for kk, v in tw.items():
            acc += v
            if r <= acc:
                return kk
        return "cut"
    # Khung nhịp ở đầu đoạn (kiểu chia khung): chiếm 6–8 nhịp đầu, các cảnh sau lùi lại
    els = plan["elements"]
    fr_end = A
    if "start" in str(K.get("frames") or "") and len(shots) >= 3:
        nb = [b for b in bs if b >= A - 0.01]
        vids = [x for x in pool if not x["img"]]
        try:
            import khung as _kh
            fmt = _kh.get(folder)
        except Exception:  # noqa
            fmt = "9:16"
        npn = {"16:9": 5, "1:1": 4, "4:5": 4}.get(fmt, 3)  # số khung theo khung hình (giống Beat.tsx tự bố cục)
        every = 2 if feel == "em" else 1
        need = npn * every + (3 if feel == "em" else 2)  # khung hiện lần lượt + giữ / thu ô + bung
        if len(nb) > need and vids:
            fr_end = min(B - 1.0, nb[need] + 0.05)
            pk = [vids[(seed + j * 3) % len(vids)] for j in range(npn)]
            els.append({"type": "beatFrames", "start": round(A, 2), "end": round(fr_end, 2), "srcs": [x["src"] for x in pk],
                        "froms": [round(x["a"] + 0.2, 2) for x in pk], "collapse": feel != "em", "exit": "expand", "beatCut": True,
                        **({"soft": True, "every": 2} if feel == "em" else {"soft": True} if feel == "vua" else {})})
            if mode == "khoi":  # khối trám: bỏ cảnh nằm dưới Khung nhịp; cắt video chính thì giữ (mốc phía sau không lệch)
                shots = [sh for sh in shots if sh["end"] > fr_end + 0.25]
                if shots:
                    shots[0]["start"] = round(fr_end, 2)
    if mode == "canh":
        plan["segments"] = [[s["from"], round(s["from"] + (s["end"] - s["start"]), 2)] for s in shots]
        plan["transition"] = "cut"
        jf = {}
        for s1, s2 in zip(plan["segments"], plan["segments"][1:]):
            t = TRANS_JOIN.get(pick_tr(), "cut")
            if t != "cut":
                jf[f"{round(s1[1], 2)}>{round(s2[0], 2)}"] = t
        if jf:
            plan["joinFx"] = jf
        plan["videoVolume"] = 0 if not talk else plan.get("videoVolume", 1)
    else:
        prev = None
        for s in shots:
            lv = clv.get(round(s["start"], 2), 0)
            if prev is None:
                t = "fade" if (K.get("blackGap") or feel == "em") else "cut"
            elif feel == "em":
                t = "fade" if lv < 3 or rnd.random() < 0.7 else "blur"  # nhạc êm: luôn mờ chồng, chỗ chuyển đoạn đôi khi nhòe chồng
            else:
                t = TRANS_IN.get(pick_tr(), "cut")
                if feel == "vua" and lv >= 3 and t == "cut":
                    t = "fade"  # chuyển đoạn của bài: chuyển mềm
                if feel == "vua" and t in ("whip", "zoom") and lv < 2:
                    t = "cut"  # hiệu ứng mạnh chỉ ở đầu ô nhịp
            el = {"type": "broll", "start": s["start"], "end": s["end"], "src": s["src"], "transition": t, "exit": "cut", "volume": 0, "beatCut": True}
            if t in ("fade", "blur"):
                el["inDur"] = soft if (feel == "em" or lv >= 3) else min(soft, 0.4)
            if not s["img"]:
                el["from"] = s["from"]
            el["kb"] = True if feel == "em" else (bool(K.get("kb")) if not s["img"] else True)
            if prev is not None and t != "cut":  # cảnh trước kéo dài thêm cho lúc chuyển không lộ video chính bên dưới
                prev["end"] = round(min(s["end"], s["start"] + el.get("inDur", 0.3) + 0.05), 2)
            els.append(el)
            prev = el
    strong = sorted([(stren[i], b) for i, b in enumerate(bs) if A + 0.3 < b < B - 0.3], reverse=True)
    if feel != "manh" and M["drop"]:  # nhạc vừa: chỉ nhấn ở cao trào thật
        dset = {round(bs[i], 2) for i in M["drop"]}
        strong = [x for x in strong if round(x[1], 2) in dset] + [x for x in strong if round(x[1], 2) not in dset]
    mul = mul * fxk if feel != "manh" else mul
    if mul:
        # zoom giật ở nhịp mạnh (chỉ khi cắt video chính — khối trám đè lên thì zoom video chính không thấy)
        zf = (K.get("zoom") or 0) * mul
        if mode == "canh" and zf > 0:
            lastp = -9
            for b in sorted(b for _, b in strong[: max(1, int(len(strong) * zf))]):
                if b - lastp >= 0.9:
                    lastp = b
                    els.append({"type": "zoom", "style": "punch", "scale": 1.12, "start": round(b, 2), "end": round(b + 0.35, 2), "beatFx": True})
        pl = (K.get("pulse") or 0) * mul if mode == "khoi" else 0
        if mode == "khoi" and not pl and zf > 0:
            pl = 25 * mul  # khối trám: thay zoom bằng khung nảy nhẹ theo nhịp
        if pl:
            els.append({"type": "fx", "style": "beat", "amount": int(min(80, pl)), "start": round(A, 2), "end": round(B, 2), "beatFx": True})
        if K.get("strong"):
            sf = (K.get("strongFrac") or 0.15) * mul
            lastp = -9
            for b in sorted(b for _, b in strong[: max(1, int(len(strong) * sf))]):
                if b - lastp >= 1.2:
                    lastp = b
                    els.append({"type": "fx", "style": K["strong"], "amount": 55, "start": round(b, 2), "end": round(b + 0.28, 2), "beatFx": True})
        nf = int(round((K.get("flash") or 0) * mul))
        for b in sorted(b for _, b in strong[:nf]):
            els.append({"type": "fx", "style": "flash", "amount": 35, "start": round(b, 2), "end": round(b + 0.2, 2), "beatFx": True})
    # màn đen chen giữa cảnh ở 1/3 đầu (trailer)
    if K.get("blackGap"):
        gp = float(K["blackGap"]) * (3 if feel == "em" else 1)
        for c in cuts[1:]:
            if A < c < A + (B - A) / 3 and c > fr_end:
                sd = {"type": "solid", "color": "#000", "start": round(c - gp, 2), "end": round(c + (gp if feel == "em" else 0), 2), "z": 15, "beatFx": True}
                if feel == "em":  # nhạc êm: mờ qua đen thay vì tắt phụt
                    sd.update({"fadeIn": round(gp * 0.9, 2), "fadeOut": round(gp * 0.9, 2)})
                els.append(sd)
    if K.get("bars"):
        els.append({"type": "bars", "start": round(A, 2), "end": round(B, 2), "z": 16, "beatFx": True})
    if K.get("overlay"):
        els.append({"type": "overlay", "kind": K["overlay"], "amount": 45 if K["overlay"] == "lightleak" else 30, "start": round(A, 2), "end": round(B, 2), "beatFx": True})
    if K.get("endBlack") and (whole or B >= total - 0.3):
        els.append({"type": "solid", "color": "#000", "fadeIn": 0.6, "start": round(max(A, B - 0.8), 2), "end": round(B, 2), "z": 25, "beatFx": True})  # dưới chữ (30): chữ kết vẫn hiện trên nền đen
    # Dải chéo ở chỗ chuyển đoạn (mỗi ~16 nhịp) — kiểu chia khung
    if "sections" in str(K.get("frames") or ""):
        nb = [b for b in bs if fr_end + 2 < b < B - 2.5]
        vids = [x for x in pool if not x["img"]]
        for j in range(15, len(nb), 16):
            v = vids[(seed + j) % len(vids)] if vids else None
            if v and j + 4 < len(nb):
                els.append({"type": "beatStrips", "start": round(nb[j], 2), "end": round(nb[j + 4] + 0.1, 2), "src": v["src"], "from": round(v["a"] + 0.2, 2),
                            "count": 3, "beatCut": True, **({"soft": True, "every": 2} if feel == "em" else {"soft": True} if feel == "vua" else {})})
    if K.get("color") and whole:
        plan["color"] = {**(plan.get("color") or {}), **K["color"]}
    # CHỮ / ĐỒ HOẠ vẫn giữ như bình thường, chỉ đưa lúc hiện vào nhịp gần nhất (lệch ≤ 0,3s) cho khớp nhạc
    NOSNAP = {"audio", "zoom", "fx", "sfx", "broll", "beatFrames", "beatStrips", "solid", "bars", "overlay", "dayBadge", "presenter"}
    nsnap = 0
    for e in els:
        if not e or e.get("beatCut") or e.get("beatFx") or e.get("type") in NOSNAP or not (A - 0.01 <= e.get("start", -1) < B):
            continue
        nb = min(bs, key=lambda b: abs(b - e["start"])) if bs else None
        d = (nb - e["start"]) if nb is not None else 0
        if 0.02 < abs(d) <= 0.3:
            e["start"] = round(e["start"] + d, 2)
            e["end"] = round(e["end"] + d, 2)
            for it in e.get("items") or []:
                if isinstance(it, dict) and isinstance(it.get("at"), (int, float)):
                    it["at"] = round(it["at"] + d, 2)
            nsnap += 1
    if nsnap:
        rep.append(f"Đưa {nsnap} khối chữ / đồ hoạ vào đúng nhịp (giữ nguyên nội dung)")
    # đoạn dựng theo nhịp: bỏ tiếng hiệu ứng của các khối trong đoạn (nhạc đã đủ nhịp)
    for e in els:
        if e and e.get("type") != "sfx" and A - 0.01 <= e.get("start", -1) <= B and e.get("sfx"):
            e.pop("sfx", None)
            e.pop("sfxOff", None)
    plan["beats"] = bs
    plan["beatEdit"] = {"on": True, "from": round(A, 2), "to": round(B, 2), "density": mat, "fx": hu, "source": nguon, "style": kname, "seed": seed, "mode": mode, "feel": feel, **({"baseSeg": True} if base_seg else {})}
    return plan, rep


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "ds":  # danh sách kiểu dựng nhịp
        for k, v in ds_kieu().items():
            print(f"{k:22} {v['ten']} — {v.get('moTa', '')}")
        return
    if sys.argv[1] == "hoc" and len(sys.argv) > 2:  # học kiểu nhịp từ video mẫu của dự án (_mau/_phan-tich/phan-tich.json)
        f = Path(sys.argv[2]).resolve()
        pt = rj(f / "_mau" / "_phan-tich" / "phan-tich.json") or rj(f / "_phan-tich" / "phan-tich.json") or rj(f / "phan-tich.json")
        if not pt:
            sys.exit("Chưa có phân tích video mẫu — chạy nho_may.py style trước.")
        bsy = hoc(pt)
        print(json.dumps(bsy, ensure_ascii=False, indent=1))
        tgt = f / "_mau" / "phong-cach.json"
        if tgt.parent.exists():
            j = rj(tgt, {}) or {}
            j["beatStyle"] = bsy
            tgt.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Đã ghi beatStyle vào {tgt} (lưu bộ phong cách bằng phongcach.py luu để dùng lại)")
        return
    folder = Path(sys.argv[1]).resolve()
    args = sys.argv[2:]

    def opt(k):
        return args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else None

    plan = rj(folder / "plan.json")
    o = {"tu": opt("--tu"), "den": opt("--den"), "mat_do": opt("--mat-do"), "nguon": opt("--nguon"), "hieu_ung": opt("--hieu-ung"), "che_do": opt("--che-do"),
         "kieu": opt("--kieu"), "seed": opt("--phuong-an"), "cam_giac": opt("--cam-giac")}
    o = {k: v for k, v in o.items() if v is not None}
    try:
        new, rep = build(folder, plan, o)
    except RuntimeError as e:
        sys.exit(str(e))
    print("\n".join(rep))
    if "--xem" in args:
        return
    if (folder / "plan.json").exists():
        shutil.copyfile(folder / "plan.json", folder / "_work" / "plan_truoc_nhip.json")
    (folder / "plan.json").write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi plan.json. Bản cũ: _work/plan_truoc_nhip.json")


if __name__ == "__main__":
    main()
