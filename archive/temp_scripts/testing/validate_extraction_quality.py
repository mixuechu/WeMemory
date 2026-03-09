#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全面验证三用户提取质量"""

import json
import sys
import io
from pathlib import Path
from collections import Counter, defaultdict

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EXTRACTION_DIR = Path("../extractions/test_three_users")

def main():
    files = list(EXTRACTION_DIR.glob("session_*.json"))

    print("=" * 80)
    print("提取质量全面检查")
    print("=" * 80)
    print()

    # 问题追踪
    issues = {
        'conversation_id_mismatch': [],  # conversation_id不匹配
        'no_entities': [],  # 没有提取任何实体
        'chat_process_events': [],  # 疑似聊天过程的事件
        'too_detailed_topics': [],  # 过于细节的主题
        'missing_user': [],  # 缺少米雪川
        'failures': []  # 提取失败
    }

    topic_keywords = Counter()  # 统计topic名称
    event_types = Counter()  # 统计event类型

    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

            # 1. 检查失败
            if not data.get('success'):
                issues['failures'].append({
                    'file': f.name,
                    'error': data.get('error', 'Unknown error')
                })
                continue

            conv_name = data['conversation']['conversation_name']
            entities = data['entities']

            # 2. 检查conversation_id字段一致性
            for person in entities.get('people', []):
                person_conv_id = person.get('conversation_id')
                if person_conv_id and person_conv_id != conv_name:
                    issues['conversation_id_mismatch'].append({
                        'file': f.name,
                        'conv_name': conv_name,
                        'person': person['name'],
                        'wrong_id': person_conv_id
                    })

            # 3. 检查是否完全没有实体
            total_entities = sum(len(entities.get(key, [])) for key in ['people', 'organizations', 'topics', 'events', 'locations'])
            if total_entities == 0:
                issues['no_entities'].append({
                    'file': f.name,
                    'conv_name': conv_name,
                    'message_count': data['conversation']['message_count']
                })

            # 4. 检查是否缺少米雪川
            people_names = [p['name'] for p in entities.get('people', [])]
            has_user = any('米雪川' in name for name in people_names)
            if not has_user and len(people_names) > 0:
                issues['missing_user'].append({
                    'file': f.name,
                    'conv_name': conv_name,
                    'people': people_names
                })

            # 5. 检查Events是否是聊天过程
            chat_keywords = ['发送', '回复', '查看', '打开', '等待', '消息', '聊天']
            for event in entities.get('events', []):
                event_types[event['type']] += 1
                if any(kw in event['name'] for kw in chat_keywords):
                    issues['chat_process_events'].append({
                        'file': f.name,
                        'event': event['name'],
                        'type': event['type']
                    })

            # 6. 统计Topics（检查是否过细）
            for topic in entities.get('topics', []):
                topic_keywords[topic['name']] += 1
                # 检查是否包含具体书名、餐厅名等细节
                detail_patterns = ['《', '》', '餐厅', '咖啡馆', 'Python', 'Java', 'React']
                if any(p in topic['name'] for p in detail_patterns):
                    issues['too_detailed_topics'].append({
                        'file': f.name,
                        'topic': topic['name']
                    })

    # 报告问题
    print("【问题1】conversation_id 字段不匹配")
    print("-" * 80)
    if issues['conversation_id_mismatch']:
        print(f"发现 {len(issues['conversation_id_mismatch'])} 处不匹配:")
        for item in issues['conversation_id_mismatch'][:10]:
            print(f"  {item['file']}: {item['person']} 的conversation_id={item['wrong_id']}, 应为{item['conv_name']}")
        if len(issues['conversation_id_mismatch']) > 10:
            print(f"  ... 还有 {len(issues['conversation_id_mismatch'])-10} 处")
    else:
        print("✅ 无问题")
    print()

    print("【问题2】完全没有提取实体")
    print("-" * 80)
    if issues['no_entities']:
        print(f"发现 {len(issues['no_entities'])} 个空提取:")
        for item in issues['no_entities'][:5]:
            print(f"  {item['file']}: {item['conv_name']} (消息数: {item['message_count']})")
    else:
        print("✅ 无问题")
    print()

    print("【问题3】缺少用户(米雪川)")
    print("-" * 80)
    if issues['missing_user']:
        print(f"发现 {len(issues['missing_user'])} 个缺失:")
        for item in issues['missing_user'][:5]:
            print(f"  {item['file']}: {item['conv_name']} - 只有: {', '.join(item['people'][:3])}")
    else:
        print("✅ 无问题")
    print()

    print("【问题4】疑似聊天过程的Events")
    print("-" * 80)
    if issues['chat_process_events']:
        print(f"发现 {len(issues['chat_process_events'])} 个疑似聊天过程:")
        for item in issues['chat_process_events'][:10]:
            print(f"  {item['event']} ({item['type']})")
    else:
        print("✅ 无问题")
    print()

    print("【问题5】过于细节的Topics")
    print("-" * 80)
    if issues['too_detailed_topics']:
        print(f"发现 {len(issues['too_detailed_topics'])} 个过细主题:")
        for item in issues['too_detailed_topics'][:10]:
            print(f"  {item['topic']}")
    else:
        print("✅ 无问题")
    print()

    print("【问题6】提取失败")
    print("-" * 80)
    if issues['failures']:
        print(f"发现 {len(issues['failures'])} 个失败:")
        for item in issues['failures'][:5]:
            print(f"  {item['file']}: {item['error'][:100]}")
    else:
        print("✅ 无问题")
    print()

    # 统计最常见的topics和events
    print("=" * 80)
    print("Topic 分布 (Top 20):")
    print("-" * 80)
    for topic, count in topic_keywords.most_common(20):
        print(f"  {topic}: {count}")
    print()

    print("Event 类型分布:")
    print("-" * 80)
    for etype, count in event_types.most_common(10):
        print(f"  {etype}: {count}")
    print()

    # 总结
    print("=" * 80)
    print("问题总结:")
    print("=" * 80)
    total_issues = sum(len(v) for k, v in issues.items())
    print(f"总问题数: {total_issues}")
    for key, items in issues.items():
        if items:
            print(f"  - {key}: {len(items)}")
    print()

    if total_issues == 0:
        print("✅ 提取质量完美，可以直接构建图谱")
    else:
        print("⚠️  发现问题，需要修复后再构建图谱")

if __name__ == '__main__':
    main()
