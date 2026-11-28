"""VIDEO KHÔNG CẦN CLIP GỐC — từ kịch bản (hoặc chỉ thời lượng) dựng cả video bằng giọng AI + cảnh AI + chữ / phụ đề / nhạc của tool
(cách làm của LumReels: gõ nội dung → AI dựng cảnh bằng code → MP4).

  video_ai.py moi "<du-an>" --kich-ban "<file .txt hoặc chữ>" [--giong "vn:Hải Đăng"|nu1|nu2|api:<id>|khong]
                [--toc-do 1.0] [--nghi 0.35] [--nen "#0B0B0D"] [--khung 9:16]
  video_ai.py moi "<du-an>" --giay 20 [--nen …]            video không lời (chữ + nhạc + cảnh AI)

Làm: mỗi dòng / câu kịch bản đọc thành 1 file giọng → ghép (nghỉ giữa câu) thành voice.wav → prepare.py chế độ CHỈ TIẾNG (nền màu
--nen, dài đúng bằng giọng, tự nhận chữ cho phụ đề). Ghi `cau.json` (mốc giây từng câu trên video) + `kich-ban-voice.txt` (đúng chữ, để
sửa phụ đề). Sau đó viết plan.json: mỗi câu = 1 cảnh AI (canh_ai.py san / moi) hoặc ảnh broll, chữ nhấn, phụ đề, nhạc.
Giọng có sẵn: tts.py ds. Đã có file giọng thật → chép thành <du-an>/voice.wav rồi chạy prepare.py, không cần lệnh này.
"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SR = 48000


def _opt(a, k, d=None):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d


def split_script(text: str) -> list:
    """mỗi dòng = 1 câu; dòng dài (> 160 ký tự) tách tiếp theo dấu . ! ? …"""
    out = []
    for ln in text.splitlines():
        ln = ln.strip().lstrip("-•*").strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [ln] if len(ln) <= 160 else re.split(r"(?<=[.!?…])\s+", ln)
        out += [p.strip() for p in parts if p.strip()]
    return out


def _dur(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] != "moi":
        sys.exit(__doc__)
    folder = Path(a[1])
    if not folder.is_absolute() and not folder.exists() and not str(a[1]).startswith(("cho-edit", ".")):
        folder = ROOT / "cho-edit" / a[1]
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.glob("*.mp4")) or any(folder.glob("*.mov")):
        sys.exit(f"{folder} đã có clip quay — lệnh này chỉ dành cho video KHÔNG clip gốc")
    work = folder / "_work"
    work.mkdir(exist_ok=True)
    nen = _opt(a, "--nen", "#EFE9DC")
    if _opt(a, "--khung"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "khung.py"), str(folder), _opt(a, "--khung")], check=False)
    ks = _opt(a, "--kich-ban")
    giong = _opt(a, "--giong", "vn:Hải Đăng")
    gap = float(_opt(a, "--nghi", 0.35))
    speed = float(_opt(a, "--toc-do", 1.0))
    for old in folder.glob("voice.*"):
        old.unlink()
    voice = folder / "voice.wav"
    cau = []
    if ks and giong != "khong":
        text = Path(ks).read_text(encoding="utf-8") if Path(ks).exists() else ks
        lines = split_script(text)
        if not lines:
            sys.exit("Kịch bản trống")
        import tts
        print(f"Đọc {len(lines)} câu bằng giọng {giong}…", flush=True)
        parts, t = [], 0.5
        for i, ln in enumerate(lines):
            r = tts.say(folder, ln, giong, speed)
            p = folder / r["path"]
            d = _dur(p)
            cau.append({"i": i + 1, "text": ln, "start": round(t, 2), "end": round(t + d, 2)})
            parts.append(p)
            t += d + gap
            print(f"  {i + 1:2d}. {cau[-1]['start']:6.2f}–{cau[-1]['end']:6.2f}s  {ln}", flush=True)
        # ghép: 0,5s đầu + từng câu + nghỉ + 1,2s cuối, cùng 48 kHz mono
        lst = work / "_ghep_giong.txt"
        sil = work / "_lang.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{gap:.3f}", str(sil)], check=True)
        head = work / "_dau.wav"
        tail = work / "_cuoi.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", "0.5", str(head)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", "1.2", str(tail)], check=True)
        norm = []
        for k, p in enumerate(parts):
            q = work / f"_cau{k:02d}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(q)], check=True)
            norm.append(q)
        seq = [head] + [x for q in norm for x in (q, sil)][:-1] + [tail]
        lst.write_text("".join(f"file '{x.as_posix()}'\n" for x in seq), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(voice)], check=True)
        for x in [lst, sil, head, tail, *norm]:
            x.unlink(missing_ok=True)
        (folder / "kich-ban-voice.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        giay = float(_opt(a, "--giay", 0) or 0)
        if giay <= 0:
            sys.exit("Cần --kich-ban (có giọng) hoặc --giay <số giây> (không lời)")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{giay:.3f}", str(voice)], check=True)
        if ks:  # kịch bản nhưng không đọc: chia đều thời lượng cho các câu (làm chữ)
            text = Path(ks).read_text(encoding="utf-8") if Path(ks).exists() else ks
            lines = split_script(text)
            st = giay / max(1, len(lines))
            cau = [{"i": i + 1, "text": ln, "start": round(i * st, 2), "end": round((i + 1) * st - 0.2, 2)} for i, ln in enumerate(lines)]
    (folder / "cau.json").write_text(json.dumps(cau, ensure_ascii=False, indent=1), encoding="utf-8")
    (folder / "video-ai.json").write_text(json.dumps({"mode": "khong-clip", "nen": nen, "giong": None if not cau or giong == "khong" else giong,
                                                       "khongLoi": not (ks and giong != "khong")}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Chuẩn bị (nền + nhận chữ cho phụ đề)…", flush=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "prepare.py"), str(folder)])
    if r.returncode:
        sys.exit("prepare.py lỗi")
    info = json.loads((work / "info.json").read_text(encoding="utf-8"))
    d = info.get("durationSec")
    print(f"\nXONG: video không clip dài {d}s — {folder}")
    print("Tiếp theo (TAI-LIEU.md mục \"VIDEO KHÔNG CẦN CLIP\"): chọn phong cách (bộ có cảnh AI: Sang trọng màu nước, Art Deco vàng kim,")
    print("Du lịch cổ điển, Bauhaus số liệu) → mỗi câu trong cau.json = 1 cảnh (canh_ai.py san) → plan.json → soat → render.")


if __name__ == "__main__":
    main()
