#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成最终的补充HTML，包含所有成功处理的对话"""
import json, pickle
from pathlib import Path

# 加载person database
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
conversation_persons = db['conversation_persons']

# 收集所有结果
all_results = []
results_by_conv = {}

# 1. 加载retry_results.json (46个对话)
try:
    with open('retry_results.json', 'r', encoding='utf-8') as f:
        retry_results = json.load(f)
    for r in retry_results:
        conv = r['conversation']
        if conv not in results_by_conv or len(r.get('merge_groups', [])) > len(results_by_conv[conv].get('merge_groups', [])):
            results_by_conv[conv] = r
    print(f"Loaded retry_results.json: {len(retry_results)} conversations")
except FileNotFoundError:
    print("retry_results.json not found")

# 2. 加载large_conversations_results.json (7个批处理对话)
try:
    with open('large_conversations_results.json', 'r', encoding='utf-8') as f:
        batch_results = json.load(f)
    for r in batch_results:
        conv = r['conversation']
        # 批处理结果优先（因为更新）
        results_by_conv[conv] = r
    print(f"Loaded large_conversations_results.json: {len(batch_results)} conversations")
except FileNotFoundError:
    print("large_conversations_results.json not found")

# 3. 尝试从现有HTML中提取数据（作为备份）
# 但这需要解析HTML，暂时跳过

# 合并所有唯一结果
all_results = list(results_by_conv.values())

# 只保留有merge_groups的对话
all_results = [r for r in all_results if r.get('merge_groups') and len(r['merge_groups']) > 0]

# 按合并组数量排序
all_results.sort(key=lambda x: len(x['merge_groups']), reverse=True)

print(f"\n=== 最终统计 ===")
print(f"总对话数: {len(all_results)}")
print(f"总合并组数: {sum(len(r['merge_groups']) for r in all_results)}")

# 保存合并后的JSON
output_json = 'final_supplement_results.json'
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到: {output_json}")

# 生成HTML
html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Person合并建议审核（补充）</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header h1 {{ color: #333; margin-bottom: 10px; }}
        .stats {{ display: flex; gap: 20px; margin-top: 15px; }}
        .stat-item {{ background: #f8f9fa; padding: 10px 15px; border-radius: 4px; }}
        .stat-item .label {{ color: #666; font-size: 12px; }}
        .stat-item .value {{ color: #2196F3; font-size: 24px; font-weight: bold; }}
        .progress {{ background: #e0e0e0; height: 8px; border-radius: 4px; margin-top: 15px; overflow: hidden; }}
        .progress-bar {{ background: linear-gradient(90deg, #4CAF50, #2196F3); height: 100%; width: 0; transition: width 0.3s; }}
        .conversation {{ background: white; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }}
        .conv-header {{ padding: 15px 20px; background: #fafafa; border-bottom: 1px solid #e0e0e0; cursor: pointer; user-select: none; }}
        .conv-header:hover {{ background: #f0f0f0; }}
        .conv-title {{ font-size: 16px; font-weight: bold; color: #333; }}
        .conv-meta {{ color: #666; font-size: 13px; margin-top: 5px; }}
        .conv-content {{ padding: 20px; display: none; }}
        .conv-content.active {{ display: block; }}
        .merge-group {{ border: 1px solid #e0e0e0; border-radius: 6px; padding: 15px; margin-bottom: 15px; background: #fafafa; }}
        .merge-group.approved {{ border-color: #4CAF50; background: #f1f8f4; }}
        .merge-group.rejected {{ border-color: #f44336; background: #fef1f0; }}
        .group-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px; }}
        .suggested-name {{ font-size: 16px; font-weight: bold; color: #2196F3; margin-bottom: 5px; }}
        .merge-reason {{ color: #666; font-size: 13px; margin-bottom: 10px; }}
        .variants {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }}
        .variant {{ background: white; border: 1px solid #ddd; border-radius: 4px; padding: 8px 12px; }}
        .variant-name {{ font-weight: bold; color: #333; }}
        .variant-count {{ color: #666; font-size: 12px; }}
        .variant-aliases {{ color: #999; font-size: 11px; margin-top: 2px; }}
        .actions {{ display: flex; gap: 10px; }}
        .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s; }}
        .btn-approve {{ background: #4CAF50; color: white; }}
        .btn-approve:hover {{ background: #45a049; }}
        .btn-reject {{ background: #f44336; color: white; }}
        .btn-reject:hover {{ background: #da190b; }}
        .btn-edit {{ background: #FF9800; color: white; }}
        .btn-edit:hover {{ background: #e68900; }}
        .edit-fields {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; display: none; }}
        .edit-fields.active {{ display: block; }}
        .edit-field {{ margin-bottom: 10px; }}
        .edit-field label {{ display: block; margin-bottom: 5px; color: #666; font-size: 13px; }}
        .edit-field input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
        .save-button {{ background: #2196F3; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }}
        .save-button:hover {{ background: #0b7dda; }}
        .bottom-actions {{ position: fixed; bottom: 0; left: 0; right: 0; background: white; padding: 15px 20px; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
        .save-results {{ background: #4CAF50; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }}
        .save-results:hover {{ background: #45a049; }}
        .status-text {{ color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Person实体合并建议审核（补充部分）</h1>
        <div class="stats">
            <div class="stat-item">
                <div class="label">对话总数</div>
                <div class="value" id="total-convs">{total_convs}</div>
            </div>
            <div class="stat-item">
                <div class="label">合并组总数</div>
                <div class="value" id="total-groups">{total_groups}</div>
            </div>
            <div class="stat-item">
                <div class="label">已批准</div>
                <div class="value" id="approved-count" style="color: #4CAF50;">0</div>
            </div>
            <div class="stat-item">
                <div class="label">已拒绝</div>
                <div class="value" id="rejected-count" style="color: #f44336;">0</div>
            </div>
        </div>
        <div class="progress">
            <div class="progress-bar" id="progress-bar"></div>
        </div>
    </div>

    <div id="conversations"></div>

    <div class="bottom-actions">
        <span class="status-text" id="status-text">请审核以上合并建议</span>
        <button class="save-results" onclick="saveDecisions()">保存审核结果</button>
    </div>

    <script>
        const mergeData = {merge_data};
        const decisions = {{}};

        function renderConversations() {{
            const container = document.getElementById('conversations');
            mergeData.forEach((conv, convIdx) => {{
                const convDiv = document.createElement('div');
                convDiv.className = 'conversation';
                convDiv.innerHTML = `
                    <div class="conv-header" onclick="toggleConv(${{convIdx}})">
                        <div class="conv-title">${{conv.conversation}}</div>
                        <div class="conv-meta">${{conv.total_persons}} 个Person，${{conv.merge_groups.length}} 个合并组</div>
                    </div>
                    <div class="conv-content" id="conv-${{convIdx}}">
                        ${{conv.merge_groups.map((group, groupIdx) => renderGroup(convIdx, groupIdx, group)).join('')}}
                    </div>
                `;
                container.appendChild(convDiv);
            }});
        }}

        function renderGroup(convIdx, groupIdx, group) {{
            const key = `${{convIdx}}-${{groupIdx}}`;
            return `
                <div class="merge-group" id="group-${{key}}">
                    <div class="group-header">
                        <div>
                            <div class="suggested-name" id="name-${{key}}">${{group.suggested_name}}</div>
                            <div class="merge-reason">${{group.reason}}</div>
                        </div>
                    </div>
                    <div class="variants">
                        ${{group.variant_details.map(v => `
                            <div class="variant">
                                <div class="variant-name">${{v.name}}</div>
                                <div class="variant-count">出现 ${{v.count}} 次</div>
                                ${{v.aliases && v.aliases.length > 0 ? `<div class="variant-aliases">别名: ${{v.aliases.join(', ')}}</div>` : ''}}
                            </div>
                        `).join('')}}
                    </div>
                    <div class="actions">
                        <button class="btn btn-approve" onclick="approve('${{key}}', ${{convIdx}}, ${{groupIdx}})">✓ 批准合并</button>
                        <button class="btn btn-reject" onclick="reject('${{key}}')">✗ 拒绝</button>
                        <button class="btn btn-edit" onclick="toggleEdit('${{key}}')">✎ 编辑</button>
                    </div>
                    <div class="edit-fields" id="edit-${{key}}">
                        <div class="edit-field">
                            <label>合并后的名称：</label>
                            <input type="text" id="edit-name-${{key}}" value="${{group.suggested_name}}">
                        </div>
                        <div class="edit-field">
                            <label>所有别名（逗号分隔）：</label>
                            <input type="text" id="edit-aliases-${{key}}" value="${{group.variants.join(', ')}}">
                        </div>
                        <button class="save-button" onclick="saveEdit('${{key}}', ${{convIdx}}, ${{groupIdx}})">保存修改</button>
                    </div>
                </div>
            `;
        }}

        function toggleConv(idx) {{
            const content = document.getElementById(`conv-${{idx}}`);
            content.classList.toggle('active');
        }}

        function approve(key, convIdx, groupIdx) {{
            const group = mergeData[convIdx].merge_groups[groupIdx];
            decisions[key] = {{
                action: 'approve',
                conversation: mergeData[convIdx].conversation,
                final_name: group.suggested_name,
                variants: group.variants,
                reason: group.reason
            }};
            document.getElementById(`group-${{key}}`).classList.add('approved');
            document.getElementById(`group-${{key}}`).classList.remove('rejected');
            updateStats();
        }}

        function reject(key) {{
            decisions[key] = {{ action: 'reject' }};
            document.getElementById(`group-${{key}}`).classList.add('rejected');
            document.getElementById(`group-${{key}}`).classList.remove('approved');
            updateStats();
        }}

        function toggleEdit(key) {{
            document.getElementById(`edit-${{key}}`).classList.toggle('active');
        }}

        function saveEdit(key, convIdx, groupIdx) {{
            const newName = document.getElementById(`edit-name-${{key}}`).value;
            const newAliases = document.getElementById(`edit-aliases-${{key}}`).value.split(',').map(s => s.trim());

            mergeData[convIdx].merge_groups[groupIdx].suggested_name = newName;
            mergeData[convIdx].merge_groups[groupIdx].variants = newAliases;

            document.getElementById(`name-${{key}}`).textContent = newName;
            document.getElementById(`edit-${{key}}`).classList.remove('active');

            if (decisions[key] && decisions[key].action === 'approve') {{
                decisions[key].final_name = newName;
                decisions[key].variants = newAliases;
            }}
        }}

        function updateStats() {{
            const approved = Object.values(decisions).filter(d => d.action === 'approve').length;
            const rejected = Object.values(decisions).filter(d => d.action === 'reject').length;
            const total = {total_groups};

            document.getElementById('approved-count').textContent = approved;
            document.getElementById('rejected-count').textContent = rejected;
            document.getElementById('progress-bar').style.width = `${{(approved + rejected) / total * 100}}%`;

            if (approved + rejected === total) {{
                document.getElementById('status-text').textContent = '✓ 全部审核完成！';
                document.getElementById('status-text').style.color = '#4CAF50';
            }}
        }}

        function saveDecisions() {{
            const approved = Object.values(decisions).filter(d => d.action === 'approve');
            const rejected = Object.values(decisions).filter(d => d.action === 'reject').length;

            const result = {{
                total_decisions: Object.keys(decisions).length,
                approved: approved,
                rejected_count: rejected,
                timestamp: new Date().toISOString()
            }};

            const blob = new Blob([JSON.stringify(result, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'merge_decisions_supplement.json';
            a.click();

            alert(`已保存 ${{approved.length}} 个批准的合并建议！`);
        }}

        renderConversations();
    </script>
</body>
</html>'''

html_content = html_template.format(
    total_convs=len(all_results),
    total_groups=sum(len(r['merge_groups']) for r in all_results),
    merge_data=json.dumps(all_results, ensure_ascii=False)
)

output_html = 'person_merge_suggestions_ai_supplement_final.html'
with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML已生成: {output_html}")
print(f"\n现在可以在浏览器中打开该文件进行审核")
