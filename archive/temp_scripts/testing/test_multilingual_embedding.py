#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 text-multilingual-embedding-002 模型对中文短文本的区分度
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
import numpy as np

# 加载环境
parent_dir = Path(__file__).parent.parent
env_file = parent_dir / '.env'
load_dotenv(env_file)

project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json_str = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

credentials_dict = json.loads(credentials_json_str)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

aiplatform.init(project=project_id, location=location, credentials=credentials)

print("=" * 80)
print("测试多语言模型 vs 当前模型")
print("=" * 80)

# 测试文本（之前发现重复的几条）
test_texts = [
    "今天一点半，小冉敏将要参加一个会议。 [事件类型:会议; 时间:今天一点半; 小冉敏别名:妹妹,小姑娘,重庆琴女王]",
    "昨天十点多，小冉敏回家了。 [事件类型:日常活动; 时间:昨天十点多; 小冉敏别名:妹妹,小姑娘,重庆琴女王]",
    "昨天回家后，小冉敏和哥哥一起吃了晚饭。 [事件类型:日常活动; 时间:昨天回家后; 小冉敏别名:妹妹,小姑娘,重庆琴女王]",
    "卫鑫打算买车。",
    "贺鹏升级当爸爸了。",
]

print("\n测试文本:")
for i, text in enumerate(test_texts, 1):
    print(f"{i}. {text[:80]}")

# 测试当前模型 (text-embedding-004)
print("\n\n[1/2] 测试当前模型: text-embedding-004")
model_004 = TextEmbeddingModel.from_pretrained("text-embedding-004")
embeddings_004 = model_004.get_embeddings(test_texts)
emb_004 = np.array([e.values for e in embeddings_004])

print(f"  维度: {len(emb_004[0])}")
print(f"  范数: min={np.min(np.linalg.norm(emb_004, axis=1)):.6f}, max={np.max(np.linalg.norm(emb_004, axis=1)):.6f}")

# 计算相似度矩阵
from sklearn.metrics.pairwise import cosine_similarity
sim_004 = cosine_similarity(emb_004)
print(f"\n  余弦相似度矩阵:")
for i in range(len(test_texts)):
    print(f"    {i+1}: ", end="")
    for j in range(len(test_texts)):
        if i != j:
            print(f"{sim_004[i][j]:.4f} ", end="")
    print()

# 测试多语言模型 (text-multilingual-embedding-002)
print("\n[2/2] 测试多语言模型: text-multilingual-embedding-002")
model_multi = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
embeddings_multi = model_multi.get_embeddings(test_texts)
emb_multi = np.array([e.values for e in embeddings_multi])

print(f"  维度: {len(emb_multi[0])}")
print(f"  范数: min={np.min(np.linalg.norm(emb_multi, axis=1)):.6f}, max={np.max(np.linalg.norm(emb_multi, axis=1)):.6f}")

# 计算相似度矩阵
sim_multi = cosine_similarity(emb_multi)
print(f"\n  余弦相似度矩阵:")
for i in range(len(test_texts)):
    print(f"    {i+1}: ", end="")
    for j in range(len(test_texts)):
        if i != j:
            print(f"{sim_multi[i][j]:.4f} ", end="")
    print()

print("\n" + "=" * 80)
print("结论:")
print("=" * 80)

# 比较非对角线元素的平均相似度
off_diag_004 = [sim_004[i][j] for i in range(len(test_texts)) for j in range(len(test_texts)) if i != j]
off_diag_multi = [sim_multi[i][j] for i in range(len(test_texts)) for j in range(len(test_texts)) if i != j]

print(f"\n非相关文本间的平均相似度:")
print(f"  text-embedding-004: {np.mean(off_diag_004):.4f} (越低越好)")
print(f"  text-multilingual-embedding-002: {np.mean(off_diag_multi):.4f} (越低越好)")

if np.mean(off_diag_multi) < np.mean(off_diag_004):
    print(f"\n✅ 多语言模型区分度更好！")
    print(f"   建议切换到 text-multilingual-embedding-002")
else:
    print(f"\n❌ 多语言模型区分度不如当前模型")

print("\n" + "=" * 80)

