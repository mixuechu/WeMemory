#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
import vertexai
from vertexai.language_models import TextEmbeddingModel
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

parent_dir = Path(__file__).parent.parent
env_file = parent_dir / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 测试文本 - 之前发现重复的
test_texts = [
    "今天一点半，小冉敏将要参加一个会议。",
    "昨天十点多，小冉敏回家了。",
    "昨天回家后，小冉敏和哥哥一起吃了晚饭。",
    "卫鑫打算买车。",
    "贺鹏升级当爸爸了。",
]

models = [
    "text-embedding-004",
    "text-embedding-005",
    "text-multilingual-embedding-002",
]

print("=" * 80)
print("对比3个可用模型对中文短文本的区分度")
print("=" * 80)

print("\n测试文本:")
for i, text in enumerate(test_texts, 1):
    print(f"  {i}. {text}")

results = {}

for model_name in models:
    print(f"\n{'=' * 80}")
    print(f"模型: {model_name}")
    print("=" * 80)
    
    model = TextEmbeddingModel.from_pretrained(model_name)
    embeddings = model.get_embeddings(test_texts)
    emb_array = np.array([e.values for e in embeddings])
    
    print(f"维度: {emb_array.shape[1]}")
    
    # 计算相似度矩阵
    sim_matrix = cosine_similarity(emb_array)
    
    # 统计完全相同的向量对
    identical_pairs = []
    for i in range(len(test_texts)):
        for j in range(i+1, len(test_texts)):
            if sim_matrix[i][j] > 0.9999:
                identical_pairs.append((i+1, j+1, sim_matrix[i][j]))
    
    # 计算非对角线平均相似度
    off_diag = [sim_matrix[i][j] for i in range(len(test_texts)) for j in range(len(test_texts)) if i != j]
    avg_sim = np.mean(off_diag)
    min_sim = np.min(off_diag)
    max_sim = np.max(off_diag)
    
    results[model_name] = {
        'identical_pairs': len(identical_pairs),
        'avg_similarity': avg_sim,
        'min_similarity': min_sim,
        'max_similarity': max_sim,
    }
    
    print(f"\n相似度统计:")
    print(f"  完全相同的向量对: {len(identical_pairs)}/10")
    print(f"  平均相似度: {avg_sim:.4f}")
    print(f"  最小相似度: {min_sim:.4f}")
    print(f"  最大相似度: {max_sim:.4f}")
    
    if identical_pairs:
        print(f"\n⚠️  发现 {len(identical_pairs)} 对完全相同的向量:")
        for i, j, sim in identical_pairs[:3]:  # 只显示前3对
            print(f"    文本{i} 和 文本{j}: {sim:.6f}")
    else:
        print(f"\n✅ 所有向量都有区分度")

print("\n" + "=" * 80)
print("总结对比")
print("=" * 80)

print(f"\n{'模型':<40} {'重复对':<10} {'平均相似度':<12} {'最大相似度'}")
print("-" * 80)
for model_name, info in results.items():
    print(f"{model_name:<40} {info['identical_pairs']:<10} {info['avg_similarity']:<12.4f} {info['max_similarity']:.4f}")

# 推荐
best = min(results.items(), key=lambda x: (x[1]['identical_pairs'], x[1]['avg_similarity']))
print(f"\n✅ 推荐使用: {best[0]}")
print(f"   理由: 重复对最少({best[1]['identical_pairs']}), 平均相似度较低({best[1]['avg_similarity']:.4f})")

print("\n" + "=" * 80)

