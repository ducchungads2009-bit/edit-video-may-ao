# Mô hình giọng VieNeu — bản sao cho máy ảo

Nhánh riêng (không gộp vào main). Gói = bộ nhớ đệm Hugging Face (thư mục hub/) của VieNeu-TTS v3 Turbo
(pnnbao-ump/VieNeu-TTS-v3-Turbo, gốc pnnbao97/VieNeu-TTS) và MOSS-Audio-Tokenizer-Nano-ONNX (OpenMOSS-Team), đều Apache-2.0
(https://www.apache.org/licenses/LICENSE-2.0) — ghi chú trong hub/NOTICE-VieNeu.txt.

Ghép: cat vieneu.tar.part-* > vieneu.tar (sha256 trong sha256.txt), giải nén vào ~/.cache/huggingface, đặt HF_HUB_OFFLINE=1.
scripts/tts.py làm việc này tự động khi máy ảo không vào được huggingface.co.

Thêm (28/11): speaker-encoder.tar (~28MB, sha256 cd363976f0f655ad75fce93e3f3bb128a3f60bfa6b79d5c04dc867ef6903998e) — speaker_encoder.onnx cho tính năng "giọng của chính bạn" (nhân bản giọng từ file mẫu). Giải nén chồng lên cùng chỗ.
