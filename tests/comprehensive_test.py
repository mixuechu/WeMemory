#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试套件 - 微信记忆系统向量检索质量评估

测试范围：
1. Triplet知识图谱检索（扩展版，60+查询）
2. Conversation对话记忆检索（新增，40+查询）
3. 边界情况和难点场景
4. 性能和质量指标统计
"""
import json
import pickle
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
env_file = parent_dir / '.env'
load_dotenv(env_file)

import faiss
import numpy as np

print("=" * 80)
print("全面测试套件 - 微信记忆系统")
print("=" * 80)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# 初始化embedding模型
print("\n[初始化] 加载Embedding模型...")
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

# ============================================================================
# Part 1: Triplet知识图谱测试（扩展版）
# ============================================================================

print("\n" + "=" * 80)
print("Part 1: Triplet知识图谱检索测试")
print("=" * 80)

# 加载索引
print("\n[加载] Triplet向量索引...")
with open('vector_stores/triplets_embeddings.pkl', 'rb') as f:
    triplet_data = pickle.load(f)

triplet_index = faiss.read_index('vector_stores/triplets.faiss')
triplet_records = triplet_data['metadata']
print(f"✓ 加载完成: {len(triplet_records):,} 条记录")

# 扩展测试用例（60+查询，12个维度）
triplet_test_cases = {
    "人物关系查询": [
        "王五和用户是什么关系",
        "用户的家人有谁",
        "赵萌是谁的妻子",
        "小冉敏的配偶是谁",
        "用户的父母是谁",
        "谁是用户的兄弟姐妹",
        "王五的朋友都有谁",
        "王露颖的家庭成员",
    ],

    "人物背景查询": [
        "王五在哪工作",
        "用户在哪个公司",
        "程培晨住在哪里",
        "王露颖的职业是什么",
        "王五的工作状态",
        "谁在北京工作",
        "有谁在国外",
    ],

    "事件查询": [
        "最近有什么聚会活动",
        "王五最近在做什么",
        "上周发生了什么",
        "有人结婚了吗",
        "最近有什么重要的事",
        "谁搬家了",
        "有人换工作了吗",
    ],

    "主题相关查询": [
        "关于工作的讨论",
        "旅行相关的计划",
        "健身锻炼的事情",
        "房子买卖的话题",
        "关于投资理财",
        "学习和进修",
        "创业相关",
    ],

    "模糊回忆查询": [
        "有人生病了",
        "谁去了医院",
        "好像有人失业了",
        "记得有人过生日",
        "谁最近不开心",
        "有人遇到困难",
        "谁在庆祝什么",
    ],

    "时间相关查询": [
        "今天发生了什么",
        "最近的新闻",
        "昨天谁联系了我",
        "下周有什么安排",
        "这个月的重要事件",
        "去年发生了什么",
    ],

    "地点相关查询": [
        "北京发生了什么事",
        "在运城的活动",
        "去西安的计划",
        "谁在上海",
        "国外的朋友",
        "深圳的事情",
    ],

    "情感关联查询": [
        "有什么开心的事",
        "谁遇到困难了",
        "吵架的事情",
        "表达感谢的对话",
        "有人抱怨什么",
        "谁在担心什么",
    ],

    "多条件组合查询": [
        "王五在北京的活动",
        "最近关于工作的讨论",
        "用户和家人的聚会",
        "朋友们的旅行计划",
        "上个月的重要事件",
    ],

    "否定和特殊查询": [
        "谁还没结婚",
        "没有工作的人",
        "从来没去过的地方",
        "很少联系的朋友",
    ],

    "细节和属性查询": [
        "谁的生日是几月几号",
        "王五的具体地址",
        "用户多大了",
        "谁有几个孩子",
        "谁的电话号码",
    ],

    "推理查询": [
        "王五可能认识谁",
        "用户和谁住得近",
        "谁可能会参加聚会",
        "下次活动可能在哪",
    ],
}

print(f"\n总测试查询数: {sum(len(v) for v in triplet_test_cases.values())}")
print(f"测试维度数: {len(triplet_test_cases)}")

# 执行Triplet测试
print("\n执行Triplet搜索测试...")
triplet_results = {}
triplet_start = datetime.now()

for category, queries in triplet_test_cases.items():
    print(f"\n  测试类别: {category} ({len(queries)}个查询)")
    category_results = []

    for query in queries:
        # 生成query embedding
        query_emb_response = model.get_embeddings([query])
        query_emb = query_emb_response[0].values
        query_vector = np.array([query_emb]).astype('float32')

        # 搜索Top-5
        distances, indices = triplet_index.search(query_vector, 5)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(triplet_records):
                record = triplet_records[idx]
                results.append({
                    'text': record['searchable_text'],
                    'type': record['type'],
                    'distance': float(dist),
                    'metadata': {k: v for k, v in record.items() if k not in ['searchable_text', 'type', 'enhanced_text']}
                })

        category_results.append({
            'query': query,
            'results': results
        })

    triplet_results[category] = category_results

triplet_elapsed = (datetime.now() - triplet_start).total_seconds()
print(f"\n✓ Triplet测试完成，耗时: {triplet_elapsed:.2f}秒")

# ============================================================================
# Part 2: Conversation对话记忆测试（新增）
# ============================================================================

print("\n" + "=" * 80)
print("Part 2: Conversation对话记忆检索测试")
print("=" * 80)

# 加载conversation embeddings
print("\n[加载] Conversation向量索引...")
with open('vector_stores/conversations_curated.pkl', 'rb') as f:
    conv_data = pickle.load(f)

conv_metadata = conv_data['metadata']
conv_content_embeddings = np.array(conv_data['content_embeddings']).astype('float32')
conv_context_embeddings = np.array(conv_data['context_embeddings']).astype('float32')

# 构建content索引（主要用content embedding搜索）
conv_index = faiss.IndexFlatL2(768)
conv_index.add(conv_content_embeddings)

print(f"✓ 加载完成: {len(conv_metadata):,} 条对话session")

# Conversation测试用例（40+查询，8个维度）
conversation_test_cases = {
    "对话内容回忆": [
        "我们聊过什么",
        "王五说了什么有趣的事",
        "用户分享的故事",
        "最近讨论的话题",
        "谁提到了工作",
        "关于旅行的对话",
    ],

    "人物提及查询": [
        "谁在对话中被提到",
        "王五在聊天中说了什么",
        "用户的消息",
        "程培晨发了什么",
        "提到家人的对话",
    ],

    "时间线查询": [
        "今天的聊天记录",
        "昨天聊了什么",
        "上周的对话",
        "最近一个月的消息",
        "很久以前的聊天",
    ],

    "主题对话": [
        "关于工作的聊天",
        "讨论旅行的对话",
        "聊美食的消息",
        "技术讨论",
        "八卦聊天",
    ],

    "情感对话": [
        "开心的聊天",
        "抱怨的消息",
        "安慰的对话",
        "祝福的话",
        "吐槽",
    ],

    "特定场景": [
        "群聊记录",
        "私聊消息",
        "语音通话后的文字",
        "分享链接的对话",
        "发红包的聊天",
    ],

    "问答查询": [
        "有人问过什么问题",
        "我回答了什么",
        "谁给了建议",
        "求助的消息",
    ],

    "活跃度查询": [
        "最活跃的对话",
        "最长的聊天",
        "最近常聊的人",
        "很少联系的人",
    ],
}

print(f"\n总测试查询数: {sum(len(v) for v in conversation_test_cases.values())}")
print(f"测试维度数: {len(conversation_test_cases)}")

# 执行Conversation测试
print("\n执行Conversation搜索测试...")
conversation_results = {}
conversation_start = datetime.now()

for category, queries in conversation_test_cases.items():
    print(f"\n  测试类别: {category} ({len(queries)}个查询)")
    category_results = []

    for query in queries:
        # 生成query embedding
        query_emb_response = model.get_embeddings([query])
        query_emb = query_emb_response[0].values
        query_vector = np.array([query_emb]).astype('float32')

        # 搜索Top-5
        distances, indices = conv_index.search(query_vector, 5)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(conv_metadata):
                meta = conv_metadata[idx]
                results.append({
                    'conversation': meta.get('conversation_name', 'unknown'),
                    'content': meta.get('content_text', '')[:200],  # 截取前200字符
                    'distance': float(dist),
                    'message_count': meta.get('message_count', 0),
                    'participants': meta.get('participants', []),
                })

        category_results.append({
            'query': query,
            'results': results
        })

    conversation_results[category] = category_results

conversation_elapsed = (datetime.now() - conversation_start).total_seconds()
print(f"\n✓ Conversation测试完成，耗时: {conversation_elapsed:.2f}秒")

# ============================================================================
# Part 3: 统计分析和质量评估
# ============================================================================

print("\n" + "=" * 80)
print("Part 3: 统计分析和质量评估")
print("=" * 80)

# 统计Triplet结果
print("\n【Triplet检索统计】")
total_triplet_queries = sum(len(v) for v in triplet_results.values())
all_triplet_distances = []
triplet_type_distribution = {'event': 0, 'relationship': 0}

for category_results in triplet_results.values():
    for item in category_results:
        for result in item['results']:
            all_triplet_distances.append(result['distance'])
            triplet_type_distribution[result['type']] = triplet_type_distribution.get(result['type'], 0) + 1

print(f"  总查询数: {total_triplet_queries}")
print(f"  总召回结果: {len(all_triplet_distances)}")
print(f"  平均距离: {np.mean(all_triplet_distances):.4f}")
print(f"  中位数距离: {np.median(all_triplet_distances):.4f}")
print(f"  最小距离: {np.min(all_triplet_distances):.4f}")
print(f"  最大距离: {np.max(all_triplet_distances):.4f}")
print(f"  距离标准差: {np.std(all_triplet_distances):.4f}")
print(f"\n  结果类型分布:")
for type_name, count in triplet_type_distribution.items():
    percentage = count / len(all_triplet_distances) * 100
    print(f"    {type_name}: {count} ({percentage:.1f}%)")

# 统计Conversation结果
print("\n【Conversation检索统计】")
total_conv_queries = sum(len(v) for v in conversation_results.values())
all_conv_distances = []
conv_names = []

for category_results in conversation_results.values():
    for item in category_results:
        for result in item['results']:
            all_conv_distances.append(result['distance'])
            conv_names.append(result['conversation'])

print(f"  总查询数: {total_conv_queries}")
print(f"  总召回结果: {len(all_conv_distances)}")
print(f"  平均距离: {np.mean(all_conv_distances):.4f}")
print(f"  中位数距离: {np.median(all_conv_distances):.4f}")
print(f"  最小距离: {np.min(all_conv_distances):.4f}")
print(f"  最大距离: {np.max(all_conv_distances):.4f}")
print(f"  距离标准差: {np.std(all_conv_distances):.4f}")

# 统计最常被召回的对话
from collections import Counter
top_conversations = Counter(conv_names).most_common(10)
print(f"\n  最常被召回的对话Top10:")
for conv_name, count in top_conversations:
    print(f"    {conv_name}: {count}次")

# 距离分布分析
print("\n【距离分布分析】")
distance_ranges = {
    '0.0-0.3 (极相关)': (0.0, 0.3),
    '0.3-0.5 (相关)': (0.3, 0.5),
    '0.5-0.7 (中等相关)': (0.5, 0.7),
    '0.7-1.0 (弱相关)': (0.7, 1.0),
    '>1.0 (不相关)': (1.0, float('inf')),
}

print("\nTriplet距离分布:")
for range_name, (low, high) in distance_ranges.items():
    count = sum(1 for d in all_triplet_distances if low <= d < high)
    percentage = count / len(all_triplet_distances) * 100
    print(f"  {range_name}: {count} ({percentage:.1f}%)")

print("\nConversation距离分布:")
for range_name, (low, high) in distance_ranges.items():
    count = sum(1 for d in all_conv_distances if low <= d < high)
    percentage = count / len(all_conv_distances) * 100
    print(f"  {range_name}: {count} ({percentage:.1f}%)")

# ============================================================================
# Part 4: 保存详细结果
# ============================================================================

print("\n" + "=" * 80)
print("保存测试结果")
print("=" * 80)

# 保存完整结果
full_results = {
    'test_info': {
        'test_time': datetime.now().isoformat(),
        'model': 'text-multilingual-embedding-002',
        'triplet_records': len(triplet_records),
        'conversation_sessions': len(conv_metadata),
    },
    'triplet_tests': {
        'test_cases': triplet_test_cases,
        'results': triplet_results,
        'statistics': {
            'total_queries': total_triplet_queries,
            'avg_distance': float(np.mean(all_triplet_distances)),
            'median_distance': float(np.median(all_triplet_distances)),
            'min_distance': float(np.min(all_triplet_distances)),
            'max_distance': float(np.max(all_triplet_distances)),
            'std_distance': float(np.std(all_triplet_distances)),
            'type_distribution': triplet_type_distribution,
        }
    },
    'conversation_tests': {
        'test_cases': conversation_test_cases,
        'results': conversation_results,
        'statistics': {
            'total_queries': total_conv_queries,
            'avg_distance': float(np.mean(all_conv_distances)),
            'median_distance': float(np.median(all_conv_distances)),
            'min_distance': float(np.min(all_conv_distances)),
            'max_distance': float(np.max(all_conv_distances)),
            'std_distance': float(np.std(all_conv_distances)),
            'top_conversations': top_conversations,
        }
    },
    'performance': {
        'triplet_elapsed': triplet_elapsed,
        'conversation_elapsed': conversation_elapsed,
        'total_elapsed': triplet_elapsed + conversation_elapsed,
    }
}

output_file = Path('comprehensive_test_results.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(full_results, f, ensure_ascii=False, indent=2)

print(f"\n✓ 完整结果已保存: {output_file}")
print(f"  文件大小: {output_file.stat().st_size / 1024:.2f} KB")

# 保存简要报告
report_lines = [
    "=" * 80,
    "微信记忆系统 - 全面测试报告",
    "=" * 80,
    f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"测试模型: text-multilingual-embedding-002",
    "",
    "【数据规模】",
    f"  Triplet记录数: {len(triplet_records):,}",
    f"  Conversation sessions: {len(conv_metadata):,}",
    "",
    "【测试规模】",
    f"  Triplet查询数: {total_triplet_queries}",
    f"  Conversation查询数: {total_conv_queries}",
    f"  总查询数: {total_triplet_queries + total_conv_queries}",
    "",
    "【Triplet检索质量】",
    f"  平均距离: {np.mean(all_triplet_distances):.4f}",
    f"  中位数距离: {np.median(all_triplet_distances):.4f}",
    f"  距离范围: {np.min(all_triplet_distances):.4f} - {np.max(all_triplet_distances):.4f}",
    "",
    "【Conversation检索质量】",
    f"  平均距离: {np.mean(all_conv_distances):.4f}",
    f"  中位数距离: {np.median(all_conv_distances):.4f}",
    f"  距离范围: {np.min(all_conv_distances):.4f} - {np.max(all_conv_distances):.4f}",
    "",
    "【性能指标】",
    f"  Triplet测试耗时: {triplet_elapsed:.2f}秒",
    f"  Conversation测试耗时: {conversation_elapsed:.2f}秒",
    f"  总耗时: {triplet_elapsed + conversation_elapsed:.2f}秒",
    f"  平均查询速度: {(total_triplet_queries + total_conv_queries) / (triplet_elapsed + conversation_elapsed):.2f} queries/sec",
    "",
    "=" * 80,
]

report_file = Path('test_report.txt')
with open(report_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print(f"✓ 简要报告已保存: {report_file}")

print("\n" + "=" * 80)
print("✅ 全面测试完成！")
print("=" * 80)
print(f"\n总测试用例: {total_triplet_queries + total_conv_queries}个查询")
print(f"总耗时: {triplet_elapsed + conversation_elapsed:.2f}秒")
print(f"\n详细结果: {output_file}")
print(f"简要报告: {report_file}")
print("=" * 80)
