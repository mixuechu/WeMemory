#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多维度测试 - 自然语言三元组搜索质量评估

测试目标：验证记忆系统能否召回"有用的信息"来辅助LLM
不要求精确匹配，关注召回的相关性和有用性
"""
import json
import pickle
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
env_file = parent_dir / '.env'
load_dotenv(env_file)

import faiss
import numpy as np

print("=" * 80)
print("多维度搜索测试")
print("=" * 80)

# 加载索引
print("\n加载向量索引...")
with open('vector_stores/triplets_embeddings.pkl', 'rb') as f:
    data = pickle.load(f)

index = faiss.read_index('vector_stores/triplets.faiss')
records = data['metadata']
print(f"✓ 加载完成: {len(records)} 条记录")

# 初始化embedding模型（使用多语言模型）
print("初始化Embedding模型...")
from google.oauth2 import service_account
import vertexai
from vertexai.language_models import TextEmbeddingModel

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
print("✓ 模型就绪 (text-multilingual-embedding-002)")

# 多维度测试用例
test_cases = {
    "人物关系查询": [
        "王五和用户是什么关系",
        "用户的家人有谁",
        "赵萌是谁的妻子",
        "小冉敏的配偶是谁",
        "用户的父母是谁",
    ],
    
    "人物背景查询": [
        "王五在哪工作",
        "用户在哪个公司",
        "程培晨住在哪里",
        "王露颖的职业是什么",
    ],
    
    "事件相关查询": [
        "最近有什么聚会活动",
        "王五最近在做什么",
        "上周发生了什么",
        "有人结婚了吗",
    ],
    
    "主题相关查询": [
        "关于工作的讨论",
        "旅行相关的计划",
        "健身锻炼的事情",
        "房子买卖的话题",
    ],
    
    "模糊回忆查询": [
        "有人生病了",
        "谁去了医院",
        "好像有人失业了",
        "记得有人过生日",
    ],
    
    "时间相关查询": [
        "今天发生了什么",
        "最近的新闻",
        "昨天谁联系了我",
        "下周有什么安排",
    ],
    
    "地点相关查询": [
        "北京发生了什么事",
        "在运城的活动",
        "去西安的计划",
        "谁在上海",
    ],
    
    "情感关联查询": [
        "有什么开心的事",
        "谁遇到困难了",
        "吵架的事情",
        "表达感谢的对话",
    ]
}

print("\n" + "=" * 80)
print("开始测试")
print("=" * 80)

# 收集所有查询
all_queries = []
query_categories = []
for category, queries in test_cases.items():
    all_queries.extend(queries)
    query_categories.extend([category] * len(queries))

print(f"\n总测试用例数: {len(all_queries)}")
print(f"测试维度: {len(test_cases)} 个")

# 批量生成查询embeddings
print("\n生成查询embeddings...")
query_embeddings_response = model.get_embeddings(all_queries)
query_embeddings = [e.values for e in query_embeddings_response]
query_array = np.array(query_embeddings).astype('float32')
print("✓ 完成")

# 执行搜索
k = 5  # 返回top-5
print(f"\n执行搜索（Top-{k}）...\n")

results = []
for i, (query, category) in enumerate(zip(all_queries, query_categories)):
    distances, indices = index.search(query_array[i:i+1], k)
    
    retrieved = []
    for dist, idx in zip(distances[0], indices[0]):
        result = records[idx]
        retrieved.append({
            'text': result['text'],
            'type': result['type'],
            'distance': float(dist),
            'metadata': result.get('metadata', {})
        })
    
    results.append({
        'category': category,
        'query': query,
        'results': retrieved
    })

# 输出结果
for category in test_cases.keys():
    print("\n" + "=" * 80)
    print(f"【{category}】")
    print("=" * 80)
    
    category_results = [r for r in results if r['category'] == category]
    
    for item in category_results:
        print(f"\n查询: \"{item['query']}\"")
        print("-" * 80)
        
        for rank, res in enumerate(item['results'], 1):
            text = res['text']
            if len(text) > 100:
                text = text[:100] + "..."
            
            print(f"{rank}. [{res['type']}] [距离:{res['distance']:.3f}] {text}")
        
        print()

# 保存结果到JSON
output_file = 'search_test_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
print(f"\n详细结果已保存到: {output_file}")

# 简单统计
print("\n基础统计:")
print(f"  总查询数: {len(results)}")
print(f"  测试维度: {len(test_cases)} 个")
print(f"  每次召回: Top-{k}")
print(f"  总召回记录数: {len(results) * k}")

# 类型分布
type_counts = {}
for item in results:
    for res in item['results']:
        t = res['type']
        type_counts[t] = type_counts.get(t, 0) + 1

print(f"\n召回类型分布:")
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    percentage = count / (len(results) * k) * 100
    print(f"  {t}: {count} ({percentage:.1f}%)")

# 距离分析
all_distances = []
for item in results:
    for res in item['results']:
        all_distances.append(res['distance'])

print(f"\n距离分析:")
print(f"  最小距离: {min(all_distances):.3f}")
print(f"  最大距离: {max(all_distances):.3f}")
print(f"  平均距离: {np.mean(all_distances):.3f}")
print(f"  中位数距离: {np.median(all_distances):.3f}")

print("\n" + "=" * 80)

