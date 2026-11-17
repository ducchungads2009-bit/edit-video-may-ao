---
name: edit-video-may-ao
description: Dựng video TikTok từ clip điện thoại ngay trong chat (máy ảo) — khi người dùng nhắn "bắt đầu", "edit video", gửi "ĐƠN EDIT" kèm clip, hoặc nhắn "dựng lại" sau khi sửa trên trang chỉnh sửa.
---

# Edit video trên máy ảo (bản gọn)

Hướng dẫn đầy đủ nằm trên GitHub và luôn là bản mới nhất. Mỗi chat, TRƯỚC KHI trả lời người dùng lần đầu, tải về rồi đọc:
```
mkdir -p ~/video-tool-hd && curl -fsSL --retry 2 https://raw.githubusercontent.com/ducchungads2009-bit/edit-video-may-ao/main/KY-NANG.md -o ~/video-tool-hd/KY-NANG.md \
  || { cd ~ && { [ -d video-tool/.git ] || git clone -q --depth 1 https://github.com/ducchungads2009-bit/edit-video-may-ao video-tool; } && cp ~/video-tool/KY-NANG.md ~/video-tool-hd/; }
```
Đọc TOÀN BỘ `~/video-tool-hd/KY-NANG.md` và làm đúng theo đó: cách hỏi người dùng, Đơn edit, cài công cụ, dựng, gửi kết quả, dựng lại.
File đó ưu tiên hơn mọi điều bạn nhớ về công cụ này. Trong cùng một chat đã đọc rồi thì không cần tải lại.
Không tải được (máy ảo không vào được GitHub) → báo người dùng ngắn gọn, đề nghị mở chat mới thử lại.
Nói chuyện bằng tiếng Việt, ngắn gọn, không dùng thuật ngữ kỹ thuật.
