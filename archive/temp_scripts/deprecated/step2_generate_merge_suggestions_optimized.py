#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2：生成Person合并建议（优化版）
策略：不进行全量两两比较，而是针对性识别
"""
import pickle
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
import re

print("=" * 80)
print("生成Person合并建议（优化版）")
print("=" * 80)

# 1. 加载数据
print("\n1. 加载数据...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print(f"  Person实例: {len(persons):,}")
print(f"  唯一人名: {len(person_index):,}")

# 2. 构建合并候选组
print("\n2. 构建合并候选组...")

merge_groups = []

def get_person_and_relation(name):
    """提取 "XXX的YYY" 中的XXX和YYY"""
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

# 策略A: 按"XXX的YYY"模式分组
print("  策略A: 关系词分组...")
relation_groups = defaultdict(lambda: defaultdict(list))  # {关系主体: {关系词: [人名列表]}}

for name in person_index.keys():
    person, relation = get_person_and_relation(name)
    if person:  # 有明确关系
        relation_groups[person][relation].append(name)
    else:
        # 纯关系词（如"妈"、"爸"）按对话分组
        relation_groups['[对话内]'][relation].append(name)

# 生成关系词合并组
for person_name, relations in relation_groups.items():
    for relation_word, names in relations.items():
        if len(names) <= 1:
            continue

        # 同一个人的同一个关系，应该合并
        if person_name != '[对话内]':
            # 例如：所有"米雪川的妈妈"
            variants = []
            for name in names:
                instances = person_index[name]
                convs = Counter(persons[idx]['conversation'] for idx in instances)
                aliases = set()
                for idx in instances:
                    aliases.update(persons[idx]['aliases'])

                variants.append({
                    'name': name,
                    'count': len(instances),
                    'conversations': list(convs.keys())[:10],
                    'conv_count': len(convs),
                    'aliases': list(aliases)[:10]
                })

            merge_groups.append({
                'suggested_name': f"{person_name}的{relation_word}",
                'confidence': 'high',
                'reason': f'都明确指向{person_name}的{relation_word}',
                'variants': variants,
                'total_instances': sum(v['count'] for v in variants)
            })

# 策略B: 同一对话内的相似人名
print("  策略B: 同对话内合并...")
for conv_name, person_names in conversation_persons.items():
    person_names = list(person_names)

    # 在同一对话内查找可合并的
    # 例如："妈" 和 "米雪川的妈妈"都在"米府"对话中
    for i, name1 in enumerate(person_names):
        person1, rel1 = get_person_and_relation(name1)

        for name2 in person_names[i+1:]:
            person2, rel2 = get_person_and_relation(name2)

            should_merge = False
            reason = ""

            # 情况1: name1是"XXX的YYY", name2是"YYY"
            if person1 and not person2 and rel1 == name2:
                should_merge = True
                reason = f'同对话"{conv_name}"内，{name1}和{name2}应该是同一人'

            # 情况2: name2是"XXX的YYY", name1是"YYY"
            elif person2 and not person1 and rel2 == name1:
                should_merge = True
                reason = f'同对话"{conv_name}"内，{name2}和{name1}应该是同一人'

            # 情况3: 都是"XXX的YYY"，但XXX相同，YYY相同
            elif person1 and person2 and person1 == person2 and rel1 == rel2:
                should_merge = True
                reason = f'同对话"{conv_name}"内，都指向{person1}的{rel1}'

            if should_merge:
                # 检查是否已经在其他组里
                already_grouped = False
                for group in merge_groups:
                    existing_names = [v['name'] for v in group['variants']]
                    if name1 in existing_names or name2 in existing_names:
                        already_grouped = True
                        break

                if not already_grouped:
                    variants = []
                    for name in [name1, name2]:
                        instances = person_index[name]
                        convs = Counter(persons[idx]['conversation'] for idx in instances)
                        aliases = set()
                        for idx in instances:
                            aliases.update(persons[idx]['aliases'])

                        variants.append({
                            'name': name,
                            'count': len(instances),
                            'conversations': list(convs.keys())[:10],
                            'conv_count': len(convs),
                            'aliases': list(aliases)[:10]
                        })

                    merge_groups.append({
                        'suggested_name': name1 if variants[0]['count'] >= variants[1]['count'] else name2,
                        'confidence': 'high',
                        'reason': reason,
                        'variants': variants,
                        'total_instances': sum(v['count'] for v in variants)
                    })

# 策略C: 名字非常相似的（简单版本 - 只检查高频名字）
print("  策略C: 相似名字...")
# 只检查出现10次以上的人名
frequent_names = [name for name, instances in person_index.items() if len(instances) >= 10]

for i, name1 in enumerate(frequent_names):
    for name2 in frequent_names[i+1:]:
        # 简单相似度：长度差不超过2，且有70%字符相同
        if abs(len(name1) - len(name2)) <= 2:
            common_chars = len(set(name1) & set(name2))
            if common_chars >= min(len(name1), len(name2)) * 0.7:
                # 检查是否有共同对话
                convs1 = set(persons[idx]['conversation'] for idx in person_index[name1])
                convs2 = set(persons[idx]['conversation'] for idx in person_index[name2])

                if convs1 & convs2:
                    variants = []
                    for name in [name1, name2]:
                        instances = person_index[name]
                        convs = Counter(persons[idx]['conversation'] for idx in instances)
                        aliases = set()
                        for idx in instances:
                            aliases.update(persons[idx]['aliases'])

                        variants.append({
                            'name': name,
                            'count': len(instances),
                            'conversations': list(convs.keys())[:10],
                            'conv_count': len(convs),
                            'aliases': list(aliases)[:10]
                        })

                    merge_groups.append({
                        'suggested_name': name1,
                        'confidence': 'medium',
                        'reason': f'名字相似，且在{len(convs1 & convs2)}个共同对话中出现',
                        'variants': variants,
                        'total_instances': sum(v['count'] for v in variants)
                    })

print(f"  总合并建议: {len(merge_groups)}")

# 3. 生成Excel
print("\n3. 生成Excel...")

rows = []
for idx, group in enumerate(merge_groups, 1):
    # 准备变体信息
    variants_info = []
    for v in group['variants']:
        conv_str = ', '.join(v['conversations'][:3])
        if v['conv_count'] > 3:
            conv_str += f" (共{v['conv_count']}个对话)"
        alias_str = ', '.join(v['aliases'][:3]) if v['aliases'] else '无'
        if len(v['aliases']) > 3:
            alias_str += f" +{len(v['aliases'])-3}个"

        variants_info.append(
            f"【{v['name']}】\n"
            f"  出现次数: {v['count']}\n"
            f"  对话: {conv_str}\n"
            f"  别名: {alias_str}"
        )

    rows.append({
        'ID': idx,
        '置信度': group['confidence'],
        '建议合并为': group['suggested_name'],
        '变体详情': '\n\n'.join(variants_info),
        '总出现次数': group['total_instances'],
        '合并原因': group['reason'],
        '您的决定': ''  # approve 或 reject
    })

df = pd.DataFrame(rows)

# 排序
confidence_order = {'high': 0, 'medium': 1, 'low': 2}
df['_conf_order'] = df['置信度'].map(confidence_order)
df = df.sort_values(['_conf_order', '总出现次数'], ascending=[True, False])
df = df.drop('_conf_order', axis=1)

# 保存Excel
output_file = 'person_merge_suggestions.xlsx'

try:
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 全部建议
        df.to_excel(writer, sheet_name='全部建议', index=False)

        # 按置信度分sheet
        for conf_key, conf_name in [('high', '高置信度'), ('medium', '中等置信度'), ('low', '低置信度')]:
            df_conf = df[df['置信度'] == conf_key]
            if len(df_conf) > 0:
                df_conf.to_excel(writer, sheet_name=conf_name, index=False)

        # 调整列宽
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.column_dimensions['A'].width = 8   # ID
            worksheet.column_dimensions['B'].width = 12  # 置信度
            worksheet.column_dimensions['C'].width = 30  # 建议合并为
            worksheet.column_dimensions['D'].width = 80  # 变体详情
            worksheet.column_dimensions['E'].width = 12  # 总出现次数
            worksheet.column_dimensions['F'].width = 50  # 合并原因
            worksheet.column_dimensions['G'].width = 15  # 您的决定

    print(f"\n完成！")
    print(f"  合并建议总数: {len(df)}")
    print(f"    高置信度: {len(df[df['置信度']=='high'])}")
    print(f"    中等置信度: {len(df[df['置信度']=='medium'])}")
    print(f"    低置信度: {len(df[df['置信度']=='low'])}")
    print(f"\n✅ Excel文件已保存: {output_file}")
    print(f"\n📝 使用说明:")
    print(f"  1. 打开Excel文件")
    print(f"  2. 审核每条合并建议")
    print(f"  3. 在'您的决定'列填写: approve（同意） 或 reject（拒绝）")
    print(f"  4. 保存文件后运行步骤3执行合并")
    print("=" * 80)

except ImportError:
    print("\n错误: 需要安装 openpyxl")
    print("运行: pip install openpyxl")

    # 降级方案：保存为CSV
    print("\n使用CSV格式保存...")
    csv_file = 'person_merge_suggestions.csv'
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"保存到: {csv_file}")
