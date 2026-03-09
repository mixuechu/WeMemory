#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Gemini 2.5 的原始响应"""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 测试 prompt
test_prompt = """请从以下对话中提取人物信息，返回 JSON 格式：

对话：
张三: 我在 XX 科技公司工作
李四: 我也是，我是软件工程师

返回格式：
{
  "people": [
    {"name": "张三", "company": "XX科技"},
    {"name": "李四", "occupation": "软件工程师"}
  ]
}"""

models_to_test = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

output_file = "knowledge_graph/gemini25_raw_response.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    for model_name in models_to_test:
        f.write(f"\n{'='*80}\n")
        f.write(f"测试: {model_name}\n")
        f.write(f"{'='*80}\n")

        print(f"测试: {model_name}...", end=" ", flush=True)

        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(
                test_prompt,
                generation_config={"max_output_tokens": 500}
            )

            f.write(f"\n原始响应 text:\n")
            f.write("-" * 80 + "\n")
            f.write(response.text)
            f.write("\n" + "-" * 80 + "\n")
            f.write(f"\n响应长度: {len(response.text)}\n")
            f.write(f"前100字符: {repr(response.text[:100])}\n")
            f.write(f"后100字符: {repr(response.text[-100:])}\n\n")

            print("OK")

        except Exception as e:
            f.write(f"错误: {e}\n")
            f.write(f"\n")
            print(f"FAIL")

print(f"\n结果已保存到: {output_file}")
