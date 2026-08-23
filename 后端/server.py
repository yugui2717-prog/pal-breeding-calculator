# -*- coding: utf-8 -*-
"""留言板后端 API（教学版，单文件）
运行：python server.py
接口：
  GET  /messages  → 返回所有留言（JSON 数组）
  POST /messages  → 提交留言，body: {"name":"玩家名","text":"留言内容"}
数据保存在同目录 messages.json 文件里，重启不丢。
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# 留言文件路径（和本脚本同目录）
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages.json")


def load_messages():
    """读取所有留言。文件不存在或读取出错时，返回空列表（不崩溃）。"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 校验一下：必须是列表，否则当成空数据
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_messages(messages):
    """把全部留言写回文件（覆盖写，保证内容一致）。"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    """处理 GET / POST 请求。"""

    # ---------- 通用小工具 ----------
    def _send_json(self, status, obj):
        """把 Python 对象打包成 JSON 发给前端。"""
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")  # 允许前端跨域调用
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        """读取请求体，返回字符串；读不到就返回空串。"""
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        return raw.decode("utf-8", errors="ignore")

    # ---------- OPTIONS：处理跨域预检请求 ----------
    def do_OPTIONS(self):
        """浏览器跨域发 POST 前会先发 OPTIONS 预检，这里放行。"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- GET：返回所有留言（置顶在前，其余按时间顺序） ----------
    def do_GET(self):
        if self.path == "/messages":
            messages = load_messages()
            # 排序：置顶留言（isPinned=true）排在最前面，其余按原顺序（即时间顺序）
            # sorted 是稳定排序，保证相同优先级下保留原列表顺序
            messages = sorted(messages, key=lambda m: 0 if m.get("isPinned") else 1)
            self._send_json(200, messages)
        else:
            self._send_json(404, {"error": "找不到这个接口"})

    # ---------- POST：提交新留言 ----------
    def do_POST(self):
        if self.path != "/messages":
            self._send_json(404, {"error": "找不到这个接口"})
            return

        # 解析前端发来的 JSON
        try:
            data = json.loads(self._read_body() or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "请求体不是合法的 JSON"})
            return

        name = (data.get("name") or "").strip()
        text = (data.get("text") or "").strip()
        # 读取可选的置顶字段，不传则默认 false
        is_pinned = bool(data.get("isPinned", False))

        # 校验：名字或留言为空 → 提示前端
        if not name or not text:
            self._send_json(400, {"error": "名字和留言内容都不能为空"})
            return

        # 组装一条新留言
        from datetime import datetime
        new_message = {
            "name": name,
            "text": text,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "isPinned": is_pinned,
        }

        # 追加保存到文件
        messages = load_messages()
        messages.append(new_message)
        try:
            save_messages(messages)
        except OSError:
            self._send_json(500, {"error": "留言保存失败，请稍后再试"})
            return

        # 成功返回
        self._send_json(200, {"message": "留言成功", "data": new_message})

    # 控制台日志更简洁一点（默认会打印一行带版本号的访问日志）
    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.command, self.path))


if __name__ == "__main__":
    print("留言板后端启动！")
    print("  GET  http://127.0.0.1:8000/messages  查看所有留言")
    print("  POST http://127.0.0.1:8000/messages  提交新留言")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
