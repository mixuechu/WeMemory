#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试所有 Gemini 模型版本"""
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

# 测试所有 Gemini 模型
test_models = [
    # 2.5 系列
    "gemini-2.5-flash",
    "gemini-2.5-flash-001",
    "gemini-2.5-pro",
    "gemini-2.5-pro-001",

    # 2.0 系列
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-pro",
    "gemini-2.0-pro-exp",

    # 1.5 系列
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
]

output_file = "knowledge_graph/all_gemini_models_test.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Vertex AI - 所有 Gemini 模型测试\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Project: {project_id}\n")
    f.write(f"Location: {location}\n\n")

    available = []

    for idx, model_name in enumerate(test_models, 1):
        f.write(f"[{idx}/{len(test_models)}] {model_name}\n")
        f.flush()

        print(f"[{idx}/{len(test_models)}] {model_name}...", end=" ", flush=True)

        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(
                "Say hi",
                generation_config={"max_output_tokens": 5}
            )
            result = response.text.strip()

            f.write(f"  ✓ 可用 - {result}\n\n")
            f.flush()

            available.append({
                'model': model_name,
                'response': result
            })
            print(f"OK - {result[:15]}")

        except Exception as e:
            error_msg = str(e)

            if "404" in error_msg or "not found" in error_msg.lower():
                f.write(f"  ✗ 404\n\n")
                print("404")
            elif "500" in error_msg or "internal" in error_msg.lower():
                f.write(f"  ✗ 500 内部错误\n\n")
                print("500")
            elif "403" in error_msg or "permission" in error_msg.lower():
                f.write(f"  ✗ 403\n\n")
                print("403")
            elif "no parts" in error_msg.lower():
                f.write(f"  ⚠️ 响应为空\n\n")
                print("空响应")
            else:
                f.write(f"  ✗ {error_msg[:80]}\n\n")
                print(f"错误")

            f.flush()

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
