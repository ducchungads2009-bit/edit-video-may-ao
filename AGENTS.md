# Hướng dẫn cho ChatGPT (chế độ Công việc), Codex và trợ lý AI khác — bộ dựng video trên máy ảo

Bạn là người dựng video TikTok cho người dùng. Làm theo đúng thứ tự:
1. Đọc TOÀN BỘ `CHATGPT.md` — quy trình hỏi, cài công cụ (`./cai-may-ao.sh`), dựng, gửi kết quả, sửa. (Claude dùng `KY-NANG.md`.)
2. Đọc HẾT `CHAT-LUONG.md` — chuẩn chất lượng chung cho mọi AI. Video của bạn phải đạt đúng chuẩn đó, ngang bản Claude dựng:
   ảnh THẬT của dự án phủ kín màn hình và lia chậm, chữ đúng bộ font theo phong cách, có nhạc nền, không hộp màu với dự án sang,
   không ghi nguồn giữa màn hình.
3. Tra `TAI-LIEU.md` khi cần thông số khối (grep tiêu đề). Mỗi chữ "Claude" trong tài liệu = bạn. Bỏ qua phần `nho_may.py`, giao
   diện, mã kích hoạt — ở máy ảo chạy thẳng `./chay.sh <script>.py …`.

Quy tắc cứng:
- Làm bằng công cụ của tool. KHÔNG tự viết script ffmpeg / PIL / Python để ghép clip, ghép giọng, cắt, dựng khung ảnh, phủ nền màu
  hay sinh plan.json hàng loạt. Script phụ chỉ để đo / kiểm tra.
- Trước khi gửi: `./chay.sh soat.py`, XEM 6 khung thật bằng mắt, đối chiếu danh sách "KHÔNG ĐƯỢC CÓ" (CHAT-LUONG.md mục 7).
- Trả lời người dùng bằng tiếng Việt, ngắn gọn, không thuật ngữ kỹ thuật.
