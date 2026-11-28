// Máy ảo (ChatGPT / Claude): một số máy chặn đọc giao diện mạng → os.networkInterfaces() ném lỗi
// ("uv_interface_addresses … Unknown system error") làm Remotion dừng. Bọc lại: lỗi thì trả rỗng. chay.sh nạp qua NODE_OPTIONS.
const os = require('os');
const orig = os.networkInterfaces;
os.networkInterfaces = function () {
  try { return orig.apply(os, arguments); } catch (e) { return {}; }
};
