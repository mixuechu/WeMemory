#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试正确的模型名称"""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

vertexai.init(project=project_id, location=location, credentials=credentials)

# 根据用户要求测试的模型
test_models = [
    # Gemini 2.5 Flash（可能的名称）
    "gemini-2.5-flash",
    "gemini-2.5-flash-exp",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",

    # Claude 4.5（可能的名称）
    "claude-4.5",
    "claude-sonnet-4.5",
    "claude-4-5-sonnet",
    "claude-sonnet-4-5@20250926",
    "claude-sonnet-4@20250926",

    # Claude 4（可能的名称）
    "claude-4",
    "claude-4-sonnet",
    "claude-sonnet-4",
    "claude-opus-4",
]

output_file = "knowledge_graph/correct_model_test.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Vertex AI 模型测试（正确名称）\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Project: {project_id}\n")
    f.write(f"Location: {location}\n\n")

    available = []

    for idx, model_name in enumerate(test_models, 1):
        f.write(f"[{idx}/{len(test_models)}] 测试: {model_name}\n")
        f.flush()

        print(f"[{idx}/{len(test_models)}] {model_name}...", end=" ", flush=True)

        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(
                "Hi",
                generation_config={"max_output_tokens": 5}
            )
            result = response.text.strip()

            f.write(f"  ✓ 可用！响应: {result}\n\n")
            f.flush()

            available.append(model_name)
            print(f"OK - {result}")

        except Exception as e:
            error_msg = str(e)

            if "404" in error_msg or "not found" in error_msg.lower():
                f.write(f"  ✗ 404 不存在\n\n")
                print("404")
            elif "403" in error_msg or "permission" in error_msg.lower():
                f.write(f"  ✗ 403 无权限\n\n")
                print("403")
            else:
                f.write(f"  ✗ 错误: {error_msg[:100]}\n\n")
                print(f"错误")

            f.flush()

    f.write("\n" + "=" * 80 + "\n")
    f.write(f"可用模型 ({len(available)} 个):\n")
    f.write("=" * 80 + "\n\n")

    if available:
        for m in available:
            f.write(f"  ✓ {m}\n")
    else:
        f.write("  (无可用模型)\n")

print(f"\n结果已保存到: {output_file}")
