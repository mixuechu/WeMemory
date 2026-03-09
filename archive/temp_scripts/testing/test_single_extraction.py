#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试单条对话的完整提取"""

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# 导入提取函数
import sys
sys.path.append(str(Path(__file__).parent))
from full_extraction import (
    format_conversation_for_extraction,
    call_gemini_extract,
    build_extraction_result,
    EXTRACTION_PROMPT
)

# 配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

VECTOR_STORE_PATH = "vector_stores/conversations_complete.pkl"


def load_sample_conversation():
    """加载一条有代表性的对话"""
    print("Loading conversation data...")

    with open(VECTOR_STORE_PATH, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    # 找一条合适的对话（6-10条消息，有内容）
    suitable = []
    for item in metadata:
        content = item.get('content_text', '')
        msg_count = item.get('message_count', 0)

        if 6 <= msg_count <= 10 and len(content) > 200:
            suitable.append(item)

    if not suitable:
        print("ERROR: No suitable conversation found")
        return None

    # 选择第一个
    selected = suitable[0]

    print(f"Selected conversation: {selected.get('conversation_name', 'Unknown')}")
    print(f"  Messages: {selected.get('message_count', 0)}")
    print(f"  Time: {selected.get('year', '?')}-{selected.get('month', '?')}")
    print(f"  Type: {selected.get('conversation_type', '?')}")

    return selected


def test_extraction():
    """测试单条提取"""
    print("=" * 80)
    print("Single Conversation Extraction Test")
    print("=" * 80)
    print()

    # 加载样本对话
    session = load_sample_conversation()
    if not session:
        return

    print()
    print("Conversation Preview:")
    print("-" * 80)
    content = session.get('content_text', '')
    print(content[:500] + "..." if len(content) > 500 else content)
    print("-" * 80)

    print()
    print("Starting extraction...")

    # 提取
    extraction_result = call_gemini_extract(session)

    # 构建完整结果
    result = build_extraction_result(session, extraction_result)

    # 保存结果
    output_file = Path("knowledge_graph/test_extraction_result.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print(f"Extraction completed!")
    print(f"Result saved to: {output_file}")

    # 显示摘要
    print()
    print("=" * 80)
    print("Extraction Summary")
    print("=" * 80)

    if result['success']:
        entities = result['entities']

        print()
        print("SUCCESS: Extraction successful")

        print()
        print("Entity Statistics:")
        print(f"  - People: {len(entities.get('people', []))}")
        print(f"  - Organizations: {len(entities.get('organizations', []))}")
        print(f"  - Topics: {len(entities.get('topics', []))}")
        print(f"  - Events: {len(entities.get('events', []))}")
        print(f"  - Locations: {len(entities.get('locations', []))}")
        print(f"  - Relationships: {len(entities.get('relationships', []))}")

        # 显示人物
        people = entities.get('people', [])
        if people:
            print()
            print(f"People ({len(people)}):")
            for person in people:
                print(f"  - {person.get('name', '?')}")
                print(f"    Relationship: {person.get('relationship_to_user', '?')}")
                if person.get('occupation'):
                    print(f"    Occupation: {person.get('occupation')}")
                if person.get('company'):
                    print(f"    Company: {person.get('company')}")
                if person.get('expertise'):
                    print(f"    Expertise: {', '.join(person.get('expertise', []))}")
                print(f"    Confidence: {person.get('confidence', 0):.2f}")
                print()

        # 显示组织
        orgs = entities.get('organizations', [])
        if orgs:
            print()
            print(f"Organizations ({len(orgs)}):")
            for org in orgs:
                print(f"  - {org.get('name', '?')} ({org.get('type', '?')})")
                if org.get('industry'):
                    print(f"    Industry: {org.get('industry')}")
                print(f"    Confidence: {org.get('confidence', 0):.2f}")
                print()

        # 显示主题
        topics = entities.get('topics', [])
        if topics:
            print()
            print(f"Topics ({len(topics)}):")
            for topic in topics[:5]:  # 只显示前5个
                print(f"  - {topic.get('name', '?')} [{topic.get('type', '?')}]")
                if topic.get('keywords'):
                    print(f"    Keywords: {', '.join(topic.get('keywords', []))}")
                print(f"    Confidence: {topic.get('confidence', 0):.2f}")
                print()
            if len(topics) > 5:
                print(f"  ... and {len(topics) - 5} more topics")

        # 显示事件
        events = entities.get('events', [])
        if events:
            print()
            print(f"Events ({len(events)}):")
            for event in events:
                print(f"  - {event.get('name', '?')} [{event.get('type', '?')}]")
                print(f"    Time: {event.get('time_reference', '?')}")
                if event.get('time_description'):
                    print(f"    Time description: {event.get('time_description')}")
                if event.get('participants'):
                    print(f"    Participants: {', '.join(event.get('participants', []))}")
                if event.get('location'):
                    print(f"    Location: {event.get('location')}")
                print(f"    Confidence: {event.get('confidence', 0):.2f}")
                print()

        # 显示地点
        locations = entities.get('locations', [])
        if locations:
            print()
            print(f"Locations ({len(locations)}):")
            for loc in locations:
                print(f"  - {loc.get('name', '?')} ({loc.get('type', '?')})")
                if loc.get('parent_location'):
                    print(f"    Parent: {loc.get('parent_location')}")
                print(f"    Confidence: {loc.get('confidence', 0):.2f}")
                print()

        # 显示关系
        relationships = entities.get('relationships', [])
        if relationships:
            print()
            print(f"Relationships ({len(relationships)}):")
            for rel in relationships:
                print(f"  - ({rel.get('source', '?')}) --[{rel.get('type', '?')}]--> ({rel.get('target', '?')})")
                print(f"    Source type: {rel.get('source_type', '?')}, Target type: {rel.get('target_type', '?')}")
                print(f"    Confidence: {rel.get('confidence', 0):.2f}")
                print()

        # 显示性能
        metadata = result.get('extraction_metadata', {})
        if metadata:
            print()
            print("Performance Metrics:")
            print(f"  - Model: {metadata.get('model', '?')}")
            print(f"  - Input tokens: {metadata.get('input_tokens', 0):,}")
            print(f"  - Output tokens: {metadata.get('output_tokens', 0):,}")
            print(f"  - Thoughts tokens: {metadata.get('thoughts_tokens', 0):,}")
            print(f"  - Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
            print(f"  - Cost: ${metadata.get('cost', 0):.6f}")

    else:
        print()
        print("ERROR: Extraction failed")
        print(f"Error: {result.get('error', 'Unknown')}")

    print()
    print("=" * 80)
    print(f"View full result: {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    test_extraction()
