#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量提取所有对话的知识图谱
- 从 chat_data_filtered 读取原始对话
- 分批处理（每批20条消息）
- 支持断点续传
- 保存所有中间JSON文件
"""

import os
import sys
import io
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
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

# 配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 路径配置
CHAT_DATA_DIR = Path("../chat_data_filtered")
# 使用固定目录以支持真正的断点续传
OUTPUT_DIR = Path("../extractions/batch_20260227_001822")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件
LOG_FILE = OUTPUT_DIR / "extraction_log.txt"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

# 提取配置
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 2
PARALLEL_WORKERS = 50  # 并行worker数（经测试50 workers可提速3.2倍，失败率可控）

# 智能分片配置（配置2.5-平衡点，经过测试验证）
TIME_GAP_MINUTES = 45   # 45分钟间隔分片
MIN_MESSAGES = 10       # 最少10条消息
MAX_MESSAGES = 100      # 最多100条消息（关键平衡点，兼顾效率和质量）

# 已处理的对话（跳过）- 不再使用这个列表，让所有对话都参与
# 在batch级别检查是否已处理，而不是对话级别
PROCESSED_CONVERSATIONS = []  # 空列表，所有对话都会被加载

# 黑名单：群聊等
BLACKLIST = [
    "🦄 西安留学生聚集地™🗿②",
    "📍XA留学生活动中心3⃣️群🌟",
    "鹏程.盘古α技术交流群①",
    "多伦多租房＋闲置群🇨🇦",
    "📍XA留学生活动中心2⃣️群💫",
    "二手家具5️⃣",
    "警民共建金水湾网格管理群",
    "租房群-13",
    "DT租房群",
    "停车群",
    "姜溪花都4号楼业主群",
    "多伦多区块链六群",
    "Cursor 号池105会员群",
    "大二～大三课本交易1️⃣",
    "GTA二手闲置租房求职考证互助群",
    "VIP 2群|一支烟花AI社区",
    "一支烟花AI 广州社区",
    "GAIDN广州AI社群",
    "Austin 的 AI 产品交流群",
    "628～29深圳站→已报名朋友进群",
    "河津年轻人创业交流群",
    "牛米之 🏠，平安永远"
]


def smart_split_messages(messages: List, time_gap_minutes: int = 30, min_messages: int = 5, max_messages: int = 50) -> List[List]:
    """
    智能分片：基于时间间隔和消息数量
    - 借鉴embedding的SessionBuilder策略
    - 保持话题完整性

    Args:
        messages: 消息列表
        time_gap_minutes: 时间间隔阈值（分钟），超过此间隔则分片
        min_messages: 最小消息数
        max_messages: 最大消息数

    Returns:
        分片后的消息批次列表
    """
    batches = []
    current_batch = []
    time_gap = timedelta(minutes=time_gap_minutes)

    for msg in messages:
        # 只处理文本消息
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

            # 时间间隔超过阈值 或 达到最大消息数
            if time_diff > time_gap or len(current_batch) >= max_messages:
                should_split = True

        if should_split and len(current_batch) >= min_messages:
            batches.append(current_batch)
            current_batch = []

        current_batch.append(msg)

    # 最后一批
    if len(current_batch) >= min_messages:
        batches.append(current_batch)

    return batches


EXTRACTION_PROMPT = """你是一个知识图谱构建专家。请从以下微信对话中提取完整的结构化信息。

## 对话信息

对话名称: {conversation_name}
对话类型: {conversation_type}
参与者: {participants}
消息时间范围: {time_range}

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
      "type": "公司/学校/机构",
      "confidence": 0.8,
      "context": "提取依据"
    }}
  ],
  "topics": [
    {{
      "name": "话题名称",
      "type": "工作/生活/技术",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.8,
      "context": "提取依据"
    }}
  ],
  "locations": [
    {{
      "name": "地点名称",
      "type": "城市/国家/餐厅",
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

1. **泛指词过滤**：
   - 不要提取"某人"、"他"、"她"、"朋友"、"同事"、"老板"等泛指词作为Person
   - 只提取有具体名字的人

2. **Person实体**：
   - 优先提取真实姓名
   - 记录所有出现的称呼作为aliases
   - is_user: 只有"米雪川"是true，其他都是false

3. **Event实体（重要）**：
   - 必须包含participants字段，列出所有参与者的名字
   - 每个participant必须在people数组中存在
   - 尽量推断具体时间（基于对话时间和相对时间）

4. **时间推断**：
   - time_reference: past（已发生）/present（正在）/future（将来）
   - inferred_time: 根据对话时间推断YYYY-MM-DD格式
   - time_precision: 标注推断精度

5. **Organization实体**：
   - 提取公司、学校、机构名称
   - type标注类型

6. **Topic实体**：
   - 提取对话中的主要话题
   - keywords列出关键词

7. **Relationships 完整性原则**：
   - 必须提取的关系：KNOWS, WORKS_AT, DISCUSSED_WITH, DISCUSSED_TOPIC
   - ⚠️ **Event关系（必需）**：每个Event的participants都必须创建PARTICIPATED_IN关系
   - ⚠️ **家庭关系（必需）**：HAS_SPOUSE（配偶）, HAS_CHILD（子女）, HAS_PARENT（父母）, HAS_SIBLING（兄弟姐妹）, HAS_COUSIN（表亲）
   - 示例：Event有3个participants → 必须创建3个PARTICIPATED_IN关系
   - 不要遗漏关系，即使很明显也要明确提取

8. **质量要求**：
   - confidence: 根据确信程度设置0.0-1.0
   - context: 简要说明提取依据
   - 只提取高质量实体，宁缺毋滥

---

**只返回JSON，不要其他内容。**
"""


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    # 打印到控制台
    print(message)

    # 写入日志文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)


def save_progress(stats: Dict):
    """保存进度"""
    stats['last_update'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def load_progress() -> Dict:
    """加载进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            # 确保有failed_batches字段（兼容旧版本）
            if 'failed_batches' not in progress:
                progress['failed_batches'] = []
            return progress
    return {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'total_cost': 0.0,
        'processed_batches': [],
        'failed_batches': []  # 新增：记录失败的batch详情
    }


def load_all_conversations() -> List[Dict]:
    """加载所有对话"""
    log("加载对话数据...")

    conversations = []
    for conv_dir in CHAT_DATA_DIR.iterdir():
        if not conv_dir.is_dir():
            continue

        json_file = conv_dir / f"{conv_dir.name}.json"
        if not json_file.exists():
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            conv_name = data['meta']['name']

            # 跳过已处理和黑名单
            if conv_name in PROCESSED_CONVERSATIONS:
                log(f"  跳过（已处理）: {conv_name}")
                continue

            if conv_name in BLACKLIST:
                log(f"  跳过（黑名单）: {conv_name}")
                continue

            messages = data.get('messages', [])
            if len(messages) == 0:
                continue

            conversations.append({
                'conversation_name': conv_name,
                'conversation_type': 'private' if len(data.get('members', [])) <= 2 else 'group',
                'messages': messages,
                'participants': [m.get('name', 'Unknown') for m in data.get('members', [])],
                'file_path': str(json_file)
            })

        except Exception as e:
            log(f"  错误加载 {json_file}: {e}")

    log(f"✅ 加载完成：{len(conversations)} 个对话")
    return conversations


def split_into_batches(conversation: Dict) -> List[Dict]:
    """
    智能分批：基于时间间隔和消息数量
    - 30分钟间隔分片
    - 5-50条消息动态调整
    - 保持话题完整性
    """
    messages = conversation['messages']

    # 使用智能分片策略
    message_batches = smart_split_messages(
        messages,
        time_gap_minutes=30,
        min_messages=5,
        max_messages=50
    )

    batches = []
    total_batches = len(message_batches)

    for batch_idx, batch_msgs in enumerate(message_batches):
        # 生成batch_id
        batch_content = json.dumps(batch_msgs, ensure_ascii=False)
        batch_id = hashlib.md5(batch_content.encode()).hexdigest()[:16]

        # 构建对话文本
        conversation_text = "\n".join([
            f"{msg.get('accountName', 'Unknown')}: {msg.get('content', '')}"
            for msg in batch_msgs
        ])

        # 计算时间范围
        timestamps = [msg.get('timestamp', 0) for msg in batch_msgs if msg.get('timestamp')]
        if timestamps:
            start_time = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M')
            end_time = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M')
            time_range = f"{start_time} ~ {end_time}"
        else:
            time_range = "Unknown"

        batches.append({
            'batch_id': batch_id,
            'conversation_name': conversation['conversation_name'],
            'conversation_type': conversation['conversation_type'],
            'participants': conversation['participants'],
            'messages': batch_msgs,
            'conversation_text': conversation_text,
            'time_range': time_range,
            'batch_index': batch_idx + 1,
            'total_batches': total_batches
        })

    return batches


def extract_entities(batch: Dict) -> Dict:
    """提取实体"""
    model = GenerativeModel(MODEL_NAME)

    prompt = EXTRACTION_PROMPT.format(
        conversation_name=batch['conversation_name'],
        conversation_type=batch['conversation_type'],
        participants=', '.join(batch['participants']),
        time_range=batch.get('time_range', 'Unknown'),
        conversation_text=batch['conversation_text']
    )

    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # 提取JSON
    if '```json' in result_text:
        result_text = result_text.split('```json')[1].split('```')[0].strip()
    elif '```' in result_text:
        result_text = result_text.split('```')[1].split('```')[0].strip()

    entities = json.loads(result_text)

    return entities


def process_batch(batch: Dict, progress: Dict) -> Dict:
    """处理单个批次"""
    batch_id = batch['batch_id']
    conv_name = batch['conversation_name']

    # 检查是否已处理
    output_file = OUTPUT_DIR / f"session_{batch_id}.json"
    if output_file.exists() or batch_id in progress.get('processed_batches', []):
        return {'status': 'skipped', 'batch_id': batch_id}

    # 提取
    try:
        entities = extract_entities(batch)

        # 保存结果
        result = {
            'session_id': batch_id,
            'success': True,
            'conversation': {
                'conversation_name': conv_name,
                'conversation_type': batch['conversation_type'],
                'conversation_time': datetime.fromtimestamp(batch['messages'][0].get('timestamp', 0)).strftime('%Y-%m-%d'),
                'participants': batch['participants'],
                'message_count': len(batch['messages']),
                'batch_index': batch['batch_index'],
                'total_batches': batch['total_batches']
            },
            'entities': {
                'people': entities.get('people', []),
                'organizations': entities.get('organizations', []),
                'topics': entities.get('topics', []),
                'locations': entities.get('locations', []),
                'events': entities.get('events', []),
                'relationships': entities.get('relationships', [])
            },
            'raw_text': batch['conversation_text'],
            'timestamp': datetime.now().isoformat(),
            'cost_usd': 0.0001
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return {
            'status': 'success',
            'batch_id': batch_id,
            'conv_name': conv_name,
            'cost': 0.0001
        }

    except Exception as e:
        error_msg = str(e)
        log(f"  ❌ 提取失败 [{conv_name} batch {batch['batch_index']}]: {error_msg}")
        return {
            'status': 'failed',
            'batch_id': batch_id,
            'conv_name': conv_name,
            'batch_index': batch['batch_index'],
            'total_batches': batch['total_batches'],
            'error': error_msg
        }


def main():
    """主函数"""
    log("=" * 80)
    log("🚀 批量提取知识图谱开始")
    log("=" * 80)

    # 加载对话
    conversations = load_all_conversations()

    # 分批
    log("\n分批处理...")
    all_batches = []
    for conv in conversations:
        batches = split_into_batches(conv)
        all_batches.extend(batches)
        log(f"  {conv['conversation_name']}: {len(batches)} 个批次")

    total_batches = len(all_batches)
    log(f"\n✅ 总批次数: {total_batches:,}")

    # 加载进度
    progress = load_progress()
    # 计算当前这批batch中有多少未处理（而不是用总的processed数量）
    processed_set = set(progress.get('processed_batches', []))
    current_batch_ids = set(b['batch_id'] for b in all_batches)
    already_processed_in_current = len(current_batch_ids & processed_set)
    remaining = total_batches - already_processed_in_current

    log(f"\n📊 提取配置:")
    log(f"  - 模型: {MODEL_NAME}")
    log(f"  - 对话数: {len(conversations)}")
    log(f"  - 总批次: {total_batches:,}")
    log(f"  - 已完成: {len(progress.get('processed_batches', [])):,}")
    log(f"  - 剩余: {remaining:,}")
    log(f"  - 并行度: {PARALLEL_WORKERS}")
    log(f"  - 输出目录: {OUTPUT_DIR}")

    if remaining == 0:
        log("\n✅ 所有批次已处理完成！")
        return

    # 预估
    log(f"\n⚠️ 预估成本: ~${remaining * 0.0001:.2f}")
    log(f"⚠️ 预估时间: ~{remaining * 2 / PARALLEL_WORKERS / 3600:.1f} 小时")

    # 检查是否有--yes参数
    import sys
    if '--yes' not in sys.argv:
        response = input("\n是否开始提取？(yes/no): ")
        if response.lower() != 'yes':
            log("❌ 已取消")
            return
    else:
        log("\n自动确认：开始提取")

    log("\n" + "=" * 80)
    log("🔥 开始并行提取...")
    log("=" * 80 + "\n")

    start_time = time.time()

    # 并行处理
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {
            executor.submit(process_batch, batch, progress): batch
            for batch in all_batches
        }

        for future in as_completed(futures):
            result = future.result()

            if result['status'] == 'success':
                progress['success'] += 1
                progress['total_cost'] += result.get('cost', 0)
                progress['processed_batches'].append(result['batch_id'])
            elif result['status'] == 'failed':
                progress['failed'] += 1
                # ✅ 新增：记录失败的batch详情
                progress['failed_batches'].append({
                    'batch_id': result['batch_id'],
                    'conv_name': result['conv_name'],
                    'batch_index': result.get('batch_index'),
                    'total_batches': result.get('total_batches'),
                    'error': result.get('error', '')[:200],  # 限制错误长度
                    'timestamp': datetime.now().isoformat()
                })
            else:
                progress['skipped'] += 1

            # 每10个批次保存进度和打印日志
            completed = progress['success'] + progress['failed'] + progress['skipped']
            if completed % 10 == 0:
                save_progress(progress)

                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_batches - completed) / rate if rate > 0 else 0

                log(f"进度: {completed}/{total_batches} ({completed/total_batches*100:.1f}%) | "
                    f"成功: {progress['success']} | 失败: {progress['failed']} | "
                    f"速度: {rate:.1f}/s | 剩余: {eta/60:.1f}分钟")

    # 最终保存
    save_progress(progress)

    total_time = time.time() - start_time

    log("\n" + "=" * 80)
    log("🎉 批量提取完成！")
    log("=" * 80)

    log(f"\n📊 最终统计:")
    log(f"  - 总耗时: {total_time/3600:.2f} 小时")
    log(f"  - 成功: {progress['success']:,}")
    log(f"  - 失败: {progress['failed']:,}")
    log(f"  - 跳过: {progress['skipped']:,}")
    log(f"  - 总成本: ${progress['total_cost']:.2f}")

    log(f"\n💾 输出目录: {OUTPUT_DIR}")
    log(f"📁 文件数量: {len(list(OUTPUT_DIR.glob('session_*.json'))):,}")
    log(f"📋 日志文件: {LOG_FILE}")
    log(f"📊 进度文件: {PROGRESS_FILE}")


if __name__ == '__main__':
    main()
