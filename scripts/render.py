"""Bước 3 — render folder video theo <folder>/plan.json.

Dùng:
  python scripts/render.py "D:/cho-edit/can-ho-01"              -> final.mp4
  python scripts/render.py "D:/cho-edit/can-ho-01" --check 2,15,30,58
        -> chỉ xuất vài khung hình kiểm tra vào _work/check.jpg (nhanh)

plan.json có "template": "review" (review căn) hoặc "challenge" (thử thách + phụ đề).
Với "challenge": nếu plan chưa có "pages", phụ đề được tạo tự động từ _work/words.json
và danh sách "fixes" ([["CHỮ SAI", "CHỮ ĐÚNG"], ...]).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiendo import Tien  # noqa: E402
from hw import render_flags  # noqa: E402

for _s in (sys.stdout, sys.stderr):  # tránh lỗi in tiếng Việt trên Windows
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
NPX = "npx.cmd" if os.name == "nt" else "npx"
ENTRY = "remotion/src/index.ts"


def apply_fixes(words, fixes):
    for wrong, right in fixes:
        pat = wrong.upper().split()
        i, out = 0, []
        while i < len(words):
            if [w["w"] for w in words[i:i + len(pat)]] == pat:
                seg = words[i:i + len(pat)]
                rw = right.split()
                if len(pat) >= 4 and len(rw) >= 2:
                    # sửa cả câu (trang chỉnh sửa): giữ phụ đề chạy từng chữ — cùng số chữ thì giữ mốc từng chữ, khác thì chia đều
                    if len(rw) == len(seg):
                        out += [{"w": r, "start": w["start"], "end": w["end"], "keep": True} for r, w in zip(rw, seg)]
                    else:
                        a, b = seg[0]["start"], seg[-1]["end"]
                        st = (b - a) / len(rw)
                        out += [{"w": r, "start": round(a + k * st, 3), "end": round(a + (k + 1) * st, 3), "keep": True} for k, r in enumerate(rw)]
                else:
                    out.append({"w": right, "start": seg[0]["start"], "end": seg[-1]["end"], "keep": True})  # giữ nguyên hoa/thường khi phụ đề chữ thường
                i += len(pat)
            else:
                out.append(words[i]); i += 1
        words = out
    return words


def make_pages(words, n=3):
    gaps = [words[i + 1]["start"] - words[i]["start"] for i in range(len(words) - 1)] + [9]
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0.3
    pages, cur = [], []
    for i, w in enumerate(words):
        cur.append(dict(w))
        g = gaps[i]
        if g > 0.7 or len(cur) >= n + 1 or (len(cur) >= n and g > med * 1.2) or (len(cur) >= 2 and g > med * 1.8):
            pages.append(cur); cur = []
    if cur:
        pages.append(cur)
    for a, b in zip(pages, pages[1:]):
        a[-1]["end"] = round(min(b[0]["start"], a[-1]["end"] + 0.8), 2)
    return pages


DENOISE_NR = [0, 10, 18, 28]  # mức lọc ồn: tắt / nhẹ / vừa / mạnh (dB giảm nhiễu)


# đổi giọng (giữ nguyên tốc độ nói -> vẫn khớp hình): trầm, cao, chuột chip, robot, vang, điện thoại, loa phát thanh
VOICE_FX = {
    "deep": "aresample=48000,asetrate=48000*0.84,aresample=48000,atempo=1.190476",
    "high": "aresample=48000,asetrate=48000*1.18,aresample=48000,atempo=0.847458",
    "chipmunk": "aresample=48000,asetrate=48000*1.5,aresample=48000,atempo=0.666667",
    "robot": "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75",
    "echo": "aecho=0.8:0.85:70|140:0.35|0.2",
    "phone": "highpass=f=320,lowpass=f=3200,acompressor=threshold=0.1:ratio=6",
    "radio": "highpass=f=200,lowpass=f=5000,acrusher=bits=10:mix=0.25,acompressor=threshold=0.12:ratio=4",
}


def clean_audio(folder: Path, src_rel: str, cfg: dict) -> str:
    """Lọc ồn / cân bằng âm lượng tiếng gốc bằng ffmpeg -> _work/clean_<mã>.mp4 (hình giữ nguyên, chỉ xử lý tiếng).
    cfg = {"denoise": 0-3, "normalize": true/false}. Trả về đường dẫn tương đối dùng làm video chính."""
    den = max(0, min(3, int(cfg.get("denoise", 0) or 0)))
    norm = bool(cfg.get("normalize"))
    voice = cfg.get("voice") if cfg.get("voice") in VOICE_FX else None
    voc = bool(cfg.get("vocals"))  # tách giọng nói khỏi nhạc nền / ồn (AI, scripts/tach_giong.py)
    if not den and not norm and not voice and not voc:
        return src_rel
    src = folder / src_rel
    st = src.stat()
    h = hashlib.md5(f"v2|{src_rel}|{st.st_size}|{st.st_mtime}|{den}|{norm}|{voice}|{voc}".encode()).hexdigest()[:8]
    work = folder / "_work"
    out = work / f"clean_{h}.mp4"
    if not out.exists():
        af = []
        if den:
            af += ["highpass=f=80", f"afftdn=nr={DENOISE_NR[den]}:nf=-35:tn=1"]
        if voice:
            af.append(VOICE_FX[voice])
        if norm:
            af.append("loudnorm=I=-14:TP=-1.5:LRA=11")
        print("Xử lý âm thanh: " + ", ".join((["tách giọng"] if voc else []) + ([f"lọc ồn mức {den}"] if den else []) + ([f"đổi giọng {voice}"] if voice else []) + (["cân bằng âm lượng"] if norm else [])) + "...")
        tmp = work / f"_tmp_clean_{h}.mp4"
        wav = work / f"_tmp_clean_{h}.wav"
        inp = src
        if voc:
            vh = hashlib.md5(f"{src_rel}|{st.st_size}|{st.st_mtime}".encode()).hexdigest()[:8]
            vw = work / f"giong_{vh}.wav"
            if not vw.exists():
                print("Tách giọng nói khỏi nhạc nền (AI)...", flush=True)
                try:
                    from tach_giong import separate
                    separate(src, vw, tick=lambda f: print(f"Tách giọng {int(f * 100)}%", flush=True))
                except Exception as e:  # noqa
                    print("[!] Không tách được giọng, dùng tiếng gốc:", e)
            if vw.exists():
                inp = vw
        # 1) lọc tiếng ra wav (không qua AAC -> không thêm khoảng đệm)
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(inp), "-vn", "-map", "0:a:0?", "-af", ",".join(["aresample=async=1:first_pts=0"] + af),
                            "-ar", "48000", "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode or not wav.exists():
            print("[!] Không xử lý được âm thanh, dùng tiếng gốc:\n" + (r.stderr or "")[-500:])
            wav.unlink(missing_ok=True)
            return src_rel
        # 2) đo xem bộ lọc có làm tiếng trễ đi không (so đường bao với tiếng gốc), rồi bù lại cho khớp hình
        shift = 0.0
        try:
            from dongbo import _audio, _lag
            dur = min(60.0, float(json.loads((work / "info.json").read_text(encoding="utf-8")).get("durationSec", 60)) - 2)
            if dur > 8:
                ref = _audio(src, 0, dur)
                sig = _audio(wav, 0.3, dur - 1.0)
                lag, conf = _lag(ref, sig, 60, 60)  # ±300 ms
                if lag is not None and conf > 0.5:
                    shift = (lag * 5 + 300) / 1000.0 - 0.3  # dương = bản lọc bị trễ
        except Exception as e:  # noqa
            print("[!] Không đo được độ trễ tiếng:", e)
        if abs(shift) >= 0.005:
            print(f"Bù độ trễ do lọc tiếng: {shift * 1000:+.0f} ms")
        a_in = ["-ss", f"{shift:.3f}", "-i", str(wav)] if shift > 0 else (["-itsoffset", f"{-shift:.3f}", "-i", str(wav)] if shift < 0 else ["-i", str(wav)])
        # 3) ghép lại: hình giữ nguyên, tiếng đã lọc + đã bù
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *a_in, "-map", "0:v:0", "-map", "1:a:0",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(tmp)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        wav.unlink(missing_ok=True)
        if r.returncode:
            print("[!] Không xử lý được âm thanh, dùng tiếng gốc:\n" + r.stderr[-500:])
            return src_rel
        for old in work.glob("clean_*.mp4"):
            old.unlink()
        tmp.replace(out)
    return out.relative_to(folder).as_posix()


def remap_words(words: list, segs: list) -> list:
    """Mốc chữ theo video gốc -> mốc theo video đã cắt (chỉ giữ chữ nằm trong các đoạn giữ lại)."""
    out, acc = [], 0.0
    for a, b in segs:
        for w in words:
            if a <= w["start"] < b:
                out.append({**w, "start": round(w["start"] - a + acc, 2), "end": round(min(w["end"], b) - a + acc, 2)})
        acc += b - a
    return out


def auto_captions(folder: Path, plan: dict):
    words = json.loads((folder / "_work" / "words.json").read_text(encoding="utf-8"))
    if plan.get("segments"):
        words = remap_words(words, plan["segments"])
    return make_pages(apply_fixes(words, plan.get("fixes", [])), plan.get("wordsPerPage", 3))


THO = "--tho" in sys.argv  # xuất bản dựng thô (xong_tho.py)


def build_plan(folder: Path) -> dict:
    """plan.json + dữ liệu dự án -> props cho Remotion, đường dẫn file vẫn TƯƠNG ĐỐI theo folder.
    Phần tử trỏ tới file không có bị bỏ qua (danh sách trong plan["_missing"])."""
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    info = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))
    if THO:  # xuất BẢN DỰNG THÔ: chỉ phần cắt ghép / chuyển cảnh / khung hình / tốc độ — không chữ, không phụ đề, không phong cách
        keep = ("segments", "transition", "joinFx", "segXf", "mainXf", "speed", "segSpeed", "segCurve", "videoVolume", "audio", "color", "blurs")
        plan = {k: plan[k] for k in keep if k in plan}
        if plan.get("transition") in (None, "", "cut") and not plan.get("joinFx"):
            plan["transition"] = "auto"  # chưa chọn chuyển cảnh -> tự thêm: cùng lần quay = zoom cut, khác clip = mờ chồng
        plan.update(template="review", captions=False, elements=[], cutFx="none")
    else:
        from phongcach import apply as apply_style  # phong cách (video mẫu / bộ đã lưu) -> font, chữ, phụ đề...
        plan = apply_style(folder, plan)
    # CHE MỜ biển số / mã QR / mã vạch (chính sách TikTok): chưa dò lần nào -> tự dò & ghi "blurs" vào plan.json ("cheMo": false = tắt)
    if plan.get("cheMo", True) is not False and "blurs" not in plan and "--check" not in sys.argv and "--cover" not in sys.argv:
        try:
            import che_mo
            print("Dò biển số / mã QR / mã vạch để che mờ...", flush=True)
            tracks, n = che_mo.run(folder, write_plan=True)
            raw = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
            plan["blurs"] = raw.get("blurs") or []
            print(f"Che mờ: {len(tracks)} vùng (biển số / mã QR / mã vạch)" if tracks else "Che mờ: không thấy biển số / mã QR nào")
        except Exception as e:  # noqa
            print("[!] Không dò được vùng cần che:", e)
    # phong cách đổi cỡ cảnh tự động (toàn/trung/cận) mà plan chưa có -> tạo & lưu vào plan.json ("shots": [] = đã tắt)
    if not THO and "shots" not in plan and ((plan.get("style") or {}).get("effects") or {}).get("shots") == "auto" and info.get("mode") != "voice":
        try:
            import canh_co
            raw = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
            raw = canh_co.run(folder, ((plan.get("style") or {}).get("effects") or {}).get("shotDensity", "vua"), raw)
            (folder / "plan.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
            plan["shots"] = raw["shots"]
            print(f"Cỡ cảnh tự động: {len(raw['shots'])} cảnh (toàn / trung / cận)")
        except Exception as e:  # noqa
            print("[!] Không tạo được cỡ cảnh:", e)
    if info.get("mode") == "voice" and info.get("video") != "_work/edit.mp4":
        sys.exit("Chế độ voice: chưa ghép cảnh. Viết canh.json rồi chạy: python scripts/assemble.py \"<folder>\"")
    brand_file = ROOT / "brand.json"
    if brand_file.exists() and "theme" not in plan:
        plan["theme"] = json.loads(brand_file.read_text(encoding="utf-8"))["theme"]
    segs = [[float(a), float(b)] for a, b in plan.get("segments") or [] if float(b) - float(a) > 0.05]
    if segs:
        plan["segments"] = segs
        plan["durationSec"] = round(sum(b - a for a, b in segs), 3)
    else:
        plan.pop("segments", None)
        plan["durationSec"] = info["durationSec"]
    # KÉO DÀI quá cuối video chính (voice / khối kéo quá cuối, hoặc "tail" giây): đứng hình ở khung cuối
    base = plan["durationSec"]
    ends = [float(e.get("end") or 0) for e in plan.get("elements", []) if e and not e.get("hidden")]
    extra = min(600.0, max(float(plan.get("tail") or 0), max(ends or [0]) - base, 0.0))
    if extra > 0.05:
        plan["durationSec"] = round(base + extra, 3)
        plan["tailFrom"] = base
        end = segs[-1][1] if segs else info["durationSec"]
        a0 = segs[-1][0] if segs else 0
        ts, at = end, base
        try:  # cuối video có khung đen -> đứng hình ở khung còn sáng, từ lúc bắt đầu đen
            from khung_cuoi import black_tail
            bt = black_tail(folder, info["video"], info["durationSec"])
            if bt is not None and end > bt - 0.05 and bt > a0:
                ts, at = max(0.0, bt - 0.1), round(base - (end - bt), 3)
        except Exception:
            pass
        plan["tailSrc"] = ts
        plan["tailAt"] = at
        plan["tailA"] = segs[-1][0] if segs else 0
        print(f"Video dài thêm {extra:.1f}s sau cuối video chính (đứng hình khung cuối)")
    if plan["template"] == "challenge" and "pages" not in plan:
        words = json.loads((folder / "_work" / "words.json").read_text(encoding="utf-8"))
        plan["pages"] = make_pages(apply_fixes(words, plan.get("fixes", [])), plan.get("wordsPerPage", 3))
    if plan["template"] == "review" and "cuts" not in plan:
        src_cuts = json.loads((folder / "_work" / "cuts.json").read_text(encoding="utf-8"))
        if segs:  # điểm nối giữa các đoạn giữ lại + điểm chuyển cảnh gốc dời theo
            acc, cuts = 0.0, set()
            for k, (a, b) in enumerate(segs):
                if k:
                    cuts.add(round(acc, 2))
                cuts |= {round(c - a + acc, 2) for c in src_cuts if a + 0.3 < c < b - 0.3}
                acc += b - a
            plan["cuts"] = sorted(cuts)
        else:
            plan["cuts"] = src_cuts
    # phụ đề: true = tự tạo từ lời nói; danh sách = phụ đề đã sửa tay (giữ nguyên); false = tắt
    if plan["template"] == "review" and plan.get("captions") is True:
        plan["captions"] = auto_captions(folder, plan)
    elif not plan.get("captions"):
        plan.pop("captions", None)
    plan.setdefault("sfxVolume", 0.35)
    # vị trí từng clip/lần quay trong video chính -> điểm nối cùng lần quay dùng zoom cut, khác lần quay dùng mờ chồng
    clips_f = folder / "_work" / "clips.json"
    if str(info.get("video", "")).endswith("ghep.mp4") and clips_f.exists():
        plan.setdefault("clipBounds", json.loads(clips_f.read_text(encoding="utf-8")))

    def find(rel: str):
        p = (folder / rel).resolve()
        if not p.exists():  # chấp nhận cùng tên khác đuôi (vd .png thay .jpg)
            alt = sorted(p.parent.glob(p.stem + ".*")) if p.parent.exists() else []
            p = alt[0] if alt else p
        return p if p.exists() else None

    kept, missing = [], []
    for e in plan.get("elements", []):
        if e.get("src"):
            p = find(e["src"])
            if not p:
                missing.append(e["src"])
                continue  # thiếu file -> bỏ qua để vẫn render được bản demo
            e["src"] = p.relative_to(folder.resolve()).as_posix()
        if e.get("srcs"):  # khung nhịp: nhiều nguồn — bỏ file thiếu
            e["srcs"] = [p.relative_to(folder.resolve()).as_posix() for p in (find(x) for x in e["srcs"] if x) if p]
            if not e["srcs"]:
                e.pop("srcs")
        if e.get("fillSrc"):  # ảnh lồng trong chữ
            p = find(e["fillSrc"])
            if p:
                e["fillSrc"] = p.relative_to(folder.resolve()).as_posix()
            else:
                e.pop("fillSrc")
        if e.get("sfx") and "/" in e["sfx"] and not e["sfx"].startswith("cua-ban/") and not find(e["sfx"]):
            e.pop("sfx")
        if e.get("type") in ("orbit", "photo3d"):  # ảnh/video của vòng quay / ảnh bay 3D: bỏ file thiếu
            its = []
            for it in e.get("items") or []:
                it = {"src": it} if isinstance(it, str) else dict(it or {})
                p = find(it.get("src") or "") if it.get("src") else None
                if p:
                    it["src"] = p.relative_to(folder.resolve()).as_posix()
                    its.append(it)
                elif it.get("src"):
                    missing.append(it["src"])
            e["items"] = its
        if e.get("type") == "screen3d" and isinstance(e.get("pages"), list):  # ảnh / video trong màn hình 3D: bỏ trang thiếu file
            pgs = []
            for pg in e["pages"]:
                if isinstance(pg, dict) and pg.get("src"):
                    p = find(pg["src"])
                    if not p:
                        missing.append(pg["src"])
                        continue
                    pg = {**pg, "src": p.relative_to(folder.resolve()).as_posix()}
                if pg:
                    pgs.append(pg)
            e["pages"] = pgs
        if e.get("type") == "object3d" and isinstance(e.get("items"), list):  # mô hình .glb của vật thể 3D: bỏ vật thiếu file
            its = []
            for it in e["items"]:
                if isinstance(it, dict) and it.get("src"):
                    p = find(it["src"])
                    if not p:
                        missing.append(it["src"])
                        continue
                    it = {**it, "src": p.relative_to(folder.resolve()).as_posix()}
                its.append(it)
            e["items"] = its
        for r in (e.get("regions") or []) if e.get("type") == "mapTour" else []:  # ảnh chân dung tròn trên bản đồ
            for b in r.get("badges") or []:
                if b.get("img"):
                    p = find(b["img"])
                    if p:
                        b["img"] = p.relative_to(folder.resolve()).as_posix()
                    else:
                        missing.append(b.pop("img"))
        kept.append(e)
    plan["elements"] = kept
    # ảnh Openverse (Creative Commons) phải ghi nguồn -> chữ nhỏ ở góc ảnh ("credit": false để tắt, chuỗi để tự ghi)
    try:
        from stock import credits as _credits
        cr = _credits(folder)
        for e in kept:
            if e.get("src") in cr and e.get("credit") is None and e.get("type") in ("broll", "pip", "card3d"):
                e["credit"] = cr[e["src"]]
    except Exception:
        pass
    m = plan.get("music")
    if m and m.get("src"):
        p = find(m["src"])
        if p:
            m["src"] = p.relative_to(folder.resolve()).as_posix()
        else:
            missing.append(m["src"])
            plan.pop("music")
    plan["_missing"] = sorted(set(missing))
    # logo + SĐT của người dùng (⚙ Cài đặt → Logo & SĐT) — không chèn vào bản dựng thô
    try:
        import thuong_hieu
        bm = None if THO else thuong_hieu.mark(folder, plan)
    except Exception as e:  # noqa
        print("[!] Không đọc được cài đặt logo / SĐT:", e)
        bm = None
    if bm:
        plan["brandMark"] = bm
    else:
        plan.pop("brandMark", None)
    # KHUNG HÌNH (khung.json): 9:16 | 4:5 | 1:1 | 16:9 — video chính khác tỉ lệ nhiều thì giữ trọn hình + nền mờ
    import khung
    fmt = khung.get(folder)
    plan["format"] = fmt
    if fmt != "9:16" or plan.get("mainFit"):
        if not plan.get("mainFit"):
            plan["mainFit"] = khung.auto_fit(info.get("width"), info.get("height"), fmt)
    if fmt != "9:16":
        for e in plan.get("elements", []):
            if e and e.get("type") in ("orbit", "photo3d"):
                e["behind"] = False  # khung khác 9:16 chưa tách người -> vòng quay vẽ đủ cả vòng trước người
    if fmt != "9:16" and any(e and (e.get("behind") or (isinstance(e.get("z"), (int, float)) and e["z"] < 0)) for e in plan.get("elements", [])):
        print("[!] Khung " + fmt + ": chưa hỗ trợ đặt khối SAU người — các khối đó nằm trước người")
        for e in plan["elements"]:
            if e:
                e.pop("behind", None)
                if isinstance(e.get("z"), (int, float)) and e["z"] < 0:
                    e["z"] = 30
    vid = info["video"]
    if (plan.get("beauty") or {}) and any((plan["beauty"].get(k) or 0) > 0 for k in ("smooth", "bright", "lip", "blush", "sharpen")):
        try:  # làm đẹp người (mịn da, sáng da, son, má hồng, độ nét) — xử lý 1 lần, lưu sẵn
            from beauty import process as beautify
            from tiendo import Tien
            tb = Tien(folder, "beauty", sum(b - a for a, b in plan.get("segments") or [[0, info["durationSec"]]]))
            vid = beautify(folder, info["video"], plan["beauty"], plan.get("segments"), lambda f: tb.update(f, f"Làm đẹp {int(f * 100)}%"))
            tb.done(True)
        except Exception as e:  # noqa
            print("[!] Không làm đẹp được, dùng video gốc:", e)
    plan["_beautyVideo"] = vid
    plan["videoSrc"] = clean_audio(folder, vid, plan.get("audio") or {})
    # khối bám mặt -> cần dữ liệu vùng mặt (scripts/mat.py)
    if any(e and (e.get("follow") == "face" or (e.get("type") in ("orbit", "photo3d") and (e.get("cx") is None or e.get("cy") is None))) for e in plan["elements"]):
        mp = folder / "_work" / "mat.json"
        if not mp.exists():
            try:
                import mat
                mat.run(folder)
            except Exception as e:  # noqa
                print("[!] Không dò được mặt — khối bám mặt sẽ đứng yên:", e)
        if mp.exists():
            m = json.loads(mp.read_text(encoding="utf-8"))
            plan["faces"] = {"step": m.get("step", 0.5), "faces": m.get("faces", [])}
    # element đặt SAU người (lớp z < 0 / "behind": true) -> cần lớp người đã tách nền đè lên trên
    from tach_nguoi import behind_of
    if any(e and behind_of(e) for e in plan["elements"]):
        try:
            from tach_nguoi import run as tach
            plan["person"] = [{"i": p["i"], "from": p["from"], "len": p["len"], "ext": p["ext"], "off": p.get("off", 0), "src": f"_work/nguoi/{p['file']}"}
                              for p in tach(folder, plan, video_rel=plan.get("_beautyVideo"))]
        except Exception as e:  # noqa
            print("[!] Không tách được người khỏi nền — các element 'sau người' sẽ nằm trước người:", e)
            plan.pop("person", None)
    duck = speech_spans(folder, plan)
    if duck:
        plan["duck"] = duck
    return plan


def speech_spans(folder: Path, plan: dict):
    """NHẠC NHƯỜNG LỜI (cách trộn của LumReels): nhạc nền giữ mức plan đặt khi có người nói, tự to lên ở khoảng lặng ≥ 0,8s
    rồi hạ lại trước câu kế. plan "musicDuck": false = tắt · {"lift": 1.8} = độ to lên ở khoảng lặng (1–3, mức sau cùng ≤ 0,6).
    Trả {"spans": [[a, b], …] (giây video xuất, đoạn đang nói), "lift": k} hoặc None."""
    cfg = plan.get("musicDuck", True)
    if cfg is False or THO:
        return None
    els = plan.get("elements") or []
    has_bgm = bool(plan.get("music")) or any(e and e.get("type") == "audio" and e.get("bgm") for e in els)
    if not has_bgm or float(plan.get("videoVolume", 1) or 0) <= 0:
        return None
    try:
        words = json.loads((folder / "_work" / "words.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        return None
    if plan.get("segments"):
        words = remap_words(words, plan["segments"])
    words = [w for w in words if isinstance(w, dict) and w.get("end", 0) > w.get("start", 0)]
    if len(words) < 3:  # vài chữ lẻ = máy nghe nhầm tiếng ồn, coi như không lời
        return None
    spans = []
    for w in sorted(words, key=lambda x: x["start"]):
        a, b = float(w["start"]), float(w["end"])
        if spans and a - spans[-1][1] < 0.8:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    lift = 1.8
    if isinstance(cfg, dict) and cfg.get("lift"):
        lift = max(1.0, min(3.0, float(cfg["lift"])))
    return {"spans": [[round(a, 2), round(b, 2)] for a, b in spans], "lift": lift}


def bundle_dir():
    """đóng gói bộ dựng 1 lần (theo mã nguồn), dùng lại cho mọi lần xuất/kiểm tra — trước đây mỗi lần đều đóng gói lại
    và chép theo toàn bộ file đã chuẩn bị (hàng trăm MB). Lỗi -> None (dùng cách cũ)."""
    pre = ROOT / "bo-dung"  # bản phát hành: bộ dựng đóng gói sẵn (không kèm mã nguồn remotion/src)
    if (pre / "index.html").exists() and not (ROOT / "remotion" / "src").exists():
        try:  # âm thanh / phông người dùng thêm vào public/ sau này -> đưa vào bộ dựng
            for p in (ROOT / "public").rglob("*"):
                if p.is_file() and "jobs" not in p.relative_to(ROOT / "public").parts:
                    d = pre / "public" / p.relative_to(ROOT / "public")
                    if not d.exists() or d.stat().st_size != p.stat().st_size:
                        d.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(p, d)
        except Exception as e:  # noqa
            print("[!] Không cập nhật được âm thanh vào bộ dựng:", e)
        return pre
    try:
        files = sorted([*(ROOT / "remotion").rglob("*.ts*"), ROOT / "remotion" / "fonts.json", ROOT / "package.json",
                        ROOT / "remotion.config.ts"])
        sfx = sorted(p for p in (ROOT / "public").rglob("*") if p.is_file() and "jobs" not in p.relative_to(ROOT / "public").parts)
        sig = "|".join(f"{p.relative_to(ROOT)}:{p.stat().st_size}:{int(p.stat().st_mtime)}" for p in files + sfx if p.exists())
        h = hashlib.md5(sig.encode()).hexdigest()[:10]
        cache = ROOT / "_cache"
        out = cache / f"bundle-{h}"
        if (out / "index.html").exists():
            return out
        pub = cache / "pub"
        shutil.rmtree(pub, ignore_errors=True)
        for p in sfx:  # thư mục public nhẹ (không có jobs/)
            d = pub / p.relative_to(ROOT / "public")
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, d)
        print("Đóng gói bộ dựng (1 lần, lần sau dùng lại)...", flush=True)
        tmp = cache / f"_bundle-{h}"
        shutil.rmtree(tmp, ignore_errors=True)
        r = subprocess.run([NPX, "remotion", "bundle", ENTRY, f"--out-dir={tmp}", f"--public-dir={pub}", "--log=error"], cwd=ROOT,
                           stdin=subprocess.DEVNULL)  # không để Remotion hỏi (Y/n) chờ bấm phím
        if r.returncode or not (tmp / "index.html").exists():
            return None
        for old in cache.glob("bundle-*"):
            shutil.rmtree(old, ignore_errors=True)
        shutil.rmtree(ROOT / "public" / "jobs", ignore_errors=True)  # file chuẩn bị kiểu cũ (không còn dùng)
        tmp.replace(out)
        return out
    except Exception as e:  # noqa
        print("[!] Không đóng gói sẵn được, dùng cách cũ:", e)
        return None


def _place(src: Path, dst: Path):
    """đưa file vào chỗ bộ dựng đọc: liên kết cứng (tức thì, không tốn dung lượng), không được thì chép"""
    if dst.exists():
        a, b = src.stat(), dst.stat()
        if (a.st_ino == b.st_ino and a.st_dev == b.st_dev) or (a.st_size == b.st_size and int(a.st_mtime) == int(b.st_mtime)):
            return
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def build_props(folder: Path) -> dict:
    plan = build_plan(folder)
    if plan["_missing"]:
        print("[!] Thiếu file minh họa, tạm bỏ qua: " + ", ".join(plan["_missing"]))
    # Remotion chỉ đọc file trong public/ -> copy video + ảnh/âm thanh vào public/jobs/<id>/
    jid = hashlib.md5(str(folder).encode()).hexdigest()[:10]
    if use_hf():
        import hf_engine
        bd = hf_engine.bundle_dir()
    else:
        bd = bundle_dir()
    plan["_bundle"] = str(bd) if bd else None
    jdir = (bd / "public" if bd else ROOT / "public") / "jobs" / jid
    jdir.mkdir(parents=True, exist_ok=True)

    def stage(rel: str, name: str = None) -> str:
        path = folder / rel
        name = name or rel.replace("/", "__")
        _place(path, jdir / name)
        return f"jobs/{jid}/{name}"

    def stage_canh(rel: str):  # cảnh AI: cả thư mục cảnh + thư viện (canh-ai/lib) -> public/jobs/<id>/canh__<tên>/
        src = (folder / rel).resolve()
        if not (src / "index.html").exists():
            print(f"[!] Cảnh AI thiếu {rel}/index.html — bỏ qua khối (tạo bằng canh_ai.py moi)")
            return None
        import canh_ai
        dst = jdir / ("canh__" + rel.strip("/").replace("/", "__"))
        for f in src.rglob("*"):
            r = f.relative_to(src)
            if f.is_dir() or r.parts[0] == "lib" or r.name in ("_thu.jpg", "MAU.md"):
                continue
            (dst / r).parent.mkdir(parents=True, exist_ok=True)
            _place(f, dst / r)
        canh_ai.sync_lib(dst)
        return f"jobs/{jid}/{dst.name}"

    for e in plan["elements"]:
        if e.get("type") == "canhAI" and e.get("canh"):
            e["canh"] = stage_canh(e["canh"])
        if e.get("src"):
            e["src"] = stage(e["src"])
        if e.get("fillSrc"):
            e["fillSrc"] = stage(e["fillSrc"])
        if e.get("srcs"):
            e["srcs"] = [stage(x) for x in e["srcs"]]
        if e.get("sfx") and "/" in e["sfx"] and not e["sfx"].startswith("cua-ban/"):
            e["sfx"] = stage(e["sfx"])
        for it in e.get("items") or [] if e.get("type") in ("orbit", "photo3d") else []:
            it["src"] = stage(it["src"])
        for pg in e.get("pages") or [] if e.get("type") == "screen3d" else []:
            if isinstance(pg, dict) and pg.get("src"):
                pg["src"] = stage(pg["src"])
        for it in e.get("items") or [] if e.get("type") == "object3d" else []:
            if isinstance(it, dict) and it.get("src"):
                it["src"] = stage(it["src"])
        for r in (e.get("regions") or []) if e.get("type") == "mapTour" else []:
            for b in r.get("badges") or []:
                if b.get("img"):
                    b["img"] = stage(b["img"])
    if plan.get("music"):
        plan["music"]["src"] = stage(plan["music"]["src"])
    for p in plan.get("person") or []:
        p["src"] = stage(p["src"])
    bm = plan.get("brandMark")
    if bm and bm.get("logo"):  # logo nằm ở thư mục tool (thuong-hieu/), không trong dự án
        lp = Path(bm["logo"])
        _place(lp, jdir / ("_logo" + lp.suffix.lower()))
        bm["logo"] = f"jobs/{jid}/_logo{lp.suffix.lower()}"
    plan["videoSrc"] = stage(plan["videoSrc"], "_main" + Path(plan["videoSrc"]).suffix.lower())
    plan["_jobDir"] = str(jdir)
    return plan


_PROG = re.compile(r"(Bundl\w*|Render\w*|Encod\w*|Stitch\w*)[^0-9]*(\d+)\s*/\s*(\d+)", re.I)
_PCT = re.compile(r"(Bundl\w*)[^0-9]*(\d+)%", re.I)


def use_hf() -> bool:
    """bộ dựng: HyperFrames (mặc định — không cần giấy phép công ty) hoặc Remotion (settings "renderEngine": "remotion" / NHM_ENGINE=remotion)"""
    e = os.environ.get("NHM_ENGINE")
    if not e:
        try:
            e = json.loads((ROOT / "settings.json").read_text(encoding="utf-8")).get("renderEngine")
        except Exception:  # noqa
            e = None
    return (e or "hf").lower() not in ("remotion", "rm")


def remotion(args, tien: Tien = None, span=(0.0, 1.0)):
    """chạy bộ dựng (HyperFrames hoặc Remotion), báo % + thời gian còn lại."""
    if use_hf():
        import hf_engine
        try:
            return hf_engine.run(args, tien, span)
        except Exception as e:  # noqa
            import traceback
            traceback.print_exc()
            if tien:
                tien.done(False)
            sys.exit(f"Render lỗi: {e}")
    if os.environ.get("REMOTION_BROWSER"):  # tùy chọn: dùng Chrome có sẵn
        args = [*args, f"--browser-executable={os.environ['REMOTION_BROWSER']}"]
    p = subprocess.Popen([NPX, "remotion", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         bufsize=0)
    a, b = span
    buf, last_print = b"", ""
    r0 = None  # (khung, thời điểm) lúc bắt đầu dựng khung -> tự tính tốc độ thật
    import time
    eof = False  # bộ mã hóa (ffmpeg của Remotion) chết giữa chừng: "write EOF" / "EPIPE" — thường do thiếu RAM / ổ đầy / tăng tốc chip lỗi
    while True:
        ch = p.stdout.read(1)
        if not ch:
            break
        if ch not in (b"\r", b"\n"):
            buf += ch
            continue
        line = buf.decode("utf-8", "replace").strip()
        buf = b""
        if not line:
            continue
        if "write EOF" in line or "EPIPE" in line or "code: 'EOF'" in line:
            eof = True
        m = _PROG.search(line)
        if m and tien:
            kind, x, y = m.group(1).lower(), int(m.group(2)), max(1, int(m.group(3)))
            f = x / y
            # bundle 0–5%, dựng khung 5–90%, mã hóa 90–100%
            frac = 0.05 * f if kind.startswith("bundl") else (0.05 + 0.85 * f if kind.startswith("render") else 0.90 + 0.10 * f)
            eta = None
            if kind.startswith("render"):
                now = time.time()
                if r0 is None or x < r0[0]:
                    r0 = (x, now)
                elif x - r0[0] >= 10 and now > r0[1]:
                    eta = (y - x) / ((x - r0[0]) / (now - r0[1])) * 1.06 + 3  # + phần mã hóa cuối
                else:
                    tr = re.search(r"remaining:\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(\d+)s", line)
                    if tr:
                        eta = int(tr.group(1) or 0) * 3600 + int(tr.group(2) or 0) * 60 + int(tr.group(3))
            elif kind.startswith("encod"):
                eta = 3
            if eta is not None and b < 1.0:
                eta = None  # còn bước khác phía sau: để Tien tự tính
            tien.update(a + (b - a) * frac, eta=eta, msg=f"{'Đang dựng khung' if kind.startswith('render') else 'Đang mã hóa' if kind.startswith('encod') else 'Chuẩn bị'} {x}/{y}")
        elif tien and _PCT.search(line):
            tien.update(a + (b - a) * 0.05 * int(_PCT.search(line).group(2)) / 100, "Chuẩn bị bộ dựng")
        key = re.sub(r"\d+", "#", line)  # in gọn: bỏ các dòng tiến độ lặp lại
        if key != last_print or not m:
            print(line, flush=True)
            last_print = key
    p.wait()
    fl = next((x for x in ("--hardware-acceleration", "--gl=") if any(a.startswith(x) for a in args)), None)
    if p.returncode and fl:
        # máy không hợp chế độ tăng tốc này -> chạy lại không có nó, ghi nhớ để lần sau khỏi thử
        print(f"[!] Chế độ tăng tốc ({'mã hóa bằng chip' if fl.startswith('--hard') else 'card đồ họa'}) không chạy được trên máy này — chạy lại...", flush=True)
        try:
            sp = ROOT / "settings.json"
            st = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
            st["renderHwAccel" if fl.startswith("--hard") else "renderGl"] = False if fl.startswith("--hard") else ""
            sp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass
        return remotion([a for a in args if not a.startswith((fl, "--browser-executable"))], tien, span)
    if p.returncode and eof and not os.environ.get("NHM_RETRY_EOF"):
        # bộ mã hóa bị tắt giữa chừng -> chạy lại 1 lần nhẹ hơn: ít luồng dựng song song, không tăng tốc chip, xoá file tạm cũ
        import shutil as _sh
        free = _sh.disk_usage(str(ROOT)).free / 1e9
        print(f"[!] Bộ mã hóa bị tắt giữa chừng (write EOF) — thường do máy thiếu RAM hoặc ổ đầy (còn {free:.1f} GB trống). "
              "Chạy lại chế độ nhẹ (ít luồng, ít RAM, không tăng tốc chip) — sẽ chậm hơn...", flush=True)
        if free < 3:
            print("[!] Ổ đĩa gần đầy — hãy dọn bớt (cần ≥ 5 GB trống để xuất video dài).", flush=True)
        os.environ["NHM_RETRY_EOF"] = "1"
        try:
            na = [x for x in args if not x.startswith(("--concurrency", "--hardware-acceleration", "--offthreadvideo-cache-size"))]
            return remotion([*na, "--concurrency=2", "--offthreadvideo-cache-size-in-bytes=512000000"], tien, span)
        finally:
            os.environ.pop("NHM_RETRY_EOF", None)
    if p.returncode:
        if tien:
            tien.done(False)
        if eof:
            print("[!] Gợi ý: đóng bớt ứng dụng nặng (Chrome nhiều tab, CapCut, Premiere...), dọn ổ đĩa còn ≥ 5 GB, "
                  "khởi động lại máy rồi xuất lại; hoặc tắt 'Xuất bằng chip' trong ⚙ Cài đặt.", flush=True)
        sys.exit("Render lỗi, xem thông báo phía trên.")


CURVE_N = 8


def _bump(u, edge, mid):  # nhanh 2 đầu, chậm giữa (hoặc ngược lại) — đường mượt
    import math
    return edge + (mid - edge) * (math.sin(math.pi * u) ** 2)


CURVES = {
    "hero": lambda u: _bump(u, 1.6, 0.35),     # anh hùng: chậm ở giữa
    "bullet": lambda u: _bump(u, 2.2, 0.25),   # đạn bay: chậm sâu ở giữa
    "montage": lambda u: _bump(u, 0.8, 2.6),   # montage: nhanh ở giữa
    "jump": lambda u: _bump(u, 1.0, 3.2),      # nhảy cóc
    "flashin": lambda u: 3.0 - 2.0 * u,        # vào nhanh rồi chậm dần
    "flashout": lambda u: 1.0 + 2.0 * u,       # bình thường rồi nhanh dần
}


SP_MIN, SP_MAX = 0.1, 16.0  # 0,1× siêu chậm … 16× timelapse


def _seg_opt(m: dict, a: float):
    for k, v in (m or {}).items():
        try:
            if abs(float(k) - float(a)) < 0.006:
                return v
        except (TypeError, ValueError):
            pass
    return None


def auto_mute(r: float) -> bool:
    """tiếng gốc ở đoạn đổi tốc độ mạnh nghe méo -> tự tắt: chậm hơn 0,75× (slow-motion) hoặc nhanh hơn 2,5× (timelapse)"""
    return r < 0.75 or r > 2.5


def speed_ranges(props: dict):
    """các khoảng [đầu, cuối, tốc độ, tắt tiếng, làm mượt] trên video xuất (trước khi đổi tốc độ); None nếu không đổi tốc độ.
    speed = cả video, segSpeed = riêng từng đoạn (khoá = giây bắt đầu đoạn trong video gốc) — giống speedAt() trong editor/logic.ts
    segAudio {"<a>": "keep" | "mute"} (không ghi = tự động: auto_mute), segSmooth {"<a>": "mci" | "blend" | "off"}
    (không ghi = tự động: chậm < 0,8× -> "blend")"""
    g = float(props.get("speed") or 1)
    ss = {}
    for k, v in (props.get("segSpeed") or {}).items():
        try:
            ss[float(k)] = float(v)
        except (TypeError, ValueError):
            pass
    segs = props.get("segments") or [[0, float(props.get("durationSec") or 0)]]
    curves = {}
    for k, v in (props.get("segCurve") or {}).items():
        try:
            curves[float(k)] = v
        except (TypeError, ValueError):
            pass
    out, acc = [], 0.0
    for a, b in segs:
        r0 = g * next((v for k, v in ss.items() if abs(k - float(a)) < 0.006), 1.0)
        cv = next((v for k, v in curves.items() if abs(k - float(a)) < 0.006), None)
        au = _seg_opt(props.get("segAudio"), a)
        sm = _seg_opt(props.get("segSmooth"), a)
        d = float(b) - float(a)
        n = CURVE_N if cv in CURVES else 1
        for q in range(n):  # đường cong tốc độ: chia đoạn thành n lát, mỗi lát 1 tốc độ (giống curveRate() trong editor/logic.ts)
            r = max(SP_MIN, min(SP_MAX, r0 * (CURVES[cv]((q + 0.5) / n) if n > 1 else 1)))
            mute = au == "mute" or (au != "keep" and cv not in CURVES and auto_mute(r))  # đường cong: giữ tiếng (thường có nhạc / lời)
            smooth = (sm or ("blend" if r < 0.8 else "off")) if r < 0.99 else "off"
            s0, s1 = acc + d * q / n, acc + d * (q + 1) / n
            if out and abs(out[-1][2] - r) < 1e-3 and out[-1][3] == mute and out[-1][4] == smooth:
                out[-1][1] = s1
            else:
                out.append([s0, s1, r, mute, smooth])
        acc += d
    tot = float(props.get("durationSec") or 0)
    if props.get("segments") and tot > acc + 0.05:  # phần kéo dài (đứng hình) sau đoạn cuối: tốc độ cả video
        r = max(SP_MIN, min(SP_MAX, g))
        out.append([acc, tot, r, False, "off"])
    return None if all(abs(r - 1) < 1e-3 and not m for _, _, r, m, _s in out) else out


def apply_speed(src: Path, dst: Path, ranges: list):
    """tăng/giảm tốc từng khoảng của bản xuất (hình + tiếng, giữ cao độ giọng).
    Đoạn chậm: làm mượt bằng nội suy khung ("blend" = trộn khung, nhẹ; "mci" = bù chuyển động, mượt nhất, xuất lâu hơn).
    Tiếng gốc của đoạn slow-motion / timelapse đã được tắt lúc dựng (EditPlan, segAudio / auto_mute); ở đây chỉ co giãn
    tiếng đã trộn (nhạc, voice, sfx). Timelapse (> 2,5×) không nén tiếng mà lấy phần đầu cho khỏi méo."""
    from hw import run_enc
    fc, n = [], len(ranges)
    for k, rg in enumerate(ranges):
        s, e, r = rg[0], rg[1], rg[2]
        mute = rg[3] if len(rg) > 3 else False
        smooth = rg[4] if len(rg) > 4 else "off"
        end = "" if k == n - 1 else f":end={e:.3f}"
        tempo, x = [], r
        while x > 2.0:
            tempo.append("atempo=2.0"); x /= 2.0
        while x < 0.5:
            tempo.append("atempo=0.5"); x /= 0.5
        tempo.append(f"atempo={x:.4f}")
        vf = f"[0:v]trim=start={s:.3f}{end},setpts=(PTS-STARTPTS)/{r:.4f}"
        if smooth == "mci":
            vf += ",minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
        elif smooth == "blend":
            vf += ",framerate=fps=30:interp_start=0:interp_end=255:scene=8"
        else:
            vf += ",fps=30"
        fc.append(vf + f",format=yuv420p[v{k}]")
        if r > 2.5:  # timelapse: không nén tiếng (nhạc / lời nghe méo) — lấy đúng phần đầu tiếng của khoảng, vuốt 2 mép
            od = ((e - s) if end else 600.0) / r
            fc.append(f"[0:a]atrim=start={s:.3f}:duration={od:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,"
                      f"afade=t=out:st={max(0.0, od - 0.06):.3f}:d=0.06[a{k}]")
        else:
            fc.append(f"[0:a]atrim=start={s:.3f}{end},asetpts=PTS-STARTPTS,{','.join(tempo)}[a{k}]")
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    r = run_enc(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]"],
                ["-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"], str(dst))
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])


def _scale_flags(props: dict) -> list:
    """16:9: lớp đồ hoạ 1080×608, xuất nét ở 1918×1080 (rồi chỉnh đúng 1920×1080)"""
    import khung
    k = khung.scale_of(props.get("format") or "9:16")
    return [f"--scale={k!r}"] if abs(k - 1) > 1e-6 else []


def _fix_size(path: Path, fmt: str):
    """file xuất phải đúng kích thước khung (16:9 = 1920×1080)"""
    import khung
    w, h = khung.OUT.get(fmt, (1080, 1920))
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        cw, ch = [int(x) for x in r.stdout.strip().split(",")[:2]]
    except Exception:
        return
    if (cw, ch) == (w, h):
        return
    tmp = path.with_name("_size" + path.suffix)
    from hw import run_enc
    rr = run_enc(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=lanczos,setsar=1", "-c:a", "copy"],
                 ["-movflags", "+faststart"], str(tmp))
    if rr.returncode == 0:
        tmp.replace(path)


LUFS = -14  # độ to chuẩn mạng xã hội (TikTok / Reels / YouTube) — cách làm của LumReels: đo rồi chỉnh 2 lượt


def chuan_loudness(path: Path):
    """đưa tiếng cả video (lời + nhạc + hiệu ứng) về −14 LUFS, đỉnh ≤ −1,5 dBTP; hình giữ nguyên (chép thẳng).
    Tắt bằng plan "loudness": false."""
    af = f"loudnorm=I={LUFS}:TP=-1.5:LRA=11:print_format=json"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0?", "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr or "")
    if not m:
        return
    j = json.loads(m.group(0))
    li, tp = float(j["input_i"]), float(j["input_tp"])
    if li < -70:  # không có tiếng
        return
    if abs(li - LUFS) <= 1.0 and tp <= -1.0:
        print(f"Độ to: {li:.1f} LUFS, đỉnh {tp:.1f} dBTP — đạt chuẩn {LUFS} LUFS")
        return
    tmp = path.with_name("_loud_" + path.name)
    af2 = (f"loudnorm=I={LUFS}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
           f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                        "-af", af2, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError((r.stderr or "")[-300:])
    tmp.replace(path)
    print(f"Độ to: {li:.1f} → {LUFS} LUFS (đỉnh {tp:.1f} → ≤ −1,5 dBTP)")


def want_fast(props: dict) -> bool:
    """dựng nhanh (chỉ dựng khúc có đồ hoạ): mặc định bật; tắt bằng --cham, plan "fastRender": false, hoặc settings "renderFast": false"""
    if THO or "--cham" in sys.argv or props.get("fastRender") is False:
        return False
    if "--nhanh" in sys.argv:
        return True
    try:
        st = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    except Exception:  # noqa
        st = {}
    return st.get("renderFast", True) is not False


def main():
    folder = Path(sys.argv[1]).resolve()
    props = build_props(folder)
    work = folder / "_work"
    pfile = work / "props.json"
    pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    comp = props["template"]
    vsec = float(props.get("durationSec") or 0)

    if "--cover" in sys.argv:
        # ẢNH BÌA: 1 khung ở giây t + dòng tiêu đề lớn -> anh-bia.jpg (1080x1920)
        k = sys.argv.index("--cover")
        t = float(sys.argv[k + 1])
        title = sys.argv[k + 2] if len(sys.argv) > k + 2 else ""
        opt = json.loads(sys.argv[k + 3]) if len(sys.argv) > k + 3 else {}
        if opt.get("nocap", True):
            props.pop("captions", None)
        if title.strip():
            props["elements"] = [e for e in props["elements"] if not (opt.get("clean") and e.get("type") in ("text", "chip", "sticker"))]
            props["elements"].append({"type": "text", "text": title, "start": max(0, t - 0.5), "end": t + 1, "y": int(opt.get("y", 260)),
                                      "size": int(opt.get("size", 120)), "look": opt.get("look") or "outline", "anim": "none", "out": "none",
                                      "upper": bool(opt.get("upper", True)), "z": 999, **({"color": opt["color"]} if opt.get("color") else {})})
        pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        png = work / "_cover.png"
        remotion(["still", props.get("_bundle") or ENTRY, comp, str(png), f"--frame={int(t * 30)}", f"--props={pfile}", "--log=error",
                  *[f for f in render_flags() if f.startswith("--gl")], *_scale_flags(props)])
        out = folder / "anh-bia.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-q:v", "2", str(out)])
        png.unlink(missing_ok=True)
        print(f"ẢNH BÌA: {out}")
        return

    if "--check" in sys.argv:
        times = [float(x) for x in sys.argv[sys.argv.index("--check") + 1].split(",")]
        shots = []
        tien = Tien(folder, "check", len(times))
        for i, t in enumerate(times):
            out = work / f"check_{i}.png"
            tien.update(i / len(times), f"Khung {i + 1}/{len(times)}", force=True)
            remotion(["still", props.get("_bundle") or ENTRY, comp, str(out), f"--frame={int(t * 30)}", f"--props={pfile}", "--log=error",
                      *[f for f in render_flags() if f.startswith("--gl")]])
            shots.append(out)
        inputs = sum([["-i", str(s)] for s in shots], [])
        fc = "".join(f"[{i}]" for i in range(len(shots))) + f"hstack={len(shots)},scale=1800:-2" if len(shots) > 1 else "scale=600:-2"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, str(work / "check.jpg")])
        for s in shots:
            s.unlink()
        tien.done(True)
        print(f"Ảnh kiểm tra: {work / 'check.jpg'}")
    else:
        NHAP = "--nhap" in sys.argv  # bản NHÁP: nửa độ phân giải (540p) — xem thử nhanh, không thay final.mp4
        out = (work / "tho_out.mp4") if THO else (work / "nhap.mp4") if NHAP else folder / "final.mp4"
        tmp = work / "_render.mp4"  # render ra file tạm: dừng giữa chừng không làm hỏng final.mp4 cũ
        tmp.unlink(missing_ok=True)
        tien = Tien(folder, "render", vsec)
        sflags = ["--scale=0.5"] if NHAP else _scale_flags(props)
        done = False
        if want_fast(props) and props.get("_bundle"):
            try:
                import dung_nhanh
                import khung
                W, H = khung.FORMATS.get(props.get("format") or "9:16", (1080, 1920))
                done = dung_nhanh.run(folder, props, W, H, tmp, remotion, render_flags(), sflags, tien, 0.5 if NHAP else 1.0)
            except SystemExit:
                raise
            except Exception as e:  # noqa
                import traceback
                traceback.print_exc()
                print(f"[!] Dựng nhanh lỗi ({e}) — dựng như thường.", flush=True)
                done = False
        if not done:
            tmp.unlink(missing_ok=True)
            remotion(["render", props.get("_bundle") or ENTRY, comp, str(tmp), f"--props={pfile}", *render_flags(), *sflags], tien)
            if props.get("format", "9:16") != "9:16" and not NHAP:
                _fix_size(tmp, props["format"])
        tmp.replace(out)
        tien.done(True)
        try:  # kiểm tra tiếng–hình có khớp không (đổi giọng / tách giọng làm đường âm khác tiếng gốc -> bỏ qua)
            from dongbo import check as sync_check, report as sync_report
            au = props.get("audio") or {}
            mode = ""
            try:
                mode = json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8")).get("mode", "")
            except Exception:  # noqa
                pass
            if mode == "audio":
                print("Đồng bộ tiếng–hình: bỏ qua (video chỉ có giọng / không clip gốc — không có hình quay để so)")
            elif au.get("voice") or au.get("vocals"):
                print("Đồng bộ tiếng–hình: bỏ qua kiểm tra (đang đổi giọng / tách giọng — đã tự bù độ trễ khi xử lý tiếng)")
            else:
                print(sync_report(sync_check(folder, out)))
        except Exception as e:  # noqa
            print("[!] Không kiểm tra được đồng bộ tiếng–hình:", e)
        rg = speed_ranges(props)
        if rg:  # đổi tốc độ (cả video / từng đoạn)
            print("Đổi tốc độ: " + ", ".join(f"{x[0]:.1f}–{x[1]:.1f}s ×{x[2]:g}" + (" (tắt tiếng gốc)" if x[3] else "") + (" (làm mượt)" if x[4] != "off" else "")
                                            for x in rg if abs(x[2] - 1) > 1e-3 or x[3]), flush=True)
            try:
                sp = work / "_speed.mp4"
                apply_speed(out, sp, rg)
                sp.replace(out)
            except Exception as e:  # noqa
                print("[!] Không đổi được tốc độ (giữ tốc độ thường):", e)
        if props.get("loudness", True) is not False and not THO:
            try:
                chuan_loudness(out)
            except Exception as e:  # noqa
                print("[!] Không chuẩn được độ to (giữ nguyên):", e)
        shutil.rmtree(props["_jobDir"], ignore_errors=True)
        print(f"XONG: {out}")
        if "--copy-to" in sys.argv and not THO and not NHAP:  # lưu thêm 1 bản ra thư mục người dùng chọn
            dst = Path(sys.argv[sys.argv.index("--copy-to") + 1])
            if dst.parent.resolve() == folder.resolve():  # để thẳng trong thư mục dự án sẽ bị coi là 1 clip quay
                dst = folder / "xuat" / dst.name
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.resolve() != out.resolve():
                    shutil.copyfile(out, dst)
                print(f"ĐÃ LƯU: {dst}")
                # nhớ chỗ đã xuất để giao diện hiện link mở lại
                lf = work / "da-xuat.json"
                try:
                    L = json.loads(lf.read_text(encoding="utf-8")) if lf.exists() else []
                except Exception:  # noqa
                    L = []
                L = [x for x in L if x.get("path") != str(dst)] + [{"path": str(dst), "time": int(time.time())}]
                lf.write_text(json.dumps(L[-10:], ensure_ascii=False, indent=1), encoding="utf-8")
            except OSError as e:
                print(f"[!] Không lưu được vào {dst}: {e} — bản chính vẫn ở {out}")


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit('Dùng: python scripts/render.py "<folder video>" [--check 2,15,30] [--copy-to "<đường dẫn file mp4>"]')
    main()
