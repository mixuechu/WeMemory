#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 Vertex AI 所有可用模型"""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
from google.cloud import aiplatform

project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

aiplatform.init(project=project_id, location=location, credentials=credentials)

print(f"Project: {project_id}")
print(f"Location: {location}")
print("\n" + "=" * 100)
print("列出所有可用模型")
print("=" * 100 + "\n")

# 使用 Model Registry API
from google.cloud.aiplatform_v1.services.model_garden_service import ModelGardenServiceClient

try:
    client = ModelGardenServiceClient(credentials=credentials)

    parent = f"projects/{project_id}/locations/{location}"

    print(f"正在查询: {parent}/publishers/google/models\n")

    # 列出 Google 发布的模型
    request = aiplatform_v1.ListPublisherModelsRequest(
        parent=f"{parent}/publishers/google"
    )

    page_result = client.list_publisher_models(request=request)

    models = []
    for model in page_result:
        models.append(model.name)

    print(f"找到 {len(models)} 个模型\n")

    for model in models:
        print(f"  - {model}")

except Exception as e:
    print(f"方法1失败: {e}\n")
    print("尝试方法2：直接测试已知的模型名称...")

    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=project_id, location=location, credentials=credentials)

    # 已知的模型名称（根据 Vertex AI 文档）
    known_models = [
        # Gemini 系列
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        "gemini-1.0-pro",
        "gemini-pro",

        # Claude 系列（通过 Vertex AI Model Garden）
        "claude-3-5-sonnet@20240620",
        "claude-3-5-sonnet-v2@20241022",
        "claude-3-opus@20240229",
        "claude-3-sonnet@20240229",
        "claude-3-haiku@20240307",
    ]

    print("\n" + "=" * 100)
    print("测试已知模型")
    print("=" * 100 + "\n")

    available = []

    for model_name in known_models:
        try:
            print(f"测试: {model_name}...", end=" ", flush=True)
            model = GenerativeModel(model_name)
            # 简单测试
            response = model.generate_content("Hi", generation_config={"max_output_tokens": 10})
            print(f"OK - 响应: {response.text[:20]}")
            available.append(model_name)
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "404" in error_msg:
                print("不可用")
            else:
                print(f"错误: {str(e)[:50]}")

    print("\n" + "=" * 100)
    print(f"可用模型汇总 ({len(available)} 个):")
    print("=" * 100)
    for m in available:
        print(f"  OK {m}")

    # 保存到文件
    with open("knowledge_graph/available_models.txt", 'w', encoding='utf-8') as f:
        f.write("Vertex AI 可用模型列表\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Project: {project_id}\n")
        f.write(f"Location: {location}\n\n")
        f.write(f"可用模型 ({len(available)} 个):\n\n")
        for m in available:
            f.write(f"  ✓ {m}\n")

    print("\n结果已保存到: knowledge_graph/available_models.txt")
