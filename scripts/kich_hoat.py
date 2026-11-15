"""Bản chạy trên máy ảo (Claude trên đám mây): không dùng mã kích hoạt theo máy."""


def status():
    return {"ok": True, "msg": "Bản máy ảo — không cần kích hoạt", "may": "may-ao"}


def require():
    return status()


def activate(_ma=None):
    return status()


if __name__ == "__main__":
    print(status()["msg"])
