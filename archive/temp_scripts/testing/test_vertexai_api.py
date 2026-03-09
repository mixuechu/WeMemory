#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Vertex AI 的正确调用方式"""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account

project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

print(f"Project: {project_id}")
print(f"Location: {location}")
print()

# 方法 1: vertexai.generative_models
print("=" * 80)
print("方法 1: vertexai.generative_models.GenerativeModel")
print("=" * 80)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=project_id, location=location, credentials=credentials)

    for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
        try:
            print(f"\n尝试: {model_name}")
            model = GenerativeModel(model_name)
            response = model.generate_content("Say hello in one word")
            print(f"  ✓ 成功！响应: {response.text}")
            break
        except Exception as e:
            print(f"  ✗ 失败: {str(e)[:100]}")
except Exception as e:
    print(f"✗ 方法 1 整体失败: {e}")

# 方法 2: vertexai.preview.generative_models
print("\n" + "=" * 80)
print("方法 2: vertexai.preview.generative_models")
print("=" * 80)
try:
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel

    vertexai.init(project=project_id, location=location, credentials=credentials)

    for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
        try:
            print(f"\n尝试: {model_name}")
            model = GenerativeModel(model_name)
            response = model.generate_content("Say hello in one word")
            print(f"  ✓ 成功！响应: {response.text}")
            break
        except Exception as e:
            print(f"  ✗ 失败: {str(e)[:100]}")
except Exception as e:
    print(f"✗ 方法 2 整体失败: {e}")

# 方法 3: google.cloud.aiplatform (PredictionServiceClient)
print("\n" + "=" * 80)
print("方法 3: google.cloud.aiplatform PredictionServiceClient")
print("=" * 80)
try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform_v1.services.prediction_service import PredictionServiceClient
    from google.protobuf import json_format
    from google.protobuf.struct_pb2 import Value

    aiplatform.init(project=project_id, location=location, credentials=credentials)

    client = PredictionServiceClient(credentials=credentials)
    endpoint = f"projects/{project_id}/locations/{location}/publishers/google/models/gemini-1.5-flash"

    instance = json_format.ParseDict({"content": "Say hello"}, Value())

    response = client.predict(endpoint=endpoint, instances=[instance])
    print(f"  ✓ 成功！")
except Exception as e:
    print(f"  ✗ 失败: {str(e)[:200]}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
