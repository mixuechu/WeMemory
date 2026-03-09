#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析所有Person实体，评估合并策略
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

print("=" * 80)
print("分析Person实体规模")
print("=" * 80)

# 1. 加载所有提取文件
output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

print(f"\n[1] 加载提取文件:")
print(f"   文件数: {len(json_files):,}")

# 2. 收集所有Person实体
all_persons = []  # 所有person实体
person_by_conversation = defaultdict(list)  # 按对话分组
person_names = Counter()  # 人名计数

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 从conversation字段中获取对话名
        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', 'Unknown')
        entities = data.get('entities', {})

        if 'people' in entities:
            for person in entities['people']:
                person_name = person.get('name', '').strip()
                if person_name:
                    all_persons.append({
                        'name': person_name,
                        'conversation': conv_name,
                        'aliases': person.get('aliases', []),
                        'file': json_file.name
                    })
                    person_by_conversation[conv_name].append(person_name)
                    person_names[person_name] += 1
    except Exception as e:
        pass

print(f"\n2 Person实体统计:")
print(f"   总Person实体数: {len(all_persons):,}")
print(f"   唯一人名数: {len(person_names):,}")
print(f"   涉及对话数: {len(person_by_conversation)}")

# 3. 分析人名分布
print(f"\n3 人名频次分布:")
freq_distribution = Counter()
for name, count in person_names.items():
    if count == 1:
        freq_distribution['出现1次'] += 1
    elif count <= 5:
        freq_distribution['出现2-5次'] += 1
    elif count <= 10:
        freq_distribution['出现6-10次'] += 1
    elif count <= 50:
        freq_distribution['出现11-50次'] += 1
    else:
        freq_distribution['出现50+次'] += 1

for freq, count in sorted(freq_distribution.items()):
    print(f"   {freq}: {count:,} 个人名")

# 4. 高频人名（可能需要跨对话合并）
print(f"\n4 高频人名 (出现10次以上, TOP 30):")
high_freq = [(name, count) for name, count in person_names.most_common(100) if count >= 10]
for name, count in high_freq[:30]:
    # 统计在多少个不同对话中出现
    convs = set()
    for p in all_persons:
        if p['name'] == name:
            convs.add(p['conversation'])
    try:
        print(f"   {name}: {count}次 (在{len(convs)}个对话中)")
    except UnicodeEncodeError:
        # 处理包含特殊字符的人名
        name_safe = name.encode('gbk', errors='replace').decode('gbk')
        print(f"   {name_safe}: {count}次 (在{len(convs)}个对话中)")

print(f"\n   出现10次以上的人名总数: {len(high_freq)}")

# 5. 按对话统计Person数量
print(f"\n5 每个对话的Person数量分布:")
conv_person_counts = [len(persons) for persons in person_by_conversation.values()]
avg_persons = sum(conv_person_counts) / len(conv_person_counts) if conv_person_counts else 0
max_persons = max(conv_person_counts) if conv_person_counts else 0
min_persons = min(conv_person_counts) if conv_person_counts else 0

print(f"   平均每个对话: {avg_persons:.1f} 个Person")
print(f"   最多: {max_persons} 个")
print(f"   最少: {min_persons} 个")

# 找出Person最多的对话
conv_person_list = [(conv, len(persons)) for conv, persons in person_by_conversation.items()]
conv_person_list.sort(key=lambda x: x[1], reverse=True)
print(f"\n   Person最多的对话 (TOP 10):")
for conv, count in conv_person_list[:10]:
    try:
        print(f"   - {conv}: {count} 个Person")
    except UnicodeEncodeError:
        conv_safe = conv.encode('gbk', errors='replace').decode('gbk')
        print(f"   - {conv_safe}: {count} 个Person")

# 6. 分析潜在的同名不同人情况
print(f"\n6 潜在同名不同人分析:")
# 找出在多个对话中都出现的人名
cross_conv_names = []
for name, count in person_names.items():
    convs = set()
    for p in all_persons:
        if p['name'] == name:
            convs.add(p['conversation'])
    if len(convs) > 1:
        cross_conv_names.append((name, count, len(convs)))

cross_conv_names.sort(key=lambda x: x[2], reverse=True)
print(f"   出现在多个对话中的人名数: {len(cross_conv_names)}")
print(f"\n   跨对话最多的人名 (TOP 20):")
for name, total_count, conv_count in cross_conv_names[:20]:
    try:
        print(f"   - {name}: 总共{total_count}次, 在{conv_count}个对话中")
    except UnicodeEncodeError:
        name_safe = name.encode('gbk', errors='replace').decode('gbk')
        print(f"   - {name_safe}: 总共{total_count}次, 在{conv_count}个对话中")

# 7. 建议策略
print(f"\n" + "=" * 80)
print(f"[建议] 合并策略建议:")
print(f"=" * 80)

total_unique = len(person_names)
cross_conv = len(cross_conv_names)

print(f"\n数据规模:")
print(f"  - 总唯一人名: {total_unique:,}")
print(f"  - 跨对话人名: {cross_conv:,}")
print(f"  - 单对话人名: {total_unique - cross_conv:,}")

if total_unique < 5000:
    print(f"\n[OK] 推荐策略: 全局一次性合并")
    print(f"   理由: 人名数量适中({total_unique:,}个), LLM可以处理")
    print(f"   优势: 一次完成, 可跨对话识别同一人")
    print(f"   方法: 分批处理(每批1000-2000个), 用LLM给出合并建议")
elif total_unique < 20000:
    print(f"\n[!] 推荐策略: 混合策略")
    print(f"   理由: 人名较多({total_unique:,}个), 需分阶段处理")
    print(f"   阶段1: 先每个对话内部合并")
    print(f"   阶段2: 再对高频人名({len(high_freq)}个)跨对话合并")
else:
    print(f"\n[!] 推荐策略: 对话内独立合并")
    print(f"   理由: 人名过多({total_unique:,}个), 全局合并困难")
    print(f"   方法: 每个对话独立处理(平均{avg_persons:.0f}个/对话)")
    print(f"   可选: 后续对特别高频的人名手动跨对话合并")

print(f"\n" + "=" * 80)
