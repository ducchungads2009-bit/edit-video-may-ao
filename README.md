# Edit video — bản máy ảo
Công cụ dựng video chạy trên máy ảo của Claude (dùng kèm bộ kỹ năng `edit-video-may-ao`).
Cài: `./cai-may-ao.sh` · Chạy script: `./chay.sh <script.py> "cho-edit/<du-an>"`. Kho riêng tư — không chia sẻ công khai.

Tài liệu: `KY-NANG.md` (quy trình cho Claude) · `CHATGPT.md` (quy trình cho ChatGPT Công việc) · `AGENTS.md` (ChatGPT / Codex đọc
đầu tiên) · `CHAT-LUONG.md` (chuẩn chất lượng chung — mọi AI bắt buộc đọc) · `TAI-LIEU.md` (tra thông số khối) ·
`canh-ai/HUONG-DAN.md` (cảnh AI tự viết bằng code + thư viện 104 mẫu phong cách — từ LumReels, MIT, `canh-ai/LICENSE-LumReels.txt`).

Bộ dựng hình: **HyperFrames** (Apache-2.0, `scripts/hf_engine.py` + `remotion/hf/`) — các khối viết theo kiểu Remotion trong
`remotion/src` chạy qua lớp thay thế riêng, không cần giấy phép công ty của Remotion. Muốn dùng lại Remotion: settings
`"renderEngine": "remotion"`.
