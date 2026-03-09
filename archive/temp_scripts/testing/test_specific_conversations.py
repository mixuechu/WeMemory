#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试特定对话的提取：三蛋 和 北葵向暖"""

import os
import sys
import json
import pickle
from pathlib import Path
from dotenv import load_dotenv

# 设置UTF-8编码以支持emoji和中文（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

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

# 导入提取相关函数
import sys
sys.path.append(str(Path(__file__).parent))
from full_extraction import (
    call_gemini_extract,
    build_extraction_result
)

VECTOR_STORE_PATH = "vector_stores/conversations_complete.pkl"
DEBUG_DIR = Path("knowledge_graph/debug")
DEBUG_DIR.mkdir(exist_ok=True)


def load_conversations_by_names(names):
    """根据对话名称加载对话"""
    print("Loading conversation data...")

    with open(VECTOR_STORE_PATH, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    # 查找指定名称的对话
    found = {}
    for item in metadata:
        conv_name = item.get('conversation_name', '')
        if conv_name in names:
            found[conv_name] = item

    return found


def display_entity_summary(result):
    """显示实体统计摘要"""
    if not result['success']:
        print(f"  ❌ 提取失败: {result.get('error', 'Unknown')}")
        return

    entities = result['entities']

    print("\n  📊 Entity Statistics:")
    print(f"    - People: {len(entities.get('people', []))}")
    print(f"    - Organizations: {len(entities.get('organizations', []))}")
    print(f"    - Topics: {len(entities.get('topics', []))}")
    print(f"    - Events: {len(entities.get('events', []))}")
    print(f"    - Locations: {len(entities.get('locations', []))}")
    print(f"    - Relationships: {len(entities.get('relationships', []))}")

    metadata = result.get('extraction_metadata', {})
    if metadata:
        print("\n  ⚡ Performance:")
        print(f"    - Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
        print(f"    - Input tokens: {metadata.get('input_tokens', 0):,}")
        print(f"    - Output tokens: {metadata.get('output_tokens', 0):,}")
        print(f"    - Thoughts tokens: {metadata.get('thoughts_tokens', 0):,}")
        print(f"    - Cost: ${metadata.get('cost', 0):.6f}")


def display_detailed_entities(result, conv_name):
    """显示详细的实体内容"""
    if not result['success']:
        return

    entities = result['entities']

    print("\n" + "=" * 80)
    print(f"📋 Detailed Extraction Results for: {conv_name}")
    print("=" * 80)

    # People
    people = entities.get('people', [])
    if people:
        print("\n👤 PEOPLE:")
        for p in people:
            print(f"\n  Name: {p.get('name')}")
            print(f"    Is User: {p.get('is_user', False)}")
            print(f"    Aliases: {p.get('aliases', [])}")
            print(f"    Relationship: {p.get('relationship_to_user', 'N/A')}")
            print(f"    Occupation: {p.get('occupation', 'N/A')}")
            print(f"    Company: {p.get('company', 'N/A')}")

            hints = p.get('disambiguation_hints', {})
            if hints:
                print(f"    Disambiguation Hints:")
                if hints.get('co_occurs_with'):
                    print(f"      - Co-occurs with: {hints.get('co_occurs_with')}")
                if hints.get('distinctive_features'):
                    print(f"      - Features: {hints.get('distinctive_features')}")

            print(f"    Context: {p.get('context', 'N/A')[:100]}...")

    # Topics (只显示前10个)
    topics = entities.get('topics', [])
    if topics:
        print(f"\n📚 TOPICS (showing first 10 of {len(topics)}):")
        for t in topics[:10]:
            print(f"  - {t.get('name')} ({t.get('type', 'N/A')})")

    # Events (只显示前5个)
    events = entities.get('events', [])
    if events:
        print(f"\n📅 EVENTS (showing first 5 of {len(events)}):")
        for e in events[:5]:
            print(f"\n  Event: {e.get('name')}")
            print(f"    Type: {e.get('type', 'N/A')}")
            print(f"    Participants: {e.get('participants', [])}")
            print(f"    Time Reference: {e.get('time_reference', 'N/A')}")
            print(f"    Time Description: {e.get('time_description', 'N/A')}")
            print(f"    Inferred Time: {e.get('inferred_time', 'N/A')}")
            print(f"    Time Precision: {e.get('time_precision', 'N/A')}")
            print(f"    Description: {e.get('description', 'N/A')[:100]}...")

    # Relationships (只显示前10个)
    relationships = entities.get('relationships', [])
    if relationships:
        print(f"\n🔗 RELATIONSHIPS (showing first 10 of {len(relationships)}):")
        for r in relationships[:10]:
            print(f"  - ({r.get('source')}) --[{r.get('type')}]--> ({r.get('target')})")


def check_previous_issues(result, conv_name):
    """检查之前的问题是否解决"""
    print("\n" + "=" * 80)
    print(f"🔍 Checking Previous Issues for: {conv_name}")
    print("=" * 80)

    if not result['success']:
        print("  ❌ Cannot check - extraction failed")
        return

    entities = result['entities']
    people = entities.get('people', [])
    topics = entities.get('topics', [])
    events = entities.get('events', [])
    relationships = entities.get('relationships', [])

    issues_fixed = []
    issues_remaining = []

    # Issue 1: 对话参与者是否被提取为 People
    participant_found = any(p.get('name') == conv_name for p in people)
    if participant_found:
        issues_fixed.append(f"✅ 对话参与者 '{conv_name}' 被正确提取为 Person")
    else:
        issues_remaining.append(f"❌ 对话参与者 '{conv_name}' 没有被提取为 Person")

    # Issue 2: 米雪川是否被提取
    user_found = any(p.get('is_user') == True for p in people)
    if user_found:
        user_person = next(p for p in people if p.get('is_user') == True)
        issues_fixed.append(f"✅ 米雪川被正确提取为 Person (name: {user_person.get('name')})")
    else:
        issues_remaining.append(f"❌ 米雪川没有被提取为 Person")

    # Issue 3: Topics 是否细粒度
    if len(topics) >= 5:
        issues_fixed.append(f"✅ Topics 数量充足 ({len(topics)} 个)，看起来是细粒度提取")
    else:
        issues_remaining.append(f"⚠️ Topics 数量较少 ({len(topics)} 个)，可能合并了")

    # Issue 4: Events 是否完整
    if len(events) >= 3:
        issues_fixed.append(f"✅ Events 数量充足 ({len(events)} 个)")
    else:
        issues_remaining.append(f"⚠️ Events 数量较少 ({len(events)} 个)，可能遗漏了")

    # Issue 5: Relationships 是否存在
    if len(relationships) >= 5:
        issues_fixed.append(f"✅ Relationships 数量充足 ({len(relationships)} 个)")
    else:
        issues_remaining.append(f"⚠️ Relationships 数量较少 ({len(relationships)} 个)")

    # Issue 6: Aliases 是否被提取
    people_with_aliases = [p for p in people if p.get('aliases') and len(p.get('aliases', [])) > 0]
    if people_with_aliases:
        issues_fixed.append(f"✅ 有 {len(people_with_aliases)} 个人物提取了 aliases")
    else:
        issues_remaining.append(f"⚠️ 没有人物提取 aliases")

    # Issue 7: Time inference 是否工作
    events_with_inferred_time = [e for e in events if e.get('inferred_time')]
    if events_with_inferred_time:
        issues_fixed.append(f"✅ 有 {len(events_with_inferred_time)} 个事件推断了时间")
    else:
        issues_remaining.append(f"⚠️ 没有事件推断时间")

    # Issue 8: Disambiguation hints 是否被提取
    people_with_hints = [p for p in people if p.get('disambiguation_hints')]
    if people_with_hints:
        issues_fixed.append(f"✅ 有 {len(people_with_hints)} 个人物提取了 disambiguation_hints")
    else:
        issues_remaining.append(f"⚠️ 没有人物提取 disambiguation_hints")

    print("\n✅ Fixed Issues:")
    for issue in issues_fixed:
        print(f"  {issue}")

    if issues_remaining:
        print("\n⚠️ Remaining Issues:")
        for issue in issues_remaining:
            print(f"  {issue}")
    else:
        print("\n🎉 所有之前的问题都已解决！")

    return len(issues_remaining) == 0


def main():
    """主函数"""
    print("=" * 80)
    print("[TEST] Testing Specific Conversations")
    print("=" * 80)
    print()

    target_names = ["三蛋", "北葵向暖"]

    # 加载对话
    conversations = load_conversations_by_names(target_names)

    print(f"Found {len(conversations)} conversations:")
    for name in target_names:
        if name in conversations:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} (NOT FOUND)")

    if len(conversations) == 0:
        print("\n❌ No target conversations found. Exiting.")
        return

    print()

    # 提取每个对话
    all_results = {}

    for conv_name, session in conversations.items():
        print("=" * 80)
        print(f"🔄 Processing: {conv_name}")
        print("=" * 80)

        print(f"\n📋 Conversation Info:")
        print(f"  - Name: {session.get('conversation_name')}")
        print(f"  - Type: {session.get('conversation_type')}")
        print(f"  - Messages: {session.get('message_count', 0)}")
        print(f"  - Time: {session.get('year', '?')}-{session.get('month', '?')}")

        # 显示对话预览
        content = session.get('content_text', '')
        print(f"\n📝 Content Preview (first 500 chars):")
        print("-" * 80)
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print("-" * 80)

        # 提取
        print(f"\n🚀 Starting extraction...")
        extraction_result = call_gemini_extract(session)
        result = build_extraction_result(session, extraction_result)

        all_results[conv_name] = result

        # 显示摘要
        display_entity_summary(result)

        # 保存结果
        session_id = session.get('session_id', 'unknown')
        result_file = DEBUG_DIR / f"test_{conv_name}_{session_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to: {result_file}")

        print()

    # 显示详细结果
    for conv_name, result in all_results.items():
        display_detailed_entities(result, conv_name)

    # 检查问题
    print("\n\n" + "=" * 80)
    print("🔍 FINAL EVALUATION")
    print("=" * 80)

    all_fixed = True
    for conv_name, result in all_results.items():
        fixed = check_previous_issues(result, conv_name)
        all_fixed = all_fixed and fixed

    print("\n" + "=" * 80)
    if all_fixed:
        print("🎉 SUCCESS! All previous issues have been resolved!")
    else:
        print("⚠️ Some issues still remain. Please review the detailed output above.")
    print("=" * 80)


if __name__ == '__main__':
    main()
