# TÀI LIỆU CÔNG CỤ (bản máy ảo)
> Bản này chạy trên máy ảo của Claude: chạy thẳng script bằng `./chay.sh <script> ...`, BỎ QUA mọi chỗ nói nho_may.py, giao diện, tiendo.py, mã kích hoạt. Quy trình chính nằm trong bộ kỹ năng edit-video-may-ao.

# Tool edit video TikTok — hướng dẫn cho Claude

Bạn (Claude) là người dựng video. Người dùng đưa một folder (hoặc folder cha chứa nhiều folder),
mỗi folder con = 1 video. Làm lần lượt từng folder, xong folder nào báo folder đó.
Luôn chạy lệnh từ thư mục gốc của tool này, đường dẫn để trong dấu "".
- Windows: dùng `python`.  - macOS: dùng `.venv/bin/python` (môi trường do cai-dat.command tạo).
Các lệnh bên dưới viết `python` — trên Mac thay bằng `.venv/bin/python`.

## ⚡ VIỆC NẶNG CHẠY TRÊN MÁY THẬT — `scripts/nho_may.py` (BẮT BUỘC)
Bạn thường chạy lệnh trong một máy ảo nhỏ (ít nhân, ít RAM, không có chip/card đồ họa) → ffmpeg / Remotion / tách người
chạy ở đó chậm gấp nhiều lần. Giao diện của tool (giao-dien.command / .bat) chạy thẳng trên máy người dùng. Vì vậy MỌI
việc nặng chạy qua: `python scripts/nho_may.py <việc> "<folder>" [tham số]` — việc: `prepare`, `check <mốc,mốc>`,
`render`, `trim`, `assemble`, `style`, `tachnguoi`, `mat`, `stock <tham số stock.py get>`, `bando "<dự án>" "<tiện ích>"…` (toạ độ cho khối bản đồ; `bando --vung` = ranh giới vùng cho mapTour). Lệnh tự gửi cho giao diện và chờ;
in "Vẫn đang chạy… cho <mã>" thì gọi `python scripts/nho_may.py cho <mã> "<folder>"` để chờ tiếp (lặp tới khi XONG).
- Đầu phiên chạy `python scripts/nho_may.py may`: báo "CHƯA mở" → nhờ người dùng mở giao-dien (cửa sổ Terminal của tool)
  rồi tiếp tục; người dùng không mở được thì mới chạy tại chỗ (lệnh tự làm, chậm).
- TUYỆT ĐỐI KHÔNG chép / cắt nhỏ / nén video hay thư mục tool để chuyển sang máy khác (container cloud...) để chạy —
  vừa chậm vừa tốn. Muốn xem khung hình: `nho_may.py check` rồi xem `_work/check.jpg`.
- Lệnh nhẹ (tiendo, soat, snap, sfx, phongcach, đọc/ghi json) chạy tại chỗ bình thường.
Các lệnh `python scripts/prepare.py|render.py|trim.py|assemble.py|style.py|stock.py get` bên dưới = gọi qua nho_may như trên.

Mỗi folder = 1 DỰ ÁN = 1 video thành phẩm. Gồm: 1 hoặc nhiều clip (thư mục gốc hoặc raw/), `brief.txt`
(không bắt buộc), `assets/` (ảnh/video minh họa, không bắt buộc), `thu-tu.txt` (thứ tự ghép, không bắt buộc),
`voice.*` (giọng đọc riêng, không bắt buộc — xem Chế độ VOICE), `nhac.*` (nhạc nền, không bắt buộc).
Nhiều clip → prepare.py tự chuẩn hóa (1080x1920, clip ngang thì nền mờ) và ghép theo thứ tự thành
`_work/ghep.mp4`; mốc từng clip trong `_work/clips.json`. Thứ tự ghép không hợp lý theo nội dung
(vd phần kêu gọi nằm giữa) → sửa thu-tu.txt (mỗi dòng 1 tên file) và chạy lại prepare.

Ảnh thả vào chỗ clip quay được tự đổi thành clip 5 giây `<tên ảnh>.mp4` (gui.py img_to_clip) — dùng như clip thường.
CHE MỜ (`blurs`): mỗi vùng {mode: blur|mosaic|den|icon, grow (phóng hộp), strength, round (bo góc 0–0.5), color, icon (emoji / tên lucide),
track [[giây gốc, x, y, w, h]...]}; che_mo.py --fps 3|6|10 = độ bám khi dò.

Người dùng có TRÌNH CHỈNH SỬA TIMELINE trong giao diện (nút ✂ Chỉnh sửa): họ tự sửa plan.json bằng tay
(kéo khối, sửa chữ, cắt đoạn, màu, âm thanh, phụ đề...). Khi được nhờ sửa tiếp, LUÔN đọc lại plan.json hiện tại
và giữ nguyên những gì họ đã chỉnh, chỉ đổi phần được yêu cầu.
`plan.markers` = [{t (giây video xuất), label?}] — MỐC người dùng đánh dấu trên timeline (phím M); label là ghi chú cho Claude
(vd "chèn ảnh mặt bằng", "cắt bớt chỗ này") → đọc và làm theo khi được nhờ sửa, xong việc ở mốc nào thì có thể bỏ mốc đó.
Khối có `"locked": true` = người dùng đã khoá (🔒) — KHÔNG dời / sửa khối đó trừ khi được nhờ đích danh.
Trình chỉnh sửa đang mở sẽ TỰ NẠP bản plan.json / video mới sau mỗi lần Claude sửa hoặc dựng lại (lần 2, 3…) — nếu người
dùng đang có chỗ chưa lưu, nó hỏi nạp bản mới hay giữ bản của họ, và không ghi đè bản của Claude khi chưa hỏi. Nhắc người dùng
bấm Lưu trong trình chỉnh sửa TRƯỚC khi nhờ Claude sửa tiếp (để Claude đọc được những gì họ vừa chỉnh tay).

## ⛔ Người dùng bấm DỪNG
Giao diện có nút "■ Dừng" khi Claude đang làm. Lệnh nào (tiendo buoc, nho_may, soat, stock, sfx…) in "⛔ NGƯỜI DÙNG ĐÃ BẤM DỪNG"
(thoát mã 9) → DỪNG NGAY: không chạy thêm lệnh, không sửa file của dự án đó, không "thử lại"; chỉ báo ngắn đã dừng ở bước nào.

## Báo tiến độ (giao diện hiện thanh % + "còn khoảng N phút") — LUÔN làm, mọi chế độ
Ở ĐẦU mỗi bước, chạy 1 lệnh ngắn (không cần đọc kết quả):
`python scripts/tiendo.py buoc "<folder>" <k>` với k: 1 Đọc nội dung & tư liệu (bước 1–2b) · 2 Lên dàn ý (bước 3) ·
3 Tìm minh họa/stock (bước 4) · 4 Viết kịch bản dựng (bước 5) · 5 Tự kiểm tra (bước 6) · 6 Xuất video (bước 7).
Xong dự án (kể cả khi dừng ở dàn ý chờ duyệt, hoặc lỗi bỏ qua): `python scripts/tiendo.py xong "<folder>"`.
Chỉ lên dàn ý thì chạy buoc 1, buoc 2, rồi xong. Edit tiếp từ dàn ý đã duyệt thì bắt đầu từ buoc 3.
Chế độ tự động nhiều dự án: trước mỗi dự án `python scripts/tiendo.py dot <thứ tự> <tổng số> "<tên folder>"`,
hết đợt `python scripts/tiendo.py het x`. Các script máy (prepare/render/style/assemble/trim) tự báo tiến độ, không cần làm gì.

## EDIT TỰ ĐỘNG TRỌN 1 DỰ ÁN (lệnh "EDIT TỰ ĐỘNG TRỌN folder …" — nút ⚡ của dự án trên giao diện)
Người dùng chỉ gửi 1 lệnh và KHÔNG chat thêm cho video đó. Làm đúng như Chế độ TỰ ĐỘNG bên dưới nhưng chỉ cho folder được chỉ:
bước 1 → 7 liền mạch (đã chuẩn bị rồi thì bỏ qua bước 1), có video mẫu / phong cách thì theo, không có thì tự chọn bộ hợp chủ đề
(xem danh sách bộ tạo sẵn ở mục Video mẫu & PHONG CÁCH); KHÔNG hỏi, KHÔNG dừng ở dàn ý, KHÔNG chờ người dùng thả ảnh; nho_may báo
"Vẫn đang chạy" thì tự gọi `cho` tiếp tới khi xong. Chỗ chưa rõ (thiếu giá, thiếu ảnh…) → chọn cách an toàn, ghi vào bao-cao.md.
Chỉ dừng khi lỗi không tự khắc phục được (ghi lý do vào bao-cao.md). Xong: báo 2–3 dòng + nhắc có thể sửa bằng ✂ Chỉnh sửa.

## Chế độ TỰ ĐỘNG (người dùng nói "edit tự động", "edit hết", "xử lý hết"...)
Mục tiêu: người dùng chỉ tải video + điền brief; Claude làm trọn từng dự án, tự kiểm tra, trả final.mp4, rồi sang dự án kế.
- Danh sách việc: mọi folder con của thư mục được chỉ định (mặc định `cho-edit`) CHƯA có `final.mp4`, bỏ qua folder
  bắt đầu bằng `_` hoặc có file `_bo-qua`. Làm theo thứ tự tên. Tạo task list để người dùng theo dõi.
- Mỗi dự án chạy liền bước 1 → 7, KHÔNG dừng hỏi. Vẫn viết outline.md và can-tim.md (để người dùng xem/sửa sau).
- `CẦN NGƯỜI DÙNG`: file đã có trong assets/ thì dùng; chưa có thì thay bằng stock nếu là cảnh chung chung,
  nếu không thì BỎ element đó khỏi plan.json (không để element trỏ tới file thiếu). Ghi lại trong can-tim.md.
- Thông tin brief không có (giá, diện tích, SĐT...) → KHÔNG bịa; bỏ đồ họa cần thông tin đó và ghi vào báo cáo.
- **CHE MỜ BIỂN SỐ / MÃ QR / MÃ VẠCH** (chính sách TikTok): `python scripts/nho_may.py chemo "<folder>"` (máy thật, ~0,5 giây xử lý /
  1 giây video) dò biển số (YOLOv9 open-image-models, MIT), mã QR, mã vạch → ghi `"blurs"` vào plan.json (làm mờ, bám theo khi vật
  di chuyển, đi theo cả zoom / cắt đoạn). Chế độ tự động: chạy sau bước 1 (prepare) để người dùng thấy ngay trong trình chỉnh sửa;
  quên thì render tự dò khi plan chưa có "blurs" (`"cheMo": false` = tắt hẳn). Mỗi vùng: {"id", "kind": bien-so|qr|ma-vach|tay,
  "mode": blur|mosaic|den, "off": true (tắt), "track": [[giây video gốc, x, y, w, h], ...]}. Thấy vật nhạy cảm khác (số điện thoại
  người khác, giấy tờ, màn hình có thông tin cá nhân) → thêm vùng "tay" (2+ mốc). Biển số 2 hàng (xe máy VN), biển nhỏ / mờ / nghiêng
  có thể sót — xem sheet.jpg; sót thì thêm vùng "tay" và ghi vào bao-cao.md.
- **CHỮ PHẢI NỔI HẲN TRÊN NỀN** (quy tắc cứng): màu chữ tách biệt rõ với nền video NGAY TẠI CHỖ chữ hiện (nền sáng / màn hình
  trắng / tường sáng → chữ tối hoặc chữ sáng có viền tối dày / nền khối; nền tối → chữ sáng). Không để chữ hoà vào nền dù phong cách
  quy định màu (vd chữ neon xanh trên màn hình trắng). Viết plan xong chạy `python scripts/tuong_phan.py "<folder>"` (đo tương phản
  trên khung thật, cả ảnh trám) → `--sua` tự thêm viền tối (hơi khó đọc) hoặc đặt chữ lên nền khối mờ (rất khó đọc), giữ màu chữ;
  muốn đổi màu chữ cho hợp hơn thì sửa tay. soat.py cũng báo lỗi này.
- **CHỮ TRÁNH MẶT NHÂN VẬT CHÍNH** (quy tắc cứng): chữ / thẻ / nhãn / khung nổi KHÔNG đè lên mặt người nói. Vùng mặt theo
  thời gian ở `_work/mat.json` (prepare tự dò; thiếu thì `python scripts/nho_may.py mat "<folder>"`). `"big"` = tỉ lệ thời
  gian nhân vật chiếm phần lớn khung → càng cao càng phải dồn chữ lên TRÊN CÙNG (y ≈ 150–400, dưới nhãn ngày nếu có) hoặc
  XUỐNG HẲN dưới mặt (trên vùng phụ đề), không đặt giữa khung. Khi đặt y, xem hộp mặt ở mốc đó (faces: [giây gốc, x, y, w, h]).
  Viết plan xong chạy `python scripts/tranh_mat.py "<folder>"` (báo khối đè mặt) → `--sua` để tự dời lên trên / xuống dưới
  (tránh cả khối khác & nhãn ngày, khung nổi quá to thì tự thu nhỏ). soat.py cũng báo lỗi này.
- TỰ KIỂM TRA trước khi render bản cuối — NHANH, KHÔNG chụp khung (người dùng còn xem lại & sửa trong trình chỉnh sửa, xem
  trước giống hệt bản xuất): chạy `python scripts/soat.py "<folder>"` (< 1 giây) rồi đọc báo cáo + plan.json, sửa 1 vòng.
  Chỉ dùng `render.py --check` (2–3 mốc) khi vừa tạo kiểu đồ họa lạ chưa chắc bố cục, hoặc người dùng nhờ kiểm tra hình. Duyệt theo danh sách:
  1. Chính tả, dấu tiếng Việt, tên riêng; số liệu khớp brief/lời nói.
  2. Không đè phụ đề, mặt người, logo, chữ cháy sẵn; không tràn khung; chip ≤ 3 cùng lúc; chữ nổi rõ trên nền (tuong_phan.py).
  3. Mỗi đồ họa xuất hiện đúng lúc nói (±0.2s); cách nhau 3–6s, không có khoảng > 10s trống minh họa (trừ khi đang
     thấy cảnh quan trọng); broll ≤ 30% thời lượng; stock đúng bối cảnh.
  4. Có hook rõ trong 3s đầu và CTA ở cuối (theo brief, mặc định kêu gọi follow/inbox).
  5. captions đúng (tắt nếu đã có phụ đề cháy sẵn), fixes đủ các chữ nhận sai.
  6. Âm thanh: tiếng gốc rè/ồn → `"audio": {"denoise": 1–2}`; tiếng nhỏ/không đều → `"normalize": true`.
  7. Đoạn người nói dài > 8s không có gì thay đổi → thêm zoom nhấn mạnh hoặc minh họa. Nhiều lần quay → đã chọn đúng
     lần đọc tốt nhất cho từng câu, điểm nối không cụt chữ.
  8. Chuyển cảnh mượt: đã chạy snap.py; không có đoạn < 1,2s vô lý; không đặt zoom punch / chữ mới hiện đúng khung điểm
     nối (lệch ra ≥ 0,2s); không lạm dụng flash. Xem check.jpg ở mốc ngay trước & sau 1–2 điểm nối.
  9. Âm thanh hiệu ứng: đã chạy `python scripts/sfx.py tu-gan "<folder>"` (mật độ theo phong cách), không dồn dập — ≈ 1 tiếng / 5s,
     chuông 1 lần; soat.py không còn báo "dày quá" / "sát nhau".
  10. Hiệu ứng kiểu AE (mục "Khối kiểu After Effects"): đã chạy `python scripts/ae.py tu-gan "<folder>"` TRƯỚC sfx tu-gan (lớp phủ theo phong
     cách, tự tắt nếu style.effects.overlay = "không"); có nhạc nền → `python scripts/ae.py bat-nhip "<folder>"`. Không lạm dụng:
     overlay ≤ 20% thời lượng, mỗi 4–8s tối đa 1 hình vẽ ra (shape), chữ 3D / cảnh dựng sẵn chỉ cho ý quan trọng.
  Sửa và kiểm tra lại, tối đa 2 vòng.
- Sau khi render: kiểm tra final.mp4 — thời lượng khớp, có tiếng, xem 3 khung (đầu/giữa/cuối) bằng ffmpeg.
- Ghi `<folder>/bao-cao.md` (ngắn): đã thêm gì; chữ đã sửa; giả định đã chọn; ảnh/thông tin nên bổ sung để bản sau tốt hơn.
  Nhắc người dùng có thể tự chỉnh tiếp bằng nút ✂ Chỉnh sửa.
- Báo người dùng 1–2 dòng mỗi dự án xong, rồi sang dự án kế. Dự án nào lỗi không tự khắc phục được → ghi lý do vào
  bao-cao.md, bỏ qua, làm tiếp dự án khác. Cuối đợt: tóm tắt bảng (dự án · thời lượng · trạng thái · cần bổ sung).
- Sửa sau đợt: người dùng nhắn "sửa <tên dự án>: ..." → chỉ sửa outline/plan/canh của dự án đó, kiểm tra, render lại,
  cập nhật bao-cao.md.
- Nếu môi trường không render được (vd máy Linux không có trình biên dịch của Remotion), chép tool + dự án sang môi
  trường render được, render ở đó rồi chép final.mp4 về đúng folder.

## Video mẫu & PHONG CÁCH — folder có `_mau/` chứa 1 video, hoặc dự án đã chọn bộ phong cách
Mục tiêu: dựng video của người dùng THEO PHONG CÁCH clip mẫu — font, cách chèn chữ, cách chữ hiện/ẩn, hiệu ứng, kiểu phụ đề,
cách chèn minh họa, nhịp cắt, âm thanh — KHÔNG chép nội dung và KHÔNG ép vào mấy khối 3D xanh có sẵn nếu mẫu không như vậy.
Phong cách được chia THÀNH PHẦN: chu (chữ & font) · phude (phụ đề) · chuyencanh (chuyển cảnh) · hieuung (zoom, chớp,
rung) · dohoa (đồ họa & nhãn dán) · minhhoa (chèn ảnh/video) · amthanh (sfx, nhạc) · mau (màu) · nhip (nhịp dựng).
Người dùng có thể TRỘN: mỗi thành phần lấy từ 1 bộ khác nhau (file `<folder>/phong-cach-tron.json`, chọn trên giao diện).
LUÔN chạy `python scripts/phongcach.py tron "<folder>"` trước khi lên dàn ý (chưa chọn → nó nhắc Claude tự chọn bộ theo nội dung) — xem từng thành phần lấy
từ đâu + mô tả + ghi chú cách dựng của từng nguồn. CHỈ áp phần ghi chú thuộc thành phần đã chọn từ nguồn đó (vd lấy
phụ đề của bộ A, chuyển cảnh của bộ B → nhịp chữ/đồ họa KHÔNG theo A hay B). render.py tự trộn style; plan.json ghi đè được.

1. Chưa có `_mau/_phan-tich/phan-tich.json` → `python scripts/nho_may.py style "<folder>"`.
2. XEM KỸ (đây là bước quan trọng nhất):
   - `hieu-ung_*.jpg`: mỗi hàng = 6 khung liền nhau cách 0,1s lúc chữ/hình xuất hiện → nhận KIỂU HIỆN (bật/nảy/trượt lên/
     gõ từng chữ/bật từng từ/mờ→nét/quét…), kiểu chèn ảnh (cắt thẳng, trượt, khung nổi, tròn…), zoom, chớp.
   - `chu_*.jpg`: khung nét → nhận FONT (so với `phong-cach/_font-mau.jpg`, chọn font gần nhất), độ đậm, màu chữ, viền,
     bóng, nền chữ, viết hoa, từ khóa tô màu khác, vị trí, cỡ chữ so với khung 1080×1920.
   - `khung_*.jpg` (mỗi ô 1 giây): mật độ chữ/minh họa, phụ đề (vị trí, kiểu, mấy chữ/dòng), màu video, mở đầu/kết.
   - `phan-tich.json`: nhịp cắt, suKien (lúc chữ/hình hiện + vùng), phuDe (gợi ý), chopSang, âm lượng; `loi-noi.txt`.
   - PHÂN TÍCH SÂU (máy đo, đối chiếu lại bằng ảnh): `bao-cao-mau.md` (tóm tắt dễ đọc) + `ban-do.png` (bản đồ nhịp dựng:
     lời nói / chuyển cảnh / chữ-đồ họa / zoom / tiếng sfx / nhịp nhạc theo thời gian — XEM ảnh này để bắt chước nhịp).
     Trong phan-tich.json: `doHoa` (từng chữ/đồ họa: khung px trên 1080×1920, màu, ở lại bao lâu) + `doHoaTongHop`;
     `zoom` (punch/push/pull trong cảnh); `mauVideo.goiYMau` (thông số màu gợi ý); `nhac` (nhạc nền, BPM, tỉ lệ cắt trùng
     nhịp); `sfx` (từng tiếng: lúc nào, loại whoosh/pop/click/impact/boom/riser/ding, gắn với cut/chu/zoom) + `sfxTongHop`;
     `nhip` (độ dài cảnh, chữ đầu tiên, mật độ chữ theo đầu–giữa–cuối, khoảng lặng — cắt sát lời không).
   - BỐ CỤC & ICON (bắt buộc học, ngang hàng font/màu): `bo-cuc_khung.jpg` (khung hình có vẽ ô: vàng = chữ, cam = khối,
     xanh lá = icon, xanh dương = khung lớn), `bo-cuc.png` (bản đồ nhiệt chỗ hay đặt chữ/icon), `icon-mau.jpg` (icon cắt
     từ mẫu) + `boCuc` trong phan-tich.json (canLe, leNgang_px, vungChu, soKhoiMotLuc, xepChong, khoangCachDong_px,
     icon.viTriCanhChu / kieu_dem / coNen_tiLe; doTinCay thấp = máy dò được ít, tự nhìn ảnh khung hình mà rút).
     Phải rút ra được: chữ căn trái/giữa/phải, lề bao nhiêu; chữ hay ở vùng nào (tránh mặt); mấy khối cùng lúc, xếp chồng
     dọc thành danh sách hay rải; icon đứng bên nào của chữ, cách bao xa, cỡ so với chữ; KIỂU icon (emoji nhiều màu / icon
     nét mảnh / icon đặc / huy hiệu tròn có nền / sticker 3D), màu icon, và ICON GÌ cho ý gì (vd giá → 💰 hay BadgeDollarSign,
     vị trí → 📍 hay MapPin, cảnh báo → ⚠️, tăng → 📈 / TrendingUp; mẫu hay dùng mũi tên chỉ, tick xanh, dấu X đỏ…).
     Máy không đọc được nghĩa icon — Claude NHÌN icon-mau.jpg + khung_*.jpg để biết họ chọn icon theo logic nào.
     Dùng để: đặt chữ đúng vùng/cỡ/thời lượng như mẫu; zoom đúng kiểu & tần suất; màu theo goiYMau; cắt theo nhịp nhạc nếu
     mẫu làm vậy (catTrungNhip_tiLe cao → đặt điểm cắt/chữ hiện trùng nhịp); sfx đúng loại ở đúng khoảnh khắc
     (goiY.style.sfx.map được sfx.py tu-gan dùng tự động).
3. Ghi `_mau/phong-cach.json` (dạng dưới) + `_mau/ghi-chu.md` (cách dựng, mỗi mục 1–2 dòng: hook 3s đầu; mật độ chữ —
   mấy giây 1 lần, chữ gì (từ khóa/câu/số), đặt ở đâu; kiểu chữ dùng khi nào; phụ đề; minh họa — tỉ lệ, kiểu, khi nào; zoom;
   chuyển cảnh; âm thanh — nhạc, sfx; kết; điều tool chưa làm được + cách gần nhất đã chọn).
   ```json
   {"ten": "Tên ngắn", "mo_ta": "1 câu mô tả", "nguon": "mau.mp4",
    "style": {"font": "Montserrat", "heading": "Anton",
      "text": {"look": "solid", "color": "#FFFFFF", "bg": "#FF3B30", "hlColor": "#FFE600", "stroke": 0, "strokeColor": "#000000",
               "shadow": "soft", "anim": "up", "out": "fade", "upper": true, "size": 86, "radius": 14},
      "captions": {"preset": "wordbox", "font": "Montserrat", "size": 64, "color": "#FFFFFF", "active": "#FFFFFF",
                   "activeBg": "#FF3B30", "upper": true, "anim": "pop"},
      "broll": {"enter": "cut", "exit": "cut", "kenburns": true, "overlay": false, "pip": "clean"},
      "templates": false},
    "plan": {"captionTop": 1300, "wordsPerPage": 2, "transition": "auto", "cutFx": "none",
             "color": {"contrast": 108, "saturation": 112}, "sfxVolume": 0.4}}
   ```
   Thêm `"thanhPhan": {"chu": "...", "phude": "...", "chuyencanh": "...", "hieuung": "...", "dohoa": "...", "minhhoa": "...",
   "amthanh": "...", "mau": "...", "nhip": "..."}` — mô tả NGẮN (≤ 12 chữ) từng thành phần để người dùng tích chọn trên giao
   diện; thành phần nào mẫu không có thì bỏ. Thêm `style.effects` ({"zoom": "nhiều|vừa|ít|không", "zoomStyle": "punch|in…",
   "shake": true, "flash": n, "overlay": ["lightleak", "filmburn"…] hoặc "không" — lớp phủ mẫu dùng}), `style.motion` ({"ease": "smooth|snappy|bouncy|elastic",
   "mblur": true} — chuyển động chữ/khối như mẫu; chữ hiện từng ký tự/từ → text.anim stagger|maskUp|rise|wave…), `style.graphics` ({"sticker": "emoji|icon|không", "ghiChu": "..."}), `style.sfx`
   ({"density": "it|vua|nhieu", "set": "mem|manh", "joins": true}), `style.pace` (nhịp) khi thấy rõ.
   LUÔN ghi bố cục + icon (thành phần "bocuc", "icon"; render và trình chỉnh sửa dùng thật):
   `style.layout` = {"align": "left|center|right" (căn chữ mặc định + phía đặt nhãn chip), "marginX": px lề ngang,
   "textZone": "top|middle|bottom", "iconPos": "left|right|above|below|none", "maxBlocks": n, "stackGap": px};
   `style.icons` = {"kind": "emoji|lucide|filled|none", "bg": "badge|circle|square|none", "bgColor": "#..", "color": "#..",
   "stroke": 2.6, "size": px, "set": ["📍", "💰", "MapPin", ...] (bộ icon mẫu hay dùng — emoji thật hoặc tên lucide giống
   nhất), "map": {"giá": "💰", "vị trí": "📍", ...} (ý → icon, theo logic chọn icon của mẫu)}.
   `style.skin` = lớp da các khối có sẵn (thẻ giá, chip, checklist, CTA, nhãn ngày) — mỗi lớp có HÌNH KHỐI riêng (remotion/src/skins.tsx):
   "3d" (bóng bẩy, kiểu cũ) | "flat" (kính tối, viền mảnh) | "light" (thẻ trắng) | "classic" (thẻ ngà viền chỉ kép màu nhấn, hoa văn ◆,
   chữ có chân) | "med" (thẻ trắng đỉnh vòm, xanh Aegean + gạch nung, đường sóng) | "luxe" (đen nhám, chữ ánh vàng kim, góc vuông)
   | "indochine" (xanh rêu viền vàng đồng kép) | "japandi" (be gỗ phẳng, chữ mảnh, 3 chấm) | "scrap" (giấy dán băng keo, chữ
   viết tay) | "ticket" (vé tàu / boarding pass có lỗ bấm) | "podcast" (tối mềm bo lớn) | "info" (thẻ trắng viền đậm + bóng đổ cứng,
   infographic) | "news" (thẻ trắng sọc đỏ, bản tin). `style.map` = mặc định cho khối map (style, theme, lineMode, camera, frame, color). `style.accent` = màu nhấn;
   `style.frame` = khung trang trí cả video: classic (viền chỉ kép + hoa văn 4 góc) | arch (viền vòm) | corners (góc chữ L) |
   letterbox (dải đen) | grain (hạt phim) | leak (vệt sáng hắt) | datestamp (ngày kiểu máy film, {"type":"datestamp","date":"'26 11 06"})
   | rec (khung REC + timecode máy quay) | wave (sóng âm trang trí podcast) | ticker (dải chữ chạy thời sự: {"type":"ticker","label","text"})
   | ink (tranh thủy mặc: dải giấy sương + núi mực + trăng + chim phía trên, lau sậy 2 góc dưới; {"type":"ink","palette":mono|color|night|dawn,
   "items":["sun","birds","reeds"]}) — chữ câu thơ đặt trong dải trên (y ≈ 180–420)
   Khối `presenter` có thêm bg: ink | ink-color | ink-night | ink-dawn (tranh thủy mặc làm nền); `style.presenter` (vd {"mode":"card",
   "bg":"ink-color","s":0.56,"y":1250}) = áp khung người nói cho CẢ video khi plan chưa có khối presenter.
   | live (nhãn LIVE + giờ: {"type":"live","label":"TIN NÓNG"}) | grid (lưới tọa độ) | coords (la bàn + tọa độ: {"type":"coords","lat","lng"}); nhiều kiểu = mảng; màu = {"type", "color"}. `plan.theme` trong bộ = màu riêng của bộ.
   Mẫu nhìn hiện đại / tối giản → "flat".
   BỘ TẠO SẴN (phong-cach/, xem mo_ta "Hợp: …") — người dùng chưa chọn gì mà nhờ "chọn phong cách hợp" thì gợi ý theo chủ đề:
   review/tour căn hộ → Review căn hộ sáng · Editorial xanh | cao cấp, biệt thự → Sang trọng BĐS · Đen trắng điện ảnh |
   tin thị trường, chính sách → Bản tin truyền hình · Tin tức thị trường | điểm tin nhanh → Tin nhanh 60 giây | infographic, giải thích
   số liệu → Infographic phẳng · Dữ liệu neon | vị trí, tiện ích, bản đồ → Bản đồ vị trí · Bản đồ sáng tối giản | giá, lãi suất, so sánh → Phân tích số liệu | thủ tục, các bước → Hướng dẫn
   từng bước | câu chuyện khách, hành trình → Kể chuyện cảm xúc | series thử thách → Thử thách 30 ngày · Năng động TikTok |
   mở bán, ưu đãi → Sự kiện mở bán | vlog, hậu trường → Vlog đời thường | môi giới cá nhân, tư vấn → Doanh nhân tối giản |
   tân cổ điển → Tân cổ điển · Hoàng gia châu Âu | biển, Santorini → Địa Trung Hải | penthouse, hàng hiệu → Đen vàng thượng lưu |
   Đông Dương, Pháp cổ → Đông Dương Indochine | tối giản gỗ → Japandi gỗ mộc | vlog chill → Vlog chill film · Camcorder hoài
   niệm | du lịch → Du lịch nhật ký · Hoàng hôn lofi | podcast → Podcast tối giản · Podcast chia khung | kể chuyện thong thả → Cà phê sáng lofi |
   đọc thơ, đọc truyện, tâm sự → Thủy mặc mực tàu · Thủy mặc nhạt màu · Thủy mặc đêm trăng · Thủy mặc bình minh · Thủy mặc khung tranh ·
   Thơ dọc hoà trộn · Thơ trên mây (thơ cổ, lục bát, thiền, quê hương → ưu tiên bộ Thủy mặc; thơ buồn/đêm → Thủy mặc đêm trăng) | tin tức có người dẫn + video hiện trường → Bản tin chia đôi |
   talking head muốn luôn thấy người nói → Talking head minh họa dưới | kể chuyện kiểu phim tài liệu → Kể chuyện điện ảnh chia đôi |
   nghỉ dưỡng, đất vườn → Thiên nhiên xanh lá | gia đình trẻ, nội thất → Pastel nhẹ nhàng | phố cổ, nhà cũ → Retro cổ điển |
   công nghệ, trẻ → Tech tối giản · Neon đêm | kiến thức, giải thích → Giấy be Papercut · SeeCut đỏ gạch · Kiến thức trắng xanh |
   video giọng đọc + hình động không người nói → Motion xanh nước. `style.graphics.ghiChu` của bộ = gợi ý khối nên dùng.
   Bộ ✨ hiệu ứng kiểu AE (lớp phủ, chữ động, hình vẽ ra, chữ/ảnh 3D, cảnh dựng sẵn): dự án hạng sang → BĐS cao cấp AE · Điện ảnh AE |
   mở bán, khuyến mãi → Mở bán bùng nổ AE | tin, phân tích → Tin tức motion AE | kiến thức, mẹo, đúng/sai → Kiến thức vẽ tay AE |
   công nghệ, AI, nhà thông minh → Công nghệ glitch AE | vlog nhẹ nhàng → Vlog mộng mơ AE | thơ hiện đại → Thơ ánh sáng AE |
   kể chuyện, hành trình → Trailer kể chuyện AE | podcast → Podcast motion AE | review nhanh, thử thách → Năng động AE.
   YÊU THÍCH: người dùng đánh dấu ⭐ trong thư viện (phong-cach/_yeu-thich.json); `phongcach.py ds` in nhóm ⭐ trước — khi tự chọn,
   ƯU TIÊN bộ yêu thích nếu hợp nội dung. Thư viện chia NHÓM CHỦ ĐỀ ("nhom" trong phong-cach.json: bds | tin | tho | chill | kechuyen |
   nangdong | podcast; bỏ trống = tool tự đoán theo tên) — khi lưu bộ mới nên ghi "nhom".
   Dự án KHÔNG chọn phong cách và không có video mẫu → Claude TỰ CHỌN 1 bộ theo nội dung (bảng chủ đề trên): đọc lời thoại + brief,
   `python scripts/phongcach.py chon "<folder>" "<tên bộ>"`, ghi lý do vào bao-cao.md. Ngoại lệ: ⚙ Cài đặt đặt "Kiểu gốc của tool"
   (settings.json "defaultStyle": "_goc") hoặc một bộ cụ thể → theo cài đặt. `phongcach.py tron` sẽ nhắc khi cần tự chọn.
   Thêm vào `thanhPhan`: "bocuc" (vd "chữ căn trái, list icon trái, vùng dưới"), "icon" (vd "emoji màu, không nền").
   Ghi chú bố cục/icon trong ghi-chu.md: cách họ trình bày từng loại thông tin (số liệu, danh sách, so sánh, cảnh báo).
   Máy đã đoán sẵn trong phan-tich.json → "goiY" (chuyển cảnh, âm thanh, nhịp, chớp) và "chuyenCanh" từng điểm (xem
   chuyen-canh_XX.jpg để xác nhận) — dùng làm điểm xuất phát, sửa nếu thấy sai.
   Thông số nào không thấy rõ thì bỏ (dùng mặc định). `templates: false` = mẫu không dùng thẻ 3D kiểu tool → dùng `text`
   (các look mới), `sticker`, `zoom`, `broll`/`pip` thay cho priceHook/chip/cta/checklist...
4. (Thư mục `_hoc-<tên>` trong cho-edit = người dùng bấm "🎬 Học phong cách từ video" ở thư viện: máy đã phân tích và lưu sẵn bộ
   "<tên>" (bản máy đoán, tên trong _ten-phong-cach.txt). Được nhờ "rút kỹ & lưu đè": làm bước 2–3 như trên rồi
   `python scripts/phongcach.py luu "<folder>" "<tên đó>"` để ghi đè bộ cũ — KHÔNG dựng video. Thư mục này có thể có video demo
   (video.mp4 + plan.json "_demo": true, do scripts/demo_style.py dựng máy) để người dùng xem/chỉnh rồi lưu đè bằng nút ⭐.)
   4. (Lưu từ VIDEO ĐÃ DỰNG mà người dùng ưng, không cần video mẫu: `python scripts/phongcach.py luu-ketqua "<folder>" "<tên>"` — giao
   diện có nút ⭐ "Lưu phong cách từ video này"; sau đó đọc ghi-chu.md của bộ, bổ sung cách dựng nếu cần.)
   Lưu thành bộ dùng lại: `python scripts/phongcach.py luu "<folder>" "<tên>"` (khi người dùng nhờ "rút/lưu phong cách",
   hoặc ở chế độ tự động — đặt tên theo đặc điểm, vd "Chữ đỏ nền khối", rồi báo người dùng tên đó). Lệnh này cũng
   chọn bộ đó cho dự án và tự vẽ ảnh minh họa (demo.jpg) hiện trong thư viện phong cách trên giao diện. Sửa
   phong-cach.json của một bộ xong → `python scripts/phongcach.py anh "<tên>"` để vẽ lại ảnh. `... ds` = danh sách.
   Gửi / nhận bộ phong cách: `python scripts/phongcach.py xuat "<tên>" [file]` → gói `.phongcach`; `... nhap "<file.phongcach>"` → thêm vào
   thư viện (trùng tên thì thêm (2)); báo nếu bộ dùng khối mà bản tool chưa có (orbit, mapTour…). Trên giao diện: 📤 / 📥.
5. Dựng plan.json theo phong cách: KHÔNG cần lặp lại style trong plan (render tự trộn) — chỉ ghi đè khi một chữ cần khác.
   Đặt chữ đúng mật độ/vị trí/kiểu của mẫu, hiệu ứng hiện theo từng loại chữ như mẫu (vd tiêu đề "bounce", từ khóa "pop").
   Theo `style.layout`: y của chữ trong vùng textZone (vẫn tránh mặt), không quá maxBlocks khối cùng lúc, danh sách xếp
   chồng cách stackGap, x/align theo mẫu (text không ghi align thì render tự căn theo layout.align + marginX).
   Theo `style.icons`: CHỈ chọn icon từ `set`/`map` hoặc cùng kiểu (mẫu dùng emoji → sticker/chip dùng emoji; mẫu dùng icon
   nét → tên lucide; kind "none" → không chèn icon). Icon đặt đúng phía iconPos so với chữ, cỡ ~icons.size.
   Tự kiểm tra: chỉ khi bắt chước bộ phong cách MỚI lần đầu thì chụp 2–3 khung (render.py --check) so với chu_*.jpg của mẫu
   — font, màu, cỡ, vị trí; sửa 1 vòng. Dùng lại bộ đã lưu thì không cần chụp.
6. Báo người dùng: đã bắt chước được gì, gần đúng chỗ nào (vd font gần nhất), chưa làm được gì.

## Chế độ CHỈ TIẾNG (folder chỉ có `voice.*`, KHÔNG có video) — `_work/info.json` có `"mode": "audio"`
Vd đọc thơ chỉ có giọng. prepare tự tạo video nền màu giấy dài đúng bằng voice (tiếng = voice) rồi nhận giọng như thường — làm như
video 1 clip, bỏ 2a/2b, không cảnh trám video. Hình do phong cách vẽ: chọn bộ có `style.backdrop` (Thủy mặc đọc thơ (chỉ tiếng) ·
Thủy mặc mực tàu (chỉ tiếng) · Thủy mặc đêm trăng (chỉ tiếng)) — cả khung là tranh thủy mặc chuyển động nhẹ. Chữ câu thơ là chính
(captions: false), ảnh minh họa = broll ẢNH toàn khung (tranh ở `assets-chung/thuy-mac/`, copy vào assets/). Nhạc: `"music"` nếu
có nhac.*. Không chọn phong cách mà nội dung là thơ → tự chọn 1 bộ "(chỉ tiếng)". `style.backdrop` = {"type":"ink","palette":...}.
**Bắt đầu từ KỊCH BẢN (không phải thơ)** — dự án tạo từ "📝 Bắt đầu từ kịch bản" (có `kich-ban-voice.txt`, voice là giọng AI,
không có video): dựng kiểu video không người (faceless) — KHÔNG để nền giấy trơn. Mỗi câu / ý của voice = 1 cảnh: ưu tiên tư liệu của
người dùng (assets/cua-ban), còn lại tìm stock VIDEO (`stock.py search ... --video`, ảnh khi không có video hợp) → `broll` nối liền
nhau 2–4s phủ gần hết video (quy tắc broll ≤ 30% KHÔNG áp dụng ở đây), cảnh chậm / nhanh thì dùng `rate` của broll; chữ nhấn từ khoá
+ số liệu, `captions: true` (phụ đề sửa theo kich-ban-voice.txt), nhạc nền nếu có. Thiếu cảnh hợp thì dùng nền phong cách + chữ lớn,
ghi vào bao-cao.md loại cảnh nên quay / bổ sung. Được tối đa ~10 lần tìm stock cho dự án kiểu này.

## Chế độ VOICE (folder có file giọng đọc riêng)
Nếu folder có `voice.*` (hoặc `giong-doc.*`, `loi-doc.*`; mp3/wav/m4a...) → video được dựng THEO VOICE:
footage (các clip) chỉ dùng làm hình, tiếng gốc tắt; lời nói, phụ đề, mốc đồ họa đều lấy từ voice.
Có thể có thêm `nhac.*` (nhạc nền). Cách nhận biết: `_work/info.json` có `"mode": "voice"`.
Khác với quy trình thường:
- Bước 1 vẫn chạy prepare.py (nếu `info.json` chưa có `"mode": "voice"` thì chạy lại — voice được thêm sau).
  Kết quả: transcript.txt / words.json là của VOICE; `_work/footage_*.jpg` = lưới khung hình footage,
  mỗi ô cách 3s, mốc giây ghi ở góc ô (giải thích trong `_work/footage.txt`); `_work/footage_cuts.json` = điểm chuyển cảnh trong footage.
- Bước 2: đọc transcript (voice) + brief, XEM HẾT các `footage_*.jpg` để biết footage có cảnh gì ở giây nào.
- Bỏ bước 2b (không dùng cut.json/trim.py).
- Bước 3 (outline.md): mỗi dòng = 1 câu/ý của voice → cảnh footage nào (mốc giây trong footage) + đồ họa gì.
  Dạng: `[giây voice] lời voice → cảnh footage [a–b]: mô tả → đồ họa/nguồn`.
- Bước 3b — viết `<folder>/canh.json` rồi chạy `python scripts/nho_may.py assemble "<folder>"`:
  ```json
  {"scenes": [[62.0, 66.5], [5.0, 9.2], [22.0, 25.8]], "origVolume": 0, "musicVolume": 0.12}
  ```
  `scenes` = các đoạn [bắt đầu, kết thúc] tính theo giây TRONG FOOTAGE, nối liền nhau từ giây 0 của video;
  thứ tự tùy ý (không cần theo thứ tự quay). Cảnh thứ k bắt đầu ở giây voice = tổng độ dài các cảnh trước →
  canh độ dài từng cảnh sao cho điểm chuyển rơi vào chỗ ngắt câu của voice (xem words.json), mỗi cảnh 2–6s,
  khớp nội dung đang nói (nói bếp → cảnh bếp). Tổng ≈ độ dài voice (`durationSec` trong info.json).
  Tránh đoạn footage rung, che ống kính, người quay lóng ngóng. `origVolume` 0 = tắt tiếng gốc (mặc định);
  `musicVolume` chỉ có tác dụng khi có `nhac.*`. Kết quả `_work/edit.mp4` dài đúng bằng voice.
- Bước 5 trở đi như thường, mốc theo voice (words.json). `captions: true` (phụ đề từ voice) trừ khi footage có
  chữ cháy sẵn. broll vẫn dùng được nhưng thường không cần vì đã chọn cảnh từ footage.
- render.py sẽ báo lỗi nếu chưa chạy assemble.py.

## KHUNG HÌNH (tỉ lệ video) — `khung.json` của dự án
Người dùng chọn lúc tạo dự án / thẻ 📐 Khung hình / trình chỉnh sửa: `9:16` (mặc định, 1080×1920) · `4:5` (1080×1350) · `1:1`
(1080×1080) · `16:9` (1920×1080). Xem: `python scripts/khung.py "<folder>"`; đổi: `python scripts/khung.py "<folder>" 1:1` (plan.json
đã có -> tự dời y các khối theo tỉ lệ). Khung khác 9:16 thì khi viết plan.json:
- `y` (px) tính trên CHIỀU CAO KHUNG (1350 / 1080 / 1080) — khối không ghi y tự co theo tỉ lệ; `captionTop` ≈ 72% chiều cao, cách
  đáy ≥ 200px; y > chiều cao − 40 là ra ngoài khung (soat.py báo). `x` dạng 0–1 tự theo bề ngang (16:9 rộng 1920).
- Cỡ chữ giữ nguyên px: khung ngang 16:9 rộng 1920 nên chữ tự trông nhỏ hơn — tiêu đề 100–140, chữ thường 64–90, phụ đề 56–64.
- Video gốc khác tỉ lệ khung nhiều -> tự `"mainFit": "blur"` (giữ trọn hình, nền mờ hai bên); muốn cắt cho đầy khung: `"mainFit": "cover"`.
- Chưa hỗ trợ: đặt khối SAU người (behind / z < 0 — tự bỏ), dò tránh mặt (tranh_mat.py bỏ qua) -> tự xem check.jpg.
- Không có vùng nút TikTok ở khung 1:1 / 16:9 — đặt CTA thấp được; 4:5 (Facebook / Instagram) vẫn chừa đáy ~120px.

## Logo & số điện thoại của người dùng (tự chèn khi xuất)
Người dùng thiết lập 1 lần ở trang chủ / ⚙ Cài đặt → 🏷 Logo & SĐT (`thuong-hieu.json` + `thuong-hieu/logo.*` ở gốc tool).
render.py TỰ chèn (plan["brandMark"], remotion/src/Brand.tsx — lớp trên cùng): logo ở góc (mặc định trên trái, tự dời sang
phải nếu video có nhãn NGÀY X/Y), SĐT dưới logo / trên phụ đề, màn kết logo to + SĐT ở mấy giây cuối nếu bật.
"Áp dụng cho tất cả" = mọi dự án; từng dự án tích/bỏ tích riêng (`<folder>/thuong-hieu.json` {"on": …}).
KHÔNG tự thêm element logo/SĐT vào plan.json (sẽ bị trùng). `python scripts/thuong_hieu.py "<folder>"` (và `phongcach.py tron`)
in vị trí logo/SĐT của dự án → đặt chữ / thẻ tránh chỗ đó; CTA cuối có thể nhắc "gọi số trên màn hình". Màn kết đã có logo + SĐT
→ CTA cuối đặt thấp (y ≥ 1100) hoặc kết thúc trước màn kết. Tắt riêng bản dựng: `"brandMark": false`; đổi vài thông số chỉ
cho video này: `"brandMark": {"logoPos": "tr", "endCard": false}`. Thông tin brief có SĐT khác → dùng SĐT trong brief cho chữ.

## Giọng đọc AI qua API (giọng clone của người dùng) — `scripts/tts_api.py`
Người dùng nhập API key + voice id ở ⚙ Cài đặt (settings.json "ttsApi" — KHÔNG in key ra, không chia sẻ settings.json).
- Kịch bản → voice cả video: trang dự án → "📝 Tạo voice từ kịch bản" (tự Chuẩn bị theo chế độ VOICE). Tự làm:
  `python scripts/tts_api.py "<folder>" "<kịch bản hoặc đường dẫn file .txt>" --voice [--giong voice-xxx] [--toc-do 1.0]`
  → `voice.wav` + `kich-ban-voice.txt` (plan.json/canh.json cũ đổi thành `_cu-...`), rồi chạy prepare. Dùng khi người dùng đưa kịch
  bản (trong brief / file) và nhờ "đọc voice", "tạo giọng đọc"; chưa có key (`python scripts/tts_api.py ds`) → báo người dùng nhập ở ⚙ Cài đặt.
- `kich-ban-voice.txt` có sẵn = ĐÚNG chữ của voice → dùng sửa phụ đề (fixes / captions) và tên riêng, số liệu cho khớp.
- Đoạn lẻ (chèn câu đọc thêm): `python scripts/tts_api.py "<folder>" "câu cần đọc"` → assets/giong-doc/*.wav → khối `audio`; hoặc
  `tts.py ... --giong api:<voice id>`. Trình chỉnh sửa: Âm thanh → Giọng đọc AI (chọn giọng API hoặc offline).
- Số / giá / chữ tiếng Anh nên viết theo cách đọc trong kịch bản nếu sợ đọc sai (vd "2,5 tỷ" → "hai tỷ rưỡi").
- Chưa có giọng API: giọng VieNeu chạy trên máy — `tts.py "<folder>" "câu" --giong "vn:Hải Đăng"` (25 giọng Bắc / Trung / Nam:
  `tts.py ds`; nam Hải Đăng, Thiện Minh (kể chuyện), Quốc Tuấn; nữ Trúc Ly, Ngọc Huyền, Mai Anh (tin tức); miền Nam Thùy Dung, Minh
  Triết…). Tự nhiên hơn giọng `nu1`/`nu2`. Lần đầu cài ~250MB + tải mô hình ~600MB từ huggingface.co; mạng chặn → tự đọc bằng `nu1`.

## Tua nhanh / slow-motion / timelapse THEO NỘI DUNG (tự quyết, không cần người dùng nhắc)
Đổi tốc độ khi nó làm nội dung dễ xem hơn — mỗi video 0–3 chỗ, đừng lạm dụng:
- TIMELAPSE (4–16×): quá trình dài không có lời quan trọng — xây dựng, dọn dẹp, sắp xếp đồ, đi đường / lái xe tới dự án, trời chuyển
  sáng–tối, dòng người / xe. Lời kịch bản kiểu "sau 3 tháng…", "cả buổi sáng…", "trên đường tới…" → timelapse đúng đoạn đó.
- TUA NHANH (1,3–2×): thao tác dài lặp lại mà vẫn cần nghe (mở cửa từng phòng, lướt điện thoại, ghi chép…); đoạn nói chậm lề mề thì
  cắt bớt trước, chỉ tua khi không cắt được.
- SLOW-MOTION (0,5× mượt; 0,25× cho khoảnh khắc "wow"): khoe chi tiết / cảm xúc — view từ ban công, ánh sáng qua cửa sổ, bước vào nhà
  lần đầu, nước chảy, phản ứng bất ngờ, câu chốt. Chỉ dùng trên cảnh KHÔNG có lời đang nói (tiếng gốc tự tắt), thường kèm nhạc nền.
- SPEED RAMP (`segCurve` "hero" / "bullet"): cảnh mở cửa, reveal căn hộ, xoay camera — nhanh vào, chậm giữa, nhanh ra.
Cách làm: chế độ thường — tách đoạn bằng `segments` rồi `segSpeed` cho đoạn đó (mốc element sau đoạn đó theo giây TRƯỚC khi đổi tốc độ,
editor/render tự tính). Chế độ VOICE — số thứ 3 trong `canh.json` scenes: `[a, b, 4]` (8s footage thành 2s, khớp câu voice ngắn),
`[a, b, 0.5]` (cảnh 2s đẹp kéo thành 4s cho câu voice dài) → chọn tốc độ sao cho (b − a) / tốc độ = độ dài câu voice; tốt hơn là lặp
cảnh hay đứng hình. Ghi vào outline.md / bao-cao.md chỗ nào đổi tốc độ và vì sao.

## Bước 1 — Chuẩn bị (máy tự chạy)
```
python scripts/nho_may.py prepare "<folder>"
```
Bỏ qua nếu `<folder>/_work/words.json` đã có (trừ khi folder có voice mà info.json chưa có `"mode": "voice"`). Kết quả trong `<folder>/_work/`.

## Bước 2 — Đọc nội dung
Đọc: `_work/transcript.txt` (mốc giây ở đầu dòng), `_work/info.json`, `brief.txt` nếu có,
và XEM `_work/sheet.jpg` (16 khung hình) để biết video có sẵn phụ đề / logo / chữ ở đâu.
Mốc chính xác từng chữ nằm trong `_work/words.json`.
**Ghi chú từng clip — `ghi-chu-clip.json`** ({tên clip: ghi chú}, người dùng gõ lúc tải video lên / ở danh sách clip): ưu tiên
CAO HƠN brief cho clip đó. Vị trí clip trong video ghép: `_work/clips.json` (start/end của từng file). Làm theo đúng ghi chú:
- "lấy đoạn …", "bỏ … giây đầu", "chỉ lấy câu …" → đưa vào cut.json / segments (bước 2a/2b);
- "lấy hình, bỏ tiếng" / "chỉ lấy tiếng" → videoVolume / voice cho đoạn đó (bước 2a, chế độ voice), hoặc che hình bằng broll;
- "hiện …", "chèn chữ / thẻ giá / ảnh … khi nói tới …" → thêm element đúng lúc trong khoảng của clip đó;
- ghi chú chỉ mô tả nội dung clip ("cảnh phòng ngủ", "flycam") → dùng để sắp thứ tự và đặt chữ/nhãn hợp.
Không làm được điều gì trong ghi chú (thiếu file, mâu thuẫn) → ghi vào báo cáo cuối cho người dùng.
Nhận giọng hay nghe sai tên riêng/tiếng Anh (vd "OSION PAC" = Ocean Park, "PHIÊN LIKE" = phiên live,
"FORLO" = follow) và số viết bằng chữ. Brief là nguồn đúng cho giá, diện tích, tên dự án.
Footage thô (lời nói chỉ là chỉ đạo người quay, nhiều đoạn im lặng) mà KHÔNG có voice → báo người dùng nên thêm
voice (tab Tổng quan → Giọng đọc) hoặc dựng không lời: tắt tiếng gốc (`"videoVolume": 0`), thêm nhạc nền, chữ.

## Dự án đang DỰNG THÔ trước khi chuẩn bị (`_work/info.json` có `"tho": true`)
Người dùng chọn "Dựng thô trước" lúc tạo dự án: tool mới chỉ GHÉP clip (chưa nhận giọng, chưa phụ đề) để họ cắt ghép trong trình
chỉnh sửa. Đừng edit tiếp: nhắc họ bấm "Xong dựng thô → Chuẩn bị" (tab Dựng thô), hoặc nếu họ nhờ thì chạy
`python scripts/nho_may.py xongtho "<folder>"` (xuất bản thô thành dung-tho.mp4, cất clip gốc vào _nguon-tho/, rồi chuẩn bị đầy
đủ; thêm `--cat-lang` = tự cắt từ đệm & khoảng lặng sau khi nhận giọng). Sau đó dự án là 1 clip đã dựng thô — làm như bình
thường, bỏ bước 2a (chọn lần quay) và phần cắt lỗi/lạc đề của 2b; nếu còn à/ừ/lặng dài (chưa có cut.json) thì chỉ chạy
`python scripts/cat_lang.py "<folder>"` rồi `python scripts/nho_may.py trim "<folder>"`.

## DỰNG THÔ do người dùng làm trước (plan.json có `"roughCut": true`)
Người dùng đã tự cắt ghép (segments), chọn chuyển cảnh (transition / joinFx) trong trình chỉnh sửa (tab ✂ Dựng thô) để tiết kiệm
lượt Claude. Khi đó: BỎ bước 2a, 2b, sắp lại thứ tự clip, snap.py; KHÔNG đổi `segments`, `transition`, `joinFx`, `segXf`, `mainXf`.
Đọc `_work/transcript_tho.txt` (lời thoại đã cắt, mốc giây theo VIDEO XUẤT RA — dùng thẳng làm start/end của element; thiếu thì
chạy `python scripts/dung_tho.py "<folder>"`) thay cho transcript_full / clips.json; chỉ tra words.json khi cần mốc chính xác (nhớ
quy đổi theo segments). Viết plan.json = plan hiện tại + elements / captions / phong cách, giữ nguyên mọi trường người dùng đã đặt.

## Bước 2a — Nhiều lần quay cùng một nội dung (2–3 file, mỗi file ưng một đoạn)
Dấu hiệu: nhiều clip có lời nói gần giống nhau (xem `_work/clips.json` để biết mỗi file nằm ở giây nào trong video ghép,
và so transcript_full.txt giữa các khoảng đó), hoặc brief/người dùng nói "quay nhiều lần", "mỗi file lấy một đoạn".
- Với MỖI câu/ý, chọn lần đọc tốt nhất: đủ câu, không vấp, không ngập ngừng, giọng/biểu cảm tốt nhất; nếu ngang nhau
  thì ưu tiên lần quay sau. Người dùng đã chỉ rõ "file X lấy đoạn Y" thì làm theo đúng.
- Ghi kết quả thành `"segments"` trong plan.json (KHÔNG dùng trim.py cho trường hợp này) — mỗi đoạn là [a, b] giây trong
  video ghép (_work/ghep.mp4), theo đúng thứ tự kể chuyện; cắt sát câu, chừa ~0.1s đầu và ~0.15s cuối.
  Người dùng sẽ thấy từng đoạn (ghi rõ lấy từ file nào) trên track Video của trình chỉnh sửa và đổi được.
- Sau đó mọi mốc của element tính theo VIDEO XUẤT RA (sau khi ghép các đoạn): mốc = tổng độ dài các đoạn trước + (giây trong
  đoạn − a). Phụ đề tự động tự đi theo segments.
- Ghi trong outline.md và bao-cao.md: câu nào lấy từ file nào.
- SAU KHI viết segments: chạy `python scripts/snap.py "<folder>"` (dời mép đoạn tới chỗ lặng ±0,15s, tự dời element theo).
- Tránh đoạn < 1,2s (nhìn giật) trừ khi cố ý tạo nhịp nhanh; gộp các mẩu ngắn liền nhau nếu được.

## Sắp lại thứ tự clip theo nội dung ("sắp lại thứ tự clip", "thứ tự clip bị sai")
Đọc `_work/clips.json` + `_work/transcript_full.txt`, xác định lời nói của từng clip, sắp theo mạch kể hợp lý:
mở đầu/hook → giới thiệu → nội dung chính (theo trình tự: vị trí → tổng quan → từng phòng/ý...) → tổng kết → kêu gọi.
Các lần quay lại của cùng một ý thì để cạnh nhau. Ghi `thu-tu.txt` (mỗi dòng 1 tên file, đúng như trong clips.json),
chạy lại `prepare.py`, rồi báo người dùng thứ tự mới kèm lý do ngắn cho từng clip.
Nếu dự án ĐÃ có plan.json: KHÔNG ghép lại (mốc sẽ lệch) — thay vào đó đổi thứ tự `segments` trong plan.json và dời
element theo (giống thao tác kéo đoạn trong trình chỉnh sửa), hoặc hỏi người dùng.

## Lấy tiếng một clip làm voice ("file X voice hay, lấy tiếng làm voice")
Giao diện có sẵn nút 🎙 (danh sách clip) và nút "Lấy tiếng làm voice" (tab Nguồn của trình chỉnh sửa). Tự làm thì:
ffmpeg tách tiếng clip đó (cắt đoạn nếu cần) thành `<folder>/voice.m4a`, chuyển clip đó vào `<folder>/_nguon-voice/`
(prepare không lấy thư mục này làm footage), đổi tên plan.json/canh.json cũ thành `_cu-...` nếu có, rồi chạy prepare
→ chế độ VOICE như mục trên. Lưu ý khớp miệng: cảnh footage thấy rõ mặt người đang nói sẽ lệch miệng với voice —
ưu tiên cảnh không thấy miệng, hoặc che bằng broll/pip.

## Bước 2b — Cắt đoạn thừa (khi có nhiều clip hoặc clip chưa edit)
Bắt đầu bằng `python scripts/cat_lang.py "<folder>"` (tự ghi cut.json cho từ đệm à/ừ/ờ đứng riêng + lặng > 0,6s, không tốn lượt),
rồi chỉ thêm tay các đoạn đọc lỗi / đọc lại / lạc đề vào cut.json.
Đọc `_work/transcript_full.txt`, tìm: câu đọc lỗi rồi đọc lại (giữ lần đọc sau), khoảng lặng > 1.2s,
đoạn lạc đề, phần lóng ngóng đầu/cuối mỗi clip (xem clips.json). Ghi `<folder>/cut.json`:
```json
{"cut": [[12.4, 15.0], [33.2, 36.8]]}
```
(mốc theo transcript_full, cắt sát đầu/cuối câu, chừa ~0.1s). Rồi chạy:
```
python scripts/nho_may.py trim "<folder>"
```
Sau đó transcript.txt / words.json / cuts.json là của video ĐÃ CẮT — mọi mốc ở các bước sau dùng bản này.
Video đã edit sơ bộ (1 clip, gọn gàng) thì bỏ qua bước này. Điểm nối sau khi cắt tự có hiệu ứng chuyển cảnh.
(Người dùng cũng có thể cắt nhanh trong trình chỉnh sửa — lưu thành `"segments"` trong plan.json, xem bước 5.)

## Bước 3 — Dàn ý edit (outline.md)
Viết `<folder>/outline.md` (tiếng Việt), mỗi dòng một đoạn:
`[giây bắt đầu–kết thúc] nội dung lời nói → minh họa bằng gì → nguồn`
Nguồn là một trong: `clip gốc` | `đồ họa` (thẻ giá, chip, checklist...) | `stock: <từ khóa EN>` |
`CẦN NGƯỜI DÙNG: <mô tả>`.
- Có tư liệu của người dùng (`assets/cua-ban/`) → dùng trước, nguồn ghi `tư liệu #k (tên file)` (xem mục trên).
- Dùng `stock` cho cảnh chung chung: thành phố, chìa khóa, ký hợp đồng, ngân hàng, gia đình, tiền...
- Dùng `CẦN NGƯỜI DÙNG` cho thứ chỉ người dùng có: phối cảnh dự án, mặt bằng căn, ảnh sổ, tiện ích thật,
  ảnh màn hình riêng. KHÔNG lấy ảnh người thật/người nổi tiếng/ảnh báo chí từ web.
- CÙNG LÚC viết `<folder>/can-tim.md` cho mọi thứ `CẦN NGƯỜI DÙNG` trong dàn ý (định dạng ở bước 4; ghi rõ
  "không bắt buộc" nếu bỏ qua vẫn ổn). Giao diện đọc file này để hiện ô thả ảnh ngay khi người dùng duyệt dàn ý.
  Không cần gì thì không tạo file.
- Nếu người dùng nói "lên dàn ý" / "lên dàn ý trước" / "demo": dừng sau bước này, báo ngắn gọn cho họ duyệt
  (dàn ý + ảnh nào nên thêm), nhắc họ thả ảnh trên giao diện rồi bấm "Edit tiếp".
- "Edit tiếp" (hoặc "edit tiếp theo dàn ý đã duyệt"): bắt đầu từ bước 4. ĐỌC LẠI outline.md (người dùng có thể đã sửa)
  và XEM assets/ — ảnh người dùng thả vào (đúng tên trong can-tim.md, hoặc ảnh tên khác ở assets/) được ưu tiên dùng
  trước stock; ảnh lạ không có trong dàn ý thì xem nội dung rồi chèn vào chỗ hợp nhất.

## Tư liệu của người dùng — `assets/cua-ban/` (ảnh/video người dùng đưa TRƯỚC)
Nếu thư mục này có file (giao diện: thẻ "🖼 Tư liệu minh họa của bạn"), làm TRƯỚC khi lên dàn ý (bước 3):
1. Chạy `python scripts/tu_lieu.py "<folder>"` → XEM `_work/tu-lieu_*.jpg` (ô #1, #2… = thứ tự trong `_work/tu-lieu.json`;
   video có 3 khung đầu-giữa-cuối). Ảnh nào chưa rõ là gì thì mở xem riêng file đó.
2. Ghi nhận mỗi tư liệu là gì (phối cảnh, mặt bằng, phòng ngủ, ảnh chụp màn hình thống kê, tiện ích…).
   GHI CHÚ CỦA NGƯỜI DÙNG (`assets/cua-ban/_ghi-chu.json`, tu_lieu.py in ra + có trong tu-lieu.json "ghiChu"): đó là YÊU
   CẦU — làm đúng: chỗ hiện (câu/đoạn/giây nào, mở đầu/kết), cách dùng (toàn màn hình → broll; khung nổi/góc → pip với y;
   sau người → "behind": true; bao lâu; hiệu ứng; nhãn chữ…). Chỗ ghi chú không nói rõ thì tự quyết phần còn lại theo
   bước 3. Không làm được đúng ghi chú (vd câu đó đã bị cắt) → làm gần nhất và ghi vào bao-cao.md. Tư liệu KHÔNG có ghi
   chú → tự phân tích và chọn như bước 3.
3. Ghép vào câu nói khớp nhất (lời nhắc tới thứ đó, hoặc đang nói về chủ đề đó). Ảnh dọc/quan trọng → `broll` 2–4s
   (có zoom nhẹ sẵn); ảnh ngang, sơ đồ, ảnh chụp màn hình → `pip` 3–5s (người nói vẫn thấy). Video → `broll` với `from`
   chọn đoạn đẹp nhất (xem 3 khung), bật `volume` nếu tiếng của video đó có ích.
4. Ưu tiên tư liệu của người dùng trước stock. Tư liệu có ghi chú thì luôn dùng. Tư liệu không ghi chú mà không hợp
   nội dung thì bỏ, ghi lý do vào bao-cao.md. Một tư liệu dùng 1 lần (trừ khi video dài và cần nhắc lại).
5. Trong outline.md ghi rõ nguồn `tư liệu #k (tên file)`. Chỗ còn thiếu minh họa → tìm stock Pixabay (bước 4) như thường.

## Bước 4 — Tìm minh họa
**ẢNH THẬT TRƯỚC, STOCK SAU (quy tắc cứng — chi tiết CHAT-LUONG.md mục 2–3).** Video nói về một dự án / địa danh cụ thể → ảnh
thật của đúng dự án (phối cảnh, tiện ích) tìm trên web, tải bằng `python scripts/stock.py url "<folder>" <ten-ngan> "<link ảnh>"`
[--nguon "Ảnh: …"] (webp tự đổi jpg). Ảnh ngang: broll phủ kín + lia `panFrom`/`panTo`. Không thu nhỏ ảnh giữa nền màu, không tự
viết script ghép / dựng khung thay tool. Hết ảnh thật mới tới Openverse, rồi Pixabay.

Stock (Pixabay, miễn phí thương mại; video tải về tối đa Full HD):
```
python scripts/stock.py search "<folder>" <ten-ngan> "<từ khóa TIẾNG ANH>" [--video] [--n 5]
```
XEM `assets/stock/_pick_<ten>.jpg`, chọn ứng viên hợp nhất (ưu tiên ảnh dọc, đúng bối cảnh Việt Nam/châu Á
nếu có), rồi:
```
python scripts/nho_may.py stock "<folder>" <ten-ngan> <số thứ tự>
```
Không có ứng viên nào hợp: thử 1 từ khóa khác; vẫn không được thì chuyển sang danh sách cần người dùng.
Video stock (`--video`) dùng cho broll động; ảnh dùng cho pip hoặc broll có hiệu ứng zoom.
Không kết nối được pixabay.com → báo người dùng cho phép tên miền pixabay.com và cdn.pixabay.com, hoặc tự tải.

**Openverse — ảnh Creative Commons, có ẢNH ĐỊA DANH THẬT** (Hồ Gươm, cầu Rồng, Landmark 81, phố cổ Hội An, chợ Bến Thành, tên
tỉnh / quận…) — Pixabay gần như không có. Chỉ ảnh (không video), chỉ lấy ảnh dùng thương mại + chỉnh sửa được. Tìm bằng mạng máy thật:
```
python scripts/nho_may.py stocksearch "<folder>" <ten-ngan> "<tên địa danh / từ khoá tiếng Anh>" --ov --n 5
```
→ XEM `assets/stock/_pick_<ten>.jpg` rồi `python scripts/nho_may.py stock "<folder>" <ten-ngan> <số>` (như Pixabay). PHẢI GHI NGUỒN:
tool tự lưu `assets/stock/_nguon.json` và tự chèn dòng chữ nhỏ "Ảnh: <tác giả> · <giấy phép> · <nguồn>" ở góc ảnh trám / dưới khung
nổi khi xuất (đừng tắt — `"credit": false` chỉ khi người dùng tự lo bản quyền); ghi thêm danh sách nguồn vào bao-cao.md. Dùng Openverse
cho địa danh / sự vật cụ thể; cảnh chung chung vẫn ưu tiên Pixabay (không cần ghi nguồn, có video). Không lấy ảnh người thật nhận rõ mặt.

Thứ cần người dùng cung cấp → ghi/cập nhật `<folder>/can-tim.md` (đã tạo từ bước 3; bỏ dòng nào người dùng đã có file):
```
- assets/03-mat-bang.jpg — mặt bằng căn 2PN (dùng ở giây 12–15)
```
Báo người dùng danh sách này. Vẫn render được bản demo: element nào thiếu file sẽ tự bỏ qua.

## Bước 5 — Viết plan.json
`"template": "review"` dùng cho mọi loại video (review căn, thử thách, kể chuyện...).
(`"challenge"` là mẫu cũ chỉ có phụ đề vàng — chỉ dùng khi người dùng yêu cầu; trình chỉnh sửa không hỗ trợ mẫu này.)
```json
{
 "template": "review",
 "captions": true,
 "captionsFrom": 0,
 "captionTop": 1390,
 "fixes": [["OSION PAC", "OCEAN PARK"], ["BA MƯƠI NGÀY", "30 NGÀY"]],
 "elements": [
  {"type": "priceHook", "start": 0.05, "end": 5.3, "price": "2,55 TỶ", "sub": "Căn 2 ngủ · Hà Nội", "sfx": "pop"},
  {"type": "chip", "start": 5.6, "end": 8.4, "icon": "FileCheck", "text": "Pháp lý đầy đủ", "y": 240, "sfx": "tick"},
  {"type": "rangeCard", "start": 24.3, "end": 27.1, "label": "Căn rộng hơn", "value": "2,5 – 3,5 tỷ", "sfx": "pop"},
  {"type": "bigQuestion", "start": 27.15, "end": 29.2, "text": "VÌ SAO RẺ?", "sfx": "pop"},
  {"type": "checklist", "start": 29.3, "end": 41.5, "title": "Lý do giá tốt",
   "items": [{"text": "Chủ cần bán thật", "at": 30.6}, {"text": "Sổ đỏ đàng hoàng", "at": 38.95}]},
  {"type": "broll", "start": 12.0, "end": 15.0, "src": "assets/stock/thanh-pho.mp4", "label": "Hà Nội", "transition": "zoom", "sfx": "pop"},
  {"type": "pip", "start": 16.0, "end": 19.5, "src": "assets/03-mat-bang.jpg", "label": "Mặt bằng 2PN", "y": 260, "sfx": "pop"},
  {"type": "text", "start": 42.0, "end": 45.0, "text": "Chỉ còn 2 căn", "look": "box", "size": 80, "y": 700, "sfx": "pop"},
  {"type": "dayBadge", "start": 0, "end": 55.9, "day": 2, "total": 30},
  {"type": "cta", "start": 55.1, "end": 65.7, "icon": "MessageCircle", "text": "INBOX nhận danh sách căn", "sfx": "pop"}
 ]
}
```
Các loại element:
- `broll`: ảnh/video phủ toàn màn hình (tiếng gốc vẫn giữ). 2–4 giây. `transition`: zoom | slide | fade.
  `from`: giây bắt đầu trong video stock. `volume`: tiếng của video trám (mặc định 0 = tắt).
  Dùng khi lời nói nhắc tới thứ không có trong clip.
- `pip`: khung ảnh/video nổi 3D ở phần trên màn hình, người nói vẫn thấy phía dưới. 3–5 giây.
  Khung tự do: `w` (bề rộng khung px, mặc định 880), `h` (chiều cao phần ảnh px, 560), `x` (tâm ngang 0–1), `y` (mép trên);
  ảnh trong khung dùng chung `cropX` / `cropY` / `cropS` / `fit` như broll (ảnh ngang trong khung dọc → chọn cropX đúng chủ thể).
- `priceHook`, `rangeCard`, `bigQuestion`, `checklist`, `chip`, `cta`: đồ họa chữ/icon (màu theo brand.json).
  Tất cả nhận `y` (vị trí dọc, px) để dời lên/xuống. Mặc định: chip 240, priceHook 520, bigQuestion 620,
  checklist 240, rangeCard 280, cta 1120, pip 260, text 700.
- `text`: chữ tự do (xuống dòng bằng \n). Thông số không ghi → lấy theo `style.text` (phong cách), rồi mặc định.
  `look`: plain (chữ viền) | outline (viền đen dày) | clean (trơn + bóng mờ) | shadow (bóng đổ cứng, màu = strokeColor) |
  solid (nền màu `bg`, bo `radius`) | highlight (vệt bút dạ quang `bg` dưới chữ) | neon (phát sáng màu chữ) |
  box (khung kính) | gold (chữ vàng 3D) | tag (nhãn vàng).
  `anim` (hiện): pop | bounce | fade | up | down | left | right | blur | zoomOut | wipe | type (gõ từng ký tự) | words
  (bật từng từ) | none; `out` (ẩn): fade | pop | up | down | left | right | blur | none.
  `font` (tên trong remotion/fonts.json, xem phong-cach/_font-mau.jpg; sang trọng: Cormorant Garamond, Playfair Display, Great Vibes — xem CHAT-LUONG.md mục 4), `weight`, `size` (mặc định 80), `color`, `bg`,
  `stroke` (px), `strokeColor`, `shadow` (none|soft|hard|glow), `upper`, `italic`, `spacing`, `hl` (danh sách từ khóa tô
  màu `hlColor`), `x` (0–1, tâm ngang; bỏ = giữa), `y`, `width` (px), `align`, `rotate` (độ).
- `sticker`: nhãn dán — `icon` = emoji ("🔥", "👇") hoặc tên icon lucide ("ArrowDown", "Heart"); `size` (150), `color`
  (cho icon), `x`, `y`, `anim`, `out`, `loop`: bob | pulse | spin | shake | none. Dùng như mẫu (mũi tên chỉ, emoji cảm xúc).
- `broll` thêm `transition` (vào): zoom | zoomout | fade | blur | cut | flash | glitch | slide | up | drop | whip | wipe | diag | split | circle | spin;
  `exit`: fade | cut | blur | zoom | zoomout | flash | slide | up | down | whip | wipe | circle.
  VÙNG HIỆN (ảnh/video khác tỉ lệ khung, vd video ngang): `cropX`, `cropY` (0–1, phần giữ lại: 0 = mép trái/trên, 1 = phải/dưới),
  `panFrom` / `panTo` (0–1): LIA NGANG — vùng hiện trượt từ panFrom tới panTo suốt khối (ảnh ngang / phối cảnh trong khung dọc:
  0.2→0.5 hoặc 0.7→0.4, khối 3–5 giây; `panYFrom` / `panYTo` = lia dọc), `cropS` (phóng thêm ≥ 1), `rotIn` (xoay ảnh bên trong khung, độ; 90/270 = xoay ảnh chụp sai chiều), `flip` (h|v|hv); `fit`: cover (mặc định, phủ kín cắt bớt) | blur (vừa khung, nền là chính video làm mờ) | contain (vừa khung, nền đen).
  Video ngang mà chủ thể lệch một bên → đặt cropX cho đúng chủ thể (xem 3 khung của file); toàn cảnh rộng không muốn cắt → fit "blur".
  `area`: full (che cả khung — mặc định) | top (nửa trên) | bottom (nửa dưới) — người nói vẫn thấy ở phần còn lại, mép giao hoà
  trộn mờ (`feather` px, mặc định 170; 0 = cắt thẳng), `split` = tỉ lệ chiều cao vùng trám (0.25–0.7, mặc định 0.45), `seam` =
  màu vạch mảnh ở mép giao. Video chính GIỮ NGUYÊN vị trí (không đẩy lên/xuống) — chọn vùng trám phía
  không có mặt người (xem mat.json / sheet.jpg); chỉ khi người dùng muốn mới thêm `"follow": true` (tự dời theo mặt). Hợp video ngang (hiện trường, flycam) dưới người dẫn. Trám nửa khung KHÔNG tính vào
  giới hạn 30% broll (người nói vẫn thấy) — dùng được dày hơn (tới ~60%). Khi trám nửa dưới: chữ/đồ hoạ đặt trong vùng trám
  (y ≈ 1250–1500) hoặc trên đầu người nói, phụ đề ngay mép giao (captionTop ≈ 960–1000); trám nửa trên: chữ trong vùng trám
  (y ≈ 200–600), phụ đề dưới người nói (≈ 1440). Phong cách đặt mặc định ở `style.broll.area/split/feather/seam`.
  `pip` thêm `look`: card3d | clean | round | polaroid. Không ghi → theo `style.broll`.
- Phụ đề: kiểu theo `style.captions.preset`: tiktok | karaoke | box | wordbox | pop | single | minimal | outline
  (+ font, size, color, active, activeBg, stroke, strokeColor, upper, anim). Vị trí vẫn là `captionTop`.
- `audio`: chèn file âm thanh / NHẠC (`src`, `from`, `volume` 0–2, `rate` tốc độ 0.5–2, `fadeIn` / `fadeOut` giây, `loop`, `bgm: true` = nhạc nền)
  trong khoảng start–end. Nhạc nên thêm dạng khối này (dài bằng bài nhạc, dài hơn video thì video tự kéo dài đứng hình khung cuối — cắt
  khối cho vừa). `music` (lặp cả video) là kiểu cũ, có thêm `rate`. Nhạc tìm trong trình chỉnh sửa (Openverse, giấy phép CC0 / CC BY)
  lưu ở assets/nhac/; bài CC BY có dòng ghi nguồn trong assets/nhac/_nguon.txt — nhắc người dùng dán vào mô tả video (ghi vào bao-cao.md).
- `beauty` (làm đẹp người, render tự xử lý trước bằng scripts/beauty.py): {"smooth": 0–100 mịn da, "bright": sáng da,
  "lip": son môi, "lipColor": "#C2185B", "blush": má hồng, "blushColor": "#FF6F91", "sharpen": độ nét cả khung}.
  Chỉ thêm khi người dùng nhờ hoặc phong cách cần (vd "Tự nhiên" 35/20/sharpen 15). Xem thử: `python scripts/beauty.py
  "<folder>" --xem <giây gốc>` → _work/beauty_xem.jpg (trước | sau + phóng to mặt).
- `color` thêm: `hue` (xoay tông, -30..30), `sepia` (0–100), `fade` (nâng vùng tối kiểu phim 0–100), `tint` (hex) +
  `tintAmount` (0–100).
- `"behind": true` trên element hình (pip, broll, text, sticker, chip...) = đặt SAU NGƯỜI nói (người đè lên trên khối, kiểu
  ảnh/chữ chui ra sau lưng). render.py tự tách người khỏi nền (scripts/tach_nguoi.py, offline) cho đúng các đoạn đó —
  KHÔNG tự ghép tay bằng công cụ khác. Hợp khi người ở giữa khung, khối đặt chồng lên đầu/vai (vd pip y 250–400).
- `zoom`: phóng video chính để NHẤN MẠNH (chữ/đồ họa đứng yên). `style`: punch (giật vào — dùng nhiều nhất) | in (từ từ vào,
  cho đoạn kể dồn dập/cao trào) | out (từ từ ra, mở cảnh) | pulse (vào rồi ra) | shake (rung — sốc, bất ngờ, dùng rất ít)
  | smooth (vào êm ~1s – giữ – ra êm ~1,2s, KHÔNG giật: video chill, thơ, podcast, kể chuyện; khối dài 3–6s).
  Phong cách có `style.effects.zoomEase: "smooth"` → mọi zoom tự thành êm, điểm nối luôn mờ chồng (không zoom cut), không gắn
  tiếng cho zoom. Với video chill dùng smooth, không dùng punch/shake.
- CỠ CẢNH tự động (thay cho zoom): `"shots": [{t (giây video GỐC), s (1 toàn | 1.28 trung | 1.6 cận), x, y (tâm = mặt), k}]` — đổi
  cỡ khung đúng chỗ ngắt câu như quay nhiều máy, hoà trộn nhẹ giữa 2 cỡ (`"shotFade"` giây, mặc định 0.5; 0 = cắt thẳng). Tạo bằng `python scripts/canh_co.py "<folder>"
  [--thua|--day]` (mặc định vừa ≥ 9s/cảnh, thưa ≥ 14s, dày ≥ 6s — ĐỪNG đổi cảnh dày hơn, người dùng thấy khó chịu; `--bo` = tắt, ghi "shots": []). Phong cách có `style.effects.shots: "auto"` (Thơ dọc hoà trộn, Thơ trên mây,
  Podcast tối giản, Podcast chia khung) → render tự tạo nếu plan chưa có; với các bộ này KHÔNG thêm khối zoom (người dùng tự
  thêm tay nếu muốn). "shots": [] = người dùng đã tắt, không tạo lại. Đổi cỡ cảnh cũng tính là "có thay đổi" cho quy tắc > 8s.
  `scale` 1.1–1.35 (punch thường 1.2), `x`, `y` = điểm zoom theo tỉ lệ khung 0–1 (mặc định 0.5, 0.4) — đặt vào MẶT người
  nói (xem sheet.jpg để ước vị trí mặt) hoặc vào vật đang nói tới (màn hình, con số). punch dài 0.8–2s, in 2–5s.
  Nên đặt ở: con số/giá, từ khóa quan trọng, câu chốt, câu hỏi, điểm bất ngờ — trung bình 1 zoom mỗi 5–8s ở đoạn người
  nói, KHÔNG zoom khi đang có broll/pip, không zoom 2 lần liền nhau < 2s. Có thể thêm `"sfx": "whoosh"` cho punch mạnh.
- `dayBadge`: nhãn NGÀY X/Y suốt video (cho video thử thách).
- `sfx` trên mọi element: tên trong thư viện (`python scripts/sfx.py ds`: whoosh, whoosh-nhe, whoosh-manh, swoosh, swipe,
  riser, impact, boom, hit, pop, bubble, click, tick, typing, boing, tada, ding, bell, notify, success, cash, sparkle, glitch,
  camera, error) | "cua-ban/<file>" (âm thanh riêng người dùng thêm) | đường dẫn file trong assets/.
  TỰ GÁN: `python scripts/sfx.py tu-gan "<folder>" [--it|--nhieu] [--ghi-de]` sau khi viết plan.json (theo loại khối,
  kiểu hiện, nội dung: giá → cash, follow → bell, chữ gõ → typing…; mật độ theo style.sfx của phong cách) rồi chỉnh tay
  chỗ cần. `"joinSfx": true` = tiếng vụt ở điểm nối (theo kiểu chuyển).
  KHÔNG LẠM DỤNG (người dùng đã phàn nàn): tiếng hiệu ứng chỉ cho KHOẢNH KHẮC CHÍNH — hook, con số/giá, câu hỏi, cảnh trám lớn,
  kêu gọi cuối. Mức "vừa" ≈ 1 tiếng / 5 giây, các tiếng cách nhau ≥ 1,5s; cụm chữ hiện liền nhau (vd 3 dòng tiêu đề) chỉ 1 tiếng;
  chữ phụ / dòng thứ 2 KHÔNG gắn tiếng; chuông `bell` chỉ 1 lần ở kêu gọi follow cuối; cash/impact/boom hiếm. tu-gan đã tự giữ
  ngân sách này; tự đặt tay thì chạy `python scripts/sfx.py giam "<folder>" [--it]` để bỏ bớt (giữ tiếng chính, rải đều).
  soat.py báo khi dày quá.
  `sfxVolume` = âm lượng riêng của hiệu ứng đó (mặc định theo `sfxVolume` chung 0.35).
- `captions: true`: phụ đề tự động kiểu TikTok. ĐẶT `false` nếu video đã có phụ đề cháy sẵn (xem sheet.jpg).
  `captionsFrom`: bắt đầu sau tiêu đề mở đầu có sẵn. `fixes`: sửa chữ sai & đổi số (khớp chữ IN HOA).
  `captionSize` (mặc định 70), `captionUpper` (mặc định true), `wordsPerPage` (mặc định 3), `captionX` (px dời ngang, bỏ = giữa).
  Nếu `captions` là DANH SÁCH các câu (mỗi câu là danh sách {w, start, end}) thì đó là phụ đề người dùng đã sửa tay
  trong trình chỉnh sửa — giữ nguyên, sửa trực tiếp trong danh sách, KHÔNG đổi lại thành true trừ khi được yêu cầu.

Trường chung (đều không bắt buộc; trình chỉnh sửa cũng ghi các trường này):
- `segments`: [[a, b], ...] các đoạn GIỮ LẠI của video chính (giây trong video chính), nối liền nhau — cắt không cần
  xuất lại file. Khi có `segments`, mọi `start/end/at` của element và phụ đề sửa tay tính theo VIDEO XUẤT RA (đã cắt);
  phụ đề tự động tự dời theo. Tự thêm segments thì phải tự dời các element phía sau cho khớp.
- `color`: {"brightness": 100, "contrast": 100, "saturation": 100, "warmth": 0, "vignette": 0, "all": false}
  (100 = giữ nguyên; warmth −100 lạnh … +100 ấm; vignette 0–100 tối 4 góc; all = áp cả cho broll/pip).
  Video tối/nhạt → brightness 105–112, contrast 105–110, saturation 110–120.
- `audio`: {"denoise": 0–3, "normalize": true/false} — lọc ồn tiếng gốc (1 nhẹ, 2 vừa, 3 mạnh) và cân bằng âm lượng
  chuẩn TikTok −14 LUFS. Xử lý bằng ffmpeg lúc render (tạo `_work/clean_*.mp4`).
- `videoVolume`: âm lượng tiếng gốc (1 = giữ nguyên, 0 = tắt, tối đa 2). Riêng từng đoạn (khoá = giây bắt đầu đoạn trong video gốc):
  `segVol` {"12.5": 0.6}, `segFadeIn` / `segFadeOut` {"12.5": 1.0} (giây to dần / nhỏ dần), `segAudio` keep|mute.
- `music`: {"src": "assets/nhac.mp3", "volume": 0.15, "from": 0} — nhạc nền tự lặp, nhỏ dần đầu/cuối.
- `sfxVolume`: âm lượng chung các hiệu ứng (mặc định 0.35).
- `theme`: màu riêng cho video này (light, mid, dark, gold1, gold2); không có thì dùng brand.json.

Quy tắc:
- Mỗi minh họa xuất hiện ĐÚNG lúc người nói nhắc tới (lấy `start` từ words.json, sớm ~0.1s).
- `chip`: tối đa 3 cái cùng lúc, y = 240, 360, 480; chữ ≤ 24 ký tự. Icon = tên icon lucide
  (FileCheck, Trees, Ruler, Tag, Building2, MapPin, Images, House, BedDouble, Bath, Car, Sofa, Sun, Wifi,
  ShieldCheck, Phone, MessageCircle, UserPlus, Key, Wallet, TrendingUp, TrendingDown, School, Hospital, ShoppingCart,
  Globe, Star, Heart, Clock, Calendar, CircleCheck, Gift, Flame, Zap, Eye, ThumbsUp, Users, Megaphone, Rocket, Trophy...).
- `sfx` chỉ đặt khi đồ họa hiện ra: "pop" (thẻ lớn, broll, pip), "tick" (chip); checklist tự có "ding".
- Không đặt đồ họa đè vùng phụ đề (y ≈ 1380–1520) và logo trên cùng; y > 1550 bị giao diện TikTok che.
- Không để pip/checklist/rangeCard trùng thời gian nhau. Cách 3–6 giây một minh họa, không dồn dập.
- broll không quá 30% thời lượng video — người xem cần thấy người nói/căn hộ thật.
- Chuyển cảnh ở ĐIỂM NỐI segments (tự động, tiếng luôn được vuốt ~0,07s cho khỏi "bụp"):
  `"transition"`: auto (mặc định — nối 2 đoạn CÙNG lần quay → zoom cut: đổi cỡ khung 100%↔108% che cú nhảy;
  khác lần quay/khác cảnh → fade: mờ chồng hình + tiếng 0,2s) | zoom | fade | cut | flash (chớp sáng) | whip (lia nhanh,
  nhòe ngang) | slide (đẩy ngang) | up (đẩy lên) | zoomin (zoom xuyên) | blur (nhòe chồng). Các kiểu khác auto/zoom/fade/cut
  chỉ dùng khi phong cách (thành phần chuyển cảnh) cần. Đổi riêng 1 điểm nối: `"joinFx": {"<b>><a>": "fade"}` (b = giây kết thúc đoạn trước,
  a = giây bắt đầu đoạn sau, làm tròn 2 số lẻ).
- Chỗ đổi cảnh có sẵn trong video gốc: mặc định KHÔNG thêm hiệu ứng. `"cutFx": "flash"` / `"bump"` / `"flash+bump"` để
  thêm chớp sáng / giật zoom (kiểu cũ — dễ thấy vấp, chỉ dùng khi video mẫu có kiểu đó).
- Video người nói một mạch (talking head) nên có zoom nhấn mạnh theo nhịp ở trên để đỡ đơn điệu — kiểm tra trong bước tự kiểm tra.

### Người nói thu nhỏ & đồ họa biên tập (remotion/src/Graphics2.tsx)
- `{"type": "presenter", "mode": card|split|corner|window|full, start, end, "bg": paper|ocean|dark|color, "bgColor", "s", "x", "y",
  "inDur"}` — video chính (kể cả lớp người tách nền) THU NHỎ để nhường chỗ cho đồ họa: card = thẻ bo góc viền trắng (s 0.5, tâm
  y 1290), split = người ở nửa dưới (vạch đen ở y 900, đồ họa ở nửa trên; tự canh mặt vào nửa dưới), corner = khung nhỏ góc phải,
  window = cửa sổ có 3 chấm. Nền mặc định giấy be nét đứt đen. Các khối presenter liền nhau (end = start kế) chuyển thẳng kiểu này
  sang kiểu kia; hết khối thì người nói phóng về toàn khung. Chữ đặt trong lúc người nói thu nhỏ trên nền sáng TỰ đổi sang màu mực
  đậm (khối chữ trắng vẫn dùng được). Dùng khi: khoe bảng giá / so sánh / liệt kê / số liệu dài 3–6s; KHÔNG dùng cho câu chào,
  câu nói trực tiếp với người xem (để toàn khung). Tối đa ~1 lần đổi kiểu mỗi 6s; mỗi lần ≥ 3s.
- `phrase` (cụm chữ 3 tầng): `sm` dòng dẫn nhỏ → `big` chữ lớn có chân in nghiêng (Playfair; `**bôi vàng**`, `__ô đen__`) →
  `tag` hộp IN HOA (tagStyle box|pill); `atBig`/`atTag` = giây (tính từ lúc khối hiện) cho từng tầng — đặt trùng lúc nói từ khóa.
- `counter` (số đếm lên): `to` ("2,55"), `from`, `prefix`, `suffix` ("tỷ", "m²"), `label`, `note`, `count` (giây đếm, 1.1).
- `stamp` (dấu ✕ / ✓ đập xuống): `icon` x|check, `text`, `x`, `y`, `size` — đúng âm "không"/"có".
- `tabs` (tab so sánh, nền trắng trượt sang tab đang nói): `title`, `items: [{text, at, note}]`.
- `tiles` (ô số 1·2·3, ô đang nói tô đậm): `items: [{text, at}]`, `cols`.
- `note` (thẻ giấy vở, kẹp + băng dính, từng dòng tích): `title` (chữ viết tay), `items: [{text, at}]`.
- `chart` (biểu đồ động): `kind` bar | hbar | donut | line | progress, `title`, `data` ("Quận 1: 120, Quận 2: 95" hoặc
  [{label, value}]), `unit`, `highlight` (nhãn tô nổi), `max` (progress), `source` (nguồn số liệu — LUÔN ghi khi số liệu từ ngoài),
  `height`, `card: false` (không nền), `colors` (màu từng cột / từng phần donut, hoặc `color` trong từng mục data), cột bar có giá trị ÂM tự vẽ
  trục 0 ở giữa, cột âm đi xuống màu đỏ (`negColor`), nhãn cột có kèm `unit`. Số liệu chỉ lấy từ lời nói / brief / nguồn kiểm chứng — KHÔNG bịa.
- `bubble` (bong bóng câu hỏi tu từ): `text` (`**bôi**`), `side` l|r, `x`, `y`.   `spark` (sao lấp lánh điểm xuyết): `x`, `y`, `size`.
- Chữ `text` thêm `hlStyle`: color (đổi màu từ khóa, mặc định) | marker (bôi vàng bút dạ quang + 2 thanh đen + chấm tay cầm) |
  box (ô đen chữ trắng). Đặt chung cho phong cách ở `style.text.hlStyle`.
- QUY TẮC THIẾT KẾ (học từ bộ seecut/luancut, soat.py báo phần đo được):
  1. Neo vào lúc NÓI TỪ KHÓA (words.json), không phải đầu câu: khối/tầng chữ hiện 0–0,1s sau âm đầu của từ khóa.
  2. Nhãn / hộp chữ IN HOA, NGẮN 1–3 từ rút từ lời ("SỔ HỒNG", "HÔM NAY") — không chép nguyên cụm lời.
  3. Lúc người nói thu nhỏ: thu xong (inDur, 0,4s) rồi mới cho khối hiện (bật đúng lúc thu sẽ che mặt / trễ nhịp); nền không để
     trống quá 1,5s — mỗi nhịp thông tin nên có ≥ 2 phần tử (vd phrase + sticker, counter + stamp), không để một chip nhỏ đứng trơ.
  4. Chữ IN HOA có dấu chồng (Ư, Ễ, Ố) nhiều dòng: render tự giãn dòng 1,35 — không ép lineHeight nhỏ hơn.
  5. Sửa chỗ trống nhịp bằng cách THÊM nội dung cùng phong cách, đừng đổi phong cách giữa chừng; bản đơn giản, nhất quán thường
     tốt hơn bản nhồi nhiều kiểu.
  6. Khoảng thở giữa khối cuối và phụ đề ≥ 40px; không đặt khối chính ở đáy khung dọc (y > 1550 bị giao diện TikTok che).

### Vị trí tự do, nhóm, hiệu ứng vào/ra, tốc độ (mọi khối hình)
- `dx`, `dy` (px dời trên khung 1080×1920), `sc` (phóng, 1 = giữ), `rot` (độ), `org: [x, y]` (tâm phóng/xoay, px — đặt bằng tâm khối khi dùng sc/rot), `group` (mã nhóm, các khối cùng mã đi cùng nhau). Trình edit ghi các trường này khi kéo thả.
- `fxIn` / `fxOut`: hiệu ứng vào/ra chung (pop, fade, up, down, left, right, blur, zoomOut, wipe, spin, drop, flip / fade, pop, zoom, up, down, left, right, blur, wipe, spin, none); `inDur` / `outDur` (giây). Chữ kiểu thường/mới và nhãn dán dùng `anim` / `out` riêng (+ inDur/outDur); broll dùng `transition` / `exit`.
- LỚP (layer): `z` — số lớn nằm trên; z < 0 = SAU người (tự tách nền). Không ghi: "behind": true → -10, broll 10, phụ đề 20
  (`capZ` ở plan), còn lại 30. Đặt z < 0 thì ghi kèm `"behind": true`. Lớp người tách theo khúc 5 giây của video gốc
  (`_work/nguoi/nguoi_k<số khúc>.webm`) nên dời khối không phải tách lại cả đoạn.
- Keyframe: `kf: [{t (giây từ lúc khối hiện), dx, dy, sc, rot, op}]` (nội suy mượt; cần `org` = tâm khối); `op` = độ hiện 0–1.
  `follow: "face"` = khối chạy theo mặt người (render.py tự nạp _work/mat.json).
- Hiệu ứng hình cả khung: `{"type": "fx", "style": shake|glitch|rgb|flash|vhs|blur|beat|bw, "amount": 0–100, start, end}`.
- Ảnh/video trám & khung nổi: `mask` (circle|round|heart|diamond|star|split-l|split-r|split-t|split-b, + maskX, maskY, maskS),
  `flip` (h|v|hv), `cropS/cropX/cropY` (cắt khung = phóng quanh tâm), `freeze: true` (đứng hình), `kb: false` (tắt zoom chậm).
  Phát ngược / xoá phông: file xử lý sẵn ở assets/_xu-ly (API /process) — `src` trỏ file mới, `srcOrig` = file gốc.
- Khung hình video chính: `mainXf: {s, dx, dy, rot, crop: [trên, phải, dưới, trái] (%), round (px), flip, bg}` cho CẢ video —
  s < 1 thu nhỏ, dx/dy dời (px), bg = nền lộ ra: black | blur (mờ từ chính video) | mã màu. Người dùng chỉnh trong trình edit
  (chọn đoạn video → kéo trên khung hình / thanh trượt). Giữ nguyên khi sửa plan. Riêng từng đoạn:
  `segXf: {"<giây bắt đầu đoạn>": {cùng các trường, + x, y tâm phóng}}` (ghi đè mainXf cho đoạn đó); `segCurve: {"<giây>": hero|bullet|montage|jump|flashin|flashout}`.
- Nhịp nhạc: `beats: [giây]` (scripts/nhip.py). Âm thanh: `"audio": {"voice": deep|high|chipmunk|robot|echo|phone|radio, "vocals": true}`
  (vocals = tách giọng khỏi nhạc nền, scripts/tach_giong.py). Giọng đọc AI: `python scripts/tts.py "<folder>" "nội dung" [--giong vn:<tên>]` -> wav trong
  assets/giong-doc → chèn bằng khối audio. Ảnh bìa: `python scripts/render.py "<folder>" --cover <giây> "Tiêu đề"` -> anh-bia.jpg.
- BẢN ĐỒ (khối `map` — bản đồ thật, camera bay, vẽ đường đi tới từng tiện ích, ghim bật kèm nhãn "5 phút"):
  `{"type": "map", start, end, "places": [{name, lng, lat, label?}] (điểm đầu = dự án), "paths": [[[lng, lat]...] cho từng tiện ích],
  "lineMode": road|arc|line, "camera": zoomin|fly|static, "theme": toi|sang|goc, "style": positron|liberty|bright|dark|fiord|tron,
  "frame": full|card, "hideLabels": true, "color"}`. Phong cách có `style.map` thì không cần ghi style/theme/camera.
  BẢN ĐỒ 3D: thêm `"d3": true` (+ `"camera": "orbit"` xoay quanh dự án) → toà nhà dựng khối 3D, nghiêng 60°, khối dự án vàng mọc
  lên (`towerH` m, `tower: false` để tắt), cột 3D ở từng tiện ích. Đẹp nhất khi tiện ích gần (≤ 3 km, toà nhà thấy rõ); xa hơn vẫn có
  khối dự án + cột. Phong cách "Bản đồ 3D" bật sẵn. Nền `liberty` / `dark` có dữ liệu toà nhà; `tron` thì chỉ có khối + cột.
  VỊ TRÍ NGƯỜI DÙNG CHỌN SẴN: dự án có `vi-tri.json` ({"places": [{name, lat, lng, label?}]}, điểm đầu = dự án — chọn ở trang dự án,
  toạ độ đúng) → DÙNG LUÔN: `python scripts/nho_may.py bando "<folder>"` (không ghi điểm nào = lấy từ vi-tri.json, chỉ tính thêm
  đường đi), nhãn `label` người dùng ghi thì giữ nguyên.
  KHI NÀO DÙNG (tự quyết, không cần người dùng nhắc): lời nói / kịch bản / brief nhắc VỊ TRÍ hoặc khoảng cách — "cách trung tâm 10
  phút", "gần trường, bệnh viện, siêu thị", "mặt đường X", "ngay cạnh hồ Y", tên khu / quận cụ thể. Mỗi video tối đa 1–2 khối.
  CÁCH LÀM — máy ảo của Claude không gọi được dịch vụ bản đồ, phải nhờ máy thật:
  `python scripts/nho_may.py bando "<folder>" "<dự án>" "<tiện ích 1>" "<tiện ích 2>" …` (tên đầy đủ kèm quận / tỉnh cho chắc;
  "Tên hiện|câu tìm" để hiện tên ngắn; "Tên@lat,lng" hoặc "Tên@<link Google Maps>" khi đã có toạ độ — brief có link thì dùng link).
  → in toạ độ, địa chỉ tìm được, phút / km đi ô tô; ghi `_work/ban-do.json` + `_work/ban-do-khoi.json` (khối map dựng sẵn đủ
  places + paths + nhãn phút) → copy vào plan.json, sửa start/end cho khớp câu đang nói. ĐỌC dòng "tìm được:" — sai chỗ (trùng tên
  tỉnh khác) thì tìm lại bằng tên đầy đủ hơn; không tìm thấy thì bỏ điểm đó, ghi bao-cao.md. Số phút trong lời nói / brief khác số
  máy tính → nhãn theo lời nói / brief. Khối 5–8 giây (1,2s zoom đầu + ~1,8s mỗi tiện ích), không đè phụ đề. Cần mạng khi xuất.
  Người dùng cũng tự tạo được trong trình chỉnh sửa (Đồ hoạ → Bản đồ: gõ tên tìm, chọn điểm, tự vẽ đường).
- BẢN ĐỒ VỆ TINH KỂ CHUYỆN (khối `mapTour` — phong cách "Bản đồ vệ tinh kể chuyện"; cho nội dung địa lý / lịch sử / phân vùng /
  quy hoạch tỉnh, nước — KHÔNG phải tiện ích quanh dự án, cái đó dùng `map`): nền ảnh vệ tinh thật, viền phát sáng neon tự vẽ, từng
  vùng viền trắng tự vẽ → tô màu → tên vùng to, camera tự bay/zoom tới từng vùng đúng mốc, nhãn tỉnh bật, ảnh chân dung tròn.
  `{"type": "mapTour", start, end, "basemap": "sat", "dim": 0.15, "glow": {"name": "Việt Nam", "color": "#d7ff3a", "at": 0.3},
   "regions": [{"name": "Quân khu 1", "parts": ["Cao Bằng", "Lạng Sơn", …] (gộp nhiều tỉnh; bỏ = tìm theo name), "color": "#1e3a8a",
     "at": <giây trong KHỐI lúc nhắc tới>, "opacity": 0.55, "labelRotate": -8, "labelSize": 56, "glow": false, "focus": true,
     "radiusKm": 35 (chỉ có 1 điểm → khung bát giác, vd quần đảo), "tags": [{"name": "Cao Bằng"}] (hộp trắng tên tỉnh),
     "badges": [{"img": "assets/x.jpg", "name": "Trung tướng A"}] (ảnh tròn + bảng tên cam; không toạ độ = giữa vùng)}],
   "lines": [{"coords": [[lng, lat]…], "at", "dur": 1.2, "color": "#ffd400"}] (đường tự vẽ), "shots": [] (bỏ trống = tự động:
   toàn cảnh → bay vào → từng vùng → toàn cảnh), "frame": full|card}`.
  Viết plan xong (geo còn thiếu) → `python scripts/nho_may.py bando "<folder>" --vung` (mạng máy thật, điền ranh giới + toạ độ nhãn
  vào plan.json; ĐỌC dòng tìm được xem đúng tỉnh chưa). Tên QUỐC GIA (Việt Nam, Lào, Trung Quốc…) lấy viền đất liền Natural Earth (không
  dính vùng biển); tỉnh / huyện lấy từ OpenStreetMap — đã theo địa giới SAU sáp nhập 2025, tỉnh cũ thường vẫn tìm được ("Tỉnh Bắc Ninh (cũ)"). Hoặc dựng sẵn khối: `bando "<folder>" --vung "*Việt Nam" "Quân khu 1=Cao Bằng+Lạng Sơn"
  "Hà Nội"` → `_work/ban-do-vung-khoi.json`. Mỗi vùng 3–6 giây theo lời kể. Ảnh vệ tinh Sentinel-2 2016 (CC BY 4.0, tự ghi nguồn ở góc),
  nét tới cấp tỉnh/huyện — cấp phường/khu đô thị thì dùng `map`. Cần mạng khi xuất. Trình chỉnh sửa: Đồ hoạ → Bản đồ vệ tinh.
- HIỆU ỨNG BẢN ĐỒ KIỂU GEOLAYERS (cho cả `map` và `mapTour`): `"terrain": true | 1.5` (ĐỊA HÌNH 3D núi đồi, số = độ nổi; kèm
  đổ bóng, `"hillshade": false` để tắt) · `"colors": {"land", "water", "park", "road", "building", "label", "boundary"}` (màu bản đồ
  theo thương hiệu; nền vệ tinh không đổi được). Riêng `map`: `"camera": "globe"` (zoom từ QUẢ ĐỊA CẦU xuống dự án rồi nghiêng 3D),
  `"routeStyle": "dash" | "glow"`, `"arrow": true` (mũi tên đầu tuyến), `"mover": "car" | "moto" | "bus" | "walk" | "plane" | "ship"
  | "train" | emoji` (xe chạy dọc tuyến lúc vẽ). Riêng `mapTour`: `"globe": true` (mở đầu từ quả địa cầu), `"pitch"` / `"bearing"`,
  vùng `"extrude": true | mét` (VÙNG NỔI KHỐI 3D), BẢN ĐỒ SỐ LIỆU: vùng `"value": số` (+ `"valueLabel"`), `"scale": {"from", "to"}`
  (màu theo số cho vùng không ghi màu), `"legend": {"title", "unit"}` (chú giải), `"extrudeBy": "value"` (khối cao theo số).
  Từ bảng số liệu: `python scripts/nho_may.py bando "<folder>" --vung --csv "assets/x.csv" ["*Việt Nam"]` (dòng "tên vùng, số[, #màu]";
  số thập phân dùng dấu chấm hoặc tách cột bằng ;) → `_work/ban-do-vung-khoi.json`. Địa hình: Terrain Tiles (AWS Open Data), cần mạng.
- VÒNG QUAY QUANH NGƯỜI (khối `orbit` — phong cách "Vòng quay quanh người"): ảnh/video minh họa xếp vòng elip quay quanh ngực người
  nói, nửa sau tự nằm SAU người (render tự tách người, chỉ khung 9:16), nửa trước đè lên. Hợp: mở đầu khoe nhiều kết quả / sản phẩm /
  video đã làm, đoạn liệt kê. `{"type": "orbit", start, end, "items": ["assets/a.jpg", {"src": "assets/b.mp4", "from": 2}],
  "period": 9 (giây/vòng), "dir": 1|-1, "rx": 430, "ry": 80, "cardW": 230, "cardH": 330, "look": glass|clean|white, "tilt": 0,
  "backDim": 0.45, "behind": false (= cả vòng trước người)}` — `cx` (0–1) / `cy` (px) bỏ trống = tự theo mặt (mat.json), ngang ngực.
  5–8 ảnh/video, 4–8 giây; tránh đặt phụ đề / chữ trùng vùng vòng (dời captionTop hoặc chữ lên trên). Trình chỉnh sửa: Đồ hoạ → Vòng quay quanh người.
- Tiếng hiệu ứng: `sfxOff` (giây, dời tiếng so với lúc khối hiện, âm = kêu trước — vd whoosh -0.15 trước ảnh trám);
  khối `{"type": "sfx", "start", "end", "sfx"}` = tiếng đứng riêng không gắn hình; `joinSfxMap: {"b>a": "whoosh" | ""}` = tiếng riêng từng điểm nối.
- KÉO DÀI quá cuối video: khối nào (vd voice/audio dài hơn video) có `end` > độ dài video → video xuất TỰ dài thêm, phần thêm
  ĐỨNG HÌNH khung cuối (cuối video có khung đen thì đứng ở khung còn sáng). `"tail": <giây>` = kéo dài tối thiểu dù không khối nào cần
  (vd màn kết). Trình chỉnh sửa: khối "⏸ Đứng hình" cuối track Video (kéo mép phải để đổi, bấm đúp để bỏ). Voice dài hơn footage
  nhiều thì nên chèn thêm ảnh trám / tư liệu cho phần cuối thay vì để đứng hình lâu.
- `rate` trên broll / pip: tốc độ phát video (0.25–4).
- `blend` trên mọi khối hình (broll, pip, text, sticker, overlay…): chế độ hoà trộn với video bên dưới — normal | screen | add |
  lighten | overlay | soft-light | multiply | color-dodge | difference (vd video hiệu ứng nền đen người dùng đưa → broll `"blend": "screen"`).

### Thư viện mẫu có sẵn (trình chỉnh sửa → Mẫu chữ / Mẫu đồ hoạ / Mẫu hiệu ứng) — `editor/presets.ts`
~50 mẫu chữ (hook, giá, nhấn từ khoá, trích dẫn, kêu gọi, tin tức, sang trọng, năng động, chill, neon, chú thích), ~24 mẫu đồ hoạ ghép,
18 mẫu PHỐI NHIỀU FONT (nhóm 2–4 dòng chữ, mỗi dòng 1 font: chữ ký + chữ đậm, serif + chữ mảnh, giá nhỏ–TO–nhỏ… — khi cần
một cụm chữ nổi bật nhiều tầng, ghép nhiều khối text cùng `group`, y xếp chồng, hiện lệch nhau ~0,15s như các mẫu này),
13 mẫu hiệu ứng, 12 bộ chuyển cảnh trám (TRANS_PRESETS), 8 chuyển động nhanh (MOTION_PRESETS). Khi viết plan.json mà không có phong
cách riêng cho chữ → lấy thông số từ các mẫu này (look, font, màu, anim, ease, mblur…) cho đồng bộ, đừng tự chế lung tung.
KIỂU CHỮ DÙNG THÊM: dự án có `kieu-chu.json` ({"ids": [mã mẫu chữ]}) = người dùng chọn vài kiểu chữ cùng với phong cách →
`phongcach.py tron` in thông số từng kiểu; dùng ĐÚNG các kiểu đó cho chữ, tự phân vai (hook / giá / từ khoá / kêu gọi…).
Chữ mới: `curve` (uốn cong -100..100), `grad` [màu1, màu2] (chuyển sắc), `fillSrc` (lồng ảnh vào chữ), `count` (số chạy),
`autofit` + `width` (+ `maxLines`) tự co cho vừa khung, `hlColors` {"từ": "#màu"} (màu riêng từng từ khoá), look mới skew | tape |
pill2 (dùng strokeColor làm màu đầu) | dashed | chat; anim `spoken` + `wt` [giây từng từ] = từng từ hiện đúng lúc đọc.
Mẫu người dùng tự lưu: `mau-cua-toi.json` (gốc tool) — nếu có, ưu tiên dùng đúng kiểu đó khi người dùng nhờ.

### Khối kiểu After Effects (AE.tsx — vẽ bằng CSS/SVG, chữ tiếng Việt đầy đủ, không cần cài thêm)
- CHỮ ĐỘNG (kinetic typography) — `anim` của khối `text`: stagger (bật từng ký tự) | wave (sóng lượn liên tục) | flip3d (lật 3D
  từng chữ) | maskUp (từng từ trồi lên từ khe — kiểu trailer) | rise (từng từ nổi lên mờ→nét, êm) | typeCursor (gõ + con trỏ nháy)
  | glitch (nhiễu tách màu) | scramble (xáo ký tự rồi giải mã). `ease` (mọi khối có hiệu ứng vào/ra): spring | smooth | snappy |
  bouncy | elastic | linear; `mblur: true` = nhòe chuyển động khi bay nhanh. Toàn video: `style.motion: {ease, mblur}`.
- `overlay` — lớp hiệu ứng phủ, tự hoà trộn (screen…): `kind` lightleak (rò sáng) | flare (lóa ống kính, x/y = tâm) | rays (tia
  sáng) | bokeh | particles (hạt sáng bay) | sparkle (lấp lánh) | filmburn (cháy phim — đặt 0,8–1,5s quanh điểm nối) | dust
  (bụi xước phim) | grain (hạt nhiễu) | snow | confetti (pháo giấy); `amount` 0–150 (70), `color`, `density`, `speed`, `seed`,
  `blend`. Lớp mặc định z 18 (dưới phụ đề). Chỗ hợp: hook 3s đầu (lightleak/flare), điểm nối khác cảnh (filmburn/lightleak),
  con số lớn (flare), kêu gọi cuối (sparkle; quà/ưu đãi → confetti). Video chill/thơ: bokeh/particles nhẹ (amount 40–55).
  Tự đặt: `python scripts/ae.py tu-gan "<folder>" [--it|--nhieu] [--ghi-de]` (khối tự đặt có "auto": "ae", chạy lại sẽ thay).
- `shape` — hình TỰ VẼ RA (nét chạy, `draw` giây, mặc định 0.6): `kind` arrow | line (x,y → x2,y2, `bend` độ cong -0.6..0.6) |
  circle | box | bracket (tâm x,y + w,h — khoanh tay hơi méo, `rough: false` = tròn đều) | underline (x,y bắt đầu, w dài, `wave`,
  `marker` bút dạ) | check | cross (tâm x,y, w cỡ) | callout (chấm nháy ở x,y + đường gấp khúc tới x2,y2 + nhãn `text`).
  `color` (mặc định vàng theme), `width` nét, `glow`. x/y ≤ 1 = tỉ lệ khung. Dùng để CHỈ vào thứ đang nói (tay nắm cửa, ban công,
  con số trên màn hình) — xem sheet.jpg / check.jpg để lấy toạ độ. Khối chỉ vào vật đang chuyển động → BÁM VẬT THỂ (dưới).
- `text3d` — chữ khối 3D xoay trong không gian: `text`, `size` (140), `depth` (26), `face` solid|gold|chrome, `color`, `side`
  (màu thành), `motion` swing|spin|rise|tilt|float|zoom, `glow`, `x`, `y`. Dùng cho con số/từ chốt quan trọng (giá, "SIÊU PHẨM").
- `card3d` — ảnh/video trên mặt phẳng 3D, camera chuyển động: `src`, `move` orbit|flyIn|tiltIn|float|flip|dolly|swing, `w` (760),
  `ratio` (1.25 cao/rộng), `y` (tâm), `label`, `reflect`, `radius`. Hợp ảnh phối cảnh / mặt bằng / ảnh chụp màn hình thay cho pip.
- `scene` — CẢNH DỰNG SẴN theo tham số (điền nội dung từ brief, KHÔNG bịa số): `kind`
  intro (`title`, `kicker`, `sub`, `hl`: từ tô màu) | outro (`title`, `sub`, `handle`, rows = nút [{icon, text}]) |
  pricetable (`title`, rows "Nhãn: giá | …" hoặc [{label, value, note, icon, hl}] — số tự đếm lên, `count: false` để tắt) |
  compare (`a`/`b`: {name, value?, items: ["ưu điểm", "- nhược điểm"]}, `win`: "a"|"b"; hoặc dạng bảng rows [{label, a, b}]) |
  amenities (rows [{icon, text, dist}]) | stats (rows "Nhãn: số | …", 2 cột). `y`, `step` (giây giữa các dòng) hoặc `at`
  ([giây từ lúc khối hiện cho từng dòng] — canh đúng lúc nói), `bg` none|dim|dark|brand (mặc định intro/outro: dim), `light`
  (thẻ sáng), `accent`. Khối 4–8 giây, dòng thứ k hiện đúng lúc lời nói nhắc tới.
- BÁM VẬT THỂ (motion tracking): `python scripts/track.py "<folder>" <số thứ tự khối> [--x px --y px] [--r 60]` → ghi
  `trackPts` [[giây gốc, x, y]] vào khối; khối dời theo vật (mũi tên bám đầu mũi tên x2,y2; callout bám chấm x,y; khối khác bám
  tâm). Đặt khối lên đúng vật ở lúc khối bắt đầu rồi chạy. Chỉ bám trong 1 đoạn liền (qua điểm nối giữ vị trí cuối). Trình edit:
  nút "Bám vật thể" (tab Cơ bản của khối). Bỏ: `--xoa`.
- ẢNH → VIDEO 2.5D (parallax): `python scripts/parallax.py "<folder>" "<ảnh>" [--move dolly|orbit|pan|rise|zoomout] [--dur 4]`
  → `assets/_xu-ly/<tên>_parallax_<move>.mp4` (độ sâu bằng mô hình Depth Anything V2 — tự tải lần đầu; không tải được thì ước lượng
  bằng tách người). Dùng làm `src` của broll/card3d thay cho ảnh tĩnh phối cảnh / nội thất (sống động hơn Ken Burns).
  Chạy nặng → gọi qua giao diện (trình edit: chọn ảnh trám → "Ảnh tĩnh → video 2.5D") hoặc chạy tại chỗ nếu giao diện đóng.
- Hiệu ứng khung `fx` thêm: glow (toả sáng — vùng sáng loé hào quang) | dreamy (mơ màng: glow + ấm nhẹ).
- BẮT NHỊP: `python scripts/ae.py bat-nhip "<folder>" [--sai 0.15]` — dời điểm hiện của zoom / overlay / shape / fx / chữ /
  3D / cảnh tới nhịp nhạc gần nhất (giữ độ dài; nhịp lấy từ plan.beats, chưa có thì dò từ plan.music). Khối không muốn dời: `"locked": true`.
- Phong cách có sẵn dùng các khối này: "Điện ảnh AE", "Năng động AE" (style.effects.overlay = danh sách kiểu lớp phủ ưa dùng,
  style.graphics.ghiChu = cách dùng shape / text3d / scene).
- Tool KHÔNG có: Lottie (cần file thiết kế), thay trời (sky replacement) — dùng gần nhất: overlay. 3D THẬT: xem mục dưới.

### 3D THẬT — Three.js (remotion/src/Three3D.tsx) — khối, ánh sáng, phản chiếu, bóng đổ thật
Khác `text3d` / `card3d` / `orbit` (vẽ bằng CSS, giả 3D): các khối dưới dựng cảnh 3D thật trên nền trong suốt đè lên video. Nặng hơn khối
thường → mỗi video 1–3 khối, mỗi khối 3–8 giây, cho Ý QUAN TRỌNG (hook giá, khoe căn, chốt vị trí). Xuất cần card đồ hoạ (render tự bật).
- `text3dPro` — CHỮ KHỐI KIM LOẠI: `{"type": "text3dPro", start, end, "text": "CĂN HỘ\nVIEW SÔNG" ("\n" xuống dòng), "sub": "Chỉ từ 2,9 tỷ"
  (dòng phụ nhỏ, trắng), "mat": gold|silver|chrome|copper|rose|white|black|color (+ "color"), "font": be-vietnam-pro|montserrat|playfair,
  "anim": drop (từng chữ lật rơi, mặc định)|rise|flip|spin|zoom, "size": 190 (px cỡ chữ), "depth": 0.28 (× cỡ chữ), "width": 920 (px tối
  đa — dòng dài tự co), "x": 540, "y": 650 (px tâm khối), "stagger": 0.06, "noGlint"/"noShadow"/"noSway": true để tắt vệt sáng / bóng /
  lắc}`. Mỗi dòng ≤ ~12 ký tự; IN HOA ngắn 1–3 từ như nhãn. Dùng thay `text3d` khi cần chữ chốt sang trọng (giá, tên dự án, "SIÊU PHẨM").
  Tránh mặt người nói (tranh_mat.py tính cả khối này). Riêng màu chữ trên nền: kim loại vàng/bạc tự có viền tối ở cạnh vát, nền rất sáng
  thì chọn `black` hoặc `color` đậm.
- `photo3d` — ẢNH BAY 3D QUANH NGƯỜI (thay `orbit` khi muốn chất 3D thật): `{"type": "photo3d", start, end, "items": [{"src": "assets/a.jpg",
  "caption": "Phòng khách"}, …] (4–6 ẢNH, không nhận video), "look": polaroid (khung trắng + chú thích, mặc định)|clean|glass,
  "hero": [{"i": 2, "at": 3.2, "hold": 1.5}] (ảnh số i — đếm từ 0 — rời vòng bay ra phóng to cạnh mặt lúc `at` giây tính từ lúc khối hiện,
  giữ `hold` giây rồi quay về; đặt `at` đúng lúc lời nói nhắc tới phòng / căn đó — tra words.json), "period": 7 (giây/vòng), "rx": 380
  (px bán kính), "tilt": 18 (độ nghiêng vòng), "cardW": 250, "dir": 1|-1, "heroX"/"heroY" (px, bỏ trống = phía đối diện người nói),
  "heroScale": 1.7, "flyIn": false (bỏ bay vào), "exit": false (bỏ bay ra), "behind": false (cả vòng trước người)}`. `cx` (0–1) / `cy` (px)
  bỏ trống = tự theo mặt (mat.json), ngang ngực. Nửa sau tự nằm SAU người (render tự tách người, chỉ khung 9:16). Khối 5–8 giây.
  Phụ đề / chữ khác không đặt trùng vùng vòng ảnh trong lúc khối chạy.
- `object3d` — VẬT THỂ 3D TRÊN MẶT ĐẤT CỦA CẢNH: `{"type": "object3d", start, end, "items": [{"kind": pin|house|tag|model, "x": 540, "y": 1150
  (px điểm vật CHẠM ĐẤT trên khung), "size": 260 (px cao), "at": 0.15 (giây trễ sau lúc khối hiện), "color", "lift" (px nhấc khỏi đất —
  ghim lơ lửng trên mái nhà: lift = cỡ nhà), "spin", "turn" (độ), "text"/"sub" (bảng giá: "3,2 TỶ" / "85m² · 2PN"), "mat" (chữ bảng giá),
  "src": "assets/x.glb" (kind model)}], "pitch": 24 (độ nhìn xuống đất), "noShadow"}`. Hợp: cảnh flycam / toàn cảnh khu đất (ghim + bảng giá
  lên đúng lô đất), cảnh mặt tiền (ngôi nhà mọc lên), chốt giá. Lấy x, y từ sheet.jpg / check.jpg (điểm trên mặt đất). Máy quay di
  chuyển → BÁM VẬT THỂ (`track.py`, như khối thường) để vật dính vào cảnh. Không bịa giá — chỉ lấy từ lời nói / brief.
  KIỂU XẾP `"layout"`: ring (vòng quay quanh người, mặc định) | fan (xoè quạt, `spread` độ, 70) | stack (xấp ảnh — ảnh trên cùng lần lượt
  lật ra sau, mỗi ảnh period/số ảnh giây) | wall (tường ảnh nghiêng, `cols`, `wallTurn` độ) | helix (xoắn ốc quay). Kiểu khác ring nên
  `"behind": false` và đặt `cx`/`cy` sang bên cạnh người nói (vd cx 0.32, cy 950). `hero` (phóng ảnh ra) dùng được với mọi kiểu.
- `screen3d` — MÀN HÌNH 3D cạnh / trước người nói: `{"type": "screen3d", start, end, "look": holo (kính hologram xanh, viền phát sáng, mở
  bung) | glass (kính mờ trắng) | device (máy tính bảng) | phone (điện thoại có tai thỏ, ratio 2.05, w 380) | curved (màn hình cong, w 900)
  | neon (bảng neon 2 ống hồng–xanh, chữ phát sáng) | tv (TV có chân đế) | billboard (bảng LED điểm sáng, chữ vàng) | card (thẻ trắng nổi,
  bóng đổ) | custom (tự thiết kế từ đầu), "frame": {…} (THIẾT KẾ KHUNG — xem dưới), "pageStyle": {…} (kiểu trang chữ), "pages": [{"src": "assets/a.mp4", "from": 3, "volume": 0} (VIDEO chạy
  khớp từng khung) | {"src": "assets/b.jpg"} | {"title": "Căn 2PN · 72 m²", "text": "View sông\nBan công Đông Nam", "sub": "…"} (trang chữ)],
  "x": 330, "y": 820 (px tâm), "w": 620 (px rộng), "ratio" (cao/rộng; 1.4 = dọc như điện thoại), "tiltY"/"tiltX" (độ nghiêng; mặc định
  quay vào phía giữa khung), "enter": unfold|fly|flip, "color" (màu hologram), "at": [giây trong khối — chuyển trang] (không ghi + không
  dò tay = tự chia đều)}`. Đặt ở khoảng trống cạnh người nói (xem mat.json), không đè mặt. Hợp: chiếu video căn / clip flycam cạnh người
  đang giới thiệu (device / glass + 1 trang video), thông tin căn dạng hologram.
  TỰ THIẾT KẾ KHUNG THEO Ý TƯỞNG (ưu tiên khi brief / phong cách có ý riêng — đừng chỉ chọn kiểu có sẵn): lấy kiểu gần nhất làm `look`
  (hoặc `custom`) rồi ghi `frame` (chỉ các thông số muốn đổi): `curve` (độ cong ngang, 0 phẳng, 40–90 cong), `corner` (bo góc 0–0.5),
  `bezel` {w px viền (0 = không khung), depth px dày, color, metal 0–1, rough 0–1}, `plate` {color, opacity} (tấm nền kính), `inset` (vùng
  nội dung 0.8–1), `glow` {color, width px, halo 0–1, pulse}, `neon` {color, color2, width, flicker}, `corners` bracket|dot|none,
  `scan` lines|led|grid|none (+ scanColor, scanOpacity), `reflection` 0–1, `shadow` 0–1, `notch`, `buttons`, `stand`, `transition`
  slide|fade|flip. `pageStyle` {bg "#màu" | ["#màu1","#màu2"] | "none", ink, accent, align left|center, font (font có trong tool — xem
  remotion/fonts.json), glow (chữ neon), titleSize}; từng trang ghi đè được bằng `style`. `enter` unfold|fly|flip|rise|fade, `color` = màu
  chủ đạo (viền / neon). Ví dụ ý tưởng → thiết kế:
  · "sang trọng, vàng kim" → look custom, frame {corner 0.08, bezel {w 10, depth 14, color "#c9a24a", metal 1, rough 0.2}, glow {color
    "#ffd27a", width 3, halo 0.8, pulse true}, reflection 0.4, shadow 0.4, corners "dot"}, pageStyle {bg ["#1a1206","#3a2a0c"], ink "#fff6dd",
    accent "#ffd27a", align "center", font "Playfair Display"}.
  · "công nghệ, tương lai" → look holo + frame {corners "bracket", scan "grid", glow {color "#7cf9ff", pulse true}}, enter unfold.
  · "trẻ trung, mạng xã hội" → look phone + pageStyle {bg ["#ff7a59","#ffb36b"], ink "#fff"}.
  · "điện ảnh, rộng" → look curved + frame {curve 90}, ratio 0.42.  · "quán bar / sự kiện đêm" → look neon, đổi color / neon.color2.
  · "tối giản, nhẹ nhàng" → look card + frame {corner 0.12, shadow 0.3}, pageStyle {accent màu thương hiệu}.
  Màu theo thương hiệu (brand.json) khi brief không nói gì. Ghi thiết kế vào bao-cao.md (để lần sau dùng lại cùng kiểu).
  THEO CỬ CHỈ TAY (người nói chỉ / vuốt trong clip): `python scripts/nho_may.py tay "<folder>" --khoi <số thứ tự khối>` → ghi `handPts`
  (đầu ngón trỏ + tâm, cỡ bàn tay theo thời gian) và `swipes` (mỗi lần vuốt ngang = lật trang; vuốt sang trái = trang sau) vào khối:
  màn hình nghiêng theo tay (`handFollow` 0–1), loé sáng chỗ ngón tay chạm, vòng sóng khi lật trang, bàn tay nằm ĐÈ LÊN kính
  (`handOver: false` để tắt; render tự tách người). Có swipes thì bỏ `at`. Số trang nên = số lần vuốt + 1 (dò được bao nhiêu lần vuốt
  thì in ra — thiếu trang thì thêm, thừa thì ghép). Đặt màn hình ở chỗ tay hay giơ lên (xem x, y trong handPts). Mô hình dò tay MediaPipe (tự tải lần đầu, chạy offline).
- Thêm font cho chữ 3D thật (máy phát triển): `python scripts/font3d.py <tên @fontsource> 800` → `remotion/src/fonts3d/`, khai báo trong
  FONTS3D (Three3D.tsx).
  Máy ảo không có card đồ hoạ: khối 3D xuất chậm hơn (vẽ bằng CPU) — dùng ít, khối ngắn. Dò tay cần tải mô hình MediaPipe (mạng
  máy ảo chặn thì bỏ qua theo tay, dùng `at` để chuyển trang theo lời nói).
- Tốc độ video: `"speed": 1.2` (cả video), `"segSpeed": {"12.5": 2}` (riêng đoạn, khoá = giây bắt đầu đoạn trong video gốc). render.py áp lên bản xuất cuối (scripts/render.py `speed_ranges` / `apply_speed`). Tốc độ 0,1–16×; `"segCurve"` đường cong (hero | bullet | montage | jump | flashin | flashout); `"segAudio": {"<giây>": "keep|mute"}` (mặc định tự tắt tiếng gốc khi < 0,75× hoặc > 2,5×), `"segSmooth": {"<giây>": "mci|blend|off"}` (slow-motion tự trộn khung; mci = mượt nhất, xuất lâu).

### CẢNH AI — khối `canhAI` (remotion/src/CanhAI.tsx, cách làm của LumReels) — đồ hoạ AI tự viết bằng code
Khi khối có sẵn không làm được đoạn cần (mở đầu thương hiệu, bảng giá / tiến độ thanh toán động, sa bàn vẽ tay, tranh màu nước tự
vẽ, infographic số liệu, kết bài có nút gọi…): tự viết 1 cảnh HTML/SVG/Canvas/Three.js rồi chèn như mọi khối. Luật viết: ĐỌC HẾT
`canh-ai/HUONG-DAN.md` (mỗi khung là hàm thuần của t, không gọi mạng, chỉ font trong thư viện). Không thay ảnh thật của dự án.
- Thư viện 104 mẫu phong cách (bản mô tả bằng chữ: màu, font, bố cục, nhịp theo giây, cách dựng, tự kiểm):
  `canh_ai.py ds [--nhom bds|ads|faceless] [--tim "<từ>"]` · `canh_ai.py xem <id>` (10 mẫu BĐS: 014, 015, 021, 042, 044, 046, 047, 050, 052, 078).
- Tạo: `canh_ai.py moi "<du-an>" <ten> [--mau <id>] [--giay 6] [--nen trong|mau]` → `canh/<ten>/index.html` (+ `MAU.md`).
- Xem thử riêng (5 mốc, không cần dựng video): `canh_ai.py thu "<du-an>" <ten>` → `canh/<ten>/_thu.jpg` — MỞ RA XEM.
- Soát: `canh_ai.py kiem "<du-an>"` (soat.py tự gọi: luật + chạy cảnh trong Chrome bắt chữ mất dấu / font hệ thống / chữ quá nhỏ).
- Khối: `{"type": "canhAI", "start", "end", "canh": "canh/<ten>", "data": {…dữ liệu cảnh đọc qua window.CANH.data…}, "from"?, "speed"?,
  "fit": "cover"|"contain", "fadeIn"?: 0.25, "fadeOut"?: 0.25, "opacity"?, "z"?, "sfx"?}`. Nền cảnh trong suốt = lớp phủ trên video;
  nền màu = chèn kín khung. Cùng 1 cảnh dùng lại được cho dự án khác — chỉ đổi `data`.
- Máy ảo: cảnh 2D (DOM/SVG/canvas) dựng nhanh như khối thường; cảnh WebGL / Three.js vẽ bằng CPU → chậm, giữ ngắn (≤ 6s).

## DỰNG THEO NHỊP NHẠC — dự án có `dung-nhip.json` {"on": true} (người dùng tích "🎵 Dựng theo nhịp nhạc")
Dùng cho trailer, đoạn mở đầu, video không lời / video đặc biệt. KHÔNG tự bật khi người dùng không tích (hoặc không nhờ).
`range`: "intro" (0 → `introSec` giây) | "all" (cả video) | "custom" (`from`–`to`); `density`: auto | 1 | 2 | 4 (số nhịp mỗi cảnh).
BẮT BUỘC có nhạc: người dùng chọn nhạc ngay khi tích ô (tìm nhạc Openverse / tải file lên) -> `dung-nhip.json` "music" (vd
`assets/nhac/epic.mp3`). Plan chưa có khối nhạc thì dung_nhip.py TỰ THÊM khối audio "bgm" bằng bài đó (mở đầu: hết đoạn + 1,5s vuốt nhỏ;
có lời nói thì âm lượng 0.25). Không có nhạc nào -> KHÔNG dựng theo nhịp, báo người dùng chọn nhạc ở thẻ 🎵 trên trang dự án.
1. Cắt cảnh theo nhịp: `python scripts/dung_nhip.py "<folder>"` (đọc dung-nhip.json; `--xem` = chỉ in kế hoạch). Script dò nhịp
   (ghi `plan.beats`), chọn cảnh đẹp từ video chính + tư liệu (assets, kể cả cua-ban), mỗi lần đổi cảnh rơi đúng nhịp (auto: nhạc
   mạnh cắt dày, nhẹ cắt thưa, cuối đoạn dồn dập), ghi `plan.beatEdit` {on, from, to} và hiệu ứng ở nhịp mạnh (zoom giật khi cắt
   video chính / khung nảy theo nhịp khi đè khối trám, chớp sáng ở vài nhịp mạnh nhất — các khối "beatFx": true). Cả video không lời
   nói -> cắt thẳng video chính (`segments`); còn lại -> các khối broll "beatCut": true đè lên (giữ lời nói). Chạy lại = thay khối cũ.
   Viết plan.json ĐẦY ĐỦ NHƯ BÌNH THƯỜNG TRƯỚC (hook, chữ tiêu đề, nhãn, thẻ giá, phụ đề, CTA, minh hoạ… — dựng theo nhịp chỉ đổi
   CÁCH CẮT CẢNH / CHUYỂN CẢNH, KHÔNG bỏ chữ), rồi mới chạy script: script giữ mọi khối khác và tự đưa lúc hiện của chữ / đồ hoạ trong
   đoạn nhịp vào nhịp gần nhất (lệch ≤ 0,3s). Cảnh trám theo nhịp nằm lớp 10, chữ lớp 30, phụ đề lớp 20 -> chữ luôn nằm trên cảnh.
   Trong đoạn nhịp vẫn cần chữ: trailer/mở đầu nên có chữ tiêu đề lớn (tên dự án, giá, câu hook) bật đúng nhịp mạnh, mỗi câu 2–4 nhịp.
   KIỂU DỰNG NHỊP (`--kieu`, dung-nhip.json "style", trình chỉnh sửa "Kiểu dựng nhịp"): `trailer` (mở chậm có màn đen chen giữa,
   dồn dập về cao trào, viền phim, chớp trắng, kết màn đen) | `nang-dong` (mỗi nhịp 1 cảnh, zoom giật + rung, lia nhanh) |
   `sang-trong` (2–4 nhịp, đẩy chậm, mờ chồng, ánh sáng loé, màu ấm — hợp BĐS) | `chia-khung` (mở bằng Khung nhịp, Dải chéo ở chỗ
   chuyển đoạn) | `glitch` (nhiễu hình / tách màu ở nhịp mạnh) | `chill` (cắt thưa, mờ chồng mềm, hạt phim) | `mau:<bộ phong cách>`
   (học từ video mẫu) | `auto` (chọn theo nhạc: tempo, độ mạnh, có cao trào không). `python scripts/dung_nhip.py ds` = danh sách.
   Mỗi lần chạy ra 1 phương án khác (`--phuong-an <số>` để lặp lại đúng phương án cũ). Chọn kiểu hợp NỘI DUNG + nhạc (BĐS cao cấp
   -> sang-trong/trailer; khuyến mãi sôi động -> nang-dong; công nghệ -> glitch), không dùng 1 kiểu cho mọi video.
   BẮT NHỊP THEO DÒNG NHẠC (tự nhận, ép bằng `--cam-giac em|vua|manh` / dung-nhip.json "feel"): script đo độ "gắt" của tiếng ở
   nhịp (thời gian lên đỉnh, đỉnh/nền), phách mạnh đầu ô nhịp, chỗ chuyển đoạn và cao trào (độ to thay đổi giữa các ô nhịp).
   - êm (ballad, piano, acoustic, lofi): cắt ở đầu ô nhịp / câu nhạc (1–2 ô mỗi cảnh), MỜ CHỒNG CHẬM (~1–1,4s), đẩy chậm vào cảnh,
     Khung nhịp hiện dần từng khung (2 phách / khung, không thu ô), màn đen kiểu trailer thì mờ qua đen; KHÔNG zoom giật / rung / chớp.
   - vừa (pop nhịp đều): cắt theo ô / nửa ô nhịp, chuyển mềm ở chỗ chuyển đoạn, hiệu ứng mạnh chỉ ở đầu ô, nhấn ở cao trào thật.
   - mạnh (EDM, trống dồn): cắt theo phách, dồn dập ở cao trào, hiệu ứng ở nhịp mạnh như kiểu đã chọn.
   Kiểu dựng quyết định "bảng màu" chuyển cảnh / hiệu ứng; cảm giác bài quyết định nhịp cắt và độ mềm — nhạc êm thì kiểu nào cũng
   chuyển mềm. Chuyển cảnh trám chậm: broll {"transition": "fade" | "blur", "inDur": giây}. Khung nhịp / Dải chéo: "soft": true.
   BỘ PHONG CÁCH NHỊP (thư viện, nhóm "🎵 Dựng theo nhịp nhạc"): "Nhịp · Trailer điện ảnh / Năng động TikTok / Sang trọng BĐS /
   Chia khung montage / Glitch công nghệ / Chill nhẹ nhàng" — chữ, phụ đề, màu hợp với kiểu nhịp; thành phần "Nhịp dựng" mang
   `style.beat` {"preset": "<kiểu>"} -> dung_nhip.py tự dùng kiểu đó khi dung-nhip.json không chỉ định "style" (thứ tự: --kieu >
   dung-nhip.json "style" > phong cách dự án > tự chọn theo nhạc). Dự án tích dựng theo nhịp mà chưa chọn phong cách: ưu tiên
   chọn 1 bộ "Nhịp · …" hợp nội dung (`phongcach.py chon`).
   HỌC KIỂU NHỊP TỪ VIDEO MẪU: sau khi phân tích mẫu (nho_may.py style), `python scripts/dung_nhip.py hoc "<folder>"` ghi
   `beatStyle` vào _mau/phong-cach.json; `phongcach.py luu` tự học nếu mẫu có nhạc -> kiểu "Từ mẫu: <bộ>" dùng lại được.
   Khối dùng trong các kiểu: `solid` (màn màu {color, fadeIn, fadeOut}), `bars` (viền phim, tự theo khung), `overlay`, `fx`.
2. Trong đoạn nhịp: KHÔNG gắn sfx (render tự bỏ tiếng hiệu ứng trong `beatEdit`, sfx.py tu-gan cũng bỏ qua; muốn giữ: `keepSfx: true`).
   Mọi chữ / khối hiện ĐÚNG NHỊP (lấy mốc trong `plan.beats`, không lệch quá 0,05s), ở lại trọn 1–4 nhịp.
3. Khối theo nhịp (chọn LINH HOẠT theo nội dung & khung hình, KHÔNG bê nguyên một công thức — mỗi video 1–2 kiểu là đủ):
   - `beatFrames` "Khung nhịp": {start, end, src (1 file: các khung ghép thành 1 cảnh liền) | srcs [nhiều file: mỗi khung 1 cảnh],
     from, layout auto|cols|rows|grid, count (0 = tự), every (số nhịp mỗi khung), gap, radius, collapse (thu thành ô), exit expand|cut, bg}.
     Bố cục tự theo khung: ngang -> khung đứng xếp ngang (4–5), dọc -> dải ngang xếp chồng (3), vuông -> lưới 2×2. Hợp mở đầu / giới
     thiệu nhiều góc (flycam, tổng quan). Dài = số khung × nhịp + 2–3 nhịp (thu ô + bung).
   - `beatStrips` "Dải chéo": {start, end, src, from, count 2–7, every, angle (0 = tự), line} — các dải xiên lộ dần cảnh mới theo nhịp;
     dùng làm chuyển cảnh giữa 2 phần (2–3 giây). Khung dọc nên ít dải (3), ngang nhiều hơn (4–5).
   - Chữ tiêu đề: `text` anim "type"/"words"/"pop" bật đúng nhịp; trailer: chữ to, ít chữ, mỗi câu 2–4 nhịp.
   - `fx` style "beat" (khung nảy theo nhịp), `zoom` punch ở nhịp mạnh (tối đa ~1/4 số nhịp), `fx` flash rất ít (đoạn cao trào).
4. Ngoài đoạn nhịp dựng như thường. Ghi trong bao-cao.md: đoạn nào dựng theo nhịp, BPM, đã dùng kiểu khối gì.

### Âm thanh tự động khi xuất (render.py — cách trộn của LumReels)
- NHẠC NHƯỜNG LỜI: nhạc nền (`music` hoặc khối `audio` có `"bgm": true`) giữ đúng volume đã đặt khi có người nói, tự to lên ×1,8 ở
  khoảng lặng ≥ 0,8s (theo `_work/words.json`) rồi hạ lại trước câu kế. Tắt: plan `"musicDuck": false`; đổi độ to lên: `{"lift": 1.5}`;
  riêng 1 khối: `"duck": false`. Video không lời (`videoVolume: 0`) thì không áp.
- ĐỘ TO CHUẨN: bản xuất cuối được đo và đưa về −14 LUFS, đỉnh ≤ −1,5 dBTP (2 lượt, hình chép thẳng) — dòng "Độ to: …". Tắt: `"loudness": false`.

## Bước 6 — Soát nhanh (không dựng hình)
```
python scripts/soat.py "<folder>"
```
Báo: thiếu file, khối ngoài video, > 3 chữ cùng lúc, chữ sát vùng phụ đề, chữ hiện đúng điểm nối, khoảng trống > 10s,
thiếu hook 3s đầu; in mọi chữ trên màn hình để soát chính tả / dấu / số liệu so với brief. Sửa plan.json 1 vòng rồi render.
Chỉ chụp khung (`python scripts/nho_may.py check "<folder>" 5,20` — 2–3 mốc) khi thật sự cần nhìn bố cục.

## Bước 7 — Render
```
python scripts/nho_may.py render "<folder>"
```
Ra `<folder>/final.mp4`. Cuối log có dòng "Đồng bộ tiếng–hình: …" (scripts/dongbo.py so bản xuất với video gốc).
Nếu "hơi lệch"/"LỆCH RÕ" → tìm nguyên nhân, sửa, render lại; không giao file lệch.
Render ở môi trường khác (máy người dùng không render được): PHẢI dùng đúng file video chính của dự án (_work/ghep.mp4 /
edit.mp4 / clip gốc) — file quá lớn thì chia nhị phân (`split -b 300m`) để chuyển rồi ghép lại (`cat`), TUYỆT ĐỐI không
nén lại / cắt lại / dựng bản nhẹ thay thế (làm lệch tiếng–hình). Sau đó chạy `python scripts/dongbo.py "<folder>"`.
Báo người dùng 2–3 dòng: đã thêm gì, chữ nào đã sửa, còn thiếu ảnh nào
(theo can-tim.md), và nhắc có thể tự chỉnh tiếp bằng nút ✂ Chỉnh sửa trong giao diện.
Khi người dùng bỏ thêm ảnh vào assets/, chỉ cần chạy lại bước 7.

## Xuất nhanh & bản nháp
- render.py mặc định DỰNG NHANH (scripts/dung_nhanh.py): chỉ những khúc có khối/chữ/ảnh trám/zoom/chuyển cảnh chồng mới dựng bằng
  Remotion (composition "partial"), phần còn lại ffmpeg lấy thẳng video gốc (giữ cắt đoạn, zoom cut 108%, màu); phụ đề vẽ bằng Python
  (scripts/phude_nhanh.py, giống kiểu phụ đề của tool); tiếng dựng riêng (composition "audio"). Video ít đồ hoạ nhanh hơn 2–3 lần, máy yếu
  (2 nhân, Mac Intel) lợi nhất. Tự dựng như cũ khi: kiểu phụ đề "box", khung người nói / nền vẽ của phong cách, logo thương hiệu, đứng hình
  cuối, đổi cỡ cảnh tự động, màu phủ (tint), hoặc đồ hoạ > 75% thời lượng. Tắt: `--cham`, plan `"fastRender": false`, settings `"renderFast": false`.
- `python scripts/render.py "<folder>" --nhap` = bản nháp 540p -> `_work/nhap.mp4` (không thay final.mp4); giao diện: nút "⚡ Xuất nháp 540p".
- Khối mới / hiệu ứng mới ảnh hưởng HÌNH video chính cả video (không nằm trong 1 khối có start/end) -> thêm vào danh sách "không áp dụng" trong
  dung_nhanh.plan(), nếu không bản nhanh sẽ thiếu hiệu ứng đó.

## Tiết kiệm quota
- Đọc transcript.txt; chỉ tra words.json cho mốc cần chính xác.
- Chỉ xem sheet.jpg, _pick_*.jpg, check.jpg; không trích thêm khung hình trừ khi cần.
- Mỗi video tối đa ~6 lần tìm stock.

## Sửa trình chỉnh sửa (dành cho Claude khi người dùng nhờ sửa tool)
Mã nguồn ở `editor/` (React, dùng chính `remotion/src/EditPlan.tsx` để xem trước). Sửa xong chạy
`npm run build-editor` để đóng gói lại vào `gui/editor/`.

## Tạo KHỐI MỚI cho hiệu ứng tool chưa có (người dùng nhờ "làm hiệu ứng giống video này", "tạo phong cách mới có hiệu ứng X")
Trước hết thử ghép bằng thứ đã có: `kf` (keyframe dx/dy/sc/rot/op), `mask`, `behind`, `follow: "face"`, `fx`, kiểu hiện/ẩn chữ,
pip/broll, `shape`, `text3d`, `card3d`, `orbit`, 3D thật (`text3dPro`, `photo3d`, `object3d`, `screen3d`), `map`/`mapTour`. Ghép được gần đúng → dùng luôn, báo người dùng chỗ khác mẫu.
Không ghép được (chuyển động / bố cục riêng, lặp lại nhiều lần trong mẫu) → viết khối mới, làm đủ các bước:
1. Xem kỹ mẫu: dải khung cách 0,1–0,2s quanh lúc hiệu ứng chạy (ffmpeg `fps=5,tile=`), ghi lại quỹ đạo, cỡ, độ sâu, thời lượng.
2. `remotion/src/<TenKhoi>.tsx`: component nhận `{e, dur}`, mọi thông số có mặc định, toạ độ theo `FR.w/FR.h`, `fy()` (frame.ts),
   ảnh/video qua `MediaFill` / `mediaSrc` (Media.tsx). Cần lớp người (nửa sau người) → tách 2 nửa như `orbit` trong EditPlan.
3. `EditPlan.tsx`: thêm vào type `El`, import, `case '<type>'` trong renderEl; khối toàn màn → zOf như map.
4. `scripts/render.py`: file nằm trong trường lồng (items, badges…) → thêm vào bước kiểm file thiếu + `stage()`. Cần tách người
   → `behind_of()` trong tach_nguoi.py và `needsPerson` trong editor/logic.ts. Cần mạng/máy thật → làm qua `nho_may`.
5. Trình chỉnh sửa: `editor/logic.ts` (mk mặc định trong addEl, `fileUrl` cho đường dẫn lồng), `editor/main.tsx` (TYPE_NAME,
   TYPE_ICON, TYPE_COLOR, thẻ trong ccgrid, hộp chỉnh `<Ten>Box`) → `npm run build-editor`.
6. Thử: `npx tsc --noEmit -p .`, `render.py --check` vài mốc (hoặc `nho_may.py check` trên máy thật), xem ảnh, sửa tới khi giống mẫu.
7. Ghi tài liệu khối vào mục element của CLAUDE.md + HUONG-DAN.md; lưu bộ phong cách dùng khối đó (`phong-cach/<tên>/` gồm
   phong-cach.json, ghi-chu.md, demo.jpg) để lần sau / người khác dùng lại (gói .phongcach báo "cần cập nhật tool" nếu thiếu khối:
   thêm tên khối + file vào `NEED_FILES` trong scripts/phongcach.py).
Báo người dùng: khối mới tên gì, giống mẫu ở đâu, chưa giống ở đâu. Người nhận gói phong cách dùng khối mới cần bản tool có khối đó.

## Đổi thương hiệu
Màu: `brand.json` (hoặc ⚙ Cài đặt trong giao diện). Sound effect: thay .wav cùng tên trong `public/sfx/`.
Key Pixabay: `settings.json`.
