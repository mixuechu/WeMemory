#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最优配置：对比不同的分片和并行策略
- 测试对象：YUAN对话（509条消息）
- 测试维度：效率（时间、API调用）+ 质量（实体数、关系数）
"""

import os
import sys
import io
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv(dotenv_path='../.env')

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# Gemini配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

MODEL_NAME = "gemini-2.5-flash"

# 测试配置组合
TEST_CONFIGS = [
    {
        'name': '配置1-保守',
        'time_gap_minutes': 30,
        'min_messages': 5,
        'max_messages': 100,
        'parallel_workers': 5
    },
    {
        'name': '配置2-中等',
        'time_gap_minutes': 60,
        'min_messages': 10,
        'max_messages': 200,
        'parallel_workers': 10
    },
    {
        'name': '配置3-激进',
        'time_gap_minutes': 90,
        'min_messages': 15,
        'max_messages': 300,
        'parallel_workers': 15
    },
    {
        'name': '配置4-极限',
        'time_gap_minutes': 120,
        'min_messages': 20,
        'max_messages': 500,
        'parallel_workers': 20
    }
]

EXTRACTION_PROMPT = """你是一个知识图谱构建专家。请从以下微信对话中提取完整的结构化信息。

## 对话信息

对话名称: {conversation_name}
消息时间范围: {time_range}
消息数量: {message_count}

## 对话内容

{conversation_text}

---

## 提取要求

请提取以下实体和关系，以JSON格式返回：

```json
{{
  "people": [
    {{
      "name": "正式姓名",
      "is_user": false,
      "aliases": ["别名1"],
      "confidence": 0.9
    }}
  ],
  "events": [
    {{
      "name": "事件名称",
      "type": "事件类型",
      "participants": ["人名1", "人名2"],
      "description": "事件描述",
      "confidence": 0.9
    }}
  ],
  "relationships": [
    {{
      "type": "KNOWS/PARTICIPATED_IN/DISCUSSED_WITH",
      "source": "源实体名",
      "target": "目标实体名",
      "source_type": "Person",
      "target_type": "Person/Event",
      "confidence": 0.9
    }}
  ]
}}
```

**重要规则**:
1. 不要提取"某人"、"他"、"她"等泛指词
2. Event必须包含participants字段
3. 每个Event的participants都必须在relationships中创建PARTICIPATED_IN关系
4. 只返回JSON，不要其他内容
"""


def smart_split_messages(messages: List, time_gap_minutes: int, min_messages: int, max_messages: int) -> List[List]:
    """智能分片"""
    batches = []
    current_batch = []
    time_gap = timedelta(minutes=time_gap_minutes)

    for msg in messages:
        if msg.get('type') != 0:
            continue

        content = msg.get('content', '').strip()
        if not content:
            continue

        should_split = False

        if current_batch:
            last_ts = current_batch[-1].get('timestamp', 0)
            curr_ts = msg.get('timestamp', 0)
            time_diff = datetime.fromtimestamp(curr_ts) - datetime.fromtimestamp(last_ts)

            if time_diff > time_gap or len(current_batch) >= max_messages:
                should_split = True

        if should_split and len(current_batch) >= min_messages:
            batches.append(current_batch)
            current_batch = []

        current_batch.append(msg)

    if len(current_batch) >= min_messages:
        batches.append(current_batch)

    return batches


def extract_batch(batch_msgs: List, batch_id: str, conv_name: str) -> Dict:
    """提取单个批次"""
    model = GenerativeModel(MODEL_NAME)

    # 构建对话文本
    conversation_text = "\n".join([
        f"{msg.get('accountName', 'Unknown')}: {msg.get('content', '')}"
        for msg in batch_msgs
    ])

    # 时间范围
    timestamps = [msg.get('timestamp', 0) for msg in batch_msgs if msg.get('timestamp')]
    if timestamps:
        start_time = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M')
        end_time = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M')
        time_range = f"{start_time} ~ {end_time}"
    else:
        time_range = "Unknown"

    prompt = EXTRACTION_PROMPT.format(
        conversation_name=conv_name,
        time_range=time_range,
        message_count=len(batch_msgs),
        conversation_text=conversation_text
    )

    start_time = time.time()
    response = model.generate_content(prompt)
    api_time = time.time() - start_time

    result_text = response.text.strip()

    # 提取JSON
    if '```json' in result_text:
        result_text = result_text.split('```json')[1].split('```')[0].strip()
    elif '```' in result_text:
        result_text = result_text.split('```')[1].split('```')[0].strip()

    entities = json.loads(result_text)

    return {
        'batch_id': batch_id,
        'entities': entities,
        'api_time': api_time,
        'message_count': len(batch_msgs)
    }


def test_config(config: Dict, conv_data: Dict, output_dir: Path) -> Dict:
    """测试单个配置"""
    print(f"\n{'='*80}")
    print(f"测试配置: {config['name']}")
    print(f"  - 时间间隔: {config['time_gap_minutes']}分钟")
    print(f"  - 消息范围: {config['min_messages']}-{config['max_messages']}条")
    print(f"  - 并行度: {config['parallel_workers']}")
    print(f"{'='*80}")

    conv_name = conv_data['meta']['name']
    messages = conv_data['messages']

    # 1. 分片
    print("\n[1] 分片中...")
    batches = smart_split_messages(
        messages,
        config['time_gap_minutes'],
        config['min_messages'],
        config['max_messages']
    )

    batch_count = len(batches)
    avg_batch_size = sum(len(b) for b in batches) / batch_count if batch_count > 0 else 0

    print(f"  - 总批次: {batch_count}")
    print(f"  - 平均批次大小: {avg_batch_size:.1f}条")

    # 2. 提取
    print("\n[2] 提取中...")
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=config['parallel_workers']) as executor:
        futures = []
        for idx, batch_msgs in enumerate(batches):
            batch_id = hashlib.md5(json.dumps(batch_msgs, ensure_ascii=False).encode()).hexdigest()[:16]
            future = executor.submit(extract_batch, batch_msgs, batch_id, conv_name)
            futures.append(future)

        for idx, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                results.append(result)
                if idx % 5 == 0 or idx == len(futures):
                    print(f"  进度: {idx}/{len(futures)}")
            except Exception as e:
                print(f"  ❌ 批次失败: {e}")

    total_time = time.time() - start_time

    # 3. 统计
    total_people = sum(len(r['entities'].get('people', [])) for r in results)
    total_events = sum(len(r['entities'].get('events', [])) for r in results)
    total_relationships = sum(len(r['entities'].get('relationships', [])) for r in results)
    participated_in = sum(
        len([rel for rel in r['entities'].get('relationships', []) if rel.get('type') == 'PARTICIPATED_IN'])
        for r in results
    )
    avg_api_time = sum(r['api_time'] for r in results) / len(results) if results else 0

    # 4. 保存结果
    config_output = output_dir / f"test_{config['name'].replace('-', '_')}.json"
    with open(config_output, 'w', encoding='utf-8') as f:
        json.dump({
            'config': config,
            'stats': {
                'batch_count': batch_count,
                'avg_batch_size': avg_batch_size,
                'total_time': total_time,
                'avg_api_time': avg_api_time,
                'total_people': total_people,
                'total_events': total_events,
                'total_relationships': total_relationships,
                'participated_in_relationships': participated_in
            },
            'results': results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n[3] 结果统计:")
    print(f"  - 总耗时: {total_time:.1f}秒")
    print(f"  - 平均API耗时: {avg_api_time:.2f}秒/批")
    print(f"  - 总People: {total_people}")
    print(f"  - 总Event: {total_events}")
    print(f"  - 总关系: {total_relationships}")
    print(f"  - PARTICIPATED_IN: {participated_in}")
    print(f"  - 结果文件: {config_output}")

    return {
        'config_name': config['name'],
        'batch_count': batch_count,
        'avg_batch_size': avg_batch_size,
        'total_time': total_time,
        'avg_api_time': avg_api_time,
        'total_people': total_people,
        'total_events': total_events,
        'total_relationships': total_relationships,
        'participated_in': participated_in
    }


def main():
    """主函数"""
    print("="*80)
    print("最优配置测试")
    print("="*80)

    # 加载YUAN对话
    yuan_file = Path("../chat_data_filtered/YUAN/YUAN.json")
    if not yuan_file.exists():
        print(f"❌ 文件不存在: {yuan_file}")
        return

    with open(yuan_file, 'r', encoding='utf-8') as f:
        conv_data = json.load(f)

    print(f"\n测试对话: {conv_data['meta']['name']}")
    print(f"消息数: {len(conv_data['messages'])}")

    # 创建输出目录
    output_dir = Path("test_config_results")
    output_dir.mkdir(exist_ok=True)

    # 测试所有配置
    all_results = []
    for config in TEST_CONFIGS:
        try:
            result = test_config(config, conv_data, output_dir)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ 配置 {config['name']} 失败: {e}")
            import traceback
            traceback.print_exc()

    # 对比总结
    print("\n" + "="*80)
    print("对比总结")
    print("="*80)

    print(f"\n{'配置':<15} {'批次':<8} {'平均批次':<10} {'耗时':<10} {'API时间':<10} {'People':<8} {'Events':<8} {'关系':<8} {'P_IN':<8}")
    print("-"*100)

    for r in all_results:
        print(f"{r['config_name']:<15} "
              f"{r['batch_count']:<8} "
              f"{r['avg_batch_size']:<10.1f} "
              f"{r['total_time']:<10.1f} "
              f"{r['avg_api_time']:<10.2f} "
              f"{r['total_people']:<8} "
              f"{r['total_events']:<8} "
              f"{r['total_relationships']:<8} "
              f"{r['participated_in']:<8}")

    print("\n建议:")
    print("  1. 查看各配置的提取质量（People、Events数量是否合理）")
    print("  2. 对比PARTICIPATED_IN关系数（应该等于Events的参与者总数）")
    print("  3. 权衡效率（批次数、耗时）和质量")
    print(f"\n详细结果保存在: {output_dir}/")


if __name__ == '__main__':
    main()
