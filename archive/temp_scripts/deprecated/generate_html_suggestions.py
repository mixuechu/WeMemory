#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Excel数据生成HTML版本的合并建议
"""
import pickle
from pathlib import Path
from collections import defaultdict, Counter
import re
import json

print("生成HTML格式的合并建议...")

# 1. 加载数据
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

# 2. 重新生成合并建议
merge_groups = []

def get_person_and_relation(name):
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

# 策略A: 明确关系词
relation_groups = defaultdict(lambda: defaultdict(list))
for name in person_index.keys():
    person, relation = get_person_and_relation(name)
    if person:
        relation_groups[person][relation].append(name)

for person_name, relations in relation_groups.items():
    for relation_word, names in relations.items():
        if len(names) <= 1:
            continue

        variants = []
        for name in names:
            instances = person_index[name]
            convs = Counter(persons[idx]['conversation'] for idx in instances)
            aliases = set()
            for idx in instances:
                if persons[idx]['aliases']:
                    aliases.update(persons[idx]['aliases'])

            variants.append({
                'name': name,
                'count': len(instances),
                'conversations': list(convs.keys()),
                'conv_count': len(convs),
                'aliases': list(aliases)
            })

        merge_groups.append({
            'suggested_name': f"{person_name}的{relation_word}",
            'confidence': 'high',
            'reason': f'都明确指向{person_name}的{relation_word}',
            'variants': variants,
            'total_instances': sum(v['count'] for v in variants)
        })

# 策略B: 同对话内匹配
processed_pairs = set()
for conv_name, person_names in conversation_persons.items():
    person_names = list(person_names)

    for i, name1 in enumerate(person_names):
        person1, rel1 = get_person_and_relation(name1)

        for name2 in person_names[i+1:]:
            person2, rel2 = get_person_and_relation(name2)

            pair_key = tuple(sorted([name1, name2]))
            if pair_key in processed_pairs:
                continue

            should_merge = False
            reason = ""

            if person1 and not person2 and rel1 == name2:
                should_merge = True
                reason = f'同对话"{conv_name}"内，"{name1}"和"{name2}"应为同一人'
            elif person2 and not person1 and rel2 == name1:
                should_merge = True
                reason = f'同对话"{conv_name}"内，"{name2}"和"{name1}"应为同一人'

            if should_merge:
                processed_pairs.add(pair_key)

                already_in_group = False
                for group in merge_groups:
                    existing = [v['name'] for v in group['variants']]
                    if name1 in existing or name2 in existing:
                        already_in_group = True
                        break

                if not already_in_group:
                    variants = []
                    for name in [name1, name2]:
                        instances = person_index[name]
                        convs = Counter(persons[idx]['conversation'] for idx in instances)
                        aliases = set()
                        for idx in instances:
                            if persons[idx]['aliases']:
                                aliases.update(persons[idx]['aliases'])

                        variants.append({
                            'name': name,
                            'count': len(instances),
                            'conversations': list(convs.keys()),
                            'conv_count': len(convs),
                            'aliases': list(aliases)
                        })

                    merge_groups.append({
                        'suggested_name': variants[0]['name'] if variants[0]['count'] >= variants[1]['count'] else variants[1]['name'],
                        'confidence': 'high',
                        'reason': reason,
                        'variants': variants,
                        'total_instances': sum(v['count'] for v in variants)
                    })

# 排序
confidence_order = {'high': 0, 'medium': 1, 'low': 2}
merge_groups.sort(key=lambda x: (confidence_order.get(x['confidence'], 3), -x['total_instances']))

# 3. 生成HTML
html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Person实体合并建议</title>
    <style>
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 20px;
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
        .controls input, .controls select, .controls button {
            margin: 5px;
            padding: 8px 12px;
            font-size: 14px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .variant-item {
            margin-bottom: 10px;
            padding: 8px;
            background-color: #f9f9f9;
            border-left: 3px solid #4CAF50;
        }
        .variant-name {
            font-weight: bold;
            color: #2196F3;
        }
        .variant-details {
            font-size: 12px;
            color: #666;
            margin-top: 3px;
        }
        .badge-high {
            background-color: #4CAF50;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .badge-medium {
            background-color: #FF9800;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .decision-buttons {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-approve {
            background-color: #4CAF50;
            color: white;
        }
        .btn-approve:hover {
            background-color: #45a049;
        }
        .btn-reject {
            background-color: #f44336;
            color: white;
        }
        .btn-reject:hover {
            background-color: #da190b;
        }
        .btn-clear {
            background-color: #9E9E9E;
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
        .save-btn:hover {
            background-color: #0b7dda;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Person实体合并建议审核</h1>

        <div class="stats">
            <strong>统计信息：</strong>
            <span id="total-count">总建议数: """ + str(len(merge_groups)) + """</span> |
            <span id="approved-count">已批准: 0</span> |
            <span id="rejected-count">已拒绝: 0</span> |
            <span id="pending-count">待处理: """ + str(len(merge_groups)) + """</span>
        </div>

        <div class="controls">
            <input type="text" id="search" placeholder="搜索人名..." style="width: 300px;">
            <select id="filter-confidence">
                <option value="all">所有置信度</option>
                <option value="high">高置信度</option>
                <option value="medium">中等置信度</option>
                <option value="low">低置信度</option>
            </select>
            <select id="filter-decision">
                <option value="all">所有决定</option>
                <option value="pending">待处理</option>
                <option value="approved">已批准</option>
                <option value="rejected">已拒绝</option>
            </select>
            <button onclick="batchApproveAll()">全部批准</button>
            <button onclick="clearAll()">清除所有决定</button>
        </div>

        <table id="suggestions-table">
            <thead>
                <tr>
                    <th style="width: 50px;">ID</th>
                    <th style="width: 100px;">置信度</th>
                    <th style="width: 200px;">建议合并为</th>
                    <th style="width: 400px;">包含的变体</th>
                    <th style="width: 100px;">总次数</th>
                    <th style="width: 300px;">原因</th>
                    <th style="width: 180px;">您的决定</th>
                </tr>
            </thead>
            <tbody id="table-body">
"""

# 添加数据行
for idx, group in enumerate(merge_groups, 1):
    # 变体信息HTML
    variants_html = ""
    for v in group['variants']:
        conv_list = v['conversations'][:5]
        conv_str = ', '.join(conv_list)
        if v['conv_count'] > 5:
            conv_str += f' (共{v["conv_count"]}个对话)'

        alias_str = ', '.join(v['aliases'][:5]) if v['aliases'] else '无'
        if len(v['aliases']) > 5:
            alias_str += f' +{len(v["aliases"])-5}个'

        variants_html += f"""
                    <div class="variant-item">
                        <div class="variant-name">{v['name']}</div>
                        <div class="variant-details">
                            次数: {v['count']} | 对话: {conv_str}<br>
                            别名: {alias_str}
                        </div>
                    </div>
        """

    confidence_badge = f'<span class="badge-{group["confidence"]}">{group["confidence"]}</span>'

    html_content += f"""
                <tr id="row-{idx}" data-confidence="{group['confidence']}" data-decision="pending">
                    <td>{idx}</td>
                    <td>{confidence_badge}</td>
                    <td><strong>{group['suggested_name']}</strong></td>
                    <td>{variants_html}</td>
                    <td>{group['total_instances']}</td>
                    <td>{group['reason']}</td>
                    <td>
                        <div class="decision-buttons">
                            <button class="btn btn-approve" onclick="setDecision({idx}, 'approve')">批准</button>
                            <button class="btn btn-reject" onclick="setDecision({idx}, 'reject')">拒绝</button>
                            <button class="btn btn-clear" onclick="setDecision({idx}, 'clear')">清除</button>
                        </div>
                    </td>
                </tr>
    """

# JavaScript代码
html_content += """
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
                } else if (decision === 'reject') {
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

            document.getElementById('approved-count').textContent = '已批准: ' + approved;
            document.getElementById('rejected-count').textContent = '已拒绝: ' + rejected;
            document.getElementById('pending-count').textContent = '待处理: ' + pending;
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
            const rows = document.querySelectorAll('#table-body tr');
            rows.forEach(row => {
                row.classList.remove('selected-approve', 'selected-reject');
                row.dataset.decision = 'pending';
            });
            updateStats();
        }

        function applyFilters() {
            const searchText = document.getElementById('search').value.toLowerCase();
            const confFilter = document.getElementById('filter-confidence').value;
            const decisionFilter = document.getElementById('filter-decision').value;

            const rows = document.querySelectorAll('#table-body tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const confidence = row.dataset.confidence;
                const decision = row.dataset.decision;

                let show = true;

                if (searchText && !text.includes(searchText)) {
                    show = false;
                }

                if (confFilter !== 'all' && confidence !== confFilter) {
                    show = false;
                }

                if (decisionFilter !== 'all') {
                    if (decisionFilter === 'pending' && decision !== 'pending') show = false;
                    if (decisionFilter === 'approved' && decision !== 'approved') show = false;
                    if (decisionFilter === 'rejected' && decision !== 'rejected') show = false;
                }

                row.style.display = show ? '' : 'none';
            });
        }

        function saveDecisions() {
            const result = {
                total: """ + str(len(merge_groups)) + """,
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

            alert('决定已保存到 merge_decisions.json\\n批准: ' + result.summary.approved + ' 拒绝: ' + result.summary.rejected);
        }

        // 事件监听
        document.getElementById('search').addEventListener('input', applyFilters);
        document.getElementById('filter-confidence').addEventListener('change', applyFilters);
        document.getElementById('filter-decision').addEventListener('change', applyFilters);
    </script>
</body>
</html>
"""

# 保存HTML
output_file = Path('person_merge_suggestions.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML文件已生成: {output_file}")
print(f"合并建议数: {len(merge_groups)}")
print(f"\n请在浏览器中打开 person_merge_suggestions.html 进行审核")
