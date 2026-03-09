#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用真实复杂prompt测试不同并行度"""

import os
import sys
import io
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv(dotenv_path='../.env')
creds_json = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')
creds_dict = json.loads(creds_json)

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=creds_dict['project_id'], location="us-central1", credentials=credentials)

MODEL_NAME = "gemini-2.5-flash"  # 与batch_extract_all.py一致

# 使用batch_extract_all.py的完整prompt
FULL_EXTRACTION_PROMPT = """# 任务目标

从微信对话中提取知识图谱，包括：
1. **Person**（人物）：对话中提及的所有具体人物
2. **Organization**（组织）：公司、机构、组织等
3. **Topic**（话题）：讨论的主题
4. **Location**（地点）：具体地点
5. **Event**（事件）：对话中提及的事件
6. **Relationships**（关系）：实体之间的关系

# 对话信息

- **对话名称**: {conversation_name}
- **对话类型**: {conversation_type}
- **参与者**: {participants}
- **时间范围**: {time_range}

# 对话内容

{conversation_text}

# 输出格式

返回JSON格式的知识图谱：

```json
{{
  "people": [
    {{
      "name": "具体姓名",
      "is_user": true/false,
      "aliases": ["别名1", "别名2"],
      "relationship_to_user": "朋友/同事/家人",
      "occupation": "职业",
      "company": "公司名",
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ],
  "organizations": [
    {{
      "name": "组织名称",
      "type": "公司/学校/政府",
      "industry": "行业",
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ],
  "topics": [
    {{
      "name": "话题名称",
      "type": "技术/生活/工作",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ],
  "locations": [
    {{
      "name": "地点名称",
      "type": "城市/国家/建筑",
      "parent_location": "上级地点",
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ],
  "events": [
    {{
      "name": "事件名称",
      "type": "会议/聚会/旅行",
      "participants": ["人名1", "人名2"],
      "location": "地点",
      "description": "事件描述",
      "time_reference": "past/present/future",
      "time_description": "昨天/下周/明年",
      "inferred_time": "YYYY-MM-DD",
      "time_precision": "year/month/day/hour",
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ],
  "relationships": [
    {{
      "type": "KNOWS/WORKS_AT/PARTICIPATED_IN/DISCUSSED_WITH/DISCUSSED_TOPIC/LOCATED_AT/HAS_SPOUSE/HAS_CHILD/HAS_PARENT/HAS_SIBLING/HAS_COUSIN",
      "source": "源实体名",
      "target": "目标实体名",
      "source_type": "Person/Organization/Topic/Location/Event",
      "target_type": "Person/Organization/Topic/Location/Event",
      "properties": {{}},
      "confidence": 0.9,
      "context": "提取依据"
    }}
  ]
}}
```

## 重要规则

1. **泛指词过滤**：不要提取"某人"、"他"、"她"、"朋友"、"同事"、"老板"等泛指词作为Person
2. **Person实体**：优先提取真实姓名，is_user只有"米雪川"是true
3. **Event实体**：必须包含participants字段，列出所有参与者
4. **Relationships完整性**：必须创建PARTICIPATED_IN关系连接Event和Person
5. **家庭关系必须提取**：HAS_SPOUSE（配偶）、HAS_CHILD（子女）、HAS_PARENT（父母）、HAS_SIBLING（兄弟姐妹）、HAS_COUSIN（表亲）
6. **只返回JSON**：不要任何其他内容
"""

# 测试用的对话文本（真实长度）
TEST_CONVERSATION = """米雪川（男）: 最近在忙什么呢
朋友A: 在公司加班，项目要上线了
米雪川（男）: 辛苦了，周末要不要一起吃饭
朋友A: 好啊，叫上小王一起吧
米雪川（男）: 行，我问问他有没有空
朋友A: 上次去的那个火锅店不错
米雪川（男）: 对，海底捞是挺好的
朋友A: 那就周六晚上7点见
米雪川（男）: OK，到时候见
朋友A: 对了，听说你要换工作了？
米雪川（男）: 嗯，在看机会，有几家公司在聊
朋友A: 加油，有好消息告诉我
米雪川（男）: 一定，谢谢
朋友A: 我先忙了，拜拜
米雪川（男）: 好的，拜拜
"""


def extract_real(idx: int) -> dict:
    """用真实复杂prompt提取"""
    model = GenerativeModel(MODEL_NAME)

    prompt = FULL_EXTRACTION_PROMPT.format(
        conversation_name=f"测试{idx}",
        conversation_type="private",
        participants="米雪川, 朋友A",
        time_range="2024-01-01 ~ 2024-01-01",
        conversation_text=TEST_CONVERSATION
    )

    start = time.time()
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        entities = json.loads(result_text)
        elapsed = time.time() - start

        return {
            'status': 'success',
            'time': elapsed,
            'idx': idx,
            'people_count': len(entities.get('people', [])),
            'events_count': len(entities.get('events', []))
        }
    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)
        is_429 = '429' in error_msg or 'Resource exhausted' in error_msg

        return {
            'status': 'failed',
            'time': elapsed,
            'idx': idx,
            'error': error_msg[:100],
            'is_429': is_429
        }


def test_workers(num_workers: int, num_batches: int):
    """测试指定worker数"""
    print(f'\n{"="*70}')
    print(f'🧪 测试 {num_workers} workers × 真实复杂prompt')
    print(f'{"="*70}')

    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(extract_real, i): i for i in range(num_batches)}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if completed % 10 == 0 or completed == num_batches:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                print(f'  进度: {completed}/{num_batches} | '
                      f'耗时: {elapsed:.1f}秒 | '
                      f'速度: {rate:.2f}批次/秒')

    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_429 = sum(1 for r in results if r['status'] == 'failed' and r.get('is_429', False))
    error_other = sum(1 for r in results if r['status'] == 'failed' and not r.get('is_429', False))

    success_times = [r['time'] for r in results if r['status'] == 'success']
    avg_time = sum(success_times) / len(success_times) if success_times else 0

    # 打印错误样本
    failed = [r for r in results if r['status'] == 'failed']
    if failed:
        print(f'\n❌ 错误样本（前5个）:')
        for r in failed[:5]:
            print(f'  [{r["idx"]}] {r.get("error", "Unknown")}')

    print(f'\n📊 结果统计:')
    print(f'  总耗时: {total_time:.2f}秒')
    print(f'  成功: {success_count}/{num_batches} ({success_count/num_batches*100:.1f}%)')
    print(f'  429错误: {error_429}')
    print(f'  其他错误: {error_other}')
    print(f'  平均速度: {num_batches/total_time:.2f} 批次/秒')
    print(f'  平均API时间: {avg_time:.2f}秒')

    return {
        'workers': num_workers,
        'rate': num_batches / total_time,
        'success_rate': success_count / num_batches * 100,
        'error_429': error_429,
        'error_other': error_other,
        'avg_time': avg_time
    }


def main():
    print('='*70)
    print('🔬 真实工作负载并行度测试')
    print('='*70)
    print(f'\n使用完整的提取prompt（与batch_extract_all.py相同）')
    print(f'测试配置: 20, 30, 50 workers\n')

    configs = [
        (20, 30),
        (30, 30),
        (50, 50),
    ]

    results = []
    for workers, batches in configs:
        result = test_workers(workers, batches)
        results.append(result)
        time.sleep(2)

    # 汇总
    print(f'\n{"="*70}')
    print('📈 对比结果')
    print(f'{"="*70}\n')
    print(f'{"Workers":<10} {"速度":<15} {"成功率":<10} {"429错误":<10} {"结论"}')
    print('-'*70)

    baseline_rate = 0.3  # 当前10 workers的速度

    for r in results:
        speedup = r['rate'] / baseline_rate

        if r['error_429'] > r['workers'] * 0.5:  # 超过50%的429
            conclusion = f'❌ 429太多'
        elif r['success_rate'] < 90:
            conclusion = f'⚠️  成功率{r["success_rate"]:.0f}%'
        elif speedup >= 3:
            conclusion = f'🏆 提速{speedup:.1f}x'
        elif speedup >= 2:
            conclusion = f'✅ 提速{speedup:.1f}x'
        else:
            conclusion = f'✓ 提速{speedup:.1f}x'

        print(f'{r["workers"]:<10} {r["rate"]:.2f}批次/秒{"":<3} '
              f'{r["success_rate"]:.0f}%{"":<5} '
              f'{r["error_429"]:<10} {conclusion}')

    # 推荐
    print(f'\n💡 推荐:')
    best = max((r for r in results if r['success_rate'] >= 90),
               key=lambda x: x['rate'], default=None)

    if best:
        speedup = best['rate'] / baseline_rate
        remaining_batches = 49214 - 10600
        hours = remaining_batches / best['rate'] / 3600

        print(f'  🎯 PARALLEL_WORKERS = {best["workers"]}')
        print(f'  ')
        print(f'  预期效果:')
        print(f'    - 速度: {best["rate"]:.2f} 批次/秒（提速{speedup:.1f}倍）')
        print(f'    - 成功率: {best["success_rate"]:.1f}%')
        print(f'    - 剩余时间: {hours:.1f} 小时')
        print(f'    - 429错误: {best["error_429"]} / {best["workers"]} workers')
    else:
        print(f'  ⚠️  所有配置成功率<90%，建议保持10 workers')


if __name__ == '__main__':
    main()
