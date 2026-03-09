#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Vertex AI生成Person合并建议
"""
import os
import sys
import json
import pickle
from pathlib import Path
from google.oauth2 import service_account
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

print("=" * 80)
print("使用Vertex AI生成Person合并建议")
print("=" * 80)

# 初始化Vertex AI
print("\n初始化Vertex AI...")
project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json_str = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

if not all([project_id, location, credentials_json_str]):
    print("错误：缺少Google Cloud配置")
    sys.exit(1)

credentials_dict = json.loads(credentials_json_str)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)

vertexai.init(project=project_id, location=location, credentials=credentials)
model = GenerativeModel("gemini-2.5-flash")

print(f"  项目: {project_id}")
print(f"  位置: {location}")
print(f"  模型: gemini-2.5-flash")

# 加载数据
print("\n加载Person数据...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print(f"  总对话数: {len(conversation_persons)}")

# 准备prompt模板
MERGE_PROMPT = """你是一个知识图谱专家，需要分析微信聊天对话中提取的Person实体，判断哪些应该合并。

对话名称：{conversation_name}

对话中的Person列表：
{person_list}

请分析哪些Person应该合并为同一个实体。注意：
1. 同一个人的不同称呼应该合并（如"张三"和"张三律师"）
2. 关系称呼如果明确指向同一个人应该合并（如"米雪川的妈妈"和"米雪川妈妈"）
3. 不要把不同的人合并（如"张三"和"张三的老公"是两个人）
4. 不要把纯关系词合并（如"妈妈"在不同上下文可能指不同的人）
5. 要考虑别名信息

请以JSON格式返回合并建议，格式如下：
{{
  "merge_groups": [
    {{
      "suggested_name": "建议使用的名字",
      "reason": "合并原因",
      "variants": ["人名1", "人名2", "人名3"]
    }}
  ]
}}

如果没有需要合并的，返回空数组。只返回JSON，不要其他解释。
"""

def analyze_conversation_with_ai(conv_name, person_names_set):
    """使用AI分析一个对话的合并建议"""
    person_names = list(person_names_set)

    if len(person_names) < 2:
        return None

    # 收集每个人的详细信息
    person_info = []
    for name in person_names:
        instances = [persons[idx] for idx in person_index.get(name, [])
                     if persons[idx]['conversation'] == conv_name]

        if instances:
            aliases = set()
            for inst in instances:
                if inst.get('aliases'):
                    aliases.update(inst['aliases'])

            person_info.append({
                'name': name,
                'count': len(instances),
                'aliases': list(aliases)[:5]
            })

    # 构建person列表字符串
    person_list_str = "\n".join([
        f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})"
        for p in person_info
    ])

    # 调用AI
    prompt = MERGE_PROMPT.format(
        conversation_name=conv_name,
        person_list=person_list_str
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 2048,
            }
        )

        # 解析JSON
        result_text = response.text.strip()
        # 移除可能的markdown代码块标记
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        result = json.loads(result_text)
        merge_groups = result.get('merge_groups', [])

        if not merge_groups:
            return None

        # 添加详细信息
        for group in merge_groups:
            variant_details = []
            for variant_name in group['variants']:
                if variant_name in person_names_set:
                    instances = [persons[idx] for idx in person_index.get(variant_name, [])
                                 if persons[idx]['conversation'] == conv_name]
                    aliases = set()
                    for inst in instances:
                        if inst.get('aliases'):
                            aliases.update(inst['aliases'])

                    variant_details.append({
                        'name': variant_name,
                        'count': len(instances),
                        'aliases': list(aliases)[:5]
                    })

            group['variant_details'] = variant_details

        return {
            'conversation': conv_name,
            'total_persons': len(person_names),
            'merge_groups': merge_groups
        }

    except Exception as e:
        print(f"  错误 - {conv_name}: {e}")
        return None

# 处理所有对话
print("\n使用AI分析对话...")
print("  (使用多线程并发处理)")

all_suggestions = []
total = len(conversation_persons)
completed = 0

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(analyze_conversation_with_ai, conv_name, person_names): conv_name
        for conv_name, person_names in conversation_persons.items()
    }

    for future in as_completed(futures):
        completed += 1
        if completed % 50 == 0:
            print(f"  进度: {completed}/{total}")

        result = future.result()
        if result:
            all_suggestions.append(result)

print(f"\n完成！")
print(f"  有合并建议的对话数: {len(all_suggestions)}")
print(f"  总合并组数: {sum(len(s['merge_groups']) for s in all_suggestions)}")

# 按合并组数量排序
all_suggestions.sort(key=lambda x: len(x['merge_groups']), reverse=True)

# 生成HTML
print("\n生成HTML...")

html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Person合并建议 - AI生成</title>
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
            margin-top: 5px;
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
        <h1>Person合并建议 - AI生成（按对话分组）</h1>

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

        html_content += f"""
                <div class="merge-group" id="group-{group_id}" data-decision="">
                    <strong>建议合并为: {group['suggested_name']}</strong>
                    <div class="merge-reason">原因: {group['reason']}</div>
                    <div style="margin-top: 8px;">
"""

        for variant in group.get('variant_details', []):
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
            a.download = 'merge_decisions_ai.json';
            a.click();
            URL.revokeObjectURL(url);

            alert('决定已保存!\\n批准: ' + result.summary.approved + ' | 拒绝: ' + result.summary.rejected);
        }

        // 搜索功能
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
output_file = Path('person_merge_suggestions_ai.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"完成！HTML文件: {output_file}")
print("\n使用说明:")
print("  1. 打开HTML文件")
print("  2. 点击对话展开查看合并建议")
print("  3. 对每组点击'批准'或'拒绝'")
print("  4. 完成后点击'保存所有决定到JSON'")
print("=" * 80)
