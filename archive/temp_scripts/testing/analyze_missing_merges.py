#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析缺失的合并建议
"""
import pickle
import re
from collections import defaultdict, Counter

with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print("=" * 80)
print("分析应该有的合并建议")
print("=" * 80)

# 1. 跨对话的明确标注
def get_person_relation(name):
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

print("\n[1] 跨对话明确标注（如'米雪川的妈妈'）")
relation_groups = defaultdict(list)
for name in person_index.keys():
    person, rel = get_person_relation(name)
    if person:
        key = f"{person}的{rel}"
        relation_groups[key].append(name)

cross_dialog_merges = {k: v for k, v in relation_groups.items() if len(v) > 1}
print(f"  应合并组数: {len(cross_dialog_merges)}")
print("\n  示例（前10组）:")
for i, (key, names) in enumerate(list(cross_dialog_merges.items())[:10], 1):
    total_count = sum(len(person_index[name]) for name in names)
    print(f"    {i}. {key}: {len(names)}个变体, 总计{total_count}次")
    for name in names[:3]:
        print(f"       - {name} ({len(person_index[name])}次)")

# 2. 同一对话内的纯关系词
print(f"\n[2] 同一对话内的关系词合并")
simple_relation_words = ['妈', '妈妈', '爸', '爸爸', '姐姐', '哥哥', '弟弟', '妹妹', '老婆', '老公', '儿子', '女儿']

same_conv_groups = []
for conv_name, person_names_set in conversation_persons.items():
    person_names = list(person_names_set)

    for rel_word in simple_relation_words:
        # 找这个关系词的所有变体
        variants = [name for name in person_names if name == rel_word or name.endswith(rel_word)]
        if len(variants) > 1:
            same_conv_groups.append({
                'conversation': conv_name,
                'relation': rel_word,
                'variants': variants
            })

print(f"  应合并组数: {len(same_conv_groups)}")
print("\n  示例（前10组）:")
for i, group in enumerate(same_conv_groups[:10], 1):
    print(f"    {i}. 对话'{group['conversation']}'中的'{group['relation']}':")
    print(f"       变体: {group['variants']}")

# 3. 同一对话内的"XXX"和"XXX的YYY"
print(f"\n[3] 同一对话内的简称/全称匹配")
same_conv_relation_matches = 0
examples = []

for conv_name, person_names_set in conversation_persons.items():
    person_names = list(person_names_set)

    for name1 in person_names:
        person1, rel1 = get_person_relation(name1)

        if person1:  # name1 是 "XXX的YYY"
            # 看看有没有单独的"YYY"
            if rel1 in person_names:
                same_conv_relation_matches += 1
                if len(examples) < 10:
                    examples.append({
                        'conversation': conv_name,
                        'full': name1,
                        'short': rel1
                    })

print(f"  应合并组数: {same_conv_relation_matches}")
print("\n  示例（前10组）:")
for i, ex in enumerate(examples, 1):
    print(f"    {i}. 对话'{ex['conversation']}'中:")
    print(f"       '{ex['full']}' 和 '{ex['short']}'")

# 4. 高频相似人名
print(f"\n[4] 高频人名（应检查相似度）")
frequent_names = [(name, len(instances)) for name, instances in person_index.items() if len(instances) >= 50]
frequent_names.sort(key=lambda x: x[1], reverse=True)

print(f"  高频人名数（>=50次）: {len(frequent_names)}")
print("\n  TOP 20:")
for i, (name, count) in enumerate(frequent_names[:20], 1):
    print(f"    {i}. {name}: {count}次")

# 总结
print(f"\n" + "=" * 80)
print("预估应该生成的合并建议数:")
print(f"  跨对话明确标注: {len(cross_dialog_merges)}")
print(f"  同对话内关系词: {len(same_conv_groups)}")
print(f"  同对话内简称/全称: {same_conv_relation_matches}")
print(f"  高频相似人名: 约100-200（需要检查相似度）")
print(f"\n  预估总数: {len(cross_dialog_merges) + len(same_conv_groups) + same_conv_relation_matches + 100} 左右")
print(f"\n  当前只生成了: 85")
print(f"  缺失: 约{len(cross_dialog_merges) + len(same_conv_groups) + same_conv_relation_matches - 85}个建议")
print("=" * 80)
