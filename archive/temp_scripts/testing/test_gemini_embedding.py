#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import numpy as np

# 加载环境
parent_dir = Path(__file__).parent.parent
env_file = parent_dir / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

print("=" * 80)
print("测试 text-embedding-004 模型对中文的区分度")
print("=" * 80)

# 测试文本
test_texts = [
    "今天一点半，小冉敏将要参加一个会议。",
    "昨天十点多，小冉敏回家了。",
    "昨天回家后，小冉敏和哥哥一起吃了晚饭。",
    "卫鑫打算买车。",
    "贺鹏升级当爸爸了。",
]

print("\n测试文本:")
for i, text in enumerate(test_texts, 1):
    print(f"{i}. {text}")

# 测试 text-embedding-004
print("\n[1/1] text-embedding-004 (当前使用)")
model = TextEmbeddingModel.from_pretrained("text-embedding-004")
embeddings = model.get_embeddings(test_texts)
emb_array = np.array([e.values for e in embeddings])

print(f"  维度: {emb_array.shape[1]}")

# 计算相似度
from sklearn.metrics.pairwise import cosine_similarity
sim_matrix = cosine_similarity(emb_array)

print(f"\n  余弦相似度矩阵:")
print("     ", end="")
for i in range(len(test_texts)):
    print(f"  {i+1}   ", end="")
print()

for i in range(len(test_texts)):
    print(f"  {i+1}: ", end="")
    for j in range(len(test_texts)):
        print(f"{sim_matrix[i][j]:.4f} ", end="")
    print()

# 检查完全相同的向量对
identical_pairs = []
for i in range(len(test_texts)):
    for j in range(i+1, len(test_texts)):
        if sim_matrix[i][j] > 0.9999:  # 几乎完全相同
            identical_pairs.append((i+1, j+1, sim_matrix[i][j]))

if identical_pairs:
    print(f"\n  ⚠️  发现 {len(identical_pairs)} 对几乎完全相同的向量:")
    for i, j, sim in identical_pairs:
        print(f"    文本{i} 和 文本{j}: 相似度 {sim:.6f}")
        print(f"      {i}. {test_texts[i-1][:60]}")
        print(f"      {j}. {test_texts[j-1][:60]}")
else:
    print(f"\n  ✓ 所有向量都有足够区分度")

print("\n" + "=" * 80)

