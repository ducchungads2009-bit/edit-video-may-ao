# Mô hình giọng VieNeu — bản sao cho máy ảo

Nhánh riêng (không gộp vào main). Gói = bộ nhớ đệm Hugging Face (thư mục hub/) của VieNeu-TTS v3 Turbo
(pnnbao-ump/VieNeu-TTS-v3-Turbo, gốc pnnbao97/VieNeu-TTS) và MOSS-Audio-Tokenizer-Nano-ONNX (OpenMOSS-Team), đều Apache-2.0
(https://www.apache.org/licenses/LICENSE-2.0) — ghi chú trong hub/NOTICE-VieNeu.txt.

Ghép: cat vieneu.tar.part-* > vieneu.tar (sha256 trong sha256.txt), giải nén vào ~/.cache/huggingface, đặt HF_HUB_OFFLINE=1.
scripts/tts.py làm việc này tự động khi máy ảo không vào được huggingface.co.
