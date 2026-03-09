#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修补现有Event节点，建立Event←→Person关系"""

import sys
import io
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv(dotenv_path='../.env')

# Gemini配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# Neo4j配置
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'password123'

MODEL_NAME = "gemini-2.5-flash"

def get_all_events(session):
    """获取所有Event节点"""
    result = session.run("""
        MATCH (e:Event)
        RETURN e.name as name,
               e.description as description,
               e.conversation_name as conversation,
               e.event_id as event_id
        ORDER BY e.conversation_name, e.name
    """)
    return list(result)

def get_all_persons_in_conversation(session, conversation_name):
    """获取某个对话中的所有Person名称"""
    result = session.run("""
        MATCH (p:Person {conversation_name: $conv})
        RETURN p.name as name, p.aliases as aliases
    """, conv=conversation_name)

    persons = {}
    for record in result:
        name = record['name']
        aliases = record.get('aliases', []) or []
        persons[name] = aliases

    return persons

def extract_participants_with_llm(model, event_name, event_desc, person_list):
    """用LLM从Event描述中提取参与者"""
    prompt = f"""你是知识图谱专家。请从Event描述中识别参与者。

Event名称: {event_name}
Event描述: {event_desc}

可能的Person列表（从图谱中提取）:
{chr(10).join(f'- {name}' for name in person_list[:100])}

任务：从Event描述中识别哪些Person参与了此Event。

规则：
1. 只返回在Person列表中存在的人名
2. 如果描述中提到的人在列表中没有，尝试匹配别名或简称
3. 如果无法匹配，不要返回
4. 至少要有1个参与者

返回JSON数组：
["Person名称1", "Person名称2", ...]

只返回JSON数组，不要其他内容。
"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # 提取JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        participants = json.loads(result_text)
        return participants if isinstance(participants, list) else []

    except Exception as e:
        print(f"  ⚠️ LLM提取失败: {e}")
        return []

def create_participated_in_relationship(session, person_name, event_name, conversation_name):
    """创建PARTICIPATED_IN关系"""
    try:
        session.run("""
            MATCH (p:Person {name: $person, conversation_name: $conv})
            MATCH (e:Event {name: $event, conversation_name: $conv})
            MERGE (p)-[r:PARTICIPATED_IN]->(e)
            SET r.confidence = 0.85
        """, person=person_name, event=event_name, conv=conversation_name)
        return True
    except Exception as e:
        print(f"  ⚠️ 创建关系失败 ({person_name} → {event_name}): {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='修补Event-Person关系')
    parser.add_argument('--limit', type=int, default=100, help='处理前N个Event（测试用）')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不创建关系')
    args = parser.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    model = GenerativeModel(MODEL_NAME)

    print("=" * 80)
    print("修补Event-Person关系")
    print("=" * 80)

    with driver.session() as session:
        # 获取所有Event
        events = get_all_events(session)
        total_events = len(events)

        if args.limit:
            events = events[:args.limit]

        print(f"\n总Event数: {total_events}")
        print(f"处理Event数: {len(events)}")
        if args.dry_run:
            print("⚠️ DRY RUN模式 - 不会创建关系")
        print("-" * 80)

        # 按对话分组
        events_by_conv = {}
        for event in events:
            conv = event['conversation']
            if conv not in events_by_conv:
                events_by_conv[conv] = []
            events_by_conv[conv].append(event)

        total_relationships = 0
        processed_events = 0

        for conv_name, conv_events in events_by_conv.items():
            print(f"\n处理对话: {conv_name} ({len(conv_events)}个Event)")

            # 获取该对话的所有Person
            persons = get_all_persons_in_conversation(session, conv_name)
            person_list = list(persons.keys())

            print(f"  该对话的Person数: {len(person_list)}")

            for i, event in enumerate(conv_events, 1):
                event_name = event['name']
                event_desc = event['description'] or ""

                if len(event_desc) < 10:
                    print(f"  [{i}/{len(conv_events)}] {event_name[:40]}: 跳过（描述太短）")
                    continue

                # 用LLM提取参与者
                participants = extract_participants_with_llm(model, event_name, event_desc, person_list)

                if participants:
                    print(f"  [{i}/{len(conv_events)}] {event_name[:40]}: {len(participants)}个参与者")

                    if not args.dry_run:
                        for person in participants:
                            if create_participated_in_relationship(session, person, event_name, conv_name):
                                total_relationships += 1
                    else:
                        for person in participants:
                            print(f"    - {person} → {event_name[:30]}")
                        total_relationships += len(participants)

                    processed_events += 1
                else:
                    print(f"  [{i}/{len(conv_events)}] {event_name[:40]}: 未识别到参与者")

        print("\n" + "=" * 80)
        print("完成！")
        print(f"  处理的Event: {processed_events}/{len(events)}")
        print(f"  创建的关系: {total_relationships}个")
        print("=" * 80)

    driver.close()

if __name__ == '__main__':
    main()
