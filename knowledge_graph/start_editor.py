#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动本地HTTP服务器并打开编辑器"""
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8765

# 切换到脚本所在目录
os.chdir(Path(__file__).parent)

Handler = http.server.SimpleHTTPRequestHandler

print(f"=== 对话与实体编辑器 ===\n")
print(f"启动本地服务器...")
print(f"地址: http://localhost:{PORT}")
print(f"\n按 Ctrl+C 停止服务器\n")

# 启动服务器
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    # 自动在浏览器中打开
    webbrowser.open(f"http://localhost:{PORT}/conversation_entity_editor.html")

    print("服务器运行中...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
