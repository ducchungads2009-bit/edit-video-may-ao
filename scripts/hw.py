"""Tăng tốc: chọn bộ mã hóa video bằng phần cứng (nếu máy có) + số luồng CPU.

- macOS: h264_videotoolbox (chip Apple)  · Windows/Linux: h264_nvenc (NVIDIA) → h264_qsv (Intel) → h264_amf (AMD)
- Không có / lỗi → libx264 veryfast. Kết quả dò lưu ở _cache/hw.json (dò 1 lần).
- Tắt trong settings.json: "hwEncode": false.
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "_cache" / "hw.json"


def cores() -> int:
    return max(1, os.cpu_count() or 2)


def _settings() -> dict:
    try:
        return json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _works(enc: str) -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
                            "-frames:v", "8", "-c:v", enc, "-f", "null", "-"], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def encoder() -> str:
    """tên bộ mã hóa H.264 nhanh nhất dùng được trên máy này"""
    if _settings().get("hwEncode") is False:
        return "libx264"
    key = f"{platform.system()}-{platform.machine()}"
    try:  # mỗi kiểu máy 1 dòng (máy thật & máy ảo dùng chung thư mục)
        c = json.loads(CACHE.read_text(encoding="utf-8"))
        c = {c["key"]: c["enc"]} if "key" in c else c
    except Exception:
        c = {}
    if key in c:
        return c[key]
    cands = ["h264_videotoolbox"] if sys.platform == "darwin" else ["h264_nvenc", "h264_qsv", "h264_amf"]
    enc = next((e for e in cands if _works(e)), "libx264")
    c[key] = enc
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c), encoding="utf-8")
    return enc


def venc() -> list:
    """tham số ffmpeg để mã hóa video trung gian chất lượng cao (1080x1920, 30fps), khung khóa mỗi 1 giây
    (giúp bộ dựng nhảy tới khung bất kỳ nhanh hơn)."""
    e = encoder()
    if e == "h264_videotoolbox":
        return ["-c:v", e, "-b:v", "20M", "-maxrate", "30M", "-bufsize", "40M", "-g", "30", "-pix_fmt", "yuv420p", "-allow_sw", "1"]
    if e == "h264_nvenc":
        return ["-c:v", e, "-preset", "p4", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-g", "30", "-pix_fmt", "yuv420p"]
    if e == "h264_qsv":
        return ["-c:v", e, "-global_quality", "20", "-look_ahead", "0", "-g", "30", "-pix_fmt", "nv12"]
    if e == "h264_amf":
        return ["-c:v", e, "-quality", "speed", "-rc", "cqp", "-qp_i", "18", "-qp_p", "20", "-g", "30", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", "30", "-pix_fmt", "yuv420p"]


def run_enc(cmd_before: list, cmd_after: list, out: str):
    """chạy ffmpeg với bộ mã hóa nhanh; lỗi thì tự chạy lại bằng libx264"""
    r = subprocess.run([*cmd_before, *venc(), *cmd_after, out], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode and encoder() != "libx264":
        print(f"[!] Mã hóa bằng phần cứng ({encoder()}) lỗi, chạy lại bằng CPU")
        r = subprocess.run([*cmd_before, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", "30", "-pix_fmt", "yuv420p",
                            *cmd_after, out], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r


def mem_gb() -> float:
    """RAM còn dùng được (GB) — Linux /proc/meminfo, tính cả giới hạn cgroup của máy ảo; không đọc được → 0"""
    gb = 0.0
    try:
        for ln in open("/proc/meminfo"):
            if ln.startswith("MemAvailable:"):
                gb = int(ln.split()[1]) / 1e6
                break
    except Exception:  # noqa
        return 0.0
    for f in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = open(f).read().strip()
            if v.isdigit() and int(v) < 1 << 50:
                used = 0
                for g in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
                    try:
                        used = int(open(g).read().strip())
                        break
                    except Exception:  # noqa
                        pass
                gb = min(gb or 1e9, (int(v) - used) / 1e9)
                break
        except Exception:  # noqa
            pass
    return max(0.0, gb)


def render_flags() -> list:
    """tham số tăng tốc cho Remotion"""
    s = _settings()
    n = cores()
    conc = s.get("renderConcurrency") or (n if n <= 4 else min(n - 1, 10))
    cache = 2000000000
    ram = mem_gb()
    if ram and not s.get("renderConcurrency"):  # máy ảo ít RAM (ChatGPT…): mỗi tab dựng ~0,8 GB → bớt tab, bớt bộ nhớ đệm video
        conc = max(1, min(conc, int((ram - 1.0) / 0.8)))
        cache = int(min(cache, max(256e6, ram * 1e9 * 0.2)))
    flags = [f"--concurrency={conc}", f"--offthreadvideo-cache-size-in-bytes={cache}", "--x264-preset=faster"]
    if sys.platform == "darwin" and s.get("renderHwAccel", True):  # mã hóa bằng chip Apple (VideoToolbox)
        flags.append("--hardware-acceleration=if-possible")
    gl = s.get("renderGl", "angle" if sys.platform in ("darwin", "win32") else "")
    if gl:
        flags.append(f"--gl={gl}")
    return flags


if __name__ == "__main__":
    print("CPU:", cores(), "nhân · bộ mã hóa:", encoder(), "· Remotion:", " ".join(render_flags()))
