"""Tiến độ & thời gian dự kiến.

1) Việc máy chạy (prepare / render / style / assemble / trim): các script gọi Tien(...) để ghi
   <folder>/_work/tien-do-may.json  {action, label, pct, msg, eta, elapsed, running, ok}
   Thời gian dự kiến tự học từ các lần chạy trước trên chính máy này (_thong-ke.json ở thư mục tool).

2) Việc Claude làm: Claude chạy lệnh này ở ĐẦU mỗi bước (xem CLAUDE.md):
     python scripts/tiendo.py buoc "<folder>" <số bước 1-6>      (1 Đọc · 2 Dàn ý · 3 Minh họa · 4 Kịch bản · 5 Kiểm tra · 6 Xuất)
     python scripts/tiendo.py xong "<folder>"
     python scripts/tiendo.py dot <số thứ tự dự án> <tổng số dự án> "<tên dự án>"   (chế độ tự động nhiều dự án)
   -> ghi <folder>/_work/tien-do.json (và <thư mục dự án>/_tien-do-chung.json) cho giao diện hiện thanh tiến trình.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATS = ROOT / "_thong-ke.json"
LABEL = {"xongtho": "Xuất bản thô + Chuẩn bị", "prepare": "Chuẩn bị", "render": "Xuất video", "check": "Kiểm tra nhanh", "style": "Phân tích video mẫu",
         "assemble": "Ghép cảnh theo voice", "trim": "Cắt đoạn thừa", "stock": "Tải ảnh stock", "stylepreview": "Vẽ ảnh phong cách", "tachnguoi": "Tách người khỏi nền", "beauty": "Làm đẹp người", "chemo": "Dò biển số / mã QR"}
# giây xử lý cho mỗi giây video (dùng khi chưa có số liệu trên máy này) + phần cố định
FACTOR = {"xongtho": 4.0, "prepare": 1.0, "render": 6.0, "check": 0.0, "style": 0.5, "assemble": 0.3, "trim": 0.5, "stock": 0.0, "stylepreview": 0.0, "tachnguoi": 3.0, "beauty": 4.0, "chemo": 0.6}
FIXED = {"xongtho": 30, "prepare": 10, "render": 20, "check": 30, "style": 10, "assemble": 5, "trim": 5, "stock": 8, "stylepreview": 25, "tachnguoi": 8, "beauty": 10, "chemo": 10}
STEPS = ["Đọc nội dung & tư liệu", "Lên dàn ý", "Tìm minh họa / stock", "Viết kịch bản dựng", "Tự kiểm tra", "Xuất video"]
STEP_SEC = [60, 150, 240, 180, 180, None]  # None = theo ước lượng render


def _stats() -> dict:
    try:
        return json.loads(STATS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_stats(s: dict):
    try:
        STATS.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _learn(group: str, key: str, val: float, lo: float = 0):
    if val < lo:  # bỏ số liệu bất thường (bấm thử, bỏ dở)
        return
    s = _stats()
    lst = s.setdefault(group, {}).setdefault(key, [])
    lst.append(round(val, 3))
    s[group][key] = lst[-20:]
    _save_stats(s)


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def estimate(action: str, video_sec: float) -> float:
    """số giây dự kiến cho 1 việc máy chạy, theo độ dài video."""
    # bỏ các lần chạy "không làm gì" (đã có sẵn kết quả, xong trong vài giây) — chúng kéo ước lượng xuống ~0 -> thanh đứng 95%
    vals = [v for v in _stats().get("may", {}).get(action, []) if v >= FACTOR.get(action, 1.0) * 0.08][-8:]
    m = _median(vals) if len(vals) >= 3 else None
    f = m if m is not None else FACTOR.get(action, 1.0)
    return FIXED.get(action, 10) + f * max(1.0, video_sec or 0)


def step_estimate(k: int, video_sec: float) -> float:
    m = _median(_stats().get("claude", {}).get(str(k), [])[-8:])
    if m is not None:
        return m
    return STEP_SEC[k - 1] if STEP_SEC[k - 1] else estimate("render", video_sec) + 60


def fmt(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60} phút {sec % 60:02d} giây" if sec >= 60 else f"{sec} giây"


class Tien:
    """Ghi tiến độ việc máy chạy. pct 0–1."""

    def __init__(self, folder: Path, action: str, video_sec: float):
        self.f = Path(folder) / "_work" / "tien-do-may.json"
        self.f.parent.mkdir(parents=True, exist_ok=True)
        self.action, self.vs = action, video_sec or 0
        self.t0 = time.time()
        self.est = estimate(action, self.vs)
        self.last = 0.0
        self.pct = 0.0
        self._stop = True
        self.update(0.0, "Bắt đầu", force=True)

    def update(self, pct: float, msg: str = "", eta: float = None, force: bool = False):
        now = time.time()
        self.pct = max(self.pct, min(0.99, pct))
        if not force and now - self.last < 1.0:
            return
        self.last = now
        el = now - self.t0
        if el > self.est * 0.85:  # chạy lâu hơn dự kiến -> nới dự kiến (thanh chậm lại thay vì đứng "95% · còn 6 giây")
            self.est = el / 0.85 * 1.25
        if eta is None:
            by_est = max(0.0, self.est - el)
            if self.pct > 0.05:
                by_rate = el / self.pct * (1 - self.pct)
                w = min(1.0, self.pct * 1.6)
                eta = w * by_rate + (1 - w) * by_est
            else:
                eta = by_est
        self._write({"action": self.action, "label": LABEL.get(self.action, self.action), "pct": round(self.pct, 3),
                     "msg": msg, "eta": round(eta), "elapsed": round(el), "est": round(self.est), "running": True})

    def clock(self, msg: str = "Đang xử lý"):
        """cho việc không tự báo % (1 lệnh ffmpeg dài): % chạy theo thời gian dự kiến."""
        import threading

        def loop():
            while not self._stop:
                el = time.time() - self.t0
                self.update(min(0.95, el / max(1.0, self.est) * 0.95), msg)
                time.sleep(2)
        self._stop = False
        threading.Thread(target=loop, daemon=True).start()

    def done(self, ok: bool = True, msg: str = ""):
        self._stop = True
        el = time.time() - self.t0
        self._write({"action": self.action, "label": LABEL.get(self.action, self.action), "pct": 1 if ok else self.pct,
                     "msg": msg or ("Xong" if ok else "Lỗi / đã dừng"), "eta": 0, "elapsed": round(el), "running": False, "ok": ok})
        if ok and self.vs > 0 and el > FIXED.get(self.action, 10) + 3:  # học tốc độ máy (bỏ lần chạy không làm gì)
            _learn("may", self.action, max(0.0, el - FIXED.get(self.action, 10)) / self.vs)

    def _write(self, d: dict):
        d["updated"] = time.time()
        try:
            self.f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def wrap(folder: Path, action: str, video_sec: float, fn, *args, msg: str = "Đang xử lý"):
    """chạy fn(*args) kèm tiến độ theo thời gian dự kiến; tự ghi xong/lỗi."""
    t = Tien(folder, action, video_sec)
    t.clock(msg)
    try:
        r = fn(*args)
    except BaseException:
        t.done(False)
        raise
    t.done(True)
    return r


def _video_sec(folder: Path) -> float:
    try:
        return float(json.loads((folder / "_work" / "info.json").read_text(encoding="utf-8"))["durationSec"])
    except Exception:
        return 60.0


STOP_MSG = ("⛔ NGƯỜI DÙNG ĐÃ BẤM DỪNG trong giao diện — DỪNG NGAY: không chạy thêm lệnh, không sửa file nào của dự án này nữa; "
            "chỉ báo người dùng đã dừng ở bước nào. (Họ copy lệnh mới trong giao diện thì cờ dừng tự gỡ.)")


def stopped(folder) -> bool:
    """người dùng bấm "Dừng Claude" trong giao diện -> _work/_dung.json (hết hiệu lực sau 12 giờ)"""
    try:
        f = Path(folder) / "_work" / "_dung.json"
        return f.exists() and time.time() - f.stat().st_mtime < 12 * 3600
    except Exception:
        return False


def stop_guard(folder):
    """gọi đầu các lệnh Claude hay dùng: đã bấm dừng -> in thông báo và thoát mã 9"""
    if stopped(folder):
        print(STOP_MSG, flush=True)
        sys.exit(9)


def claude_step(folder: Path, k: int):
    """Claude bắt đầu bước k (1..6): ghi tien-do.json + học thời gian bước trước."""
    f = folder / "_work" / "tien-do.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    try:
        old = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        old = {}
    if old.get("dang_lam") and old.get("buoc_so") and old.get("bat_dau_buoc") and old["buoc_so"] < k:
        _learn("claude", str(old["buoc_so"]), now - old["bat_dau_buoc"], 15)  # học thời gian thật của bước vừa xong
    vs = _video_sec(folder)
    left = sum(step_estimate(j, vs) for j in range(k, len(STEPS) + 1))
    done_part = sum(step_estimate(j, vs) for j in range(1, k))
    d = {"dang_lam": True, "buoc_so": k, "buoc": STEPS[k - 1], "cac_buoc": STEPS,
         "pct": round(done_part / max(1.0, done_part + left), 3), "con_lai_giay": round(left),
         "bat_dau": old.get("bat_dau") if old.get("dang_lam") else now, "bat_dau_buoc": now, "cap_nhat": now}
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"Tiến độ: bước {k}/{len(STEPS)} — {STEPS[k - 1]} · còn khoảng {fmt(left)}")


def claude_done(folder: Path):
    f = folder / "_work" / "tien-do.json"
    try:
        old = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        old = {}
    now = time.time()
    if old.get("dang_lam") and old.get("bat_dau_buoc"):
        _learn("claude", str(old["buoc_so"]), now - old["bat_dau_buoc"], 15)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"dang_lam": False, "xong": True, "cap_nhat": now,
                             "tong_giay": round(now - old.get("bat_dau", now))}, ensure_ascii=False), encoding="utf-8")
    print("Tiến độ: xong.")


def batch(n: int, total: int, name: str):
    """chế độ tự động: đang làm dự án n/total."""
    s = json.loads((ROOT / "settings.json").read_text(encoding="utf-8")) if (ROOT / "settings.json").exists() else {}
    ws = Path(s.get("workspace") or ROOT / "cho-edit")
    per = sum(step_estimate(j, 60) for j in range(1, len(STEPS) + 1))
    d = {"dang_lam": n <= total, "so": n, "tong": total, "du_an": name, "con_lai_giay": round(per * (total - n + 1)),
         "cap_nhat": time.time()}
    (ws / "_tien-do-chung.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"Tiến độ chung: dự án {n}/{total} ({name}) · còn khoảng {fmt(d['con_lai_giay'])}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "buoc":
        stop_guard(Path(a[1]).resolve())
        claude_step(Path(a[1]).resolve(), max(1, min(len(STEPS), int(a[2]))))
    elif len(a) >= 2 and a[0] == "xong":
        claude_done(Path(a[1]).resolve())
    elif len(a) >= 4 and a[0] == "dot":
        batch(int(a[1]), int(a[2]), a[3])
    elif len(a) >= 2 and a[0] == "het":  # xong cả đợt tự động
        s = json.loads((ROOT / "settings.json").read_text(encoding="utf-8")) if (ROOT / "settings.json").exists() else {}
        ws = Path(s.get("workspace") or ROOT / "cho-edit")
        (ws / "_tien-do-chung.json").write_text(json.dumps({"dang_lam": False, "cap_nhat": time.time()}), encoding="utf-8")
    else:
        sys.exit(__doc__)
