#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为自然语言三元组生成embeddings并构建FAISS索引

使用 text-multilingual-embedding-002 模型（768维，多语言优化，中文区分度极佳）
"""
import json
import pickle
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载.env
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
load_dotenv(env_file)

from google.oauth2 import service_account
import vertexai
from vertexai.language_models import TextEmbeddingModel
import numpy as np

print("=" * 80)
print("自然语言三元组 - Embedding生成器（多语言模型版）")
print("=" * 80)

# 初始化Vertex AI
PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 1. 加载数据
print("\n[1/5] 加载自然语言三元组数据...")
input_file = project_root / 'data/knowledge_graph/triplets.json'

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
print("\n[2/5] 提取文本用于向量化...")
texts = []
for record in records:
    # 优先使用searchable_text，如果没有则用text
    text = record.get('searchable_text', record.get('text', ''))
    texts.append(text)

print(f"✓ 提取完成: {len(texts)} 个文本")

# 统计文本长度
avg_len = sum(len(t) for t in texts) / len(texts)
max_len = max(len(t) for t in texts)
print(f"  - 平均长度: {avg_len:.1f} 字符")
print(f"  - 最大长度: {max_len} 字符")

# 3. 初始化多语言Embedding模型
print("\n[3/5] 初始化多语言Embedding模型...")
MODEL_NAME = "text-multilingual-embedding-002"
print(f"  - 模型: {MODEL_NAME}")
print(f"  - 维度: 768")
print(f"  - 优势: 中文优化，短文本区分度极佳")

model = TextEmbeddingModel.from_pretrained(MODEL_NAME)
print("✓ 模型初始化成功")

# 4. 生成embeddings
print("\n[4/5] 批量生成embeddings...")
print(f"  - 批次大小: 250 (API限制)")

start_time = datetime.now()

# 批量处理
batch_size = 250
all_embeddings = []

for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    try:
        embeddings_response = model.get_embeddings(batch)
        batch_embeddings = [emb.values for emb in embeddings_response]
        all_embeddings.extend(batch_embeddings)

        if (i // batch_size + 1) % 5 == 0:
            print(f"  进度: {i+len(batch)}/{len(texts)}")
    except Exception as e:
        print(f"  ✗ Batch {i//batch_size + 1} 失败: {e}")
        # 返回零向量作为fallback
        all_embeddings.extend([[0.0] * 768 for _ in batch])

print(f"✓ Embedding生成完成")

# 验证
embeddings_array = np.array(all_embeddings)
print(f"  - 形状: {embeddings_array.shape}")
print(f"  - 数据类型: {embeddings_array.dtype}")

# 检查零向量
zero_vectors = np.sum(np.all(embeddings_array == 0, axis=1))
if zero_vectors > 0:
    print(f"  ⚠ 警告: {zero_vectors} 个零向量（API失败）")

elapsed = (datetime.now() - start_time).total_seconds()
print(f"  - 耗时: {elapsed:.1f} 秒")
print(f"  - 速度: {len(texts)/elapsed:.1f} 条/秒")

# 5. 构建FAISS索引
print("\n[5/5] 构建FAISS索引...")

try:
    import faiss

    # 使用IndexFlatL2（精确搜索）
    dimension = 768
    index = faiss.IndexFlatL2(dimension)

    # 添加向量
    index.add(embeddings_array.astype('float32'))

    print(f"✓ FAISS索引构建完成")
    print(f"  - 索引类型: IndexFlatL2 (精确搜索)")
    print(f"  - 向量数量: {index.ntotal}")
    print(f"  - 向量维度: {dimension}")

except ImportError:
    print("✗ FAISS未安装，跳过索引构建")
    index = None

# 6. 保存结果
print("\n" + "=" * 80)
print("保存结果")
print("=" * 80)

output_dir = project_root / 'vector_stores/triplets'
output_dir.mkdir(parents=True, exist_ok=True)

# 备份旧文件
old_pkl = output_dir / 'embeddings.pkl'
old_faiss = output_dir / 'index.faiss'

if old_pkl.exists():
    backup_pkl = output_dir / f'embeddings_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl'
    old_pkl.rename(backup_pkl)
    print(f"备份旧embeddings: {backup_pkl.name}")

if old_faiss.exists():
    backup_faiss = output_dir / f'index_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.faiss'
    old_faiss.rename(backup_faiss)
    print(f"备份旧索引: {backup_faiss.name}")

# 保存为pickle格式
output_data = {
    'embeddings': all_embeddings,
    'metadata': records,
    'info': {
        'model': MODEL_NAME,
        'dimension': 768,
        'total_records': len(records),
        'events': len(events),
        'relationships': len(relationships),
        'created_at': datetime.now().isoformat(),
        'source_file': str(input_file)
    }
}

pkl_file = output_dir / 'embeddings.pkl'
with open(pkl_file, 'wb') as f:
    pickle.dump(output_data, f)

file_size = pkl_file.stat().st_size / (1024 * 1024)
print(f"\n✓ Embeddings已保存:")
print(f"  文件: {pkl_file}")
print(f"  大小: {file_size:.2f} MB")

# 保存FAISS索引
if index is not None:
    faiss_file = output_dir / 'index.faiss'
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

    # 测试查询
    test_queries = [
        "赵萌是谁",
        "米雪川的老婆是谁",
        "米雪川的家人有谁"
    ]

    print("\n生成测试查询的embeddings...")
    query_embeddings_response = model.get_embeddings(test_queries)
    query_embeddings = [e.values for e in query_embeddings_response]
    query_array = np.array(query_embeddings).astype('float32')

    k = 3  # 返回top-3

    for i, query in enumerate(test_queries):
        print(f"\n【测试 {i+1}】查询: \"{query}\"")

        # 搜索
        distances, indices = index.search(query_array[i:i+1], k)

        print(f"Top-{k} 结果:")
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), 1):
            result = records[idx]
            text = result['text'][:80]
            result_type = result.get('type', 'unknown')
            print(f"  {rank}. [{result_type}] [距离: {dist:.3f}] {text}...")

print("\n" + "=" * 80)
print("✅ 全部完成！")
print("=" * 80)

print(f"\n数据统计:")
print(f"  - 总记录: {len(records)}")
print(f"  - 事件: {len(events)}")
print(f"  - 关系: {len(relationships)} (核心关系，手动审核)")

print(f"\n使用的模型: {MODEL_NAME}")
print("优势: 专为多语言优化，中文短文本区分度极佳")

print("\n下一步: 重启后端API服务")
print("  kill <backend_pid> && python3 api/main.py &")

print("\n" + "=" * 80)
