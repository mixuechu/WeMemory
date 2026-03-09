#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为每个对话生成独立的Person合并建议（修复版）
"""
import pickle
import json
from pathlib import Path
from collections import defaultdict
import re

print("=" * 80)
print("为每个对话生成独立的合并建议（修复版）")
print("=" * 80)

# 加载数据
print("\n加载数据...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print(f"  总对话数: {len(conversation_persons)}")

# 关系词列表 - 用于排除"XXX的YYY"这类不应合并的情况
RELATION_WORDS = [
    '妈妈', '妈', '爸爸', '爸', '老公', '老婆', '丈夫', '妻子',
    '儿子', '女儿', '孩子', '宝宝',
    '哥哥', '姐姐', '弟弟', '妹妹', '兄弟', '姐妹',
    '爷爷', '奶奶', '外公', '外婆', '爹', '娘',
    '叔叔', '阿姨', '舅舅', '姨妈', '姑姑', '伯伯',
    '朋友', '同学', '同事', '老板', '领导', '助理',
    '男友', '女友', '对象', '伴侣', '配偶'
]

def get_person_relation(name):
    """提取'XXX的YYY'格式"""
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

def should_merge(name1, name2):
    """判断两个人名是否应该合并"""
    person1, rel1 = get_person_relation(name1)
    person2, rel2 = get_person_relation(name2)

    # 规则1: 一个是"XXX的YYY"，一个是"YYY"，且YYY不是关系词
    # 例如: "米雪川的妈妈" 和 "妈妈" → 应该合并（在同一对话内）
    if person1 and not person2 and rel1 == name2:
        # 只有当YYY是关系词时才合并
        if rel1 in RELATION_WORDS or name2 in RELATION_WORDS:
            return True, f'"{name1}"和"{name2}"在同一对话内应该是同一人'
        return False, None

    if person2 and not person1 and rel2 == name1:
        if rel2 in RELATION_WORDS or name1 in RELATION_WORDS:
            return True, f'"{name2}"和"{name1}"在同一对话内应该是同一人'
        return False, None

    # 规则2: 都是"XXX的YYY"格式，XXX相同且YYY相同
    # 例如: "米雪川的妈妈" 和 "米雪川妈妈" → 应该合并
    if person1 and person2 and person1 == person2 and rel1 == rel2:
        return True, f'都指向{person1}的{rel1}'

    # 规则3: 简单的名字变体（更严格的判断）
    # 例如: "任悦" vs "任悦律师", "Lisa" vs "Lisa Chai"
    if name1 in name2 or name2 in name1:
        # 必须排除"XXX" vs "XXX的YYY"这种情况
        if person2 and person2 == name1:
            # name2 是 "name1的YYY"
            return False, None
        if person1 and person1 == name2:
            # name1 是 "name2的YYY"
            return False, None

        # 长度差异不能太大（避免误判）
        if abs(len(name1) - len(name2)) <= 5:
            # 更长的名字应该包含更短的名字
            if len(name2) > len(name1):
                if name2.startswith(name1) or name2.endswith(name1):
                    return True, f'"{name2}"可能是"{name1}"的完整称呼'
            else:
                if name1.startswith(name2) or name1.endswith(name2):
                    return True, f'"{name1}"可能是"{name2}"的完整称呼'

    return False, None

def analyze_conversation(conv_name, person_names_in_conv):
    """分析一个对话中的Person，返回合并建议"""
    merge_groups = []

    # 统计每个人名在本对话中的详细信息
    person_details = {}
    for name in person_names_in_conv:
        instances = []
        for idx in person_index.get(name, []):
            if persons[idx]['conversation'] == conv_name:
                instances.append(persons[idx])

        if instances:
            aliases = set()
            for inst in instances:
                if inst.get('aliases'):
                    aliases.update(inst['aliases'])

            person_details[name] = {
                'count': len(instances),
                'aliases': list(aliases)
            }

    # 找相似的人名
    person_list = list(person_names_in_conv)
    processed = set()

    for i, name1 in enumerate(person_list):
        if name1 in processed:
            continue

        variants = [name1]
        reasons = []

        for name2 in person_list[i+1:]:
            if name2 in processed:
                continue

            should_merge_flag, reason = should_merge(name1, name2)

            if should_merge_flag:
                variants.append(name2)
                if reason:
                    reasons.append(reason)
                processed.add(name2)

        # 如果找到了变体，添加到合并组
        if len(variants) > 1:
            variant_details = []
            for v in variants:
                details = person_details.get(v, {'count': 0, 'aliases': []})
                variant_details.append({
                    'name': v,
                    'count': details['count'],
                    'aliases': details['aliases'][:5]
                })

            merge_groups.append({
                'variants': variant_details,
                'suggested_name': variants[0],
                'total_count': sum(v['count'] for v in variant_details),
                'reason': reasons[0] if reasons else '名称相似'
            })

            processed.add(name1)

    return merge_groups

# 分析所有对话
print("\n分析每个对话...")
all_suggestions = []

for i, (conv_name, person_names_set) in enumerate(conversation_persons.items(), 1):
    if i % 50 == 0:
        print(f"  进度: {i}/{len(conversation_persons)}")

    person_names = list(person_names_set)

    if len(person_names) < 2:
        continue

    merge_groups = analyze_conversation(conv_name, person_names)

    if merge_groups:
        all_suggestions.append({
            'conversation': conv_name,
            'total_persons': len(person_names),
            'merge_groups': merge_groups
        })

# 按合并组数量排序
all_suggestions.sort(key=lambda x: len(x['merge_groups']), reverse=True)

print(f"\n完成！")
print(f"  有合并建议的对话数: {len(all_suggestions)}")
print(f"  总合并组数: {sum(len(s['merge_groups']) for s in all_suggestions)}")

# 生成HTML（复用之前的模板，添加原因显示）
print("\n生成HTML...")

html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Person合并建议 - 按对话分组（修复版）</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .stats {
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .controls {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .conversation-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .conversation-header {
            background-color: #f5f5f5;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .conversation-header:hover {
            background-color: #e0e0e0;
        }
        .conversation-header h3 {
            margin: 0;
            color: #333;
        }
        .conversation-badge {
            background-color: #2196F3;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
        }
        .conversation-content {
            display: none;
            padding: 15px;
            background-color: white;
        }
        .conversation-content.active {
            display: block;
        }
        .merge-group {
            border-left: 3px solid #4CAF50;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f9f9f9;
        }
        .merge-reason {
            color: #666;
            font-size: 13px;
            font-style: italic;
            margin-bottom: 8px;
        }
        .variant-item {
            margin: 5px 0;
            padding: 5px;
            background-color: white;
            border-radius: 3px;
        }
        .variant-name {
            font-weight: bold;
            color: #1976D2;
        }
        .variant-info {
            font-size: 12px;
            color: #666;
            margin-left: 10px;
        }
        .decision-buttons {
            margin-top: 10px;
            display: flex;
            gap: 8px;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }
        .btn-approve {
            background-color: #4CAF50;
            color: white;
        }
        .btn-reject {
            background-color: #f44336;
            color: white;
        }
        .selected-approve {
            background-color: #c8e6c9 !important;
        }
        .selected-reject {
            background-color: #ffcdd2 !important;
        }
        .save-btn {
            background-color: #2196F3;
            color: white;
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
        }
        input[type="text"] {
            padding: 8px;
            width: 300px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .expand-all {
            padding: 8px 16px;
            background-color: #9E9E9E;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Person合并建议 - 按对话分组（修复版）</h1>

        <div class="stats">
            <strong>统计：</strong>
            有合并建议的对话: """ + str(len(all_suggestions)) + """ 个 |
            总合并组数: """ + str(sum(len(s['merge_groups']) for s in all_suggestions)) + """ |
            已批准: <span id="approved-count">0</span> |
            已拒绝: <span id="rejected-count">0</span>
        </div>

        <div class="controls">
            <input type="text" id="search" placeholder="搜索对话名称或人名...">
            <button class="expand-all" onclick="expandAll()">展开全部</button>
            <button class="expand-all" onclick="collapseAll()">收起全部</button>
        </div>

        <div id="conversations-container">
"""

# 为每个对话添加卡片
for idx, suggestion in enumerate(all_suggestions):
    conv_name = suggestion['conversation']
    total_persons = suggestion['total_persons']
    merge_groups = suggestion['merge_groups']

    html_content += f"""
        <div class="conversation-card" data-conv-id="{idx}">
            <div class="conversation-header" onclick="toggleConversation({idx})">
                <div>
                    <h3>{conv_name}</h3>
                    <small>共{total_persons}个Person | {len(merge_groups)}组合并建议</small>
                </div>
                <span class="conversation-badge">{len(merge_groups)}组</span>
            </div>
            <div class="conversation-content" id="conv-{idx}">
"""

    for group_idx, group in enumerate(merge_groups):
        group_id = f"{idx}-{group_idx}"
        reason = group.get('reason', '名称相似')

        html_content += f"""
                <div class="merge-group" id="group-{group_id}" data-decision="">
                    <strong>建议合并为: {group['suggested_name']}</strong>
                    <div class="merge-reason">原因: {reason}</div>
                    <div style="margin-top: 8px;">
"""

        for variant in group['variants']:
            aliases_str = ', '.join(variant['aliases'][:3]) if variant['aliases'] else '无'
            html_content += f"""
                        <div class="variant-item">
                            <span class="variant-name">{variant['name']}</span>
                            <span class="variant-info">出现{variant['count']}次 | 别名: {aliases_str}</span>
                        </div>
"""

        html_content += f"""
                    </div>
                    <div class="decision-buttons">
                        <button class="btn btn-approve" onclick="setDecision('{group_id}', 'approve')">批准</button>
                        <button class="btn btn-reject" onclick="setDecision('{group_id}', 'reject')">拒绝</button>
                    </div>
                </div>
"""

    html_content += """
            </div>
        </div>
"""

html_content += """
        </div>

        <button class="save-btn" onclick="saveDecisions()">保存所有决定到JSON</button>
    </div>

    <script>
        let decisions = {};

        function toggleConversation(idx) {
            const content = document.getElementById('conv-' + idx);
            content.classList.toggle('active');
        }

        function expandAll() {
            document.querySelectorAll('.conversation-content').forEach(el => {
                el.classList.add('active');
            });
        }

        function collapseAll() {
            document.querySelectorAll('.conversation-content').forEach(el => {
                el.classList.remove('active');
            });
        }

        function setDecision(groupId, decision) {
            const group = document.getElementById('group-' + groupId);
            decisions[groupId] = decision;

            group.classList.remove('selected-approve', 'selected-reject');
            if (decision === 'approve') {
                group.classList.add('selected-approve');
            } else {
                group.classList.add('selected-reject');
            }

            updateStats();
        }

        function updateStats() {
            const approved = Object.values(decisions).filter(d => d === 'approve').length;
            const rejected = Object.values(decisions).filter(d => d === 'reject').length;

            document.getElementById('approved-count').textContent = approved;
            document.getElementById('rejected-count').textContent = rejected;
        }

        function saveDecisions() {
            const result = {
                decisions: decisions,
                summary: {
                    total: """ + str(sum(len(s['merge_groups']) for s in all_suggestions)) + """,
                    approved: Object.values(decisions).filter(d => d === 'approve').length,
                    rejected: Object.values(decisions).filter(d => d === 'reject').length
                }
            };

            const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'merge_decisions_by_conversation.json';
            a.click();
            URL.revokeObjectURL(url);

            alert('决定已保存!\\n批准: ' + result.summary.approved + ' | 拒绝: ' + result.summary.rejected);
        }

        document.getElementById('search').addEventListener('input', function(e) {
            const searchText = e.target.value.toLowerCase();
            document.querySelectorAll('.conversation-card').forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(searchText) ? '' : 'none';
            });
        });
    </script>
</body>
</html>
"""

# 保存HTML
output_file = Path('person_merge_by_conversation_fixed.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"完成！HTML文件: {output_file}")
print("\n修复说明:")
print("  - 不再建议合并'陈晨'和'陈晨的老公'这类明显不同的人")
print("  - 只合并真正的变体，如'米雪川的妈'和'米雪川妈'")
print("  - 每个建议都有'原因'说明")
print("=" * 80)
