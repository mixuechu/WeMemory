#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试完整流程 - 只处理2个对话"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 设置代理
proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

# 获取access token
creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

MODEL = "gemini-2.5-flash"

print(f"Project: {PROJECT_ID}")
print(f"Model: {MODEL}\n")

# 加载数据
base_dir = Path(__file__).parent
with open(base_dir / 'merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    all_merged_data = json.load(f)
with open('/Users/mimimi/Downloads/wechat_memory_selection_2026-03-05.json', 'r', encoding='utf-8') as f:
    selection = json.load(f)
selected_names = set(friend['name'] for friend in selection['selected_friends'])
curated_merged_data = {name: all_merged_data[name] for name in selected_names if name in all_merged_data}
with open(base_dir / 'conversation_entity_edits_curated.json', 'r', encoding='utf-8') as f:
    entity_edits = json.load(f)

# 测试前2个对话
conversations = sorted(curated_merged_data.keys())[:2]
results = {}

for i, conv_name in enumerate(conversations):
    print(f"\n[{i+1}/2] 处理: {conv_name}")

    entities_data = curated_merged_data[conv_name]
    entity_names = sorted(entities_data.keys())[:20]  # 只测试前20个

    existing_edits = entity_edits.get('conversation_edits', {}).get(conv_name)

    print(f"  实体数: {len(entity_names)}")
    if existing_edits:
        print(f"  已有编辑: 排除{len(existing_edits.get('excluded_entities', []))}个, 合并{len(existing_edits.get('manual_merges', []))}组")

    # 构建prompt
    prompt = f"""你是一个实体合并专家。请分析以下Person实体列表，建议哪些应该合并。

对话: {conv_name}

实体列表（前20个）:
{chr(10).join(f'{i+1}. {name}' for i, name in enumerate(entity_names))}

请按以下JSON格式输出:
{{
  "merge_groups": [
    {{
      "final_name": "最终名称",
      "entities": ["实体1", "实体2"],
      "reason": "合并原因"
    }}
  ]
}}

合并规则:
1. 只合并指向同一个人的不同名称
2. 合并家庭关系表述
3. 不要合并明显不同的人

只输出JSON，不要其他文字。"""

    # API调用
    credentials.refresh(Request())
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096
        }
    }

    response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=60)

    if response.status_code == 200:
        result = response.json()
        response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

        # 提取JSON
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        parsed = json.loads(response_text)
        suggestions = parsed.get('merge_groups', [])

        print(f"  ✓ 生成 {len(suggestions)} 个合并建议:")
        for sug in suggestions:
            print(f"    - {sug['final_name']}: {', '.join(sug['entities'])}")
            print(f"      原因: {sug['reason']}")

        results[conv_name] = {
            'conversation': conv_name,
            'entity_count': len(entity_names),
            'merge_suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }
    else:
        print(f"  ✗ 错误 {response.status_code}: {response.text}")
        results[conv_name] = {
            'conversation': conv_name,
            'error': f"{response.status_code}: {response.text}"
        }

# 保存测试结果
output_file = base_dir / 'test_merge_suggestions.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({'test_results': results}, f, ensure_ascii=False, indent=2)

print(f"\n✓ 测试结果已保存: {output_file}")
print("\n🎉 测试成功！完整脚本可以使用")
