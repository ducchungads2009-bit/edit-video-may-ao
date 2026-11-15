"""Dựng nhanh 1 bản DEMO áp phong cách lên video (không cần Claude, không tốn lượt) — để xem / chỉnh phong cách trước khi lưu.

    python scripts/demo_style.py "<folder>"

Đọc lời nói (_work/words.json) + phong cách của dự án -> plan.json: phụ đề, chữ nhấn (cụm từ của câu) theo mật độ / vị trí
/ kiểu hiện của phong cách, zoom theo mức zoom, đổi cỡ cảnh nếu phong cách có, tiếng hiệu ứng theo mật độ. Rồi tự dời chữ khỏi mặt.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STOP = {"là", "và", "thì", "mà", "của", "cho", "với", "các", "những", "một", "này", "đó", "nhé", "ạ", "à", "ừ", "thế", "nào", "được",
        "có", "không", "cũng", "đã", "đang", "sẽ", "rồi", "lại", "ra", "vào", "lên", "xuống", "ở", "trong", "ngoài", "nhưng", "nên", "vì"}


def sentences(words: list, gap: float = 0.45) -> list:
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > gap or str(cur[-1]["w"])[-1:] in ".?!"):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def phrase(sent: list, n: int = 5) -> tuple:
    """cụm 2–n chữ đáng chú ý nhất trong câu (nhiều chữ "nặng", có số) -> (text, start, end)"""
    best, bs = None, -1.0
    if 2 <= len(sent) <= 6:  # câu ngắn: lấy trọn câu
        return " ".join(str(x["w"]) for x in sent), sent[0]["start"], sent[-1]["end"]
    for i in range(len(sent)):
        for L in range(3, n + 1):
            seg = sent[i:i + L]
            if len(seg) < L:
                break
            ws = [re.sub(r"[^\w]", "", str(x["w"]).lower()) for x in seg]
            if ws[0] in STOP or ws[-1] in STOP:
                continue
            sc = sum(len(w) for w in ws if w not in STOP) + 6 * sum(any(c.isdigit() for c in w) for w in ws) + L
            sc += 6 if i + L == len(sent) else 0  # trọn đến cuối câu -> đọc tự nhiên hơn
            sc += 3 if i == 0 else 0
            if sc > bs:
                best, bs = seg, sc
    if not best:
        best = sent[: min(n, len(sent))]
    return " ".join(str(x["w"]) for x in best), best[0]["start"], best[-1]["end"]


def build(folder: Path) -> dict:
    import phongcach
    work = folder / "_work"
    words = json.loads((work / "words.json").read_text(encoding="utf-8"))
    info = json.loads((work / "info.json").read_text(encoding="utf-8"))
    dur = float(info["durationSec"])
    eff = phongcach.apply(folder, {"template": "review"})
    st = eff.get("style") or {}
    zone = (st.get("layout") or {}).get("textZone") or "top"
    y = {"top": 320, "middle": 760, "bottom": 1180}.get(zone, 320)
    pace = st.get("pace") or {}
    every = 10.0 / max(0.8, min(4.0, float(pace.get("chuHinhMoi10s") or 0) / 4 or 2.0))  # giãn đều theo mật độ chữ của mẫu
    every = max(3.0, min(8.0, every))
    upper = (st.get("text") or {}).get("upper")
    els, last = [], -99.0
    for s in sentences(words):
        if s[0]["start"] - last < every or s[-1]["end"] - s[0]["start"] < 0.8:
            continue
        txt, a, b = phrase(s)
        txt = txt.upper() if upper else txt
        e = {"type": "text", "start": round(max(0.0, a - 0.1), 2), "end": round(min(dur, max(b + 1.2, a + 2.0)), 2), "text": txt, "y": y}
        els.append(e)
        last = a
    zl = (st.get("effects") or {}).get("zoom") or "vừa"
    zgap = {"nhiều": 5.0, "vừa": 8.0, "ít": 14.0}.get(zl)
    if zgap and not (st.get("effects") or {}).get("shots"):
        zs = (st.get("effects") or {}).get("zoomStyle") or "punch"
        t = 2.5
        while t < dur - 2:
            els.append({"type": "zoom", "start": round(t, 2), "end": round(t + (3.0 if zs in ("in", "smooth") else 1.2), 2), "style": zs, "scale": 1.18})
            t += zgap
    plan = {"template": "review", "captions": True, "captionsFrom": 0, "fixes": [], "elements": sorted(els, key=lambda e: e["start"]), "_demo": True}
    if (st.get("effects") or {}).get("shots") == "auto":
        import canh_co
        plan = canh_co.run(folder, (st.get("effects") or {}).get("shotDensity", "thua"), plan)
    if isinstance((st.get("effects") or {}).get("overlay"), list):  # phong cách có lớp hiệu ứng phủ (kiểu AE)
        try:
            import ae
            plan, _ = ae.tu_gan_plan(plan, st, dur)
        except Exception as e:  # noqa
            print("[!] Không đặt được lớp hiệu ứng:", e)
    try:
        import sfx as sfxmod
        plan = sfxmod.auto(plan, "vua", False, True, st)
    except Exception as e:  # noqa
        print("[!] Không gán được tiếng hiệu ứng:", e)
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "tranh_mat.py"), str(folder), "--sua"])
    print(f"Plan demo: {sum(1 for e in els if e['type'] == 'text')} chữ, {sum(1 for e in els if e['type'] == 'zoom')} zoom -> plan.json")
    return plan


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    build(Path(sys.argv[1]).resolve())
