# CẢNH AI — luật viết một cảnh đồ hoạ động (khối `canhAI`)

Gốc: `engine/AUTHORING.md` của LumReels (github.com/lumtekvn/lumreels, MIT — `canh-ai/LICENSE-LumReels.txt`), sửa cho tool.
Đọc HẾT trước khi viết cảnh. Mỗi chữ "mày" / "engine" của bản gốc = bạn / bộ dựng của tool.

## 0. Khi nào dùng cảnh AI
Cảnh AI là đồ hoạ TỰ VIẾT bằng code cho đoạn mà khối có sẵn của tool không làm được: mở đầu thương hiệu, bảng giá / tiến độ
thanh toán động, sa bàn vẽ tay, tranh màu nước tự vẽ, infographic số liệu, kết bài có nút gọi… Nó KHÔNG thay ảnh thật của dự án
(CHAT-LUONG.md mục 2) và KHÔNG thay chữ / phụ đề / thẻ của phong cách đã chọn.
- Chữ trong cảnh theo phong cách của video: đọc `window.CANH.style` (`heading`, `font`, `fonts`, `text.color`…) — hoặc font của mẫu
  khi cả cảnh là một phong cách riêng (mẫu LumReels).
- Một video có lời: cảnh AI ngắn 3–8 giây, nền TRONG SUỐT (lớp phủ trên người nói) hoặc chèn kín khung ở chỗ không có mặt người.
- Video không lời / cảnh trám: cảnh kín khung 4–10 giây được.
- Thư viện 104 mẫu phong cách (10 mẫu hợp BĐS): `canh_ai.py ds [--nhom bds]`, `canh_ai.py xem <id>`. Bản mô tả mẫu tả bằng chữ:
  màu (hex), font, bố cục theo % khung, nhịp theo giây, cách dựng bằng code, mục "Tự kiểm" — dựng theo đúng bản mô tả, ô nội dung
  lấy từ brief (không chép ví dụ trong bản mô tả, không bịa số).

## 1. Quy trình
1. `canh_ai.py moi "<du-an>" <ten> [--mau <id>] [--giay 6] [--nen trong|mau]` → `canh/<ten>/index.html` (khung đúng luật) +
   `MAU.md` (bản mô tả mẫu nếu có `--mau`) + `lib/` (thư viện, không sửa).
2. Viết cảnh trong `index.html`: dữ liệu (giá, tên dự án, SĐT…) để ở khối plan.json `"data"`, cảnh đọc `window.CANH.data`
   (có giá trị mặc định khi thiếu) — sửa chữ không cần sửa code, trang chỉnh sửa / người dùng đổi được.
3. `canh_ai.py thu "<du-an>" <ten>` → `canh/<ten>/_thu.jpg` (5 mốc, ô cờ = vùng trong suốt). MỞ RA XEM, trả lời mục 12 "Tự kiểm"
   của MAU.md từng câu. Sai câu nào sửa câu đó.
4. Thêm khối vào plan.json:
   ```json
   {"type": "canhAI", "start": 3.2, "end": 9.2, "canh": "canh/<ten>", "data": {"tenDuAn": "…", "gia": "4,2 tỷ"}, "z": 30}
   ```
   `from` (giây bắt đầu trong cảnh), `speed`, `fit` (`cover` | `contain` khi khung video khác 9:16), `fadeIn` / `fadeOut` (giây,
   mặc định 0,25), `opacity`, `sfx` (tiếng hiệu ứng lúc khối hiện, như mọi khối). `z` < 20 = dưới phụ đề.
5. `soat.py` tự chạy `canh_ai.py kiem` (luật + font tiếng Việt trong trình duyệt thật). Rồi `render.py --check` xem khung trong video.

## 2. Khung bắt buộc
```html
<!doctype html>
<html lang="vi">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<link rel="stylesheet" href="./lib/fonts/fonts.css" />
<script src="./lib/vendor/gsap.min.js"></script>   <!-- tuỳ chọn -->
<script src="./lib/runtime/scene.js"></script>
<style>
  html, body { margin:0; width:1080px; height:1920px; overflow:hidden; background:transparent; }  /* hoặc màu nền nếu cảnh kín khung */
  #root { position:relative; width:1080px; height:1920px; overflow:hidden; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="6" data-fps="30" data-width="1080" data-height="1920">
  <!-- DOM / SVG / <canvas> của cảnh -->
</div>
<script>
  const D = window.CANH.data;   // dữ liệu từ plan.json
  VideoScene.define({
    duration: 6, fps: 30, width: 1080, height: 1920,   // PHẢI khớp data-* của #root
    setup() { /* dựng DOM/hình 1 lần, ĐỒNG BỘ (hoặc async setup() khi phải chờ font cho canvas) */ },
    render(t) { /* vẽ TOÀN BỘ khung ở giây t */ },
  });
</script>
</body>
</html>
```
- Three.js: `<script type="module"> import * as THREE from './lib/vendor/three.module.js'; … VideoScene.define({…}) </script>`;
  `new THREE.WebGLRenderer({ canvas, antialias:true, alpha:true, preserveDrawingBuffer:true })` (`alpha:true` + `setClearColor(0, 0)`
  khi cảnh trong suốt).
- KHÔNG gọi mạng: cấm `http(s)://`, CDN, Google Fonts, `fetch` ra ngoài. Ảnh / SVG / JSON của cảnh để cạnh `index.html` (ảnh dự án
  thật thì chép vào `canh/<ten>/` — vẫn ưu tiên khối broll cho ảnh phủ kín).
- `window.CANH`: `data` (plan.json), `w`/`h` (cỡ thiết kế 1080×1920), `frameW`/`frameH` (khung video thật), `dur` (độ dài khối),
  `style` (font / màu của phong cách video: `heading`, `font`, `fonts`, `text`, `captions`).

## 3. Luật thời gian (quan trọng nhất)
- **Mọi khung là hàm thuần của t.** `render(t)` phải đặt lại mọi thứ nó đụng tới (style, text, transform, canvas) chỉ dựa vào t. Remotion tua nhảy cóc, lùi, dựng song song nhiều tab và dựng nhanh từng khúc rời.
- Cấm: `Math.random()` (dùng `const r = VideoScene.rng(42)`, tạo mảng ngẫu nhiên MỘT lần ở ngoài render), `Date.now()`, `performance.now()`, `setTimeout/setInterval` để tạo chuyển động, `requestAnimationFrame` tự chạy vòng, CSS `animation`/`transition` (không seek được), `<video>` tự phát.
- Hiệu ứng tích luỹ (hạt bay, vệt mờ): tính lại từ t (vị trí = p0 + v·t), không cộng dồn qua khung.
- `VideoScene.rng(seed)` nhận 1 số nguyên, trả về **một hàm** `r()`; mỗi lần gọi `r()` ra số thực trong [0, 1), cùng seed thì luôn ra cùng chuỗi số. Gọi trong setup (hoặc ngoài render) để sinh dữ liệu cố định:
  ```js
  const r = VideoScene.rng(1234);
  const stars = Array.from({ length: 200 }, () => ({ x: r() * 1080, y: r() * 1920, s: 1 + r() * 3, ph: r() * Math.PI * 2 }));
  // trong render(t): nhấp nháy là hàm của t, không gọi r() nữa
  // const a = 0.5 + 0.5 * Math.sin(t * 3 + star.ph);
  ```
  Đừng gọi `r()` trong render(t): số ra sẽ phụ thuộc thứ tự seek.
- Tiện ích: `VideoScene.prog(t, start, dur)` → 0..1; `VideoScene.ease.outCubic/inOutCubic/outBack/outExpo/linear`; `VideoScene.lerp(a,b,k)`; `VideoScene.fmtNum(n, '.')` → `1.234.567`.
- GSAP (`./lib/vendor/gsap.min.js`, không bắt buộc nạp): được dùng timeline riêng nhưng phải `paused: true` và trong `render(t)` gọi `myTl.seek(t)`. Đơn giản nhất: tự tính trong render.
- Canvas: `clearRect` đầu mỗi render. WebGL/Three: `new THREE.WebGLRenderer({ canvas, antialias:true, preserveDrawingBuffer:true })`, gọi `renderer.render(scene, camera)` trong render(t).
- Shader: truyền `uTime = t` qua uniform, không dùng đồng hồ.

## 4. Font (đủ dấu tiếng Việt)
CHỈ dùng các họ font dưới đây (nằm trong `./lib/fonts/fonts.css`, subset tiếng Việt thật). Soát báo lỗi cảnh khai báo font ngoài
danh sách, và chạy cảnh trong Chrome báo `FONT_OUTSIDE` / `FONT_FALLBACK` / `FONT_WEIGHT` / `FONT_SMALL` / `FONT_DONG` /
`FONT_DIGITS`. Luôn ghi fallback chung (`sans-serif`, `serif`, `monospace`) ở cuối.

| Loại | font-family | weight có sẵn |
|---|---|---|
| sans | `'Be Vietnam Pro'` | 100 200 300 400 500 600 700 800 900 · italic 100 200 300 400 500 600 700 800 900 |
| sans | `'Montserrat'` | 100 200 300 400 500 600 700 800 900 · italic 100 200 300 400 500 600 700 800 900 |
| sans | `'Inter'` | 100 200 300 400 500 600 700 800 900 · italic 100 200 300 400 500 600 700 800 900 |
| sans | `'Roboto'` | 100 200 300 400 500 600 700 800 900 · italic 100 200 300 400 500 600 700 800 900 |
| sans | `'Lexend'` | 100 200 300 400 500 600 700 800 900 |
| sans | `'Nunito'` | 200 300 400 500 600 700 800 900 · italic 200 300 400 500 600 700 800 900 |
| sans | `'Josefin Sans'` | 100 200 300 400 500 600 700 · italic 100 200 300 400 500 600 700 |
| sans | `'Chakra Petch'` | 300 400 500 600 700 · italic 300 400 500 600 700 |
| condensed | `'Oswald'` | 200 300 400 500 600 700 |
| condensed | `'Barlow Condensed'` | 100 200 300 400 500 600 700 800 900 · italic 100 200 300 400 500 600 700 800 900 |
| condensed | `'Saira Condensed'` | 100 200 300 400 500 600 700 800 900 |
| display | `'Anton'` | 400 |
| display | `'Bungee'` | 400 |
| display | `'Paytone One'` | 400 |
| display | `'Baloo 2'` | 400 500 600 700 800 |
| serif | `'Playfair Display'` | 400 500 600 700 800 900 · italic 400 500 600 700 800 900 |
| serif | `'Merriweather'` | 300 400 500 600 700 800 900 · italic 300 400 500 600 700 800 900 |
| serif | `'Cormorant Garamond'` | 300 400 500 600 700 · italic 300 400 500 600 700 |
| script | `'Great Vibes'` | 400 |
| script | `'Imperial Script'` | 400 |
| script | `'Lobster'` | 400 |
| script | `'Pacifico'` | 400 |
| script | `'Dancing Script'` | 400 500 600 700 |
| hand | `'Patrick Hand'` | 400 |
| sans | `'Space Grotesk'` | 300 400 500 600 700 |
| sans | `'Manrope'` | 200 300 400 500 600 700 800 |
| mono | `'Space Mono'` | 400 700 · italic 400 700 |
| mono | `'VT323'` | 400 |
| mono | `'IBM Plex Mono'` | 100 200 300 400 500 600 700 · italic 100 200 300 400 500 600 700 |
| mono | `'JetBrains Mono'` | 100 200 300 400 500 600 700 800 · italic 100 200 300 400 500 600 700 800 |
| display | `'Alfa Slab One'` | 400 |
| display | `'Bangers'` | 400 |
| display | `'Grenze Gotisch'` | 100 200 300 400 500 600 700 800 900 |
| hand | `'Mali'` | 200 300 400 500 600 700 · italic 200 300 400 500 600 700 |
| serif | `'Lora'` | 400 500 600 700 · italic 400 500 600 700 |

Chữ ngoài cảnh (khối text, phụ đề) chỉ có 24 font đầu (remotion/fonts.json); 11 font cuối (Space Grotesk → Lora) chỉ dùng trong cảnh AI.

### Guidance gọi X → dùng Y
Bản mô tả mẫu (`canh-ai/mau/*.md`) có khi gọi font không có ở đây. Số trong ngoặc = số mẫu nhắc tới.
| Guidance ghi | Dùng |
|---|---|
| Nunito (21), Varela Round | `'Nunito'` cùng weight |
| Baloo 2 (15), Fredoka (13), Chewy, Titan One, Luckiest Guy, Bowlby One | `'Baloo 2'` (Fredoka 500–600 → 600; Chewy/Titan/Luckiest/Bowlby → 800) |
| Playfair Display (16), DM Serif Display (11), Abril Fatface, Bodoni Moda | `'Playfair Display'` (DM Serif → 700; Abril/Bodoni → 900) |
| Montserrat (11), Archivo Black, Futura | `'Montserrat'` (Archivo Black → 900; Futura → 500–600) · Josefin Sans → `'Josefin Sans'` |
| Poppins (8) | `'Montserrat'` cùng weight (gần nhất về dáng hình học) |
| Inter (9) | `'Inter'` · Manrope (5) → `'Manrope'` · DM Sans (4), Outfit (4) → `'Manrope'` cùng weight (thân bài dài → `'Be Vietnam Pro'`) |
| Be Vietnam Pro | `'Be Vietnam Pro'` |
| Space Grotesk | `'Space Grotesk'` |
| JetBrains Mono (8) | `'JetBrains Mono'` |
| IBM Plex Mono (6), Courier/Courier New (3), Share Tech Mono | `'IBM Plex Mono'` (Courier máy chữ → `'Space Mono'`) |
| Space Mono (3), Special Elite | `'Space Mono'` |
| Oswald (8), Bebas Neue (5) | `'Oswald'` (Bebas → 600–700, in hoa, letter-spacing 0.02em) |
| Anton (5) | `'Anton'` 400 |
| Barlow Condensed, Roboto Condensed, League Gothic, Teko | `'Barlow Condensed'` · Saira Condensed → `'Saira Condensed'` |
| Cormorant Garamond (7), Cormorant (3), EB Garamond (2), Cinzel (3), Fraunces, Recoleta, Cooper | `'Playfair Display'` (Cormorant/Garamond 300–500 → 400; 600+ → 700; italic → italic 400/700; Cinzel → 700 in hoa, letter-spacing 0.08em; Fraunces/Recoleta/Cooper → 700–900). Tool có `'Cormorant Garamond'` (300–700, italic): dùng được, xem kỹ dấu chồng (§10.5) |
| Jost | `'Montserrat'` 500 |
| Shrikhand, Bungee Shade | `'Bungee'` hoặc `'Lobster'` (tít trang trí, không cho số) |
| Rye, Ultra, Courier Prime | Rye/Ultra → `'Alfa Slab One'`; Courier Prime → `'Space Mono'` |
| Noto Serif JP, Shippori, chữ Hán/Nhật/Hàn | KHÔNG có font CJK: viết chữ Việt (dọc thì `writing-mode: vertical-rl; text-orientation: upright`), con dấu/ký tự Á Đông vẽ bằng SVG |
| DSEG7 / LED 7 đoạn | tự vẽ 7 thanh bằng SVG/canvas |
| Lora (5), Noto Serif, Georgia | `'Lora'` · Merriweather → `'Merriweather'` |
| Alfa Slab One (3), Rockwell | `'Alfa Slab One'` |
| Bungee (4), Monoton, Righteous | `'Bungee'` |
| Bangers | `'Bangers'` |
| Patrick Hand (3), Caveat (3), Kalam (2), Permanent Marker | `'Patrick Hand'` (Permanent Marker → `'Patrick Hand'` + `font-weight:400`, cỡ to) |
| Mali / Itim / viết tay tròn | `'Mali'` |
| Dancing Script | `'Dancing Script'` |
| Pacifico | `'Pacifico'` |
| Lobster | `'Lobster'` |
| VT323 (3), Press Start 2P (3), Silkscreen (3), Pixelify Sans | `'VT323'` (Press Start/Silkscreen: cỡ chữ ×1,6 vì VT323 nhỏ hơn) |
| Rubik (4) | `'Nunito'` 700–800 |
| Helvetica, Arial, Open Sans, Lato | `'Be Vietnam Pro'` · Roboto → `'Roboto'` |
| Impact | `'Anton'` |
| gothic, Blackletter, Fraktur, UnifrakturMaguntia/Cook, Pirata One, MedievalSharp, New Rocker, Old English | `'Grenze Gotisch'` (tít 700–800; thân chữ gothic dài thì 500, kèm chữ cái đầu to). Các font gothic kia không có tiếng Việt. |

### Chờ font trước khi vẽ lên canvas / WebGL
Font CSS chỉ tải khi có phần tử DOM dùng nó. `VideoScene.define` tự chờ font của các phần tử DOM, nhưng chữ vẽ bằng `ctx.fillText` hay texture Three.js thì phải chờ bằng tay:
```js
// define gọi ĐỒNG BỘ ở đầu script (không có await nào đứng trước nó); chờ font TRONG setup async
VideoScene.define({
  duration: 8, fps: 30, width: 1080, height: 1920,
  async setup() {
    await VideoScene.fontsReady(["800 120px 'Barlow Condensed'", "700 64px 'Baloo 2'"]);
    // giờ ctx.font = "800 120px 'Barlow Condensed'"; ctx.fillText('ĐƯỢC', …) mới đúng font, đủ dấu
  },
  render(t) { /* ... */ },
});
```
Đừng viết `await VideoScene.fontsReady(...)` rồi mới gọi `define`: bộ dựng tìm `window.__scene` ngay khi trang nạp, `define` đến muộn thì khung đầu trống. `setup` trả Promise thì runtime tự chờ nó xong mới vẽ khung.
`VideoScene.fontsReady()` không tham số = chờ mọi font mà các phần tử chữ trong DOM đang dùng. Texture chữ Three.js: vẽ canvas sau khi chờ, rồi `new THREE.CanvasTexture(canvas)`; đổi chữ theo t thì vẽ lại và đặt `texture.needsUpdate = true`.

## 5. Chữ tiếng Việt
- Viết đủ dấu, đúng chính tả. Kiểm chữ có dấu trên/dưới (Ữ, Ặ, Ỷ, Ệ, Ọ) không bị cắt hay đè dòng: tiêu đề in hoa nhiều dòng dùng `line-height ≥ 1.08` (dấu nặng của Ệ/Ọ dòng trên rơi đúng vào đầu chữ dòng dưới nếu dòng quá sát), chừa 0,15em trên dòng đầu. `overflow:hidden` trên khối chữ hay cắt mất dấu.
- Tiếng Việt dài hơn tiếng Anh ~20–30%: giới hạn ký tự trong guidance áp cho bản Việt; chữ không vừa thì rút gọn câu, không bóp font dưới 32px.
- Tiền: `3.000.000đ`, `3 triệu` hoặc `VNĐ` — KHÔNG dùng ký hiệu `₫` (nhiều font vẽ sai, soát báo `FONT_DONG`); số lớn tròn hợp lý (`2,07 tỷ`). Dấu ngăn nghìn là dấu chấm, thập phân là dấu phẩy. Số đếm đặt trong font mono để không giật bề ngang.
- Số liệu phải TÍNH THẬT theo công thức và ghi giả định; các phần cộng lại phải khớp tổng.
- **Cỡ chữ tối thiểu 28px** trên khung 1080 (chữ chính ≥ 40px), tính cả khi bị scale nhỏ; soát báo `FONT_SMALL`.
- **Con số không dùng font script/viết tay** (Dancing Script, Lobster, Pacifico, Patrick Hand, Mali): ngày tháng, giá, điểm số, đồng hồ → dùng sans/condensed/mono. Script chỉ cho chữ ký, tên, câu ngắn trang trí.
- **Chữ viền**: `-webkit-text-stroke` vẽ viền đè vào TRONG nét chữ (chữ mảnh đi, dấu tiếng Việt bị lấp). Luôn kèm `paint-order: stroke fill` và đặt độ dày gấp đôi độ viền muốn thấy:
  ```css
  .vien { color:#fff; -webkit-text-stroke: 12px #000; paint-order: stroke fill; }  /* thấy viền ~6px bên ngoài */
  ```
  Hoặc dùng `text-shadow` nhiều lớp (viền tròn, an toàn cho dấu): `text-shadow: 0 0 0 #000, 3px 0 #000, -3px 0 #000, 0 3px #000, 0 -3px #000, 2px 2px #000, -2px 2px #000, 2px -2px #000, -2px -2px #000;`. Canvas: `ctx.lineJoin='round'; ctx.strokeText(...)` TRƯỚC rồi `ctx.fillText(...)` sau.
- Ký hiệu ngoài chữ cái (▲ ▼ ★ ✓ → ♥) nhiều font không có: vẽ bằng SVG/CSS, đừng gõ ký tự (soát báo `FONT_FALLBACK … thiếu glyph`).

## 6. Khung 9:16 và vùng an toàn
- Khung 1080×1920. Lề trái/phải ≥ 54px (5%).
- Trên 0–8% (0–150px) và dưới 82–100% (từ ~1580px) là vùng app (TikTok/Reels/Shorts) có thể che bởi tên kênh, caption, nút. Chữ chính (tiêu đề, số chốt, CTA) nằm trong 8%–82%. Guidance của mẫu đặt thứ gì ở mép (băng chạy, nhãn kênh) thì giữ theo guidance, nhưng đừng để thông tin bắt buộc chỉ nằm ở đó.
- Cột phải 85–100% chiều ngang ở nửa dưới bị nút like/share che: tránh đặt số quan trọng ở đó.

## 7. Xem thử & soát
- `canh_ai.py thu "<du-an>" <ten> [--moc 0,1.5,3] [--data '{…}']` → `_thu.jpg`. `canh_ai.py kiem "<du-an>" [<ten>]` → luật + font.
- Trong video: `render.py "<du-an>" --check 3.5,6` (khung thật, cảnh đè lên video).

## 8. Âm thanh
Cảnh AI không tự có tiếng. Tiếng hiệu ứng theo mốc chuyển động: khối `sfx` của tool (`{"type":"sfx","start":<giây>,"sfx":"<tên>"}` —
tên trong `public/sfx`), đặt ĐÚNG mốc của `prog(t, …)` trong cảnh (giây khối + giây trong cảnh). Nhạc nền: theo CHAT-LUONG.md mục 5.

## 9. Lỗi hay gặp
- Khung 0,0s trống: phần tử đầu tiên phải hiện ở t=0 (hook), đừng để mọi thứ fade-in từ 0.
- Quên đặt lại style ở nhánh else → khi seek lùi phần tử vẫn còn trạng thái cũ.
- Đặt chuyển động bằng CSS transition/animation → render ra đứng im hoặc giật.
- Font chưa nạp: luôn dùng đúng tên họ trong bảng §4. Đừng đo kích thước chữ (offsetWidth) trong setup rồi giữ lại: font có thể nạp sau; đo lại trong render.
- `render` bị gọi trước khi setup xong → lỗi `null.setAttribute`: dựng mọi phần tử trong setup (đồng bộ) hoặc sẵn trong HTML.
- Canvas mờ: đặt thuộc tính `width/height` = kích thước px thật (1080×1920 hoặc kích thước vùng), không chỉ CSS.
- SVG `stroke-dashoffset` cần độ dài path: lấy `path.getTotalLength()` trong setup, không đoán.
- `text-shadow`/`filter: blur` lớn trên nhiều phần tử làm render chậm: giữ ≤ 20 phần tử có glow.
- Viết `NaN`/`undefined` ra màn hình khi t ngoài khoảng: luôn kẹp tiến độ bằng `prog()`.

## 10. Bài học từ 104 cảnh thử (LumReels)
Rút từ đợt dựng thử toàn bộ thư viện mẫu (mỗi mẫu 1 cảnh 8 giây, render trên máy không có GPU rời). Guidance của mẫu nào còn ghi khác mục này thì làm theo mục này.

### 10.1 Màu Three.js bị tối / bạc
- Texture vẽ từ canvas (chữ, hoạ tiết): `tex.colorSpace = THREE.SRGBColorSpace` ngay sau `new THREE.CanvasTexture(canvas)`. Thiếu dòng này màu nhạt và bạc.
- `ShaderMaterial` tự viết: cuối fragment shader thêm `#include <colorspace_fragment>` (sau dòng gán `gl_FragColor`), nếu không cả cảnh tối hẳn so với vật liệu chuẩn. Dùng tone mapping thì thêm `#include <tonemapping_fragment>` trước nó.
- `RawShaderMaterial` không có các chunk này: tự đổi `pow(c, vec3(1.0/2.2))` hoặc dùng `ShaderMaterial`.

### 10.2 Bloom rẻ (thay UnrealBloomPass)
`./lib/vendor` chỉ có Three.js lõi (`three.module.js`, bản 0.170), KHÔNG có `examples/jsm` (không UnrealBloomPass, BokehPass, EffectComposer, Reflector, RoomEnvironment, RoundedBoxGeometry, TextGeometry, Line2, mergeGeometries, ContactShadows). Đừng import chúng. Bloom làm thế này:
- **Three.js**: tạo `WebGLRenderTarget` bằng ¼ kích thước khung (270×480). Mỗi khung: ẩn vật không phát sáng (hoặc đổi sang vật liệu đen), render cảnh vào target đó; hiện lại, render cảnh chính; rồi vẽ 1 mặt phẳng phủ khung lấy texture target (`LinearFilter`, phóng to = tự nhoè), `blending: THREE.AdditiveBlending`, `depthTest:false`, cường độ 0,6–1,2. Muốn quầng rộng hơn: làm thêm 1 target ⅛ và cộng cả hai.
- **Canvas 2D**: vẽ các vật phát sáng lên 1 canvas nhỏ (¼ khung), rồi `ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(nho, 0, 0, 1080, 1920)` (phóng to là nhoè). Quầng neon của nét: vẽ chồng 3 nét cùng đường, rộng dần (×1, ×3, ×6) và mờ dần (alpha 1 / 0,25 / 0,08), không dùng `shadowBlur` hay `filter: blur()` mỗi khung.
- Sprite quầng: 1 texture gradient tròn vẽ 1 lần trong setup, đặt sau mỗi đèn với `AdditiveBlending`.

### 10.3 DOF giả theo độ sâu (thay BokehPass)
- Chia cảnh thành 2–3 tầng (xa / giữa / gần). Tầng xa render vào target ½ hoặc ¼ độ phân giải rồi phóng to (mờ tự nhiên), tầng nét render đủ độ phân giải đè lên.
- Vật đơn lẻ (lá, hạt bụi, đèn mờ phía trước): vẽ sẵn bản mờ thành texture trong setup (canvas `filter='blur(12px)'` gọi 1 lần), mỗi khung chỉ chọn bản theo độ sâu.
- 2D/DOM: lớp xa đặt sẵn `filter: blur()` tĩnh (không đổi theo t) hoặc vẽ trước lên canvas nhỏ.

### 10.4 Phản chiếu sàn bằng lật trục (thay Reflector)
- Three.js: `const refl = vat.clone(); refl.scale.y = -1; refl.position.y = 2*sanY - vat.position.y;` (cập nhật mỗi khung theo vật thật), đặt dưới một mặt sàn bán trong (`MeshBasicMaterial` màu sàn, `transparent:true, opacity:0.7–0.85`) và thêm mặt phẳng gradient mờ dần theo khoảng cách. Vật liệu bản lật đặt `side: THREE.DoubleSide` (lật trục đảo pháp tuyến).
- Canvas: `ctx.save(); ctx.translate(0, 2*sanY); ctx.scale(1, -1); veVat(); ctx.restore();` rồi phủ gradient màu sàn từ alpha 0,4 → 1.

### 10.5 Font
- **Cormorant Garamond**: LumReels thấy dấu mũ ê/ô/â (và ế, ộ, ẩ) lệch cao. Tool vẫn dùng Cormorant cho bộ Sang trọng BĐS (đã duyệt bằng mắt) — trong cảnh AI dùng được, nhưng chữ Việt có nhiều dấu chồng thì xem kỹ ảnh `_thu.jpg`; lệch thì đổi `'Playfair Display'` (số liệu thêm `font-variant-numeric: lining-nums`).
- Playfair Display không có 900 italic: dùng italic 700. Be Vietnam Pro trong tool có đủ 100–900 và italic.
- VT323 là font pixel duy nhất (nét mảnh): làm đậm bằng `text-shadow: 2px 0 currentColor, 0 2px currentColor, 2px 2px currentColor`.
- Patrick Hand là font cọ/viết tay duy nhất (mảnh): làm dày bằng viền `paint-order: stroke fill` cùng màu chữ.
- Tít in hoa có dấu nhiều dòng (Á, Í, Ỗ, Ế): `line-height ≥ 1.05` với font hẹp, `≥ 1.12` với serif.
- Không có font CJK, không có font slab ngoài Alfa Slab One, không có glyph ▲▼★✓→¡ trong đa số font: vẽ bằng SVG.

### 10.6 Thứ tự khởi tạo
- `VideoScene.define({...})` gọi đồng bộ ở đầu script, không có `await` đứng trước. Mọi việc phải chờ (font cho canvas/texture, dựng texture chữ) đặt trong `async setup()` (xem §4).
- Vẽ WebGL rồi dùng lại làm ảnh cho canvas 2D/DOM: renderer bật `preserveDrawingBuffer:true` và `ctx.drawImage(glCanvas, …)` ngay trong render(t). Đừng dùng `toDataURL()` làm `background-image` (bất đồng bộ, hay chụp ra khung trống).
- Hiệu ứng "vệt tích luỹ" (vẽ đè nền alpha nhỏ qua nhiều khung) trái luật §3: tính lại vệt từ lịch sử quỹ đạo — vẽ N vị trí trước đó `p(t - k·dt)` với alpha giảm dần.

### 10.7 Shader nhiều chất liệu / nhiều cảnh
- Mỗi pixel chỉ tính chất liệu đang hiện: rẽ nhánh bằng uniform (`if (uScene < 0.5) {...} else {...}`), lúc chuyển cảnh chỉ tính 2 chất liệu ở dải chuyển, không gọi cả 8 hàm rồi `mix`.
- Texture nguồn (canvas vẽ chữ/hình đưa vào shader) để ½ độ phân giải và chỉ upload lại (`needsUpdate = true`) khi nội dung đổi, không phải mọi khung.
- Nhiễu toàn khung: đọc 1 texture nhiễu 256×256 dựng sẵn thay cho nhiều tầng `sin`/fbm tính tại chỗ.

### 10.8 Ngân sách hiệu năng
Máy render là CPU (WebGL phần mềm). Mỗi khung phải chụp xong **dưới 1 giây ở 1080×1920**; cảnh 8 giây = 240 khung, render bị dừng ở 10 phút. Những thứ đã làm cảnh vượt giới hạn trong đợt thử:
| Đừng | Làm thay |
|---|---|
| `feTurbulence` / `feDisplacementMap` đổi tham số theo t | dựng 3–4 bản nhiễu/nét sôi tĩnh trong setup, mỗi khung chọn 1 bản (đổi 8–12 lần/giây) hoặc rung toạ độ |
| `<pattern>` SVG xoay/dời theo t, tram chấm bằng pattern SVG | canvas `createPattern` vẽ 1 lần, xoay bằng `ctx.rotate` |
| `mix-blend-mode`, `filter`, `backdrop-filter` trên lớp toàn khung | vẽ sẵn lớp texture/lão hoá lên canvas 1 lần; trộn màu bằng gradient thường hoặc trong shader |
| `filter: blur()`, `shadowBlur`, `text-shadow` lớn đổi theo t | bản mờ vẽ sẵn (§10.3), quầng chồng nét (§10.2), ≤ 20 phần tử có glow |
| Shadow map 2048 + `PCFSoftShadowMap`, `PointLight` đổ bóng cho từng đèn | shadow map 1024 + `PCFShadowMap`, tối đa 1 đèn đổ bóng; bóng tiếp đất = đĩa gradient tối dưới vật; đèn nhỏ thì nướng sáng vào vertex color/`MeshBasicMaterial` |
| Hàng chục lớp vỏ (lông, len) × nhiều vật | ≤ 18 lớp vỏ cho cả cảnh |
| Hàng nghìn nét canvas vẽ lại mỗi khung | vẽ phần đã xong lên canvas đệm 1 lần (cache theo mốc), mỗi khung chỉ vẽ phần đang mọc; hoặc 1 lệnh vẽ WebGL (`InstancedMesh`/`Points`) |
| Upload 2 canvas 1080×1920 vào texture mỗi khung | texture ½ độ phân giải, chỉ upload khi đổi |
Kiểm nhanh: `canh_ai.py thu "<du-an>" <ten> --moc 4` — 1 khung mất quá vài giây là cảnh sẽ làm video dựng rất lâu (máy ảo ~10 giây dựng / 1 giây video, cảnh nặng còn chậm hơn).

### 10.9 Thay các addon Three.js khác
| Guidance cũ gọi | Làm bằng Three.js lõi |
|---|---|
| RoomEnvironment / PMREM từ HDR | `scene.environment = pmrem.fromScene(phongTuDung).texture` với `const pmrem = new THREE.PMREMGenerator(renderer)` và `phongTuDung` = 1 hộp `BoxGeometry` mặt trong (`side: BackSide`) + 2–3 tấm `MeshBasicMaterial` sáng làm softbox; dựng 1 lần trong setup. Hoặc bỏ environment, dùng `HemisphereLight` + 1 `DirectionalLight` |
| RoundedBoxGeometry / CapsuleGeometry addon | `THREE.CapsuleGeometry` có sẵn trong lõi; hộp bo góc = `ExtrudeGeometry` từ `Shape` hình chữ nhật bo góc (`bevelEnabled:true, bevelSize` nhỏ) |
| TextGeometry / FontLoader | chữ 3D giả: vẽ chữ lên canvas → `CanvasTexture` trên `PlaneGeometry`, xếp 6–10 lớp plane lùi dần màu tối hơn để ra độ dày đùn; hoặc chữ DOM chồng trên canvas WebGL |
| Line2 / nét dày | dải `PlaneGeometry`/`TubeGeometry` theo đường cong, hoặc vẽ nét trên canvas 2D rồi làm texture |
| mergeGeometries | `InstancedMesh` cho vật lặp lại; vật khác nhau thì để nhiều mesh (vài chục mesh vẫn nhẹ) |
| ContactShadows | đĩa `CircleGeometry` + texture gradient tròn tối, đặt sát sàn dưới vật, co giãn theo độ cao vật |

### 10.10 Shader GLSL hỏng lặng lẽ
- Đừng đặt tên biến/hàm GLSL trùng từ khoá hoặc từ dành riêng của GLSL ES 3.0 (Three.js biên dịch shader ở WebGL2): `patch`, `sample`, `input`, `output`, `filter`, `active`, `common`, `partition`, `smooth`, `flat`, `centroid`, `buffer`, `shared`, `resource`, `texture` (đã là hàm), `half`, `fixed`, `superp`, `namespace`, `using`. Shader không biên dịch thì Three.js chỉ in lỗi ra console, preview vẫn chạy nhưng vật đó biến mất hoặc đen — hiệu ứng mất mà không ai báo.
- Đặt tên có tiền tố (`vPatch`, `uSample`, `colIn`) cho an toàn. Lỗi biên dịch shader chỉ thấy khi XEM ảnh `_thu.jpg`: vật biến mất / đen là phải soát tên biến.

### 10.11 Môi trường phản chiếu giả (không có HDR)
Vật kim loại/kính/men bóng cần thứ để phản chiếu. Dựng 1 "phòng softbox" nhỏ trong setup rồi nướng ra environment:
```js
const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene();
envScene.add(new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10), new THREE.MeshBasicMaterial({ color: 0x202024, side: THREE.BackSide })));
for (const [x, y, z, w, h, c] of [[0, 4.9, 0, 6, 2, 0xffffff], [-4.9, 1, 0, 3, 4, 0xffe2c0], [4.9, 0, 1, 2, 5, 0xc0d8ff]]) {
  const p = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide }));
  p.position.set(x, y, z); p.lookAt(0, 0, 0); envScene.add(p);   // tấm phẳng phát sáng = softbox
}
scene.environment = pmrem.fromScene(envScene, 0.02).texture;     // 1 lần, không làm lại mỗi khung
```
Đổi màu/vị trí tấm softbox để đổi "ánh phòng" phản chiếu trên vật; nền thật của cảnh vẫn là `scene.background` riêng.
