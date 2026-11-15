"""GIỌNG ĐỌC AI QUA API (giọng clone của người dùng) — audio-api.nghiencuuai.com.

Cài đặt (⚙ Cài đặt → Giọng đọc AI qua API), lưu trong settings.json (KHÔNG chia sẻ file này):
  "ttsApi": {"key": "tts_...", "voices": [{"id": "voice-12ce2dd4", "name": "Giọng của tôi"}],
             "mode": "fast|standard", "model": "omnivoice", "language": "vi", "url": "..."}

  python scripts/tts_api.py "<folder>" "Nội dung" [--giong voice-xxx] [--toc-do 1.0] [--che-do fast|standard] [--voice]
     -> file wav trong assets/giong-doc/ (in đường dẫn + độ dài)
     --voice: lưu thành voice.wav của dự án (chế độ VOICE) + kich-ban-voice.txt
  python scripts/tts_api.py ds      -> danh sách giọng đã cài
Bài dài tự chia thành từng đoạn (theo câu) rồi ghép lại, giữa các đoạn nghỉ ngắn.
"""
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "settings.json"
URL = "https://audio-api.nghiencuuai.com/api/v1/voice-clone/generate"
MAX_CHARS = 450  # mỗi lần gửi tối đa ~450 ký tự (bài dài chia nhỏ cho chắc)


def cfg() -> dict:
    try:
        s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        s = {}
    c = s.get("ttsApi") or {}
    c.setdefault("voices", [])
    c.setdefault("mode", "fast")
    c.setdefault("model", "omnivoice")
    c.setdefault("language", "vi")
    return c


def voices() -> list:
    return [v for v in cfg().get("voices", []) if v.get("id")]


def ready() -> bool:
    c = cfg()
    return bool(c.get("key")) and bool(voices())


def chunks(text: str, n: int = MAX_CHARS) -> list:
    """chia theo đoạn / câu, mỗi phần ≤ n ký tự"""
    out = []
    for para in [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]:
        cur = ""
        for s in re.split(r"(?<=[.!?…;:])\s+", para):
            s = s.strip()
            if not s:
                continue
            while len(s) > n:  # câu quá dài -> cắt ở dấu phẩy / khoảng trắng gần nhất
                k = max(s.rfind(",", 0, n), s.rfind(" ", 0, n))
                k = k if k > n // 3 else n
                if cur:
                    out.append(cur)
                    cur = ""
                out.append(s[:k + 1].strip())
                s = s[k + 1:].strip()
            if len(cur) + len(s) + 1 > n and cur:
                out.append(cur)
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            out.append(cur)
    return out


def _err(code: int, body: str) -> str:
    try:
        j = json.loads(body)
        msg = j.get("detail") or j.get("error") or j.get("message") or body
        msg = json.dumps(msg, ensure_ascii=False) if not isinstance(msg, str) else msg
    except Exception:
        msg = body
    hint = {401: "API key sai hoặc đã hết hạn — kiểm tra lại ở ⚙ Cài đặt",
            403: "API key không có quyền dùng giọng này",
            402: "Tài khoản hết lượt / hết tiền", 429: "Gửi quá nhiều — đợi một lúc rồi thử lại",
            404: "Không thấy giọng (voice id sai?)"}.get(code, "")
    return f"Lỗi API giọng đọc ({code}){': ' + hint if hint else ''} — {str(msg)[:300]}"


def gen(text: str, voice_id: str, speed: float = 1.0, mode: str = None, timeout: int = 300) -> tuple:
    """1 lần gọi API -> (wav bytes, độ dài giây)"""
    c = cfg()
    if not c.get("key"):
        raise RuntimeError("Chưa nhập API key giọng đọc (⚙ Cài đặt → Giọng đọc AI qua API)")
    body = json.dumps({"voice_id": voice_id, "gen_text": text, "model": c.get("model") or "omnivoice",
                       "language": c.get("language") or "vi", "mode": mode or c.get("mode") or "fast",
                       "speed": round(float(speed), 2)}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(c.get("url") or URL, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {c['key']}", "Content-Type": "application/json",
                                          "User-Agent": "video-tool"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(_err(e.code, e.read().decode("utf-8", "replace")))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Không kết nối được máy chủ giọng đọc (cần mạng): {e.reason}")
    if not data.get("audio_base64"):
        raise RuntimeError("API không trả về âm thanh: " + json.dumps(data, ensure_ascii=False)[:300])
    return base64.b64decode(data["audio_base64"]), float(data.get("duration_sec") or 0)


def _dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def say(folder: Path, text: str, voice_id: str = None, speed: float = 1.0, mode: str = None, out: Path = None,
        progress=None) -> dict:
    """đọc cả bài -> wav trong dự án. progress(k, n) báo tiến độ từng đoạn."""
    text = text.strip()
    if not text:
        raise ValueError("Chưa có nội dung để đọc")
    vs = voices()
    voice_id = voice_id or (cfg().get("default") or (vs[0]["id"] if vs else ""))
    if not voice_id:
        raise RuntimeError("Chưa có giọng nào (⚙ Cài đặt → Giọng đọc AI qua API → thêm voice id)")
    mode = mode or cfg().get("mode") or "fast"
    parts = chunks(text)
    if out is None:
        d = folder / "assets" / "giong-doc"
        d.mkdir(parents=True, exist_ok=True)
        h = hashlib.md5(f"{voice_id}|{speed}|{mode}|{text}".encode()).hexdigest()[:8]
        out = d / f"giong-api_{h}.wav"
        if out.exists():
            return {"path": out.relative_to(folder).as_posix(), "dur": round(_dur(out), 2), "parts": len(parts)}
    with tempfile.TemporaryDirectory() as td:
        files = []
        for k, t in enumerate(parts):
            if progress:
                progress(k, len(parts))
            wav, _ = gen(t, voice_id, speed, mode)
            p = Path(td) / f"p{k:03d}.wav"
            p.write_bytes(wav)
            files.append(p)
        if progress:
            progress(len(parts), len(parts))
        out.parent.mkdir(parents=True, exist_ok=True)
        if len(files) == 1:
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(files[0]), "-ar", "48000", str(out)],
                               capture_output=True, text=True)
        else:  # ghép các đoạn, nghỉ 0,25s giữa các đoạn
            ins = sum([["-i", str(p)] for p in files], [])
            fl = "".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,apad=pad_dur=0.25[a{i}];" for i in range(len(files)))
            fl += "".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1[o]"
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fl, "-map", "[o]", str(out)],
                               capture_output=True, text=True)
        if r.returncode or not out.exists():
            raise RuntimeError("Không ghép được giọng đọc: " + r.stderr[-300:])
    return {"path": out.relative_to(folder).as_posix() if folder in out.parents else str(out), "dur": round(_dur(out), 2), "parts": len(parts)}


def make_voice(folder: Path, text: str, voice_id: str = None, speed: float = 1.0, mode: str = None, progress=None) -> dict:
    """kịch bản -> voice.wav của dự án (chế độ VOICE) + kich-ban-voice.txt (đúng chữ, dùng sửa phụ đề)"""
    from prepare import AUDIO_EXT, VOICE_NAMES
    tmp = folder / "_work" / "voice_moi.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    r = say(folder, text, voice_id, speed, mode, out=tmp, progress=progress)
    for old in folder.iterdir():  # chỉ giữ 1 file voice
        if old.is_file() and old.suffix.lower() in AUDIO_EXT and old.stem.lower() in VOICE_NAMES:
            old.unlink()
    tmp.replace(folder / "voice.wav")
    (folder / "kich-ban-voice.txt").write_text(text.strip() + "\n", encoding="utf-8")
    for k in ("plan.json", "canh.json"):  # kịch bản dựng cũ không còn khớp voice mới
        if (folder / k).exists():
            (folder / k).replace(folder / ("_cu-" + k))
    return {"path": "voice.wav", "dur": r["dur"], "parts": r["parts"]}


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    a = sys.argv[1:]
    if a[:1] == ["ds"]:
        c = cfg()
        print("API key:", "đã nhập" if c.get("key") else "CHƯA nhập")
        for v in voices():
            print(f"  {v['id']}  {v.get('name', '')}")
        sys.exit(0)
    if len(a) < 2:
        sys.exit(__doc__)

    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    folder = Path(a[0]).resolve()
    text = a[1]
    if Path(text).is_file():  # truyền đường dẫn file kịch bản
        text = Path(text).read_text(encoding="utf-8")
    sp = float(opt("--toc-do", 1.0))
    pr = lambda k, n: print(f"Đang đọc đoạn {min(k + 1, n)}/{n}…", flush=True)  # noqa: E731
    fn = make_voice if "--voice" in a else say
    print(json.dumps(fn(folder, text, opt("--giong"), sp, opt("--che-do"), progress=pr), ensure_ascii=False))
