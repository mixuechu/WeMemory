#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import aiplatform

parent_dir = Path(__file__).parent.parent
env_file = parent_dir / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

aiplatform.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

print("=" * 80)
print(f"项目 {PROJECT_ID} 在 {LOCATION} 可用的模型")
print("=" * 80)

# 列出所有发布者模型
print("\n正在查询可用模型...")

try:
    # 使用 Model Registry API
    client = aiplatform.gapic.ModelServiceClient(credentials=credentials)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    
    print(f"\n查询路径: {parent}\n")
    
    # 列出模型
    models = client.list_models(parent=parent)
    
    print("已部署的模型:")
    count = 0
    for model in models:
        print(f"  - {model.display_name}")
        count += 1
        if count > 20:  # 限制显示数量
            print("  ...")
            break
    
    if count == 0:
        print("  (无自定义模型)")
        
except Exception as e:
    print(f"无法列出模型: {e}")

print("\n" + "=" * 80)
print("尝试直接测试常见的Embedding模型")
print("=" * 80)

from vertexai.language_models import TextEmbeddingModel

# 常见的embedding模型列表
embedding_models = [
    # Text Embedding
    "text-embedding-004",
    "text-embedding-005", 
    "text-multilingual-embedding-002",
    
    # Gecko系列
    "textembedding-gecko@001",
    "textembedding-gecko@002", 
    "textembedding-gecko@003",
    "textembedding-gecko@latest",
    "textembedding-gecko-multilingual@001",
    
    # Gemini embedding
    "text-embedding-preview-0409",
    "text-embedding-preview-0815",
    
    # 其他
    "embedding-001",
    "textembedding-gecko-multilingual@latest",
]

available_models = []

print("\n测试文本: '这是一个测试'")
print()

for model_name in embedding_models:
    try:
        print(f"测试 {model_name:<50} ", end="", flush=True)
        model = TextEmbeddingModel.from_pretrained(model_name)
        result = model.get_embeddings(["这是一个测试"])
        dim = len(result[0].values)
        print(f"✅ 可用 (维度: {dim})")
        available_models.append((model_name, dim))
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"❌ 不存在")
        elif "403" in error_msg:
            print(f"❌ 无权限")
        else:
            print(f"❌ {error_msg[:50]}")

print("\n" + "=" * 80)
print("可用的Embedding模型总结")
print("=" * 80)

if available_models:
    print(f"\n找到 {len(available_models)} 个可用模型:\n")
    for model_name, dim in available_models:
        print(f"  ✓ {model_name:<50} {dim}维")
else:
    print("\n未找到可用的embedding模型")

print("\n" + "=" * 80)

