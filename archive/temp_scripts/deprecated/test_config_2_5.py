#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试配置2.5 - 平衡点（MAX_MESSAGES=100）"""

import os
import sys
import io
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
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

# 配置2.5 - 平衡点
CONFIG = {
    'name': '配置2.5-平衡点',
    'time_gap_minutes': 45,
    'min_messages': 10,
    'max_messages': 100,  # 关键：100条上限
    'parallel_workers': 10
}

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
      "type": "KNOWS/PARTICIPATED_IN/DISCUSSED_WITH/HAS_CHILD/HAS_SPOUSE/HAS_PARENT/HAS_COUSIN",
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
4. **家庭关系必须提取**：HAS_SPOUSE（配偶）, HAS_CHILD（子女）, HAS_PARENT（父母）, HAS_SIBLING（兄弟姐妹）, HAS_COUSIN（表兄弟）
5. 只返回JSON，不要其他内容
"""


def smart_split_messages(messages, time_gap_minutes, min_messages, max_messages):
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


def extract_batch(batch_msgs, batch_id, conv_name):
    """提取单个批次"""
    model = GenerativeModel(MODEL_NAME)

    conversation_text = "\n".join([
        f"{msg.get('accountName', 'Unknown')}: {msg.get('content', '')}"
        for msg in batch_msgs
    ])

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


def main():
    print('='*80)
    print(f'测试配置: {CONFIG["name"]}')
    print(f'  - 时间间隔: {CONFIG["time_gap_minutes"]}分钟')
    print(f'  - 消息范围: {CONFIG["min_messages"]}-{CONFIG["max_messages"]}条')
    print(f'  - 并行度: {CONFIG["parallel_workers"]}')
    print('='*80)

    # 加载YUAN对话
    yuan_file = Path("../chat_data_filtered/YUAN/YUAN.json")
    with open(yuan_file, 'r', encoding='utf-8') as f:
        conv_data = json.load(f)

    conv_name = conv_data['meta']['name']
    messages = conv_data['messages']

    print(f'\n对话: {conv_name}')
    print(f'消息数: {len(messages)}')

    # 分片
    print('\n分片中...')
    batches = smart_split_messages(
        messages,
        CONFIG['time_gap_minutes'],
        CONFIG['min_messages'],
        CONFIG['max_messages']
    )

    batch_count = len(batches)
    avg_batch_size = sum(len(b) for b in batches) / batch_count if batch_count > 0 else 0

    print(f'  - 总批次: {batch_count}')
    print(f'  - 平均批次大小: {avg_batch_size:.1f}条')

    # 显示批次分布
    print('\n批次分布:')
    for i, batch in enumerate(batches, 1):
        print(f'  批次{i:2d}: {len(batch):3d}条')

    # 提取
    print('\n提取中...')
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=CONFIG['parallel_workers']) as executor:
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
                    print(f'  进度: {idx}/{len(futures)}')
            except Exception as e:
                print(f'  批次失败: {e}')

    total_time = time.time() - start_time

    # 统计
    total_people = sum(len(r['entities'].get('people', [])) for r in results)
    total_events = sum(len(r['entities'].get('events', [])) for r in results)
    total_relationships = sum(len(r['entities'].get('relationships', [])) for r in results)

    # 家庭关系统计
    family_rel_count = 0
    family_rels_detail = []
    for r in results:
        for rel in r['entities'].get('relationships', []):
            rel_type = rel.get('type', '')
            if any(kw in rel_type for kw in ['CHILD', 'SPOUSE', 'FATHER', 'MOTHER', 'PARENT', 'COUSIN', 'SIBLING']):
                family_rel_count += 1
                family_rels_detail.append(f"{rel.get('source')} --[{rel_type}]--> {rel.get('target')}")

    participated_in = sum(
        len([rel for rel in r['entities'].get('relationships', []) if rel.get('type') == 'PARTICIPATED_IN'])
        for r in results
    )

    avg_api_time = sum(r['api_time'] for r in results) / len(results) if results else 0

    # 保存结果
    output_dir = Path('test_config_results')
    config_output = output_dir / 'test_配置2.5_平衡点.json'
    with open(config_output, 'w', encoding='utf-8') as f:
        json.dump({
            'config': CONFIG,
            'stats': {
                'batch_count': batch_count,
                'avg_batch_size': avg_batch_size,
                'total_time': total_time,
                'avg_api_time': avg_api_time,
                'total_people': total_people,
                'total_events': total_events,
                'total_relationships': total_relationships,
                'participated_in_relationships': participated_in,
                'family_relationships': family_rel_count
            },
            'results': results
        }, f, ensure_ascii=False, indent=2)

    print(f'\n结果统计:')
    print(f'  - 总耗时: {total_time:.1f}秒')
    print(f'  - 平均API耗时: {avg_api_time:.2f}秒/批')
    print(f'  - 总People: {total_people}')
    print(f'  - 总Event: {total_events}')
    print(f'  - 总关系: {total_relationships}')
    print(f'  - PARTICIPATED_IN: {participated_in}')
    print(f'  - 家庭关系: {family_rel_count}')

    if family_rel_count > 0:
        print(f'\n家庭关系详情:')
        for rel in family_rels_detail:
            print(f'  - {rel}')

    print(f'\n结果文件: {config_output}')


if __name__ == '__main__':
    main()
