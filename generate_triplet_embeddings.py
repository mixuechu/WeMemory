#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为自然语言三元组生成embeddings并构建FAISS索引

使用Google Vertex AI text-embedding-004模型（768维）
"""
import json
import pickle
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加父目录到Python路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from embedding.client import GoogleEmbeddingClient

print("=" * 80)
print("自然语言三元组 - Embedding生成器")
print("=" * 80)

# 1. 加载数据
print("\n[1/5] 加载自然语言三元组数据...")
input_file = 'natural_language_triplets_with_aliases.json'

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
print(f"✓ 加载完成: {len(records)} 条记录")

# 统计
events = [r for r in records if r['type'] == 'event']
relationships = [r for r in records if r['type'] == 'relationship']
print(f"  - 事件描述: {len(events)}")
print(f"  - 关系三元组: {len(relationships)}")

# 2. 提取文本
print("\n[2/5] 提取searchable_text用于向量化...")
texts = []
for record in records:
    text = record.get('searchable_text', record.get('text', ''))
    texts.append(text)

print(f"✓ 提取完成: {len(texts)} 个文本")

# 统计文本长度
avg_len = sum(len(t) for t in texts) / len(texts)
max_len = max(len(t) for t in texts)
print(f"  - 平均长度: {avg_len:.1f} 字符")
print(f"  - 最大长度: {max_len} 字符")

# 3. 初始化Embedding客户端
print("\n[3/5] 初始化Google Vertex AI Embedding客户端...")
try:
    client = GoogleEmbeddingClient()
    print("✓ 客户端初始化成功")
except Exception as e:
    print(f"✗ 初始化失败: {e}")
    print("\n请检查.env文件中的Google Cloud配置:")
    print("  - VITE_GOOGLE_CLOUD_PROJECT")
    print("  - VITE_GOOGLE_CLOUD_LOCATION")
    print("  - VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")
    sys.exit(1)

# 4. 生成embeddings
print("\n[4/5] 批量生成embeddings...")
print(f"  - 模型: text-embedding-004")
print(f"  - 维度: 768")
print(f"  - 批次大小: 250 (Google API限制)")

start_time = datetime.now()

try:
    embeddings = client.get_embeddings(texts)
    print(f"✓ Embedding生成完成")
    
    # 验证
    import numpy as np
    embeddings_array = np.array(embeddings)
    print(f"  - 形状: {embeddings_array.shape}")
    print(f"  - 数据类型: {embeddings_array.dtype}")
    
    # 检查零向量
    zero_vectors = np.sum(np.all(embeddings_array == 0, axis=1))
    if zero_vectors > 0:
        print(f"  ⚠ 警告: {zero_vectors} 个零向量（API失败）")
    
except Exception as e:
    print(f"✗ Embedding生成失败: {e}")
    sys.exit(1)

elapsed = (datetime.now() - start_time).total_seconds()
print(f"  - 耗时: {elapsed:.1f} 秒")
print(f"  - 速度: {len(texts)/elapsed:.1f} 条/秒")

# 5. 构建FAISS索引
print("\n[5/5] 构建FAISS索引...")

try:
    import faiss
    
    # 使用IndexFlatL2（精确搜索，数据量不大适合）
    dimension = 768
    index = faiss.IndexFlatL2(dimension)
    
    # 添加向量
    index.add(embeddings_array)
    
    print(f"✓ FAISS索引构建完成")
    print(f"  - 索引类型: IndexFlatL2 (精确搜索)")
    print(f"  - 向量数量: {index.ntotal}")
    print(f"  - 向量维度: {dimension}")
    
except ImportError:
    print("✗ FAISS未安装，跳过索引构建")
    print("  安装命令: pip install faiss-cpu")
    index = None

# 6. 保存结果
print("\n" + "=" * 80)
print("保存结果")
print("=" * 80)

output_dir = Path('vector_stores')
output_dir.mkdir(exist_ok=True)

# 保存为pickle格式（与现有系统一致）
output_data = {
    'embeddings': embeddings,
    'metadata': records,  # 保存完整记录作为metadata
    'info': {
        'model': 'text-embedding-004',
        'dimension': 768,
        'total_records': len(records),
        'events': len(events),
        'relationships': len(relationships),
        'created_at': datetime.now().isoformat(),
        'source_file': input_file
    }
}

pkl_file = output_dir / 'triplets_embeddings.pkl'
with open(pkl_file, 'wb') as f:
    pickle.dump(output_data, f)

file_size = pkl_file.stat().st_size / (1024 * 1024)
print(f"\n✓ Embeddings已保存:")
print(f"  文件: {pkl_file}")
print(f"  大小: {file_size:.2f} MB")

# 保存FAISS索引
if index is not None:
    faiss_file = output_dir / 'triplets.faiss'
    faiss.write_index(index, str(faiss_file))
    
    index_size = faiss_file.stat().st_size / (1024 * 1024)
    print(f"\n✓ FAISS索引已保存:")
    print(f"  文件: {faiss_file}")
    print(f"  大小: {index_size:.2f} MB")

# 7. 测试搜索
if index is not None:
    print("\n" + "=" * 80)
    print("测试搜索功能")
    print("=" * 80)
    
    # 随机选3个查询测试
    test_queries = [
        "Jake最近在做什么",
        "米雪川的家人有谁",
        "最近有什么聚会活动"
    ]
    
    print("\n生成测试查询的embeddings...")
    query_embeddings = client.get_embeddings(test_queries)
    query_array = np.array(query_embeddings)
    
    k = 3  # 返回top-3
    
    for i, query in enumerate(test_queries):
        print(f"\n【测试 {i+1}】查询: \"{query}\"")
        
        # 搜索
        distances, indices = index.search(query_array[i:i+1], k)
        
        print(f"Top-{k} 结果:")
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), 1):
            result = records[idx]
            text = result['text'][:80]
            print(f"  {rank}. [距离: {dist:.3f}] {text}...")

print("\n" + "=" * 80)
print("✅ 全部完成！")
print("=" * 80)

print("\n使用方法:")
print("""
import pickle
import faiss
import numpy as np
from embedding.client import GoogleEmbeddingClient

# 1. 加载索引
with open('vector_stores/triplets_embeddings.pkl', 'rb') as f:
    data = pickle.load(f)
    
index = faiss.read_index('vector_stores/triplets.faiss')
records = data['metadata']

# 2. 搜索
client = GoogleEmbeddingClient()
query = "你的查询"
query_emb = client.get_embeddings([query])[0]

distances, indices = index.search(np.array([query_emb]), k=5)

# 3. 获取结果
for idx in indices[0]:
    print(records[idx]['text'])
""")

print("\n" + "=" * 80)

