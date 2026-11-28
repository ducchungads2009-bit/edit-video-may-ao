"""BỘ DỰNG HYPERFRAMES (thay Remotion — không cần giấy phép công ty).

Giữ nguyên toàn bộ khối đồ hoạ trong remotion/src: đóng gói bằng esbuild, gói 'remotion' được thay bằng remotion/hf/shim.tsx.
- Hình: HyperFrames (Apache-2.0) mở trang, tua từng khung (sự kiện hf-seek), chụp + mã hoá, nhiều luồng song song.
- Video trong khung: máy chủ khung ở file này (ffmpeg giải mã tuần tự, trả JPEG/PNG) — trang chỉ hiện <img>.
- Tiếng: trang chạy cả dòng thời gian ở chế độ 'audio', ghi lại khung nào phát file nào / đoạn nào / to bao nhiêu -> trộn bằng numpy.

Dùng như hàm remotion() cũ trong render.py:  run(["render", bundle, comp, out, "--props=...", "--muted", "--scale=0.5"], tien, span)
                                              run(["still", bundle, comp, out.png, "--frame=12", "--props=..."])
"""
import hashlib
import http.server
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
SR = 48000
NODE = "node.exe" if os.name == "nt" else "node"


# ---------------------------------------------------------------- đóng gói
def bundle_dir() -> Path:
    """đóng gói 1 lần theo mã nguồn (≈2 giây), dùng lại; thư mục có public/ (tiếng hiệu ứng...) + public/jobs/ (file từng dự án)"""
    pre = ROOT / "bo-dung-hf"  # bản phát hành: đóng gói sẵn
    if (pre / "bundle.js").exists() and not (ROOT / "remotion" / "src").exists():
        _sync_public(pre)
        return pre
    files = sorted([*(ROOT / "remotion").rglob("*.ts*"), ROOT / "remotion" / "hf" / "build.mjs", ROOT / "remotion" / "fonts.json",
                    ROOT / "package.json"])
    sig = "|".join(f"{p.relative_to(ROOT)}:{p.stat().st_size}:{int(p.stat().st_mtime)}" for p in files if p.exists())
    h = hashlib.md5(sig.encode()).hexdigest()[:10]
    cache = ROOT / "_cache"
    out = cache / f"hfb-{h}"
    if not (out / "bundle.js").exists():
        print("Đóng gói bộ dựng HyperFrames...", flush=True)
        tmp = cache / f"_hfb-{h}"
        shutil.rmtree(tmp, ignore_errors=True)
        r = subprocess.run([NODE, str(ROOT / "remotion" / "hf" / "build.mjs"), str(tmp)], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode or not (tmp / "bundle.js").exists():
            raise RuntimeError("Đóng gói lỗi: " + (r.stderr or r.stdout)[-1500:])
        for old in cache.glob("hfb-*"):
            if old.name != out.name:
                shutil.rmtree(old, ignore_errors=True)
        tmp.replace(out)
    _sync_public(out)
    return out


def _sync_public(bd: Path):
    src = ROOT / "public"
    if not src.exists():
        return
    for p in src.rglob("*"):
        if p.is_file() and "jobs" not in p.relative_to(src).parts:
            d = bd / "public" / p.relative_to(src)
            if not d.exists() or d.stat().st_size != p.stat().st_size:
                d.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if d.exists():
                        d.unlink()
                    os.link(p, d)
                except OSError:
                    shutil.copyfile(p, d)


# ---------------------------------------------------------------- trình duyệt / HyperFrames
def browser_path() -> str:
    """ưu tiên Chrome Headless Shell (nhanh hơn Chrome đầy đủ ~10%), rồi trình duyệt cai-may-ao.sh đã thử chạy được"""
    for k in ("HYPERFRAMES_BROWSER_PATH", "NHM_BROWSER"):
        if os.environ.get(k) and Path(os.environ[k]).exists():
            return os.environ[k]
    rb = os.environ.get("REMOTION_BROWSER", "")
    if rb and "headless" in rb and Path(rb).exists():
        return rb
    home = Path.home()
    pats = ["chs/*/chrome-headless-shell-*/chrome-headless-shell*", ".cache/chs/*/chrome-headless-shell-*/chrome-headless-shell*",
            ".cache/hyperframes/chrome/*/chrome-headless-shell-*/chrome-headless-shell*",
            ".cache/puppeteer/chrome-headless-shell/*/chrome-headless-shell-*/chrome-headless-shell*"]
    for base in (home, ROOT / "_cache"):
        for pat in pats:
            for p in sorted(base.glob(pat), reverse=True):
                if p.is_file() and os.access(p, os.X_OK) and p.suffix in ("", ".exe"):
                    return str(p)
    # Chrome Headless Shell do Remotion tải kèm
    for p in sorted((ROOT / "node_modules").glob(".remotion/chrome-headless-shell/*/chrome-headless-shell*/chrome-headless-shell*")):
        if p.is_file():
            return str(p)
    if rb and Path(rb).exists():
        return rb
    return ""


def hf_bin() -> list:
    for p in (ROOT / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes"),
              ROOT / "_cache" / "hyperframes" / "node_modules" / ".bin" / "hyperframes"):
        if p.exists():
            return [str(p)]
    raise RuntimeError("Chưa cài HyperFrames (npm install)")


def hf_env() -> dict:
    env = dict(os.environ)
    env.update(HYPERFRAMES_NO_TELEMETRY="1", HYPERFRAMES_RENDER_LOCK="off", HYPERFRAMES_NO_AUTO_INSTALL="1", NO_COLOR="1",
               HYPERFRAMES_NO_UPDATE_CHECK="1")
    b = browser_path()
    if b:
        env["HYPERFRAMES_BROWSER_PATH"] = b
    return env


def workers() -> int:
    if os.environ.get("HF_WORKERS"):
        return max(1, int(os.environ["HF_WORKERS"]))
    try:
        from hw import mem_gb
        mem = mem_gb()
    except Exception:  # noqa
        mem = 8
    cpu = os.cpu_count() or 2
    return max(1, min(cpu, int(mem // 1.5), 8))


# ---------------------------------------------------------------- máy chủ khung + tệp tĩnh
class _Dec:
    """1 tiến trình ffmpeg giải mã tuần tự từ khung i0 — xin khung kế tiếp rất nhanh (không tua lại)"""

    def __init__(self, path: str, i0: int, info: dict, alpha: bool, W: int, H: int):
        self.i0, self.next, self.last, self.used = i0, i0, None, time.time()
        self.lock = threading.Lock()
        fps = info["fps"]
        vf = [f"fps={fps}"]
        # thu nhỏ video quá lớn (4K) về cỡ khung; đổi màu đúng chuẩn (BT.709/601, dải TV/PC theo nhãn của file) -> JPEG/PNG trình duyệt hiểu đúng
        vf.append(f"scale='if(gt(a,{W}/{H}),-2,min(iw,{int(W * 1.25)}))':'if(gt(a,{W}/{H}),min(ih,{int(H * 1.25)}),-2)':flags=bicubic"
                  ":in_color_matrix=auto:in_range=auto:out_color_matrix=bt601:out_range=pc")
        dec = ["-c:v", "libvpx-vp9"] if alpha and info.get("codec") == "vp9" else ["-c:v", "libvpx"] if alpha and info.get("codec") == "vp8" else []
        enc = ["-pix_fmt", "rgba", "-c:v", "png", "-compression_level", "1"] if alpha else ["-pix_fmt", "yuvj420p", "-c:v", "mjpeg", "-q:v", "2"]
        cmd = ["ffmpeg", "-loglevel", "error", "-nostdin", *dec, "-ss", f"{i0 / fps:.6f}", "-i", path, "-an", "-sn", "-vf", ",".join(vf),
               "-f", "image2pipe", *enc, "-"]
        self.alpha = alpha
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1 << 20)
        self.buf = b""
        self.eof = False

    def _read(self, n=1 << 16):
        ch = self.p.stdout.read1(n) if hasattr(self.p.stdout, "read1") else self.p.stdout.read(n)
        if not ch:
            self.eof = True
        self.buf += ch

    def _frame(self):
        if self.alpha:  # PNG: 8 byte chữ ký + các khối tới IEND
            while True:
                pos = 8
                while True:
                    if len(self.buf) < pos + 8:
                        break
                    ln = int.from_bytes(self.buf[pos:pos + 4], "big")
                    typ = self.buf[pos + 4:pos + 8]
                    if len(self.buf) < pos + 12 + ln:
                        break
                    pos += 12 + ln
                    if typ == b"IEND":
                        fr, self.buf = self.buf[:pos], self.buf[pos:]
                        return fr
                if self.eof:
                    return None
                self._read()
        st = 2
        while True:
            k = self.buf.find(b"\xff\xd9", st)
            if k >= 0:
                fr, self.buf = self.buf[:k + 2], self.buf[k + 2:]
                return fr
            st = max(2, len(self.buf) - 1)
            if self.eof:
                return None
            self._read()

    def get(self, i: int):
        self.used = time.time()
        if self.last and i <= self.last[0]:
            return self.last[1]
        while self.next <= i:
            fr = self._frame()
            if fr is None:  # hết video: giữ khung cuối
                return self.last[1] if self.last else None
            self.last = (self.next, fr)
            self.next += 1
        return self.last[1]

    def close(self):
        try:
            self.p.kill()
        except Exception:  # noqa
            pass


class Server:
    """máy chủ cục bộ: /f?s=<file>&t=<giây>[&a=1] -> khung video; còn lại: tệp trong thư mục bộ dựng (cho trang chụp ảnh / tiếng)"""

    def __init__(self, root: Path, W=1080, H=1920):
        self.root, self.W, self.H = root, W, H
        self.info, self.decs, self.lock = {}, {}, threading.Lock()
        self.cache = {}  # (file, i, alpha) -> bytes (vài khung gần nhất)
        srv = self

        class H_(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(root), **k)

            def log_message(self, *a):
                pass

            def end_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store" if self.path.startswith("/f?") else "max-age=3600")
                super().end_headers()

            def do_GET(self):
                if self.path.startswith("/f?"):
                    try:
                        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                        b, ct = srv.frame(q["s"][0], float(q["t"][0]), q.get("a", ["0"])[0] == "1")
                    except Exception as e:  # noqa
                        self.send_error(500, str(e)[:200])
                        return
                    if b is None:
                        self.send_error(404, "no frame")
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    try:
                        self.wfile.write(b)
                    except Exception:  # noqa
                        pass
                    return
                return super().do_GET()

        class TS(http.server.ThreadingHTTPServer):
            daemon_threads = True
            request_queue_size = 128

        self.httpd = TS(("127.0.0.1", 0), H_)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def path_of(self, s: str) -> str:
        if re.match(r"^https?:", s):
            return s
        return str((self.root / s.lstrip("/")).resolve())

    def probe(self, path: str) -> dict:
        if path in self.info:
            return self.info[path]
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate,r_frame_rate,codec_name:format=duration",
                            "-of", "json", path], capture_output=True, text=True)
        fps, codec, dur = 30.0, "", 0.0
        try:
            j = json.loads(r.stdout)
            st = j["streams"][0]
            codec = st.get("codec_name", "")
            for k in ("avg_frame_rate", "r_frame_rate"):
                a, b = st.get(k, "0/0").split("/")
                if float(b or 0) > 0 and 1 <= float(a) / float(b) <= 240:
                    fps = float(a) / float(b)
                    break
            dur = float(j.get("format", {}).get("duration") or 0)
        except Exception:  # noqa
            pass
        fps = min(60.0, fps)
        self.info[path] = {"fps": round(fps, 3), "codec": codec, "dur": dur}
        return self.info[path]

    def frame(self, s: str, t: float, alpha: bool):
        path = self.path_of(s)
        info = self.probe(path)
        i = int(math.floor(t * info["fps"] + 1e-3))
        if info["dur"] > 0:
            i = min(i, max(0, int(info["dur"] * info["fps"]) - 1))
        ct = "image/png" if alpha else "image/jpeg"
        key = (path, i, alpha)
        b = self.cache.get(key)
        if b is not None:
            return b, ct
        with self.lock:
            lst = self.decs.setdefault((path, alpha), [])
            best = None
            for d in lst:
                if d.lock.locked():
                    continue
                last_i = d.last[0] if d.last else d.i0 - 1
                if last_i <= i <= d.next + int(2.5 * info["fps"]):
                    if best is None or d.next > best.next:
                        best = d
            if best is None:
                if len(lst) >= 10:  # bỏ bộ giải mã lâu không dùng
                    old = min(lst, key=lambda d: d.used)
                    old.close()
                    lst.remove(old)
                best = _Dec(path, i, info, alpha, self.W, self.H)
                lst.append(best)
            best.lock.acquire()
        try:
            b = best.get(i)
        finally:
            best.lock.release()
        if b is not None:
            self.cache[key] = b
            if len(self.cache) > 48:
                for k in list(self.cache)[:16]:
                    self.cache.pop(k, None)
        return b, ct

    def close(self):
        try:
            self.httpd.shutdown()
        except Exception:  # noqa
            pass
        for lst in self.decs.values():
            for d in lst:
                d.close()


# ---------------------------------------------------------------- trang dựng
def comp_meta(comp: str, props: dict):
    """kích thước + số khung (giống calculateMetadata trong Root.tsx)"""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import khung
        W, H = khung.FORMATS.get(props.get("format") or "9:16", (1080, 1920))
    except Exception:  # noqa
        W, H = 1080, 1920
    if comp == "partial":
        n = sum(b - a for a, b in props.get("__ranges") or [[0, 30]])
    elif comp in ("review", "audio", "challenge"):
        n = round(float(props.get("durationSec") or 10) * FPS)
    elif comp == "fontsheet":
        W, H, n = 1080, 1960, 1
    else:
        W, H, n = 1080, 1920, 60
    return W, H, max(1, int(n))


def write_page(bd: Path, comp: str, props: dict, mode: str, fs_url: str, scale: float = 1.0) -> Path:
    W, H, n = comp_meta(comp, props)
    w, h = int(round(W * scale / 2) * 2), int(round(H * scale / 2) * 2)
    conf = {"comp": comp, "props": props, "fps": FPS, "base": "/public", "fs": fs_url, "mode": mode, "scale": scale}
    js = json.dumps(conf, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>dung</title><link rel="icon" href="data:,">
<script>/* các khối (bản đồ, 3D, React) chạy theo giờ thật như khi dựng bằng Remotion: trả lại setTimeout / rAF / Date gốc
  mà HyperFrames thay bằng giờ ảo; thời gian của khung do sự kiện hf-seek quyết định */
(function(){{var V=window.__HF_VIRTUAL_TIME__;if(!V)return;window.setTimeout=V.originalSetTimeout;window.clearTimeout=V.originalClearTimeout;
window.setInterval=V.originalSetInterval;window.clearInterval=V.originalClearInterval;
if(V.originalRequestAnimationFrame){{window.requestAnimationFrame=V.originalRequestAnimationFrame;window.cancelAnimationFrame=V.originalCancelAnimationFrame;}}
try{{var D=Object.getPrototypeOf(window.Date);if(D&&D!==Function.prototype&&D.now)window.Date=D;}}catch(e){{}}
try{{delete window.performance.now;}}catch(e){{}}}})();</script>
<link rel="stylesheet" href="bundle.css">
<style>html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
#root{{position:relative;overflow:hidden;width:{w}px;height:{h}px}}
#stage{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform-origin:0 0;transform:scale({scale})}}</style>
</head><body>
<div id="root" data-composition-id="main" data-width="{w}" data-height="{h}" data-start="0" data-duration="{n / FPS:.6f}" data-fps="{FPS}"><div id="stage"></div></div>
<script>window.__HF={js};</script>
<script src="bundle.js"></script>
</body></html>"""
    name = f"job-{hashlib.md5((js + mode + str(time.time())).encode()).hexdigest()[:10]}.html"
    p = bd / name
    p.write_text(html, encoding="utf-8")
    return p


# ---------------------------------------------------------------- tiếng
def _decode(path: str, ss: float = 0.0, dur: float = None, rate: float = 1.0):
    import numpy as np
    af = []
    r = rate
    while r > 2.0 + 1e-9:
        af.append("atempo=2.0")
        r /= 2.0
    while r < 0.5 - 1e-9:
        af.append("atempo=0.5")
        r /= 0.5
    if abs(r - 1) > 1e-6:
        af.append(f"atempo={r:.6f}")
    cmd = ["ffmpeg", "-loglevel", "error", "-nostdin"]
    if ss > 0:
        cmd += ["-ss", f"{ss:.6f}"]
    if dur:
        cmd += ["-t", f"{dur:.6f}"]
    cmd += ["-i", path, "-vn", "-ac", "2", "-ar", str(SR)]
    if af:
        cmd += ["-af", ",".join(af)]
    cmd += ["-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(out, dtype=np.float32)
    return a[: len(a) // 2 * 2].reshape(-1, 2)


def _duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def mix_audio(data: dict, root: Path, out: Path):
    """trộn tiếng theo bản ghi từng khung (giống cách Remotion trộn: mỗi đoạn liền mạch 1 lần cắt, âm lượng theo khung)"""
    import numpy as np
    fps, n = data["fps"], data["n"]
    spf = SR / fps
    total = int(round(n * spf))
    mix = np.zeros((total, 2), dtype=np.float32)
    by = {}
    for r in data["recs"]:
        by.setdefault(r["k"], []).append(r)
    full, durs = {}, {}

    def path_of(s):
        return s if re.match(r"^https?:", s) else str((root / s.lstrip("/")).resolve())

    for k, rs in by.items():
        rs.sort(key=lambda x: x["f"])
        p = path_of(rs[0]["src"])
        if not (re.match(r"^https?:", p) or Path(p).exists()):
            print(f"[!] Thiếu file tiếng: {rs[0]['src']}", flush=True)
            continue
        # gói vòng lặp (loop): khung nguồn quay lại s0 khi hết file
        if any(x["loop"] for x in rs):
            if p not in durs:
                durs[p] = _duration(p)
            D = durs[p] * fps
            for x in rs:
                per = D - x["s0"]
                if per > 1:
                    x["m"] = x["s0"] + ((x["m"] - x["s0"]) % per)
        runs, cur = [], []
        for x in rs:
            if cur:
                y = cur[-1]
                if not (x["f"] == y["f"] + 1 and abs(x["m"] - (y["m"] + x["r"])) < 0.02 and abs(x["r"] - y["r"]) < 1e-6):
                    runs.append(cur)
                    cur = []
            cur.append(x)
        if cur:
            runs.append(cur)
        for run in runs:
            f0, m0, rate, cnt = run[0]["f"], run[0]["m"], run[0]["r"], len(run)
            need = int(round(cnt * spf))
            ss = max(0.0, m0 / fps)
            if abs(rate - 1) < 1e-6:
                if p not in full:
                    full[p] = _decode(p)
                src = full[p]
                a0 = int(round(ss * SR))
                seg = src[a0:a0 + need]
            else:
                seg = _decode(p, ss, cnt / fps * rate + 0.1, rate)[:need]
            if not len(seg):
                continue
            # âm lượng: nội suy tuyến tính giữa các khung
            vols = np.array([x["v"] for x in run], dtype=np.float32)
            pos = (np.arange(len(seg), dtype=np.float32) / spf) - 0.5
            env = np.interp(pos, np.arange(cnt, dtype=np.float32), vols).astype(np.float32)
            o0 = int(round(f0 * spf))
            m = min(len(seg), total - o0)
            if m <= 0:
                continue
            mix[o0:o0 + m] += seg[:m] * env[:m, None]
    pcm = (np.clip(mix, -1.0, 1.0) * 32767.0).astype("<i2")
    import wave
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out


def _short(text: str) -> str:
    """rút gọn lỗi trình duyệt: lấy câu lỗi đầu tiên (bỏ ngăn xếp gọi hàm)"""
    for pat in (r"Lỗi khi dựng[^\n|]*", r"lỗi khối: ([^\n|]*)", r"(?:Type|Reference|Range|Syntax)?Error: [^\n|]*"):
        m = re.search(pat, text or "")
        if m:
            return m.group(0)[:400]
    lines = [x for x in (text or "").splitlines() if x.strip() and not re.match(r"^\s*(at\s|\S+ \(https?://)", x)]
    return " / ".join(lines[-3:])[:400]


def _drive(args: list, env: dict, W: int, H: int):
    e = dict(env)
    e.update(HF_W=str(W), HF_H=str(H), NODE_PATH=str(ROOT / "node_modules"))
    r = subprocess.run([NODE, str(ROOT / "remotion" / "hf" / "drive.mjs"), *args], cwd=ROOT, env=e, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError("Trình duyệt lỗi: " + _short((r.stderr or "") + (r.stdout or "")))
    return r


def render_audio(bd: Path, comp: str, props: dict, out: Path, srv: Server = None):
    own = srv is None
    srv = srv or Server(bd)
    try:
        page = write_page(bd, "audio" if comp in ("review", "partial") else comp, props, "audio", srv.url)
        js = out.with_suffix(".json")
        t0 = time.time()
        try:
            _drive(["audio", f"{srv.url}/{page.name}", str(js)], hf_env(), 1080, 1920)
        finally:
            page.unlink(missing_ok=True)
        data = json.loads(js.read_text(encoding="utf-8"))
        js.unlink(missing_ok=True)
        mix_audio(data, bd, out)
        print(f"   tiếng: {len(data['recs'])} bản ghi, {time.time() - t0:.1f}s", flush=True)
        return out
    finally:
        if own:
            srv.close()


# ---------------------------------------------------------------- lệnh kiểu Remotion
_PROG = re.compile(r"@hf-progress\s+(\{.*\})")


def _parse(args):
    pos, opt = [], {}
    for a in args:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            opt[k] = v if _ else True
        else:
            pos.append(a)
    return pos, opt


def run(args, tien=None, span=(0.0, 1.0)):
    pos, opt = _parse(args)
    cmd, bundle, comp, out = pos[0], Path(pos[1]), pos[2], Path(pos[3])
    if not (bundle / "bundle.js").exists():
        bundle = bundle_dir()
    props = json.loads(Path(opt["props"]).read_text(encoding="utf-8")) if opt.get("props") else {}
    scale = float(opt.get("scale") or 1)
    W, H, n = comp_meta(comp, props)
    srv = Server(bundle, W, H)
    env = hf_env()
    env.setdefault("PRODUCER_FORCE_SCREENSHOT", "true")  # bản đồ / 3D cần requestAnimationFrame thật
    try:
        if cmd == "still":
            frames = [int(x) for x in str(opt.get("frame", "0")).split(",")]
            page = write_page(bundle, comp, props, "still", srv.url, scale)
            try:
                pat = str(out.with_name(out.stem + "_%d.png")) if len(frames) > 1 else str(out.with_name("_still_%d.png"))
                _drive(["still", f"{srv.url}/{page.name}", ",".join(map(str, frames)), pat],
                       env, int(round(W * scale / 2) * 2), int(round(H * scale / 2) * 2))
                if len(frames) == 1:
                    Path(pat.replace("%d", "0")).replace(out)
            finally:
                page.unlink(missing_ok=True)
            return
        if cmd != "render":
            raise RuntimeError("lệnh lạ: " + cmd)
        a, b = span
        if opt.get("codec") == "wav":  # chỉ tiếng
            render_audio(bundle, comp, props, out, srv)
            return
        audio = None
        th = None
        if not opt.get("muted"):  # tiếng làm song song với hình
            audio = out.with_name("_hf_audio.wav")
            err = {}

            def _a():
                try:
                    render_audio(bundle, comp, props, audio, srv)
                except Exception as e:  # noqa
                    err["e"] = e
            th = threading.Thread(target=_a, daemon=True)
            th.start()
        page = write_page(bundle, comp, props, "video", srv.url, scale)
        vid = out.with_name("_hf_video.mp4")
        vid.unlink(missing_ok=True)
        nw = int(opt.get("concurrency") or 0) or workers()
        nw = max(1, min(nw, max(1, n // 15)))
        hcmd = [*hf_bin(), "render", str(bundle), "-c", page.name, "-o", str(vid), "--workers", str(nw), "--fps", str(FPS), "--crf",
                str(opt.get("crf") or 18), "--no-wait"]
        if os.environ.get("HF_LOW_MEM") == "0":
            env["PRODUCER_LOW_MEMORY_MODE"] = "false"
        t0 = time.time()
        p = subprocess.Popen(hcmd, cwd=bundle, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", bufsize=1)
        tail = []
        for line in p.stdout:
            line = line.rstrip()
            m = _PROG.search(line)
            if m:
                try:
                    j = json.loads(m.group(1))
                    pct = float(j.get("pct", 0)) / 100
                    if tien:
                        done, tot = j.get("done"), j.get("total")
                        c = str(j.get("code") or "")
                        msg = "Đang mã hóa" if c in ("encode", "assemble", "mux") else "Chuẩn bị" if c in ("compile", "setup", "probe", "extract") \
                            else "Đang dựng khung"
                        tien.update(a + (b - a) * min(0.98, pct), msg=f"{msg} {done}/{tot}" if tot else msg)
                except Exception:  # noqa
                    pass
                continue
            if line.startswith(("[INFO]", "  █", "  ░")) or "█" in line:
                continue
            tail.append(line)
            tail = tail[-40:]
            if re.search(r"error|lỗi|failed|warn", line, re.I) and not re.search(r"Lint:|lint issues|non-blocking|favicon|No index\.html", line):
                print("   [hf] " + line[:300], flush=True)
        p.wait()
        page.unlink(missing_ok=True)
        if p.returncode or not vid.exists():
            print("\n".join(x for x in tail[-30:] if not re.match(r"^\s*(at\s|\S+ \(https?://)", x))[-3000:], flush=True)
            raise RuntimeError("HyperFrames dựng lỗi — " + _short("\n".join(tail)))
        print(f"   hình ({n} khung, {nw} luồng): {time.time() - t0:.0f}s", flush=True)
        if th:
            th.join()
            if err.get("e"):
                raise err["e"]
        if audio and audio.exists():
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v",
                                "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                               capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError("Ghép tiếng lỗi: " + r.stderr[-500:])
            vid.unlink(missing_ok=True)
            audio.unlink(missing_ok=True)
        else:
            vid.replace(out)
    finally:
        srv.close()
