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

test_texts = [
    "今天一点半，小冉敏将要参加一个会议。",
    "昨天十点多，小冉敏回家了。",
    "昨天回家后，小冉敏和哥哥一起吃了晚饭。",
    "卫鑫打算买车。",
    "贺鹏升级当爸爸了。",
]

models_to_test = [
    "text-embedding-004",
    "textembedding-gecko@003",
    "textembedding-gecko@latest",
    "textembedding-gecko-multilingual@001",
]

print("=" * 80)
print("测试所有可用的Embedding模型对中文的区分度")
print("=" * 80)

results = {}

for model_name in models_to_test:
    print(f"\n测试模型: {model_name}")
    try:
        model = TextEmbeddingModel.from_pretrained(model_name)
        embeddings = model.get_embeddings(test_texts)
        emb_array = np.array([e.values for e in embeddings])
        
        print(f"  ✓ 维度: {emb_array.shape[1]}")
        
        sim_matrix = cosine_similarity(emb_array)
        
        # 统计完全相同的向量对
        identical_count = 0
        for i in range(len(test_texts)):
            for j in range(i+1, len(test_texts)):
                if sim_matrix[i][j] > 0.9999:
                    identical_count += 1
        
        # 计算平均非对角线相似度
        off_diag = [sim_matrix[i][j] for i in range(len(test_texts)) for j in range(len(test_texts)) if i != j]
        avg_sim = np.mean(off_diag)
        
        results[model_name] = {
            'dimension': emb_array.shape[1],
            'identical_pairs': identical_count,
            'avg_similarity': avg_sim
        }
        
        print(f"  完全相同的向量对: {identical_count}/10")
        print(f"  平均相似度: {avg_sim:.4f}")
        
    except Exception as e:
        print(f"  ✗ 失败: {str(e)[:100]}")

print("\n" + "=" * 80)
print("总结")
print("=" * 80)

print(f"\n{'模型':<50} {'维度':<8} {'重复对数':<12} {'平均相似度'}")
print("-" * 80)
for model_name, info in results.items():
    print(f"{model_name:<50} {info['dimension']:<8} {info['identical_pairs']:<12} {info['avg_similarity']:.4f}")

# 找到最好的模型
if results:
    best_model = min(results.items(), key=lambda x: (x[1]['identical_pairs'], x[1]['avg_similarity']))
    print(f"\n✅ 推荐使用: {best_model[0]}")
    print(f"   重复对数: {best_model[1]['identical_pairs']}, 平均相似度: {best_model[1]['avg_similarity']:.4f}")

print("\n" + "=" * 80)

