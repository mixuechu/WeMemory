#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量并行修补Event-Person关系"""

import sys
import io
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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

# 批量大小
BATCH_SIZE = 30  # 每批处理30个Event

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

def batch_extract_participants_with_llm(model, events_batch, persons_dict):
    """批量用LLM提取Event参与者

    Args:
        persons_dict: {name: [aliases]} 字典
    """
    # 构建包含别名的Person列表
    person_lines = []
    for name, aliases in list(persons_dict.items())[:150]:
        if aliases and len(aliases) > 0:
            alias_str = ', '.join(aliases)
            person_lines.append(f'- {name} (别名: {alias_str})')
        else:
            person_lines.append(f'- {name}')

    # 构建批量prompt
    prompt = f"""你是知识图谱专家。请从多个Event描述中批量识别参与者。

可能的Person列表（包含别名）:
{chr(10).join(person_lines)}

待处理的Events:

"""

    for i, event in enumerate(events_batch):
        prompt += f"""
【Event {i}】
名称: {event['name']}
描述: {event['description'][:200]}
"""

    prompt += """

任务：为每个Event识别参与者。

规则：
1. Event描述中的人名可能是正式名称或别名，都要识别
2. 例如："吉月和米雪川吃饭" → 应识别出"王露颖"（别名吉月）和"米雪川"
3. **必须返回正式名称**（即Person列表中 "-" 后面的名称），不要返回别名
4. 如果无法匹配或Event描述太短，返回空数组

返回JSON格式（使用正式名称）：
{
  "0": ["王露颖", "米雪川"],
  "1": ["Hunter"],
  "2": []
}

只返回JSON对象，不要其他内容。
"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # 提取JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        results = json.loads(result_text)

        # 转换为数组格式
        participants_list = []
        for i in range(len(events_batch)):
            key = str(i)
            participants_list.append(results.get(key, []))

        return participants_list

    except Exception as e:
        print(f"  ⚠️ 批量LLM提取失败: {e}")
        return [[] for _ in events_batch]

def create_relationships_batch(driver, events_with_participants, conversation_name):
    """批量创建PARTICIPATED_IN关系"""
    created = 0

    with driver.session() as session:
        for event_name, participants in events_with_participants:
            if not participants:
                continue

            for person in participants:
                try:
                    session.run("""
                        MATCH (p:Person {name: $person, conversation_name: $conv})
                        MATCH (e:Event {name: $event, conversation_name: $conv})
                        MERGE (p)-[r:PARTICIPATED_IN]->(e)
                        SET r.confidence = 0.85
                    """, person=person, event=event_name, conv=conversation_name)
                    created += 1
                except Exception as e:
                    print(f"  ⚠️ 创建关系失败 ({person} → {event_name[:30]}): {e}")

    return created

def process_conversation_batch(conv_name, conv_events, driver, model):
    """处理一个对话的所有Event（批量）"""
    print(f"\n[{conv_name}] 开始处理 {len(conv_events)} 个Event")

    # 获取该对话的所有Person（包含aliases）
    with driver.session() as session:
        persons = get_all_persons_in_conversation(session, conv_name)

    print(f"[{conv_name}] Person数: {len(persons)}")

    # 过滤掉描述太短的Event
    valid_events = [e for e in conv_events if (e['description'] or '') and len(e['description']) >= 10]
    print(f"[{conv_name}] 有效Event: {len(valid_events)}/{len(conv_events)}")

    if not valid_events:
        return 0

    total_relationships = 0

    # 分批处理
    for batch_start in range(0, len(valid_events), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(valid_events))
        batch = valid_events[batch_start:batch_end]

        print(f"[{conv_name}] 处理batch {batch_start//BATCH_SIZE + 1}/{(len(valid_events)-1)//BATCH_SIZE + 1} ({len(batch)}个Event)")

        # 批量调用LLM（传入完整的persons字典，包含aliases）
        participants_list = batch_extract_participants_with_llm(model, batch, persons)

        # 准备批量创建关系
        events_with_participants = []
        for i, event in enumerate(batch):
            participants = participants_list[i]
            if participants:
                events_with_participants.append((event['name'], participants))
                print(f"  ✓ {event['name'][:40]}: {len(participants)}个参与者")

        # 批量创建关系
        created = create_relationships_batch(driver, events_with_participants, conv_name)
        total_relationships += created

        # 短暂延迟避免API限制
        time.sleep(0.5)

    print(f"[{conv_name}] 完成! 创建了 {total_relationships} 个关系")
    return total_relationships

def main():
    import argparse
    parser = argparse.ArgumentParser(description='批量修补Event-Person关系')
    parser.add_argument('--workers', type=int, default=3, help='并行worker数量')
    args = parser.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    model = GenerativeModel(MODEL_NAME)

    print("=" * 80)
    print("批量修补Event-Person关系")
    print("=" * 80)

    with driver.session() as session:
        # 获取所有Event
        events = get_all_events(session)
        total_events = len(events)

    print(f"\n总Event数: {total_events}")
    print(f"批量大小: {BATCH_SIZE}")
    print(f"并行Worker: {args.workers}")
    print("-" * 80)

    # 按对话分组
    events_by_conv = {}
    for event in events:
        conv = event['conversation']
        if conv not in events_by_conv:
            events_by_conv[conv] = []
        events_by_conv[conv].append(event)

    print(f"\n对话数: {len(events_by_conv)}")
    for conv, evts in sorted(events_by_conv.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {conv}: {len(evts)}个Event")

    # 并行处理所有对话
    start_time = time.time()
    total_relationships = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}

        for conv_name, conv_events in events_by_conv.items():
            future = executor.submit(process_conversation_batch, conv_name, conv_events, driver, model)
            futures[future] = conv_name

        for future in as_completed(futures):
            conv_name = futures[future]
            try:
                relationships = future.result()
                total_relationships += relationships
            except Exception as e:
                print(f"\n⚠️ [{conv_name}] 处理失败: {e}")

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("完成！")
    print(f"  处理的Event: {total_events}")
    print(f"  创建的关系: {total_relationships}个")
    print(f"  耗时: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)")
    print(f"  平均速度: {total_events/elapsed_time:.1f} Event/秒")
    print("=" * 80)

    driver.close()

if __name__ == '__main__':
    main()
