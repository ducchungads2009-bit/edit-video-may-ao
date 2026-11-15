# Cách dựng — "tin tức" (infographic tài chính, học từ mau.mp4)

- **Kiểu video:** giọng đọc + đồ họa động, KHÔNG có người nói, KHÔNG phụ đề. Hợp nhất với chế độ VOICE / CHỈ TIẾNG; có footage thì footage chỉ là nền phụ, đồ họa là chính.
- **Hook 3s đầu:** chữ/hình đầu tiên ở 0,4s — logo/ảnh doanh nghiệp trong vòng tròn + ngay lập tức các con số "khủng" (40.000 NHÂN SỰ, 448 ĐẠI LÝ…) bật ra theo lời đọc, nối bằng đường kẻ trắng.
- **Mật độ chữ:** dày, ~7 lần/10s (đầu 6 · giữa 8 · cuối 7). Mỗi con số được đọc → hiện ngay (0–0,1s sau âm đầu). Chữ KHÔNG biến mất nhanh mà tích lũy thành một "trang" dọc, rồi camera lướt xuống trang kế. Tool: dùng nhiều khối nối đuôi, ở lại tới khi chuyển cụm ý (2–6s), out fade.
- **Chữ:** Montserrat 800–900 IN HOA, trắng, bóng mềm; con số + đơn vị màu vàng cam #F2A516 (hl), số âm / cảnh báo đỏ #E3141B; dòng chú thích biểu đồ nhỏ xám nhạt, chữ thường cỡ nhỏ. Tiêu đề lớn ~80–90px, nhãn ~50–60px. Kiểu hiện: wipe (quét trái→phải) cho nhãn, type (gõ từng ký tự) cho tiêu đề ngày tháng ("TẠI NGÀY 31/12/2025"), fade+phóng nhẹ cho ảnh.
- **Bố cục:** căn giữa, xếp chồng dọc thành cột thông tin (tiêu đề → biểu đồ → chú thích → kết luận), cách ~120px; cặp so sánh đặt 2 bên (2 khung viền trắng bo góc + dấu › ở giữa). Icon nét trắng đặt TRÁI cụm chữ 2 dòng (dòng trắng trên, dòng vàng dưới).
- **Đồ họa:** chart bar (cột vàng/xanh chanh/cam, cột âm đỏ), line (vùng tô xanh lá mờ, nhãn +92%), donut (đỏ sẫm #6B0000 / trắng, % ở giữa), cán cân (Nợ vs Vốn), checklist trong khung viền trắng (mục chữ đỏ), nhãn số nền be. Biểu đồ luôn có nguồn = lời đọc/brief, KHÔNG bịa số.
- **Minh họa:** ảnh thật nhỏ (pip clean, viền trắng mảnh) kèm nhãn vàng ngay dưới; người cầm loa / logo cắt nền khi "tự giới thiệu". Không dùng broll toàn khung nhiều.
- **Chuyển cảnh:** gần như không cắt — camera lướt dọc xuống (transition "up") khi sang khối kế; đổi chương lớn thì lia ngang nhanh (whip/slide); có 1–2 chỗ cắt thẳng sang nền xám bê tông cho chương "KẾT QUẢ KINH DOANH". Không flash, không rung.
- **Zoom:** rất ít (1 lần đẩy vào chậm ~1,08 ở đoạn cao trào nợ).
- **Màu:** nền xám than #1E1B1C có lưới ô vuông mờ + hạt nhẹ (frame grid + grain); tông tối, ít bão hòa ngoài các mảng số liệu.
- **Âm thanh:** nhạc nền nhỏ (thấp hơn giọng ~17 dB); ding khi chữ/số hiện, pop khi biểu đồ/khung lớn hiện, 1 boom ở điểm sốc (dòng tiền âm). Giữ mức "vừa" (~1 tiếng/5s) theo quy tắc tool, đừng gắn ding cho mọi dòng như mẫu.
- **Kết:** câu tổng kết + khối cuối, mẫu không có CTA rõ — tool vẫn thêm CTA follow ngắn theo brief.
- **Tool chưa làm được / gần nhất:** nền lưới xám than tự vẽ khi có footage (đã dùng frame grid + color tối, nên dùng presenter/nền tối hoặc voice-only); camera cuộn liên tục cả trang → mô phỏng bằng kf dy cho nhóm khối + transition "up"; cán cân Nợ–Vốn → dùng 2 counter/tabs đối xứng; đường nối kiểu sơ đồ cây → bỏ hoặc dùng chữ xếp tầng.

## Bản demo chuẩn (cho-edit/demo tin tức)
- Dựng từ GIỌNG ĐỌC của mẫu (chế độ chỉ tiếng), không dùng hình clip mẫu: nền = broll ảnh xám than toàn khung (`assets/nen-xam-than.jpg`, z 1, kb false) để che nền giấy của chế độ chỉ tiếng; lưới + hạt do frame của bộ vẽ.
- Chia 10 cụm theo ý; trong cụm, khối hiện dần đúng lúc đọc số và ở lại tới hết cụm, hết cụm cả cụm trượt lên (`out`/`fxOut` "up") = cảm giác camera lướt xuống.
- Khối dùng: text (căn trái + icon trái cho danh sách số liệu, `dx` dời chữ), chart bar có `colors`/cột âm đỏ, line, donut `colors: ["#7A0A0A","#FFFFFF"]`, checklist, text look solid nền #141112 làm khung so sánh, sticker lucide trắng/vàng/đỏ, pip round/clean cho ảnh.
- soat.py báo "> 3 khối cùng lúc" là bình thường với bộ này (trang infographic cộng dồn).
