#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试几个关键模型"""
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

# 只测试最关键的几个模型
test_models = [
    "claude-3-5-sonnet-v2@20241022",  # Claude Sonnet 4.5
    "claude-3-5-sonnet@20240620",     # Claude Sonnet 3.5
    "gemini-1.5-flash-002",           # Gemini Flash
    "gemini-1.5-pro-002",             # Gemini Pro
]

output_file = "knowledge_graph/model_test_results.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Vertex AI 模型可用性测试\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Project: {project_id}\n")
    f.write(f"Location: {location}\n\n")

    for idx, model_name in enumerate(test_models, 1):
        f.write(f"[{idx}/{len(test_models)}] 测试: {model_name}\n")
        f.flush()  # 立即写入文件

        print(f"[{idx}/{len(test_models)}] 测试: {model_name}...", flush=True)

        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(
                "Say hi in one word",
                generation_config={"max_output_tokens": 10}
            )
            result = response.text.strip()

            f.write(f"  状态: 可用\n")
            f.write(f"  测试响应: {result}\n\n")
            f.flush()

            print(f"  OK - {result}")

        except Exception as e:
            error_msg = str(e)

            if "not found" in error_msg.lower() or "404" in error_msg:
                f.write(f"  状态: 不可用 (404)\n\n")
                print(f"  不可用")
            elif "permission" in error_msg.lower() or "403" in error_msg:
                f.write(f"  状态: 无权限 (403)\n\n")
                print(f"  无权限")
            else:
                f.write(f"  状态: 错误\n")
                f.write(f"  错误信息: {error_msg[:200]}\n\n")
                print(f"  错误: {error_msg[:50]}")

            f.flush()

    f.write("\n" + "=" * 80 + "\n")
    f.write("测试完成\n")

print(f"\n结果已保存到: {output_file}")
print("请查看文件了解详细信息。")
