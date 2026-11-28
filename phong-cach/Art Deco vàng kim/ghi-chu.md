# Art Deco vàng kim — bộ có CẢNH AI đi kèm (mẫu LumReels 051)
Chữ, phụ đề, ảnh trám dựng như bộ thường. Cảnh AI dựng sẵn (canh-ai/san, chỉ đổi data — KHÔNG viết lại):
- MỞ ĐẦU: `art-deco` data {"che":"mo","nhan":"…","ten":"<tên dự án, ngắn>","phuDe":"…"} — 6 giây, kín khung.
- KẾT: `art-deco` data {"che":"ket","ten":"…","cta":"Đặt lịch tham quan","sdt":"<SĐT trong brief>"}.
- TIẾN ĐỘ / VAY: `bieu-do-vay` data {"giaoDien":"toi","mau":"#D9B45A",…}.
- VỊ TRÍ: `tuyen-tien-ich` data {"giaoDien":"toi","mau":"#D9B45A",…}.
Chép vào dự án: `canh_ai.py moi "<du-an>" <tên-trong-dự-án> --san <cảnh>`, rồi khối
`{"type":"canhAI","start":…,"end":…,"canh":"canh/<tên-trong-dự-án>","data":{…}}`. Xem thử: `canh_ai.py thu "<du-an>" <tên>`.
- Video quay thật có người nói: cảnh mở / kết kín khung chỉ đặt ở 3–6 giây đầu (trước khi người nói vào) và phần kết; cảnh thẻ
  (nền trong suốt) đặt khi lời nói nhắc tới giá / tiện ích / tiến độ, tránh che mặt (y thấp, ≥ 900).
- Video KHÔNG CLIP (video_ai.py): cảnh kín khung nối nhau phủ cả video, cảnh thẻ đè lên nền phong cách.
- Không bịa số: data chỉ lấy từ brief; thiếu thì bỏ cảnh đó.
