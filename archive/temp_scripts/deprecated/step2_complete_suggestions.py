#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2：生成完整的Person合并建议
"""
import pickle
from pathlib import Path
from collections import defaultdict, Counter
import re
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

print("=" * 80)
print("生成完整的Person合并建议")
print("=" * 80)

# 加载数据
print("\n[1/4] 加载数据...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print(f"  Person实例: {len(persons):,}")
print(f"  唯一人名: {len(person_index):,}")

# 合并建议列表
merge_groups = []

def get_person_and_relation(name):
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

# 策略1: 同一对话内，关系词结尾的人名合并
print("\n[2/4] 策略1: 同一对话内关系词合并...")
simple_relation_words = ['妈', '妈妈', '爸', '爸爸', '姐姐', '哥哥', '弟弟', '妹妹', '老婆', '老公', '儿子', '女儿']

for conv_name, person_names_set in conversation_persons.items():
    person_names = list(person_names_set)

    for rel_word in simple_relation_words:
        # 找所有包含这个关系词的人名
        variants = []
        for name in person_names:
            # 精确匹配或以关系词结尾
            if name == rel_word or name.endswith(rel_word):
                variants.append(name)

        if len(variants) > 1:
            # 收集详细信息
            variant_details = []
            for name in variants:
                instances = person_index[name]
                aliases = set()
                for idx in instances:
                    if persons[idx]['aliases']:
                        aliases.update(persons[idx]['aliases'])

                variant_details.append({
                    'name': name,
                    'count': len(instances),
                    'conversations': [conv_name],  # 只在这一个对话中
                    'conv_count': 1,
                    'aliases': list(aliases)
                })

            merge_groups.append({
                'suggested_name': f"{conv_name}的{rel_word}",
                'confidence': 'high',
                'reason': f'同一对话"{conv_name}"内，都是{rel_word}相关',
                'variants': variant_details,
                'total_instances': sum(v['count'] for v in variant_details),
                'type': 'same_conv_relation'
            })

print(f"  找到: {len(merge_groups)}组")

# 策略2: 同一对话内，"XXX的YYY"和"YYY"匹配
print("\n[3/4] 策略2: 同一对话内简称/全称匹配...")
strategy2_count = 0
processed_pairs = set()

for conv_name, person_names_set in conversation_persons.items():
    person_names = list(person_names_set)

    for name1 in person_names:
        person1, rel1 = get_person_and_relation(name1)

        if not person1:  # name1不是"XXX的YYY"格式，跳过
            continue

        # 看看有没有单独的"YYY"
        if rel1 in person_names:
            pair_key = (conv_name, tuple(sorted([name1, rel1])))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            # 检查是否已经在之前的组里
            already_in_group = False
            for group in merge_groups:
                existing_names = [v['name'] for v in group['variants']]
                if name1 in existing_names or rel1 in existing_names:
                    already_in_group = True
                    break

            if not already_in_group:
                variant_details = []
                for name in [name1, rel1]:
                    instances = person_index[name]
                    aliases = set()
                    for idx in instances:
                        if persons[idx]['aliases']:
                            aliases.update(persons[idx]['aliases'])

                    variant_details.append({
                        'name': name,
                        'count': len(instances),
                        'conversations': [conv_name],
                        'conv_count': 1,
                        'aliases': list(aliases)
                    })

                merge_groups.append({
                    'suggested_name': name1,
                    'confidence': 'high',
                    'reason': f'同一对话"{conv_name}"内，"{name1}"和"{rel1}"应为同一人',
                    'variants': variant_details,
                    'total_instances': sum(v['count'] for v in variant_details),
                    'type': 'same_conv_match'
                })
                strategy2_count += 1

print(f"  找到: {strategy2_count}组")

print(f"\n  合并建议总数: {len(merge_groups)}")

# 生成HTML
print("\n[4/4] 生成HTML...")

html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Person实体合并建议（完整版）</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1600px;
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
            margin-top: 0;
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
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }
        .controls input, .controls select, .controls button {
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .controls input[type="text"] {
            width: 300px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px 8px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        td {
            padding: 10px 8px;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .variant-item {
            margin-bottom: 8px;
            padding: 6px;
            background-color: #f9f9f9;
            border-left: 3px solid #2196F3;
            font-size: 13px;
        }
        .variant-name {
            font-weight: bold;
            color: #1976D2;
        }
        .variant-details {
            font-size: 11px;
            color: #666;
            margin-top: 2px;
        }
        .badge {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            color: white;
        }
        .badge-high { background-color: #4CAF50; }
        .badge-medium { background-color: #FF9800; }
        .badge-low { background-color: #9E9E9E; }
        .decision-buttons {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }
        .btn-approve { background-color: #4CAF50; color: white; }
        .btn-approve:hover { background-color: #45a049; }
        .btn-reject { background-color: #f44336; color: white; }
        .btn-reject:hover { background-color: #da190b; }
        .btn-clear { background-color: #9E9E9E; color: white; }
        .selected-approve { background-color: #c8e6c9 !important; }
        .selected-reject { background-color: #ffcdd2 !important; }
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
        .save-btn:hover { background-color: #0b7dda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Person实体合并建议审核（完整版）</h1>

        <div class="stats">
            <strong>统计信息：</strong>
            总建议数: <span id="total-count">TOTAL_COUNT</span> |
            已批准: <span id="approved-count">0</span> |
            已拒绝: <span id="rejected-count">0</span> |
            待处理: <span id="pending-count">TOTAL_COUNT</span>
        </div>

        <div class="controls">
            <input type="text" id="search" placeholder="搜索人名或对话...">
            <select id="filter-decision">
                <option value="all">所有决定</option>
                <option value="pending">待处理</option>
                <option value="approved">已批准</option>
                <option value="rejected">已拒绝</option>
            </select>
            <button onclick="batchApproveAll()" style="background-color: #4CAF50; color: white;">全部批准</button>
            <button onclick="clearAll()" style="background-color: #9E9E9E; color: white;">清除所有决定</button>
        </div>

        <table id="suggestions-table">
            <thead>
                <tr>
                    <th style="width: 40px;">ID</th>
                    <th style="width: 80px;">置信度</th>
                    <th style="width: 180px;">建议合并为</th>
                    <th style="width: 400px;">包含的变体</th>
                    <th style="width: 80px;">总次数</th>
                    <th style="width: 300px;">原因</th>
                    <th style="width: 150px;">您的决定</th>
                </tr>
            </thead>
            <tbody id="table-body">
ROWS_PLACEHOLDER
            </tbody>
        </table>

        <button class="save-btn" onclick="saveDecisions()">保存决定到JSON文件</button>
    </div>

    <script>
        let decisions = {};

        function setDecision(id, decision) {
            const row = document.getElementById('row-' + id);
            if (decision === 'clear') {
                delete decisions[id];
                row.classList.remove('selected-approve', 'selected-reject');
                row.dataset.decision = 'pending';
            } else {
                decisions[id] = decision;
                row.classList.remove('selected-approve', 'selected-reject');
                if (decision === 'approve') {
                    row.classList.add('selected-approve');
                    row.dataset.decision = 'approved';
                } else {
                    row.classList.add('selected-reject');
                    row.dataset.decision = 'rejected';
                }
            }
            updateStats();
            applyFilters();
        }

        function updateStats() {
            const totalRows = document.querySelectorAll('#table-body tr').length;
            const approved = Object.values(decisions).filter(d => d === 'approve').length;
            const rejected = Object.values(decisions).filter(d => d === 'reject').length;
            const pending = totalRows - approved - rejected;
            document.getElementById('approved-count').textContent = approved;
            document.getElementById('rejected-count').textContent = rejected;
            document.getElementById('pending-count').textContent = pending;
        }

        function batchApproveAll() {
            if (!confirm('确定要批准所有建议吗？')) return;
            const rows = document.querySelectorAll('#table-body tr');
            rows.forEach(row => {
                const id = parseInt(row.id.replace('row-', ''));
                setDecision(id, 'approve');
            });
        }

        function clearAll() {
            if (!confirm('确定要清除所有决定吗？')) return;
            decisions = {};
            document.querySelectorAll('#table-body tr').forEach(row => {
                row.classList.remove('selected-approve', 'selected-reject');
                row.dataset.decision = 'pending';
            });
            updateStats();
        }

        function applyFilters() {
            const searchText = document.getElementById('search').value.toLowerCase();
            const decisionFilter = document.getElementById('filter-decision').value;
            document.querySelectorAll('#table-body tr').forEach(row => {
                const text = row.textContent.toLowerCase();
                const decision = row.dataset.decision;
                let show = true;
                if (searchText && !text.includes(searchText)) show = false;
                if (decisionFilter !== 'all') {
                    if (decisionFilter !== decision && decision !== decisionFilter) show = false;
                }
                row.style.display = show ? '' : 'none';
            });
        }

        function saveDecisions() {
            const result = {
                total: TOTAL_COUNT,
                decisions: decisions,
                summary: {
                    approved: Object.values(decisions).filter(d => d === 'approve').length,
                    rejected: Object.values(decisions).filter(d => d === 'reject').length
                }
            };
            const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'merge_decisions.json';
            a.click();
            URL.revokeObjectURL(url);
            alert('决定已保存!\\n批准: ' + result.summary.approved + ' | 拒绝: ' + result.summary.rejected);
        }

        document.getElementById('search').addEventListener('input', applyFilters);
        document.getElementById('filter-decision').addEventListener('change', applyFilters);
    </script>
</body>
</html>
"""

# 生成表格行
rows_html = ""
for idx, group in enumerate(merge_groups, 1):
    # 变体信息
    variants_html = ""
    for v in group['variants']:
        conv_str = ', '.join(v['conversations'][:3])
        if v['conv_count'] > 3:
            conv_str += f' (共{v["conv_count"]}个)'
        alias_str = ', '.join(v['aliases'][:3]) if v['aliases'] else '无'
        if len(v['aliases']) > 3:
            alias_str += f' +{len(v["aliases"])-3}个'

        variants_html += f"""<div class="variant-item">
                        <div class="variant-name">{v['name']}</div>
                        <div class="variant-details">次数: {v['count']} | 对话: {conv_str} | 别名: {alias_str}</div>
                    </div>"""

    rows_html += f"""<tr id="row-{idx}" data-confidence="{group['confidence']}" data-decision="pending">
                    <td>{idx}</td>
                    <td><span class="badge badge-{group['confidence']}">{group['confidence']}</span></td>
                    <td><strong>{group['suggested_name']}</strong></td>
                    <td>{variants_html}</td>
                    <td>{group['total_instances']}</td>
                    <td>{group['reason']}</td>
                    <td>
                        <div class="decision-buttons">
                            <button class="btn btn-approve" onclick="setDecision({idx}, 'approve')">批准</button>
                            <button class="btn btn-reject" onclick="setDecision({idx}, 'reject')">拒绝</button>
                        </div>
                    </td>
                </tr>
"""

# 替换模板
html_content = html_template.replace('TOTAL_COUNT', str(len(merge_groups)))
html_content = html_content.replace('ROWS_PLACEHOLDER', rows_html)

# 保存HTML
output_file = Path('person_merge_suggestions_complete.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"完成！")
print(f"  合并建议总数: {len(merge_groups)}")
high_count = sum(1 for g in merge_groups if g['confidence'] == 'high')
print(f"    高置信度: {high_count}")
print(f"\nHTML文件: {output_file}")
print(f"\n请在浏览器中打开审核，完成后点击'保存决定到JSON文件'")
print("=" * 80)
