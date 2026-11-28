# CHUẨN CHẤT LƯỢNG VIDEO — bắt buộc cho MỌI AI (Claude, ChatGPT Công việc, Codex) và MỌI phong cách

Mục tiêu: dù AI nào dựng, trên máy tính hay máy ảo, video ra cùng một chất lượng. Đọc HẾT file này trước khi viết plan.json.
Video chuẩn để đối chiếu: dự án "hai van bay sang trong" (27/11/2026) — ảnh phối cảnh thật phủ kín màn hình và lia chậm, chữ có
chân thanh mảnh, tiêu đề tô chuyển sắc vàng champagne, chữ nhấn thư pháp chữ hoa uốn lượn (Imperial Script), nhạc piano nhẹ, không hộp màu, không ghi nguồn giữa màn hình.

Cách gọi lệnh: trên máy tính dùng `python scripts/nho_may.py <việc> …` (xem CLAUDE.md / AGENTS.md); trên máy ảo dùng
`./chay.sh <script>.py …` (xem KY-NANG.md / CHATGPT.md). Bên dưới ghi tên script, tự đổi theo nơi đang chạy.

## 1. Làm bằng công cụ của tool — KHÔNG tự viết đường dựng riêng
- Ghép clip + giọng đọc: `thu-tu.txt` + `prepare` (mục giọng đọc / nhiều clip). Cắt: `segments` trong plan.json.
- KHÔNG tự viết script ffmpeg / PIL / Python để ghép clip, ghép tiếng, cắt, dựng khung ảnh, phủ nền màu hay sinh plan.json hàng
  loạt. Script phụ chỉ được dùng để ĐO / KIỂM TRA. Tool thiếu tính năng → nói với người dùng, đừng tự dựng thay.
- Viết plan.json bằng tay theo tài liệu khối (huong-dan/khoi.md trên máy tính, TAI-LIEU.md Bước 5 trên máy ảo).

## 2. Minh hoạ — ẢNH THẬT TRƯỚC, STOCK SAU
1. Video nói về một DỰ ÁN / địa danh / sản phẩm cụ thể, hoặc brief nhờ "tìm hình ảnh về dự án" → BẮT BUỘC dùng ảnh thật của đúng
   dự án đó (phối cảnh, tiện ích, mặt bằng, ảnh thực tế). Không thay bằng cảnh thiên nhiên / thành phố chung chung.
2. Tìm: tìm web tên dự án + "phối cảnh" / "tiện ích" / "mặt bằng". Ưu tiên trang chủ đầu tư và sàn chính thức (vd
   market.vinhomes.vn), rồi báo lớn. Mở trang lấy link ảnh LỚN NHẤT (link có cỡ kiểu `/900x600/` thường đổi được sang
   `/2025x1350/`). Ảnh phải cao ≥ 1300 px; ảnh nhỏ hơn thì tìm bản khác.
3. Tải: `stock.py url "<folder>" <tên-ngắn> "<link ảnh>"` (máy tính: `nho_may.py stockurl …`; webp tự đổi jpg).
   Ảnh Creative Commons thêm `--nguon "Ảnh: <tác giả> · <giấy phép> · <nguồn>"`.
   Bị chặn mạng / tải lỗi → KHÔNG hỏi, KHÔNG báo người dùng giữa chừng: tự thử tiếp (a) cùng ảnh ở trang khác (báo, trang môi giới,
   CDN ảnh của trang đó), (b) cỡ ảnh khác của cùng link, (c) mục 4 dưới. Chỉ ghi vào bao-cao.md những ảnh không lấy được.
4. Cảnh không có ảnh dự án (đèo, núi, địa danh lân cận) → Openverse ảnh địa danh thật (`stock.py search … --ov`). Cuối cùng mới
   Pixabay. Không lấy ảnh người thật nhận rõ mặt, không lấy ảnh có tên / nội dung tiêu cực (vd "Ecocide…").
5. Ghi nguồn: ảnh phối cảnh của chính dự án người dùng đang bán → KHÔNG ghi trên hình, ghi link trang vào bao-cao.md. Ảnh CC BY
   → để tool tự chèn dòng nhỏ ở góc. TUYỆT ĐỐI không đặt khối chữ ghi nguồn giữa màn hình.

## 3. Cách đặt ảnh / video minh hoạ
- Ảnh NGANG trong khung dọc: broll `"fit": "cover"` (phủ kín) + LIA NGANG `"panFrom"` → `"panTo"` (0–1, vd 0.2→0.5 hoặc
  0.8→0.5; hai ảnh liền nhau lia ngược chiều), `"transition": "fade"`, `"exit": "fade"`, `"inDur": 0.6`.
- 3–5 giây một ảnh; đoạn lời dài thì chia nhiều ảnh, không để một ảnh tĩnh > 6 giây. Cùng một ảnh dùng lại thì cách ≥ 20 giây
  và lia vùng khác (`cropS` 1.1–1.2).
- KHÔNG thu nhỏ ảnh đặt giữa nền màu, KHÔNG tự vẽ khung viền quanh ảnh, KHÔNG `fit: "contain"` cho ảnh dự án.
- Ảnh nhắc đúng lúc lời nói nhắc tới (±0,3 s). Mỗi đoạn kể nhiều ý (vd "5 tầng cảnh quan") → mỗi ý một ảnh + một nhãn chương.

## 4. Chữ trên màn hình — THEO ĐÚNG PHONG CÁCH (mọi bộ)
Hai AI dựng cùng một phong cách phải ra cùng một kiểu chữ. Vì vậy:
- Khối `text`: KHÔNG ghi `font`, `look`, `color`, `size`, `weight`, `spacing`, `upper`, `shadow`, `anim` — để TRỐNG cho phong cách tự áp
  (style.heading / style.text của bộ). Chỉ ghi khi cần đổi thật (cỡ to hơn cho số lớn, `hl` tô từ khoá, `y`, `width`).
- Font khác chỉ được dùng nếu nằm trong `style.fonts` của bộ; kiểu hộp chữ (`solid`, `tag`…) chỉ khi bộ dùng hộp (`style.text.look`
  hoặc `style.looks`). Đọc `ghiChu.chu` của bộ (phong-cach/<bộ>/phong-cach.json) để biết dòng phụ / tên riêng dùng font nào.
- Đồ hoạ (chip, cta, checklist, priceHook…) tự lấy màu theo bộ — không ghi màu riêng.
- soat.py có dòng "CHUẨN: LỆCH PHONG CÁCH" → sửa cho hết.
- Chọn bộ: brief / người dùng chọn → dùng đúng bộ đó; "tự chọn" → theo bảng chủ đề (TAI-LIEU.md / huong-dan/phong-cach.md).

### 4b. Bộ "Sang trọng BĐS" (dự án cao cấp / nghỉ dưỡng / biệt thự / brief nói "sang")
Tiêu đề để trống font = Cormorant Garamond (mặc định của bộ). Thêm các dòng sau theo bảng:

| Vai trò | font | thông số |
|---|---|---|
| Dòng nhỏ phía trên (kicker) | Montserrat | weight 600, size 30–34, upper, spacing 10–12, `"grad": ["#FFF0BF","#FFC94D"]` |
| Tiêu đề / tên chương | Cormorant Garamond (bộ tự áp) | size 80–92, `"grad": ["#FFFFFF","#FFF1C7","#FFD877"]` (trắng → champagne) |
| Dòng phụ | Cormorant Garamond | weight 500, italic, size 54–72, màu `#FFF8E7` |
| Số chương (01, 02…) | Cormorant Garamond | weight 500, italic, size 60–70, `"grad": ["#FFF0BF","#FFC94D"]` |
| CHỮ NHẤN MẠNH: tên dự án, từ khoá đắt giá, tên người dẫn | Imperial Script (thư pháp chữ hoa uốn lượn) | size 100–150, 1–4 chữ, một dòng, viết Hoa Đầu Mỗi Chữ, `"grad": ["#FFFDF2","#FFE08A","#F5B935","#C98A14"]`, `"gradAngle": 180` |

- Chữ trơn, bóng mềm, hiện mờ dần (bộ tự áp), màu tô chuyển sắc vàng champagne (`grad`). KHÔNG hộp màu. Mỗi cảnh 1 chữ nhấn
  Imperial Script là đủ (tiêu đề in hoa + chữ nhấn bên dưới), đừng dùng chữ thư pháp cho cả câu dài.
- Vị trí: kicker y ≈ 230, tiêu đề y ≈ 290–320, dòng phụ y ≈ 400–430 (trên đầu người nói). Phụ đề `captionTop` ≈ 1400, kiểu
  `minimal`, Montserrat 600 cỡ 46.
- Nền sáng (trời, ảnh phối cảnh) ở MỌI bộ chữ trơn → chép `assets-chung/lop/che-sang.png` vào `<folder>/assets/lop/` rồi thêm 1 khối
  `{"type":"broll","src":"assets/lop/che-sang.png","start":0,"end":<hết video>,"z":12,"kb":false,"transition":"fade","exit":"fade"}`
  (tối dần mép trên và dưới). Bộ chữ trơn dùng cách này thay cho `tuong_phan.py --sua` (cách đó đặt chữ lên hộp, lệch phong cách).
- Tên Việt có dấu đầy đủ, đúng chính tả. Không viết chữ chiếm 3 dòng trở lên; tên dự án bị xuống dòng thì giảm size.

## 5. Âm thanh
- Luôn có nhạc nền theo phong cách (trừ khi nhac.json / người dùng nói không). Máy tính: `nhac.py … tim "<từ khoá EN>"` rồi
  `lay <số>` (sang trọng: "cinematic piano", "peaceful orchestra"). Máy ảo: kho `assets-chung/nhac/danh-sach.json` — sang trọng chọn
  `lovely-piano-song.mp3`, `nostalgic-piano.mp3`, `night-in-venice.mp3`, `novus-initium.mp3`, `infinite-peace.mp3`.
  Khối `audio` `"bgm": true`, `"loop": true`, volume 0,12–0,15 dưới lời nói (không lời 0,5–0,7), fadeIn 0,8, fadeOut 2,5.
  Bài CC BY → ghi nguồn trong bao-cao.md.
- Nhạc theo nhóm phong cách (máy tính: từ khoá tìm; máy ảo: `mood` trong danh-sach.json):
  | Nhóm bộ | Máy tính (từ khoá) | Máy ảo (mood) |
  |---|---|---|
  | Sang trọng, Đen vàng thượng lưu, Hoàng gia, Tân cổ điển, BĐS cao cấp, Địa Trung Hải, Indochine | cinematic piano / elegant | piano, sang-trong |
  | Năng động, TikTok, Mở bán, Sự kiện, Thử thách | upbeat corporate / energetic | soi-dong |
  | Chill, lofi, Vlog, Pastel, Japandi, Cà phê | lofi chill / acoustic | chill, vui-tuoi |
  | Thủy mặc, Thơ, Kể chuyện cảm xúc, Thiên nhiên | calm piano / ambient | nhe-nhang, piano |
  | Điện ảnh, Trailer, Đen trắng điện ảnh | cinematic | dien-anh |
  | Tin tức, Kiến thức, Podcast, Infographic, Doanh nhân | corporate light (volume 0,08–0,10) | nhe-nhang, chill |
  Bộ có `thanhPhan.amthanh` ghi rõ thì theo đó. Dựng theo nhịp (dung-nhip.json) dùng đúng bài đã chọn.
- Lời nói gốc: giữ `"audio": {"denoise": 1, "normalize": true}`.

## 6. Mẫu khối bộ Sang trọng BĐS (chép rồi sửa chữ / thời gian; bộ khác: khối text chỉ cần text, start, end, y)
```json
{"type":"text","start":0.04,"end":2.7,"text":"Điều làm nên","y":236,"font":"Montserrat","size":32,"weight":600,"color":"#E9D9A6","upper":true,"spacing":12,"look":"clean","shadow":"soft","stroke":0,"anim":"fade","out":"fade","inDur":0.6,"width":960,"align":"center"},
{"type":"text","start":0.1,"end":2.7,"text":"Giá trị","y":290,"size":84,"grad":["#FFFFFF","#FFF1C7","#FFD877"],"width":960},
{"type":"text","start":0.5,"end":2.7,"text":"Khác Biệt","y":372,"font":"Imperial Script","size":140,"weight":400,"grad":["#FFFDF2","#FFE08A","#F5B935","#C98A14"],"gradAngle":175,"look":"clean","shadow":"soft","stroke":0,"anim":"fade","out":"fade","inDur":0.6,"width":960,"align":"center"},
{"type":"broll","start":12.66,"end":16.02,"src":"assets/du-an/toan-canh.jpg","fit":"cover","panFrom":0.2,"panTo":0.45,"transition":"fade","exit":"fade","inDur":0.6},
{"type":"text","start":17.42,"end":20.07,"text":"Địa thế hùng vĩ","y":428,"font":"Cormorant Garamond","size":58,"weight":500,"italic":true,"color":"#FFF8E7","look":"clean","shadow":"soft","stroke":0,"anim":"fade","out":"fade","inDur":0.6,"width":960,"align":"center"}
```

## 7. Tự kiểm tra trước khi giao (bắt buộc, không bỏ bước)
1. `soat.py "<folder>"` → KHÔNG còn dòng nào bắt đầu bằng "CHUẨN:" (cổng chất lượng chung, scripts/chat_luong.py), hết lỗi đè mặt
   và chữ khó đọc (bộ chữ trơn: sửa bằng lớp che sáng / dời chữ, không đặt hộp).
2. XEM khung hình thật: `render.py --check` (máy tính: `nho_may.py check`) 6 mốc mỗi lần, phủ cả mở đầu, giữa, kết. Mở ảnh
   ra xem bằng mắt. Không xem được ảnh thì nói rõ với người dùng.
3. Đối chiếu danh sách KHÔNG ĐƯỢC CÓ: ảnh nhỏ giữa nền màu · khung tự vẽ quanh ảnh · chữ ghi nguồn giữa màn hình · ảnh dự án
   bị thay bằng cảnh chung chung · ảnh tĩnh không chuyển động > 6 giây · hộp màu sặc sỡ ở dự án sang · chữ đè mặt · không nhạc ·
   ảnh mờ vỡ (ảnh gốc thấp hơn 1300 px).
4. Xuất xong ghi bao-cao.md: ảnh lấy từ đâu (link), nhạc + nguồn, giả định đã đặt, việc người dùng nên bổ sung.
