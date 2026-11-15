# Bản đồ vệ tinh kể chuyện — cách dựng
- Hook 3s đầu: khối mapTour mở bằng toàn cảnh châu Á rồi bay vào cả nước, viền neon vàng-xanh tự vẽ (glow).
- Mỗi ý trong lời kể = 1 vùng (regions[] có `at` = giây trong khối lúc nhắc tới): viền trắng vẽ ra 0,9s → tô màu đậm trong suốt → tên vùng to (Oswald in hoa, `labelRotate` theo dáng vùng).
- Tên tỉnh trong vùng: `tags` (hộp trắng chữ đen) bật lần lượt; nhắc tới người → `badges` (ảnh tròn viền trắng + bảng tên cam, ảnh để trong assets/).
- Vùng gộp nhiều tỉnh: `parts` ["Cao Bằng", "Lạng Sơn", …] — đường ranh từng tỉnh vẫn hiện bên trong.
- Quần đảo: 1 điểm → tự vẽ khung bát giác (`radiusKm`), `opacity` thấp (0.05) cho giống viền khoanh.
- Đường di chuyển / tuyến: `lines` (tự vẽ, phát sáng).
- Ranh giới: viết plan xong chạy `python scripts/nho_may.py bando "<folder>" --vung` (cần giao diện mở — mạng máy thật).
- Kết: bay lại toàn cảnh (tự động khi còn > 3s), sticker LIKE / FOLLOW.
- Chưa làm được: ảnh vệ tinh cổ (2016, độ nét tối đa ~zoom 14 — không dùng cho cấp phường/khu đô thị; khi đó dùng khối `map` thường hoặc `d3`).
