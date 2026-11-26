"""Nhờ MÁY THẬT chạy việc nặng (chuẩn bị, xuất video, chụp khung, tách người...) qua giao diện đang mở.

Claude thường chạy lệnh trong một máy ảo nhỏ (ít nhân, ít RAM, không dùng được chip/card đồ họa) — chạy ffmpeg / Remotion
ở đó chậm gấp nhiều lần. Giao diện (giao-dien.command / .bat) chạy thẳng trên máy người dùng và dùng hết sức máy, nên
lệnh này gửi việc cho giao diện rồi chờ kết quả. Giao diện chưa mở -> tự chạy tại chỗ (chậm hơn).

  python scripts/nho_may.py prepare  "<folder>"
  python scripts/nho_may.py check    "<folder>" 5,20
  python scripts/nho_may.py render   "<folder>"
  python scripts/nho_may.py trim|assemble|style|tachnguoi "<folder>"
  python scripts/nho_may.py stock    "<folder>" <tham số stock.py get>
  python scripts/nho_may.py stocksearch "<folder>" <ten> "<từ khóa>" [--ov] [--video]   # tìm stock bằng mạng máy thật
  python scripts/nho_may.py bando    "<folder>" "Dự án" "Tiện ích 1" "Tiện ích 2"   # toạ độ + đường đi cho khối bản đồ
  python scripts/nho_may.py cho <mã>          # việc dài: chờ tiếp việc đã gửi
  python scripts/nho_may.py may               # giao diện có đang mở không

Mỗi lần chờ tối đa ~150 giây (giới hạn lệnh của Claude); chưa xong thì in mã để gọi `cho <mã>` tiếp.
"""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
RELAY = ROOT / "_cache" / "nho-may"
BEAT = ROOT / "_cache" / "may.json"
WAIT = float(os.environ.get("NHO_MAY_WAIT", 150))
LOCAL = {
    "prepare": lambda f, a: ["scripts/prepare.py", f, *a[:1]],
    "xongtho": lambda f, a: ["scripts/xong_tho.py", f, *a[:1]],
    "check": lambda f, a: ["scripts/render.py", f, "--check", a[0] if a else "2,10,20"],
    "render": lambda f, a: ["scripts/render.py", f, *a],
    "stock": lambda f, a: ["scripts/stock.py", "get", f, *a],
    "stocksearch": lambda f, a: ["scripts/stock.py", "search", f, *a],
    "bando": lambda f, a: ["scripts/ban_do.py", f, *a],
    "trim": lambda f, a: ["scripts/trim.py", f],
    "assemble": lambda f, a: ["scripts/assemble.py", f],
    "style": lambda f, a: ["scripts/style.py", f],
    "tachnguoi": lambda f, a: ["scripts/tach_nguoi.py", f],
    "mat": lambda f, a: ["scripts/mat.py", f],
    "chemo": lambda f, a: ["scripts/che_mo.py", f, *a],
    "tay": lambda f, a: ["scripts/tay.py", f, *a],
}


def alive():
    try:
        b = json.loads(BEAT.read_text(encoding="utf-8"))
        return b if abs(time.time() - b["t"]) < 15 else None
    except Exception:
        return None


def progress(folder: str):
    try:
        d = Path(folder)
        if not d.is_dir():
            d = ROOT / "cho-edit" / folder
        p = json.loads((d / "_work" / "tien-do-may.json").read_text(encoding="utf-8"))
        if p.get("running"):
            return f"{p.get('label', '')} {int(p.get('pct', 0) * 100)}% — {p.get('msg', '')}"
    except Exception:
        pass
    return ""


def _fdir(folder: str) -> Path:
    d = Path(folder)
    return d if d.is_dir() else ROOT / "cho-edit" / folder


def _stopped(folder: str) -> bool:
    try:
        from tiendo import stopped
        return bool(folder) and stopped(_fdir(folder))
    except Exception:
        return False


def wait(rid: str, folder: str = "") -> int:
    out = RELAY / f"{rid}.xong.json"
    t0, last = time.time(), ""
    while time.time() - t0 < WAIT:
        if _stopped(folder):
            from tiendo import STOP_MSG
            (RELAY / f"{rid}.json").unlink(missing_ok=True)  # chưa nhận thì huỷ luôn
            print(STOP_MSG, flush=True)
            return 9
        if out.exists():
            try:
                r = json.loads(out.read_text(encoding="utf-8"))
            except Exception:
                time.sleep(0.5)
                continue
            print(r.get("log", "")[-3000:])
            print("== XONG (máy thật) ==" if r.get("ok") else "== LỖI (máy thật) — xem log ở trên ==")
            return 0 if r.get("ok") else 1
        pg = progress(folder) if folder else ""
        if pg and pg != last:
            print(pg, flush=True)
            last = pg
        time.sleep(2)
    print(f"Vẫn đang chạy trên máy thật. Chờ tiếp: python scripts/nho_may.py cho {rid}" + (f" {folder}" if folder else ""))
    return 3


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "may":
        b = alive()
        print(f"Giao diện đang mở trên {b['os']} — việc nặng sẽ chạy trên máy thật." if b else "Giao diện CHƯA mở (việc nặng sẽ chạy tại chỗ, chậm).")
        return 0
    if a[0] == "cho":
        return wait(a[1], a[2] if len(a) > 2 else "")
    action, folder, rest = a[0], Path(a[1]).name if len(a) > 1 else "", a[2:]
    if action not in LOCAL or not folder:
        sys.exit(__doc__)
    if _stopped(a[1]):
        from tiendo import STOP_MSG
        print(STOP_MSG, flush=True)
        return 9
    if alive():
        RELAY.mkdir(parents=True, exist_ok=True)
        rid = time.strftime("%H%M%S") + "-" + uuid.uuid4().hex[:6]
        tmp = RELAY / f"{rid}.tmp"
        tmp.write_text(json.dumps({"folder": folder, "action": action, "args": rest}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(RELAY / f"{rid}.json")
        b = alive()
        q = " (đang chờ việc khác xong)" if b and b.get("running") else ""
        print(f"Đã gửi '{action}' cho máy thật{q}. Mã: {rid}", flush=True)
        return wait(rid, a[1])
    print("[!] Giao diện chưa mở — chạy tại chỗ (chậm hơn nhiều). Nên nhờ người dùng mở giao-dien rồi chạy lại.", flush=True)
    f = str(Path(a[1]).resolve())
    return subprocess.call([sys.executable, *LOCAL[action](f, rest)], cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
