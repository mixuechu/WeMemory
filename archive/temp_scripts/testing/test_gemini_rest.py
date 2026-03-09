#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Gemini REST API - 通过HTTP代理"""

import json
import os
import requests
from pathlib import Path
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
credentials.refresh(Request())
access_token = credentials.token

print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")
print("✓ 获取access token成功")

# Gemini REST API endpoint
model = "gemini-2.0-flash-exp"
url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# 测试简单请求
payload = {
    "contents": [{
        "role": "user",
        "parts": [{"text": "Say hello in one word"}]
    }],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 100
    }
}

print("\n测试Gemini REST API...")
response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=30)

if response.status_code == 200:
    result = response.json()
    text = result['candidates'][0]['content']['parts'][0]['text']
    print(f"✓ 成功: {text}")
else:
    print(f"✗ 错误 {response.status_code}: {response.text}")
    exit(1)

# 测试实体合并建议
print("\n测试实体合并建议...")

# 加载数据
base_dir = Path(__file__).parent
with open(base_dir / 'merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    all_merged_data = json.load(f)
with open('/Users/mimimi/Downloads/wechat_memory_selection_2026-03-05.json', 'r', encoding='utf-8') as f:
    selection = json.load(f)
selected_names = set(friend['name'] for friend in selection['selected_friends'])
curated_merged_data = {name: all_merged_data[name] for name in selected_names if name in all_merged_data}

# 测试第一个对话
conv_name = list(curated_merged_data.keys())[0]
entities = curated_merged_data[conv_name]
entity_names = sorted(entities.keys())[:15]  # 只测试前15个

print(f"对话: {conv_name}")
print(f"实体数: {len(entity_names)}")

prompt = f"""你是一个实体合并专家。请分析以下Person实体列表，建议哪些应该合并。

实体列表:
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

    print("\n原始响应:")
    print(response_text[:300])

    # 提取JSON
    if '```json' in response_text:
        response_text = response_text.split('```json')[1].split('```')[0].strip()
    elif '```' in response_text:
        response_text = response_text.split('```')[1].split('```')[0].strip()

    suggestions = json.loads(response_text)
    merge_groups = suggestions.get('merge_groups', [])

    print(f"\n✓ 生成 {len(merge_groups)} 个合并建议:")
    for sug in merge_groups:
        print(f"  - {sug['final_name']}: {', '.join(sug['entities'])}")
        print(f"    原因: {sug['reason']}")

    print("\n🎉 测试成功！REST API方式可用")
else:
    print(f"✗ 错误 {response.status_code}: {response.text}")
