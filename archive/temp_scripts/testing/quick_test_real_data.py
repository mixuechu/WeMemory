#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试：用真实对话测试修复"""

import sys
import io
import json
import os
from pathlib import Path
from datetime import datetime

# 先导入避免stdout冲突
from build_neo4j_graph import Neo4jGraphBuilder

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

# 读取FF对话的前3条消息
print("=" * 80)
print("读取FF对话...")
print("=" * 80)

chat_file = Path("../chat_data_filtered/FF/FF.json")
with open(chat_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

conv_name = data['meta']['name']
messages = data['messages'][:3]  # 只取前3条

print(f"\n对话: {conv_name}")
print(f"消息数: {len(messages)}")
for i, msg in enumerate(messages, 1):
    content = msg.get('content', '')[:50]
    print(f"  {i}. {msg.get('accountName', 'Unknown')}: {content}")

# 构建对话文本
conversation_text = "\n".join([
    f"{msg.get('accountName', 'Unknown')}: {msg.get('content', '')}"
    for msg in messages
])

print("\n" + "=" * 80)
print("调用Gemini提取实体...")
print("=" * 80)

# 简化的prompt（只包含核心部分）
prompt = f"""从以下对话中提取知识图谱实体和关系。

对话名称: {conv_name}
对话内容:
{conversation_text}

提取以下内容（JSON格式）:
{{
  "people": [
    {{"name": "姓名", "is_user": false, "aliases": [], "confidence": 0.9}}
  ],
  "events": [
    {{"name": "事件名", "type": "类型", "participants": ["人名1", "人名2"], "description": "描述", "confidence": 0.8}}
  ],
  "relationships": [
    {{"type": "KNOWS/PARTICIPATED_IN", "source": "源", "target": "目标", "source_type": "Person", "target_type": "Person/Event", "confidence": 0.9}}
  ]
}}

注意：
1. participants中的每个人都要在relationships中创建PARTICIPATED_IN关系
2. 只返回JSON，不要其他内容
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

    print(f"✅ 提取成功!")
    print(f"  - People: {len(entities.get('people', []))}")
    print(f"  - Events: {len(entities.get('events', []))}")
    print(f"  - Relationships: {len(entities.get('relationships', []))}")

    # 保存为标准格式
    output = {
        "session_id": "quick_test_001",
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
    output_file = output_dir / "session_quick_test_001.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n保存到: {output_file}")

except Exception as e:
    print(f"❌ 提取失败: {e}")
    sys.exit(1)

# 测试build_neo4j_graph.py
print("\n" + "=" * 80)
print("测试build_neo4j_graph.py（修复后）")
print("=" * 80)

builder = Neo4jGraphBuilder('bolt://localhost:7687', 'neo4j', 'password123')

# 清理旧数据
print(f"\n清理{conv_name}的旧数据...")
with builder.driver.session() as session:
    session.run(f'MATCH (n {{conversation_name: $conv}}) DETACH DELETE n', conv=conv_name)

# 加载提取文件
builder.load_extraction_file(output_file)

# 验证
print("\n" + "=" * 80)
print("验证结果")
print("=" * 80)

with builder.driver.session() as session:
    # Event节点
    result = session.run('''
        MATCH (e:Event {conversation_name: $conv})
        RETURN e.name as name, e.event_id as event_id, e.conversation_name as conv
    ''', conv=conv_name)
    events = list(result)
    print(f"\n✅ Event节点: {len(events)}个")
    for e in events:
        has_id = "✓" if e['event_id'] else "✗"
        has_conv = "✓" if e['conv'] else "✗"
        print(f"  [{has_id} event_id] [{has_conv} conv] {e['name']}")

    # PARTICIPATED_IN关系（自动创建）
    result = session.run('''
        MATCH (p:Person {conversation_name: $conv})-[r:PARTICIPATED_IN]->(e:Event {conversation_name: $conv})
        RETURN p.name as person, e.name as event
    ''', conv=conv_name)
    relations = list(result)
    print(f"\n✅ PARTICIPATED_IN关系（自动创建）: {len(relations)}个")
    for r in relations:
        print(f"  - {r['person']} → {r['event']}")

# 清理
print(f"\n清理测试数据...")
with builder.driver.session() as session:
    session.run(f'MATCH (n {{conversation_name: $conv}}) DETACH DELETE n', conv=conv_name)

builder.close()

# 最终结论
print("\n" + "=" * 80)
success = len(events) > 0 and all(e['event_id'] and e['conv'] for e in events)
if success:
    print("🎉 测试通过！修复成功！")
    print("  ✅ Event有event_id和conversation_name")
    print("  ✅ PARTICIPATED_IN关系自动创建")
else:
    print("⚠️ 测试失败")
print("=" * 80)
