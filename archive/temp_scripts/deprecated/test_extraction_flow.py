#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试提取流程：从真实对话到JSON文件"""

import sys
import io
import json
import os
from pathlib import Path
from datetime import datetime

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
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

model = GenerativeModel("gemini-2.5-flash")

print("=" * 80)
print("测试提取流程：从真实对话到JSON")
print("=" * 80)

# 读取FF对话
chat_file = Path("../chat_data_filtered/FF/FF.json")
if not chat_file.exists():
    print(f"错误: 找不到文件 {chat_file}")
    sys.exit(1)

with open(chat_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

conv_name = data['meta']['name']
messages = data['messages'][:5]  # 只取前5条

print(f"\n对话名称: {conv_name}")
print(f"消息数量: {len(messages)}")
for i, msg in enumerate(messages, 1):
    sender = msg.get('accountName', 'Unknown')
    content = msg.get('content', '')[:50]
    print(f"  {i}. {sender}: {content}...")

# 构建对话文本
conversation_text = "\n".join([
    f"{msg.get('accountName', 'Unknown')}: {msg.get('content', '')}"
    for msg in messages
])

print("\n" + "=" * 80)
print("调用Gemini提取实体（使用修复后的prompt）")
print("=" * 80)

# 使用修复后的prompt（与full_extraction.py保持一致）
prompt = f"""从以下对话中提取知识图谱实体和关系。

对话名称: {conv_name}
对话内容:
{conversation_text}

请提取以下实体和关系（JSON格式）:

{{
  "people": [
    {{
      "name": "正式姓名",
      "is_user": false,
      "aliases": ["别名1", "别名2"],
      "confidence": 0.9
    }}
  ],
  "events": [
    {{
      "name": "事件名称",
      "type": "事件类型",
      "participants": ["人名1", "人名2"],
      "description": "事件描述",
      "confidence": 0.8
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

**重要规则**:
1. **泛指词过滤**: 不要提取"某人"、"他"、"她"、"朋友"等泛指词作为Person
2. **Event必须包含participants**: 每个Event必须列出参与的人名
3. **PARTICIPATED_IN关系必需**: 每个Event的participants都必须在relationships中创建PARTICIPATED_IN关系
4. 只返回JSON，不要其他内容
"""

try:
    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # 提取JSON
    if '```json' in result_text:
        result_text = result_text.split('```json')[1].split('```')[0].strip()
    elif '```' in result_text:
        result_text = result_text.split('```')[1].split('```')[0].strip()

    entities = json.loads(result_text)

    print(f"\n提取成功!")
    print(f"  - People: {len(entities.get('people', []))} 个")
    print(f"  - Events: {len(entities.get('events', []))} 个")
    print(f"  - Relationships: {len(entities.get('relationships', []))} 个")

    # 验证关键字段
    print("\n" + "=" * 80)
    print("验证提取结果")
    print("=" * 80)

    # 检查1: Event是否有participants字段
    events = entities.get('events', [])
    events_with_participants = [e for e in events if e.get('participants')]
    print(f"\n检查1: Event.participants字段")
    print(f"  - Events总数: {len(events)}")
    print(f"  - 有participants: {len(events_with_participants)} 个")
    if len(events) > 0:
        if len(events_with_participants) == len(events):
            print(f"  ✅ 所有Event都有participants字段")
        else:
            print(f"  ❌ 部分Event缺少participants字段")
            for e in events:
                if not e.get('participants'):
                    print(f"     缺失: {e.get('name')}")

    # 检查2: PARTICIPATED_IN关系
    relationships = entities.get('relationships', [])
    participated_in_rels = [r for r in relationships if r.get('type') == 'PARTICIPATED_IN']
    print(f"\n检查2: PARTICIPATED_IN关系")
    print(f"  - 关系总数: {len(relationships)}")
    print(f"  - PARTICIPATED_IN: {len(participated_in_rels)} 个")

    # 验证每个Event的participants都有对应关系
    total_expected_rels = sum(len(e.get('participants', [])) for e in events)
    print(f"  - 预期关系数: {total_expected_rels} 个（基于participants）")
    if total_expected_rels > 0:
        if len(participated_in_rels) >= total_expected_rels:
            print(f"  ✅ PARTICIPATED_IN关系数量符合预期")
        else:
            print(f"  ⚠️ PARTICIPATED_IN关系可能缺失（{len(participated_in_rels)}/{total_expected_rels}）")

    # 检查3: 泛指词过滤
    print(f"\n检查3: 泛指词过滤")
    people = entities.get('people', [])
    generic_words = ['某人', '他', '她', '朋友', '对方', '那个人', '这个人']
    generic_people = [p for p in people if p.get('name') in generic_words]
    print(f"  - People总数: {len(people)}")
    print(f"  - 泛指词: {len(generic_people)} 个")
    if len(generic_people) == 0:
        print(f"  ✅ 没有泛指词")
    else:
        print(f"  ❌ 发现泛指词:")
        for p in generic_people:
            print(f"     - {p.get('name')}")

    # 保存为标准格式
    output = {
        "session_id": "test_extraction_ff",
        "success": True,
        "conversation": {
            "conversation_name": conv_name,
            "conversation_time": datetime.fromtimestamp(messages[0].get('timestamp', 0)).strftime('%Y-%m-%d'),
            "participants": list(set([msg.get('accountName') for msg in messages]))
        },
        "entities": {
            "people": entities.get('people', []),
            "organizations": [],
            "topics": [],
            "locations": [],
            "events": entities.get('events', []),
            "relationships": entities.get('relationships', [])
        },
        "raw_text": conversation_text,
        "timestamp": datetime.now().isoformat(),
        "cost_usd": 0.001
    }

    output_dir = Path("extraction_output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "session_test_extraction_ff.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n保存到: {output_file}")

    # 最终结论
    print("\n" + "=" * 80)
    all_checks_passed = (
        len(events) == 0 or len(events_with_participants) == len(events)
    ) and (
        total_expected_rels == 0 or len(participated_in_rels) >= total_expected_rels
    ) and (
        len(generic_people) == 0
    )

    if all_checks_passed:
        print("🎉 测试通过！提取流程正常工作")
        print("  ✅ Event有participants字段")
        print("  ✅ PARTICIPATED_IN关系完整")
        print("  ✅ 泛指词已过滤")
    else:
        print("⚠️ 部分检查未通过，请查看上方详情")
    print("=" * 80)

except Exception as e:
    print(f"❌ 提取失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
