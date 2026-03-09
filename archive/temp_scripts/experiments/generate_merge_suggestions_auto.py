#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成实体合并建议 - 自动加载.env配置
"""

import json
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime

# 加载.env文件
print("=== 加载配置 ===")
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    print(f"✓ 找到.env文件: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
else:
    print(f"✗ 找不到.env文件: {env_file}")
    exit(1)

# 从环境变量读取配置
PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

if not PROJECT_ID or not CREDENTIALS_JSON:
    print("✗ .env文件缺少必要配置")
    exit(1)

print(f"✓ Project ID: {PROJECT_ID}")
print(f"✓ Location: {LOCATION}")

# 创建临时credentials文件
credentials_dict = json.loads(CREDENTIALS_JSON)
temp_creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(credentials_dict, temp_creds_file)
temp_creds_file.close()

# 设置环境变量
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_file.name
print(f"✓ 已设置认证凭证")

# 初始化Vertex AI客户端
from anthropic import AnthropicVertex

client = AnthropicVertex(region=LOCATION, project_id=PROJECT_ID)
MODEL = "claude-sonnet-4-20250514"
print(f"✓ Vertex AI客户端已初始化")

# 加载数据
print("\n=== 加载数据 ===")
base_dir = Path(__file__).parent

with open(base_dir / 'merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    all_merged_data = json.load(f)

with open('/Users/mimimi/Downloads/wechat_memory_selection_2026-03-05.json', 'r', encoding='utf-8') as f:
    selection = json.load(f)

selected_names = set(friend['name'] for friend in selection['selected_friends'])
curated_merged_data = {name: all_merged_data[name] for name in selected_names if name in all_merged_data}

with open(base_dir / 'conversation_entity_edits_curated.json', 'r', encoding='utf-8') as f:
    entity_edits = json.load(f)

print(f"✓ 加载 {len(curated_merged_data)} 个对话")

# 分类对话
edited_conversations = []
unedited_conversations = []

for conv_name in curated_merged_data.keys():
    conv_edit = entity_edits.get('conversation_edits', {}).get(conv_name, {})
    has_excluded = conv_edit and conv_edit.get('excluded_entities', [])
    has_merges = conv_edit and conv_edit.get('manual_merges', [])

    if has_excluded or has_merges:
        edited_conversations.append(conv_name)
    else:
        unedited_conversations.append(conv_name)

print(f"✓ 已编辑: {len(edited_conversations)} 个")
print(f"✓ 未编辑: {len(unedited_conversations)} 个")

# 加载或创建进度文件
progress_file = base_dir / 'merge_suggestions_progress.json'
if progress_file.exists():
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    print(f"\n✓ 恢复进度: 已处理 {progress['processed']} 个对话")
else:
    progress = {
        'processed': 0,
        'total': len(curated_merged_data),
        'suggestions': {},
        'errors': [],
        'start_time': datetime.now().isoformat()
    }

def save_progress():
    """保存进度"""
    progress['last_update'] = datetime.now().isoformat()
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def analyze_conversation(conv_name, entities_data, existing_edits=None):
    """分析一个对话的实体并生成合并建议"""

    entity_names = sorted(entities_data.keys())

    if len(entity_names) < 2:
        return {
            'conversation': conv_name,
            'entity_count': len(entity_names),
            'merge_suggestions': [],
            'reason': '实体数量少于2个，无需合并'
        }

    # 限制实体数量
    if len(entity_names) > 100:
        entity_names = entity_names[:100]
        note = "（仅分析前100个实体）"
    else:
        note = ""

    # 构建prompt
    prompt = f"""你是一个实体合并专家。请分析以下对话中的Person实体列表，建议哪些实体应该合并。

对话名称: {conv_name}

实体列表（共{len(entity_names)}个）{note}:
{chr(10).join(f'{i+1}. {name}' for i, name in enumerate(entity_names))}

"""

    if existing_edits:
        excluded = existing_edits.get('excluded_entities', [])
        merges = existing_edits.get('manual_merges', [])

        if excluded:
            prompt += f"\n已排除的实体（请忽略）:\n{chr(10).join(f'- {e}' for e in excluded[:20])}\n"

        if merges:
            prompt += f"\n已有的合并规则:\n"
            for merge in merges[:10]:
                prompt += f"- {merge['final_name']}: {', '.join(merge['merged_entity_names'])}\n"
            prompt += "\n请建议进一步的合并（不要重复已有的合并）。\n"

    prompt += """
请按以下JSON格式输出合并建议:
{
  "merge_groups": [
    {
      "final_name": "最终名称",
      "entities": ["实体1", "实体2"],
      "reason": "合并原因"
    }
  ]
}

合并规则:
1. 只合并指向同一个人的不同名称（如"张涛"和"涛"）
2. 合并家庭关系表述（如"米雪川的母亲"、"妈妈"、"母亲"）
3. 不要合并明显不同的人
4. 确保最终名称是最明确的那个
5. 如果不确定，不要合并

只输出JSON，不要其他文字。
"""

    try:
        message = client.messages.create(
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            model=MODEL,
        )

        response_text = message.content[0].text.strip()

        # 提取JSON
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        result = json.loads(response_text)

        return {
            'conversation': conv_name,
            'entity_count': len(entity_names),
            'merge_suggestions': result.get('merge_groups', []),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'conversation': conv_name,
            'entity_count': len(entity_names),
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 主循环
print("\n=== 开始生成合并建议 ===")
print(f"总对话数: {len(curated_merged_data)}")
print(f"已处理: {progress['processed']}")
print(f"剩余: {len(curated_merged_data) - progress['processed']}")

start_index = progress['processed']
conversations = sorted(curated_merged_data.keys())

try:
    for i, conv_name in enumerate(conversations[start_index:], start=start_index):
        print(f"\n[{i+1}/{len(conversations)}] 处理: {conv_name}")

        entities_data = curated_merged_data[conv_name]
        existing_edits = entity_edits.get('conversation_edits', {}).get(conv_name)

        print(f"  实体数: {len(entities_data)}")
        if existing_edits:
            print(f"  已有编辑: 排除{len(existing_edits.get('excluded_entities', []))}个, 合并{len(existing_edits.get('manual_merges', []))}组")

        # 分析
        result = analyze_conversation(conv_name, entities_data, existing_edits)

        if 'error' in result:
            print(f"  ✗ 错误: {result['error']}")
            progress['errors'].append(result)
        else:
            suggestions = result.get('merge_suggestions', [])
            print(f"  ✓ 生成 {len(suggestions)} 个合并建议")
            if suggestions:
                for sug in suggestions[:3]:  # 显示前3个
                    print(f"    - {sug['final_name']}: {', '.join(sug['entities'][:3])}...")
            progress['suggestions'][conv_name] = result

        progress['processed'] = i + 1

        # 每10个对话保存一次进度
        if (i + 1) % 10 == 0:
            save_progress()
            print(f"\n>>> 进度已保存 ({i+1}/{len(conversations)}) <<<")

        # 速率限制
        time.sleep(2)

finally:
    # 清理临时文件
    try:
        os.unlink(temp_creds_file.name)
    except:
        pass

# 最终保存
save_progress()

# 生成最终报告
print("\n=== 生成完成 ===")
print(f"✓ 处理对话: {progress['processed']} 个")
print(f"✓ 成功: {len(progress['suggestions'])} 个")
print(f"✓ 错误: {len(progress['errors'])} 个")

total_merge_groups = sum(len(s.get('merge_suggestions', [])) for s in progress['suggestions'].values())
print(f"✓ 总合并建议: {total_merge_groups} 组")

# 保存最终结果
final_output = {
    'metadata': {
        'generated_at': datetime.now().isoformat(),
        'total_conversations': len(curated_merged_data),
        'processed': progress['processed'],
        'total_merge_groups': total_merge_groups,
        'model': MODEL,
        'project_id': PROJECT_ID
    },
    'suggestions': progress['suggestions'],
    'errors': progress['errors']
}

output_file = base_dir / 'ai_merge_suggestions.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(final_output, f, ensure_ascii=False, indent=2)

print(f"\n✓ 最终结果已保存: {output_file}")
print(f"✓ 进度文件: {progress_file}")

print("\n🎉 任务完成！你可以在醒来后查看 ai_merge_suggestions.json")
