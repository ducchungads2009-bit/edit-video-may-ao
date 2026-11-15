# Ghi chú cách dựng — Thủy mặc mực tàu (chỉ tiếng) (video CHỈ CÓ TIẾNG)
- Dùng cho dự án chỉ có voice (info.json "mode": "audio"): không có hình quay — cả khung là tranh thủy mặc vẽ sẵn, chuyển động nhẹ
  (chim bay, lau sậy đung đưa, tranh "thở"). Không cần cảnh trám video.
- Chữ: mỗi câu thơ 1 khối `text` giữa mặt nước (y ≈ 1180–1450, dưới thuyền, trên lau sậy), hiện đúng lúc đọc (blur), ở lại tới hết câu,
  ẩn fade; câu dài thì xuống dòng (\n), mỗi dòng ≤ 7 chữ. Có thể đặt tên bài / tác giả ở trên trời (y ≈ 200–360, cỡ 80) trong 3–5s đầu.
  Tô 1–2 chữ "hồn" của câu (hl). Không phụ đề tự động (captions: false), không nhãn dán, không thẻ đồ họa.
- Minh họa: tranh có sẵn ở `assets-chung/thuy-mac/` (thuyen-muc, thuyen-mau, nui-chim-muc, nui-chim-mau) — copy vào assets/ của
  dự án, dùng `broll` ảnh toàn khung 4–7s (transition fade, exit fade, kenburns) khi câu thơ nhắc sông nước / thuyền / núi / chim,
  cách nhau ≥ 12s, chữ câu thơ vẫn hiện trên ảnh (đặt chữ khối text sau broll trong danh sách hoặc z cao hơn). Chọn bản màu/mực hợp bộ.
- Âm thanh: giọng đọc là chính; nhạc nền (nhac.*) đàn tranh / sáo, volume 0.08–0.12 (`"music": {"src": "nhac.mp3", "volume": 0.1}`).
  Không sfx (hoặc 1 tiếng chuông nhẹ ở câu kết).
- Kết: câu cuối ở lại thêm 2–3s, mờ dần.
