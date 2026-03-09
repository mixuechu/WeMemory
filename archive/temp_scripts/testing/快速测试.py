#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试 - 小对话"""

import json
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.auth.transport.requests import Request

start_time = time.time()

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

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

MODEL = "gemini-2.5-flash"

# 加载数据
base_dir = Path(__file__).parent
with open(base_dir / 'merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    all_merged_data = json.load(f)

# 找一个中等大小的对话（30-50个实体）
conversations = sorted(all_merged_data.items(), key=lambda x: len(x[1]))
medium_conv = [c for c in conversations if 30 <= len(c[1]) <= 50][0]
conv_name, entities = medium_conv

print(f"测试对话: {conv_name}")
print(f"实体数: {len(entities)}")

entity_names = sorted(entities.keys())[:40]  # 测试40个

prompt = f"""你是一个实体合并专家。请分析以下Person实体列表，建议哪些应该合并。

实体列表（共{len(entity_names)}个）:
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

只输出JSON。"""

api_start = time.time()
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
        "maxOutputTokens": 65536
    }
}

print("\n调用API...")
response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=120)
api_time = time.time() - api_start

if response.status_code == 200:
    result = response.json()
    response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

    if '```json' in response_text:
        response_text = response_text.split('```json')[1].split('```')[0].strip()

    parsed = json.loads(response_text)
    suggestions = parsed.get('merge_groups', [])

    total_time = time.time() - start_time

    print(f"\n✓ 成功")
    print(f"  API调用时间: {api_time:.1f}秒")
    print(f"  总耗时: {total_time:.1f}秒")
    print(f"  生成建议: {len(suggestions)} 组")

    print(f"\n估算:")
    print(f"  40个实体耗时: {total_time:.1f}秒")
    print(f"  250个实体预计: {total_time * 250 / 40:.1f}秒 = {total_time * 250 / 40 / 60:.1f}分钟")
    print(f"  675个实体(分3批)预计: {total_time * 675 / 40:.1f}秒 = {total_time * 675 / 40 / 60:.1f}分钟")
    print(f"  138个对话(平均41实体)预计: {total_time * 138:.1f}秒 = {total_time * 138 / 60:.1f}分钟 = {total_time * 138 / 3600:.1f}小时")
else:
    print(f"✗ 错误: {response.status_code}")
