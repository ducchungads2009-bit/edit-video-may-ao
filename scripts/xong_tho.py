"""XONG DỰNG THÔ -> xuất bản thô thành 1 video liền rồi CHUẨN BỊ đầy đủ trên video đó.

    python scripts/xong_tho.py "<folder>" [--cat-lang]

1. render.py --tho: chỉ cắt ghép / chuyển cảnh / khung hình / tốc độ người dùng đã làm (không chữ, không phụ đề).
2. Clip gốc + thu-tu.txt + ghi chú clip + plan dựng thô chuyển vào <folder>/_nguon-tho/ (giữ lại, không xoá).
3. Bản thô thành <folder>/dung-tho.mp4 = clip DUY NHẤT của dự án; _work cũ được dọn.
4. prepare.py đầy đủ (nhận giọng, phụ đề, dò mặt...) trên dung-tho.mp4 — từ đây mọi thứ làm trên video đã dựng thô.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main(folder: Path):
    work = folder / "_work"
    info = json.loads((work / "info.json").read_text(encoding="utf-8")) if (work / "info.json").exists() else {}
    if not info.get("tho"):
        sys.exit("Dự án này không ở chế độ dựng thô (đã chuẩn bị đầy đủ rồi).")
    if not (folder / "plan.json").exists():
        (folder / "plan.json").write_text('{"template": "review", "elements": []}', encoding="utf-8")
    print("1/2 Xuất bản dựng thô…", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "render.py"), str(folder), "--tho"])
    out = work / "tho_out.mp4"
    if r.returncode or not out.exists():
        sys.exit("Không xuất được bản dựng thô — xem lỗi phía trên.")
    from prepare import list_clips
    src = folder / "_nguon-tho"
    src.mkdir(exist_ok=True)

    def stash(p: Path):
        rel = p.relative_to(folder)
        dst = src / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        k = 1
        while dst.exists():
            dst = dst.with_name(f"{p.stem}-{k}{p.suffix}")
            k += 1
        shutil.move(str(p), str(dst))

    for c in list_clips(folder):
        stash(c)
    for n in ("thu-tu.txt", "ghi-chu-clip.json"):
        if (folder / n).exists():
            stash(folder / n)
    if (folder / "plan.json").exists():
        shutil.move(str(folder / "plan.json"), str(src / "plan-dung-tho.json"))
    final = folder / "dung-tho.mp4"
    shutil.move(str(out), str(final))
    for p in list(work.iterdir()):  # dọn kết quả ghép thô cũ (giữ thư mục _work)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
    print("2/2 Chuẩn bị đầy đủ trên video đã dựng thô…", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "prepare.py"), str(folder)])
    if r.returncode:
        sys.exit(r.returncode)
    if "--cat-lang" in sys.argv:  # tự cắt à / ừ / khoảng lặng còn sót (không cần Claude)
        print("Tự cắt từ đệm & khoảng lặng…", flush=True)
        subprocess.run([sys.executable, str(HERE / "cat_lang.py"), str(folder), "--chay"])
    print(f"XONG DỰNG THÔ: {final.name} — clip gốc cất ở _nguon-tho/")


if __name__ == "__main__":
    import kich_hoat  # bản quyền: chưa kích hoạt / hết hạn -> dừng
    kich_hoat.require()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
