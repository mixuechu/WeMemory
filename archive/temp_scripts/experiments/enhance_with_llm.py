#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可选：用LLM增强部分三元组和事件描述

使用场景：
1. 规则生成的效果不够好
2. 需要更自然的表达
3. 想融入更多context信息
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# 初始化Gemini
PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

MODEL_NAME = "gemini-2.5-flash-002"
model = GenerativeModel(MODEL_NAME)

print(f"✓ Gemini客户端已初始化 ({MODEL_NAME})")

def enhance_relationship(record):
    """用LLM增强关系三元组描述"""

    metadata = record['metadata']
    subject = metadata['subject']
    relation_type = metadata['relation_type']
    obj = metadata['object']
    context = metadata.get('context', '')

    prompt = f"""将以下关系转换为一句自然、简洁的中文描述。

关系信息：
- 主体：{subject}
- 关系类型：{relation_type}
- 对象：{obj}
{f"- 上下文：{context[:200]}" if context else ""}

要求：
1. 生成一句话，简洁明了
2. 如果有上下文，可以适当融入关键信息
3. 不要添加额外信息或猜测
4. 保持客观，不添加主观评价

只输出这一句话，不要其他内容。
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 200,
            }
        )

        enhanced_text = response.text.strip()
        return enhanced_text

    except Exception as e:
        print(f"  ✗ 增强失败: {e}")
        return record['text']  # 失败则返回原文

def enhance_event(record):
    """用LLM增强事件描述"""

    metadata = record['metadata']
    event_name = metadata.get('event_name', '')
    event_type = metadata.get('event_type', '')
    time_desc = metadata.get('time_description', '')
    participants = metadata.get('participants', [])

    # 获取原始描述（从text中提取）
    original_text = record['text']

    prompt = f"""将以下事件信息转换为一句自然、流畅的中文描述。

事件信息：
- 事件名称：{event_name}
- 事件类型：{event_type}
- 时间：{time_desc}
- 参与者：{', '.join(participants)}
- 原始描述：{original_text}

要求：
1. 生成一句话描述，融合时间、人物、事件
2. 语言自然流畅，符合口语表达
3. 保持事实准确，不添加细节
4. 如果时间明确，放在句首

只输出这一句话，不要其他内容。
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 300,
            }
        )

        enhanced_text = response.text.strip()
        return enhanced_text

    except Exception as e:
        print(f"  ✗ 增强失败: {e}")
        return record['text']

def enhance_records(input_file, output_file,
                   enhance_relations=True,
                   enhance_events=False,
                   max_records=None):
    """
    增强记录

    参数：
    - enhance_relations: 是否增强关系三元组
    - enhance_events: 是否增强事件描述（更慢，成本更高）
    - max_records: 最多增强多少条（用于测试）
    """

    print("=" * 80)
    print("LLM增强三元组")
    print("=" * 80)

    # 加载数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data['records']

    # 筛选需要增强的记录
    to_enhance = []

    if enhance_relations:
        relation_records = [r for r in records if r['type'] == 'relationship']
        to_enhance.extend(relation_records[:max_records] if max_records else relation_records)
        print(f"\n计划增强关系三元组: {len(relation_records)} 条")

    if enhance_events:
        event_records = [r for r in records if r['type'] == 'event']
        to_enhance.extend(event_records[:max_records] if max_records else event_records)
        print(f"计划增强事件描述: {len(event_records)} 条")

    if max_records:
        to_enhance = to_enhance[:max_records]
        print(f"\n测试模式：只增强前 {max_records} 条")

    print(f"\n总计需要增强: {len(to_enhance)} 条")
    print(f"预计耗时: {len(to_enhance) * 1.5 / 60:.1f} 分钟")
    print(f"预计成本: ~${len(to_enhance) * 0.0005:.2f} USD")

    # 确认
    confirm = input("\n是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消")
        return

    # 开始增强
    print("\n开始增强...\n")
    enhanced_count = 0

    for i, record in enumerate(to_enhance):
        print(f"[{i+1}/{len(to_enhance)}] {record['id']}")
        print(f"  原文: {record['text'][:60]}...")

        # 增强
        if record['type'] == 'relationship':
            enhanced_text = enhance_relationship(record)
        else:
            enhanced_text = enhance_event(record)

        # 更新
        if enhanced_text != record['text']:
            record['original_text'] = record['text']  # 保存原文
            record['text'] = enhanced_text
            enhanced_count += 1
            print(f"  增强: {enhanced_text[:60]}...")
        else:
            print(f"  保持原样")

        # 速率限制
        time.sleep(1.5)

    # 更新元数据
    data['metadata']['llm_enhanced'] = True
    data['metadata']['enhancement_stats'] = {
        'enhanced_count': enhanced_count,
        'total_count': len(to_enhance),
        'model': MODEL_NAME
    }

    # 保存
    print(f"\n保存到 {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("✅ 增强完成！")
    print("=" * 80)
    print(f"增强记录数: {enhanced_count}/{len(to_enhance)}")
    print(f"输出文件: {output_file}")

if __name__ == '__main__':
    # 示例用法

    # 测试模式：只增强前10条关系
    print("测试模式：只增强前10条关系三元组\n")
    enhance_records(
        input_file='natural_language_triplets.json',
        output_file='natural_language_triplets_enhanced_test.json',
        enhance_relations=True,
        enhance_events=False,
        max_records=10
    )

    # 完整模式（注释掉，需要时取消注释）
    """
    enhance_records(
        input_file='natural_language_triplets.json',
        output_file='natural_language_triplets_enhanced.json',
        enhance_relations=True,  # 增强所有关系
        enhance_events=True,     # 增强所有事件
        max_records=None         # 全部增强
    )
    """
