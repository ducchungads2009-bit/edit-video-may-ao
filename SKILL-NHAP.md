---
name: edit-video-may-ao
description: Dựng video TikTok bất động sản / đời sống từ clip điện thoại ngay trong chat (máy ảo đám mây) — dùng khi người dùng nhắn "bắt đầu", "edit video", gửi clip để dựng, hoặc nhắn "dựng lại" sau khi sửa trên trang chỉnh sửa.
---

# Edit video trên máy ảo

Người dùng (thường dùng điện thoại) gửi clip vào chat; bạn chạy công cụ dựng video trên máy ảo của phiên, gửi lại video
và một TRANG CHỈNH SỬA để họ chạm sửa cơ bản. Mọi việc nặng làm trên máy ảo — người dùng khoá màn hình được.
Nói chuyện bằng tiếng Việt, ngắn gọn, không nói thuật ngữ kỹ thuật.

## 1. Hỏi từng câu một (khi người dùng nhắn "bắt đầu" / "edit video" mà chưa gửi đủ)
**ĐƠN EDIT** (người dùng điền ở trang "Đơn edit" — https://claude.ai/artifact/LVDpawtr3fajeiVqAc1vzr — rồi dán vào chat kèm video): tin nhắn có dòng `ĐƠN EDIT` → KHÔNG hỏi
câu nào nữa, đọc đơn rồi làm luôn mục 2 → 3. Chỉ hỏi lại khi thiếu video. Cách hiểu đơn:
- "Loại video: <loại>" → không phải Bất động sản thì KHÔNG dùng thẻ / câu chữ đặc thù BĐS (priceHook, "căn", "sổ hồng"…), tự chọn phong cách
  theo loại (tin tức → nhóm tin, review / sự kiện → năng động, vlog → chill, chia sẻ → podcast, thơ → thủy mặc). Nhãn các dòng thông
  tin đổi theo loại (vd "Tên quán / sản phẩm", "Địa chỉ", "Ưu đãi") — đọc theo nghĩa.
- "Phong cách: <tên bộ>" → `./chay.sh phongcach.py chon "<du-an>" "<tên bộ>"` (đúng tên trong thư viện); "tự chọn" → tự chọn theo nội dung;
  "theo video mẫu gửi kèm" → file có chữ "mau" trong tên (hoặc file gửi kèm khác loại với clip) là video mẫu → `_mau/`.
- "Nhạc: <tên> (<file>.mp3)" → chép `assets-chung/nhac/<file>.mp3`; "tự chọn" / "không nhạc" / "file nhạc gửi kèm" như tên gọi.
- "Ý tưởng" + "Nội dung chi tiết" (nhiều dòng, người dùng tự gõ theo loại video: giá, ý chính, lời thơ, ghi chú clip…) → chép nguyên vào
  `brief.txt` (kèm "SĐT", "Kêu gọi cuối" nếu có — không có SĐT thì không hiện SĐT, không có kêu gọi thì tự chọn câu hợp nội dung); dòng ghi chú clip (thứ tự, bỏ đoạn, lấy hình bỏ tiếng) làm theo như mục ghi chú clip của TAI-LIEU.md.
- "Video gốc: cảnh quay không lời" → dựng không lời (chữ + nhạc); "Giọng đọc: có gửi kèm file" → file âm thanh gửi kèm là `voice.*`.
- "Tư liệu minh họa: có" → ảnh / video không phải clip chính → `assets/cua-ban/`. "Khung hình" → khung.py.
Nhắn "bắt đầu" mà KHÔNG có đơn → trả lời 1 dòng: "Điền nhanh ở trang Đơn edit (https://claude.ai/artifact/LVDpawtr3fajeiVqAc1vzr) rồi dán vào đây kèm video — hoặc mình hỏi từng câu:"
rồi hỏi câu 1 bên dưới.

MỖI TIN CHỈ HỎI 1 CÂU, ngắn 1–2 dòng, chờ họ trả lời rồi mới hỏi câu kế. Không gửi cả danh sách, không giải thích dài.
Thứ tự (câu nào họ đã trả lời / đã gửi kèm từ trước thì bỏ qua, không hỏi lại):
1. **Video gốc** (bắt buộc): "Gửi mình các clip nhé (theo thứ tự muốn ghép; clip nào lấy đoạn nào thì ghi kèm)."
   Chưa có video thì không sang câu 2. Nhận xong video thì cài công cụ (mục 2) ngay trong lượt đó rồi mới hỏi câu 2.
2. **Brief**: "Video về gì? Gửi thông tin chính: tên dự án, giá, diện tích, vị trí, SĐT, câu kêu gọi… (không có thì nhắn 'bỏ qua')."
3. **Phong cách**: hỏi bằng nút chọn (AskUserQuestion nếu có): Tự chọn hợp nội dung (khuyên dùng) · Gửi video tham chiếu ·
   Xem danh sách phong cách. Chọn "xem danh sách" → chạy `./chay.sh phongcach.py ds`, gửi gọn theo nhóm chủ đề, chờ họ chọn.
4. **Cảnh trám / tư liệu**: "Có ảnh/video minh họa không (phối cảnh, mặt bằng, sổ, tiện ích…)? Gửi kèm ghi chú dùng ở câu nào,
   hoặc nhắn 'không'."
5. **Nhạc**: nút chọn: Tự chọn theo phong cách · Sôi động · Chill nhẹ nhàng · Sang trọng (họ có thể gõ kiểu khác / gửi file / "không nhạc").
6. **Giọng đọc**: chỉ hỏi khi clip là cảnh quay không lời / lời chỉ đạo người quay (xem transcript sau khi chuẩn bị, hoặc họ nói vậy):
   "Có file giọng đọc không? Gửi file, hoặc gửi kịch bản để mình đọc giọng AI, hoặc 'không' để dựng chữ + nhạc."
7. **Khung hình**: nút chọn: 9:16 TikTok (khuyên dùng) · 4:5 Facebook · 1:1 · 16:9 YouTube.
Sau câu cuối: nhắn 1 dòng "Đủ rồi, mình làm luôn — xong gửi video + link trang chỉnh sửa, bạn khoá màn hình được." rồi làm mục 3.
Bất cứ lúc nào họ nhắn "làm luôn" / "thôi làm đi" → dừng hỏi, các câu còn lại dùng mặc định (tự chọn phong cách & nhạc, 9:16).
Thiếu thông tin không bắt buộc → tự chọn cách an toàn, KHÔNG bịa giá / số liệu.

## 2. Cài công cụ (mỗi phiên 1 lần, ~1 phút)
Kho công khai — không cần GitHub hay kết nối gì:
```
cd ~ && [ -d video-tool/.git ] || git clone --depth 1 https://github.com/ducchungads2009-bit/edit-video-may-ao video-tool
cd ~/video-tool && git pull -q --depth 1 2>/dev/null; ./cai-may-ao.sh   # phải in "SẴN SÀNG" + dòng kiểm tra mạng
```
Clone lỗi (mạng / bị chặn) → thử lại 1 lần; vẫn lỗi thì báo người dùng nguyên văn lỗi.
Luôn để công cụ ở `~/video-tool` (KHÔNG để trong /tmp — trang chỉnh sửa không đăng được từ /tmp). Mọi lệnh sau chạy trong
~/video-tool qua `./chay.sh <script> ...`. File người dùng gửi nằm ở /mnt/user-data/uploads/.

## 3. Dựng (làm liền, không hỏi lại)
Tài liệu đầy đủ của công cụ: `TAI-LIEU.md` (chỉ đọc mục cần: grep tiêu đề). BỎ QUA mọi chỗ nói `nho_may.py`, giao diện,
`tiendo.py`, mã kích hoạt — ở máy ảo chạy thẳng script bằng `./chay.sh`.
1. Tạo `cho-edit/<ten-du-an>/`, chép clip vào (đặt tên theo thứ tự `01-…`, `02-…` nếu cần đúng thứ tự), `brief.txt`,
   tư liệu vào `assets/cua-ban/`, video tham chiếu vào `_mau/`, giọng đọc thành `voice.*`, nhạc của họ thành `nhac.*`.
   Khung khác 9:16: `./chay.sh khung.py "<du-an>" 1:1`.
2. `./chay.sh prepare.py "<du-an>"` (clip 4K mất lâu: ~2–3 phút / phút video). Chạy nền + kiểm tra định kỳ nếu > 2 phút.
3. Đọc `_work/transcript_full.txt`, `clips.json`, XEM `_work/sheet.jpg`. Lời nói ít / không có (chỉ vài chữ "Ừ" lặp
   đều = máy nghe nhầm tiếng ồn) → video KHÔNG LỜI: tạo lưới khung hình
   `ffmpeg -i _work/ghep.mp4 -vf "fps=1/2,scale=120:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=16x5" -frames:v 1 /tmp/luoi.jpg`
   rồi xem để chọn cảnh.
4. Phong cách: video tham chiếu → `./chay.sh style.py "<du-an>"` rồi làm mục "Video mẫu & PHONG CÁCH" của TAI-LIEU.md;
   tên bộ → `./chay.sh phongcach.py chon "<du-an>" "<tên>"`; "tự chọn" → chọn theo bảng chủ đề trong TAI-LIEU.md.
5. Cắt: có lời → `./chay.sh cat_lang.py` + thêm đoạn đọc lại / vấp vào `cut.json` → `./chay.sh trim.py` (hoặc
   `segments` khi nhiều lần quay — mục 2a TAI-LIEU.md). Không lời → `segments` 3–5 giây / cảnh đẹp, xếp theo lối đi,
   `"videoVolume": 0`, `"captions": false`, có nhạc.
6. Ghi tên từng cảnh (để trang chỉnh sửa hiện) vào `_work/nhan-canh.json` = ["Phòng khách", "Bếp", …] theo thứ tự segments
   (video có lời thì bỏ qua — trang tự hiện lời nói).
7. Viết `plan.json` theo TAI-LIEU.md (bước 5). Nhạc từ kho: chép `assets-chung/nhac/<file>.mp3` vào `assets/nhac/` →
   `"music": {"src": "assets/nhac/<file>.mp3", "volume": 0.15}` (video không lời: 0.5–0.7). Danh sách: `assets-chung/nhac/danh-sach.json`.
   Chưa có: khối cần tách người (behind, orbit, presenter) — không dùng trên máy ảo.
8. `./chay.sh soat.py "<du-an>"`, sửa 1 vòng. `./chay.sh render.py "<du-an>"` (máy ảo ~10 giây dựng / 1 giây video:
   chạy nền, kiểm tra mỗi 2–4 phút; KHÔNG kết thúc lượt trả lời khi đang dựng).
9. Xem 3–4 khung của `final.mp4` (ffmpeg) để chắc đúng.

## 4. Gửi kết quả
1. `./chay.sh trang_sua.py "<du-an>" --ten "<tên ngắn>"` → thư mục `<du-an>/_trang-sua/`.
2. Lần đầu: publish_files (title "Sửa video: <tên>", mọi file trong `_trang-sua`), rồi declare_capabilities với
   `{"db": {"rules": [{"path": "ban-sua", "read": "interact", "write": "interact"}]}, "user": {}}`. Ghi slug vào
   `<du-an>/_work/trang-sua-slug.txt`. Lần sau: publish_files vào đúng slug đó (base_version = bản đang chạy), `mode: "replace"`.
3. Chép `final.mp4` ra `/mnt/user-data/outputs/<ten>.mp4`, gửi bằng SendUserFile.
4. Báo 3–5 dòng: đã làm gì, giả định gì (vd không có giá nên không ghi), nên bổ sung gì; nhắc: "sửa trên trang
   rồi bấm Lưu, quay lại nhắn **dựng lại**; hoặc nhắn thẳng yêu cầu sửa".

## 5. "Dựng lại" / yêu cầu sửa
- Sau khi người dùng bấm Lưu trên trang: db_get (slug trong `trang-sua-slug.txt`, path `ban-sua/hien-tai`), ghi phần
  data ra `/tmp/ban-sua.json`, chạy `./chay.sh ap_ban_sua.py "<du-an>" /tmp/ban-sua.json`. Đọc dòng "GHI CHÚ:" (nếu có)
  và tự sửa plan.json theo ghi chú. Rồi render lại → trang_sua.py → publish_files cùng slug → gửi video mới.
- Tin nhắn có `BAN-SUA:{…}` (người dùng mở trang ngoài Claude nên trang chép bản sửa để dán): ghi phần JSON sau `BAN-SUA:` ra
  `/tmp/ban-sua.json` rồi chạy ap_ban_sua.py như trên.
- Người dùng nhắn yêu cầu bằng lời: đọc plan.json hiện tại, chỉ sửa phần được nhờ, render lại, cập nhật trang.
- "Làm tiếp" / "thử lại" / phản hồi trước bị đứt giữa chừng: KHÔNG làm lại từ đầu — xem `ls ~/video-tool/cho-edit/*/` và
  `_work/` để biết đã tới bước nào (đã cài? có words.json? có plan.json? có final.mp4?) rồi làm tiếp từ đó.
- Phiên mới (máy ảo đã mất file): nói rõ cần gửi lại clip để dựng lại; giữ lời nhắn sửa của họ.

## KHỐI CẦN MẠNG
`cai-may-ao.sh` in và ghi `.mang.json` (co / khong) cho từng nhóm. Chỉ dùng khối khi mạng "co"; "khong" thì thay
bằng cách khác (vd nhãn chữ "📍 Cách trung tâm 10 phút" thay cho khối bản đồ) và ghi vào báo cáo:
- Khối `map` (bản đồ, đường đi): cần tiles.openfreemap.org, nominatim.openstreetmap.org, router.project-osrm.org.
- Khối `mapTour` (bản đồ vệ tinh): thêm tiles.maps.eox.at; địa hình 3D: s3.amazonaws.com.
- Ảnh / video stock: pixabay.com, cdn.pixabay.com (+ khoá Pixabay); ảnh địa danh: api.openverse.org.
Muốn bật: người dùng thêm các tên miền trên vào danh sách được phép (claude.ai → Cài đặt → Capabilities), mở phiên mới.
Không cần mạng: chữ, phụ đề, thẻ, chữ 3D, thẻ 3D, lớp phủ, hình vẽ, cảnh dựng sẵn, zoom, chuyển cảnh, nhạc trong kho.

## Lưu ý
- Không bịa giá, diện tích, SĐT, số phòng khi brief không có (số phòng đoán theo hình thì nói rõ là đoán).
- Chỉ dùng ảnh / nhạc người dùng gửi, kho nhạc có sẵn (CC0), hoặc stock khi có khoá Pixabay.
- Mỗi file trang chỉnh sửa ≤ 20 MiB (trang_sua.py tự nén video xem thử).
