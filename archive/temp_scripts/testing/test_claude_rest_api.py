#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Vertex AI Claude（使用 REST API）"""
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()

from google.auth import default
from google.auth.transport.requests import Request

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")

def get_access_token() -> str:
    """获取 Google Cloud access token"""
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    return credentials.token

# 测试不同的 Claude 模型
test_models = [
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-4",
    "claude-3-5-sonnet-v2",
    "claude-3-5-sonnet",
]

output_file = "knowledge_graph/claude_rest_api_test.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Vertex AI Claude 模型测试（REST API）\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Project: {PROJECT_ID}\n")
    f.write(f"Location: global\n\n")

    access_token = get_access_token()

    available = []

    for idx, model_name in enumerate(test_models, 1):
        f.write(f"[{idx}/{len(test_models)}] {model_name}\n")
        f.flush()

        print(f"[{idx}/{len(test_models)}] {model_name}...", end=" ", flush=True)

        url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/anthropic/models/{model_name}:rawPredict"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        request_body = {
            "anthropic_version": "vertex-2023-10-16",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Say hi in one word"}]
                }
            ],
            "max_tokens": 10
        }

        try:
            response = requests.post(url, headers=headers, json=request_body, timeout=30)

            if response.ok:
                result = response.json()
                content = result.get('content', [{}])[0].get('text', '')

                f.write(f"  ✓ 可用 - 响应: {content}\n\n")
                f.flush()

                available.append({
                    'model': model_name,
                    'response': content
                })
                print(f"OK - {content}")

            else:
                error_msg = response.text[:100]
                status_code = response.status_code

                if status_code == 404:
                    f.write(f"  ✗ 404 不存在\n\n")
                    print("404")
                elif status_code == 403:
                    f.write(f"  ✗ 403 无权限\n\n")
                    print("403")
                else:
                    f.write(f"  ✗ {status_code} - {error_msg}\n\n")
                    print(f"{status_code}")

                f.flush()

        except Exception as e:
            f.write(f"  ✗ 错误: {str(e)[:80]}\n\n")
            f.flush()
            print(f"错误")

    f.write("\n" + "=" * 80 + "\n")
    f.write(f"可用模型汇总 ({len(available)} 个)\n")
    f.write("=" * 80 + "\n\n")

    if available:
        for item in available:
            f.write(f"  ✓ {item['model']}\n")
            f.write(f"    测试响应: {item['response']}\n\n")
    else:
        f.write("  (无可用模型)\n")

print(f"\n结果已保存到: {output_file}")
