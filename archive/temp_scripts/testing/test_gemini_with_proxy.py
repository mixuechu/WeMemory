#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试Gemini - 配置代理"""

import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 设置代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
os.environ['GRPC_PROXY'] = 'http://127.0.0.1:7890'

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 先测试简单的对话
print("测试Gemini连接（使用代理 127.0.0.1:7890）...")
model = GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content("Say hello")
print(f"✓ Gemini连接成功: {response.text[:50]}")

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
entity_names = sorted(entities.keys())[:20]  # 只测试前20个

print(f"\n测试对话: {conv_name}")
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

response = model.generate_content(prompt, generation_config={"temperature": 0.1})
response_text = response.text.strip()

print("\n原始响应:")
print(response_text[:500])

# 提取JSON
if '```json' in response_text:
    response_text = response_text.split('```json')[1].split('```')[0].strip()
elif '```' in response_text:
    response_text = response_text.split('```')[1].split('```')[0].strip()

result = json.loads(response_text)
suggestions = result.get('merge_groups', [])

print(f"\n✓ 生成 {len(suggestions)} 个合并建议:")
for sug in suggestions:
    print(f"  - {sug['final_name']}: {', '.join(sug['entities'])}")
    print(f"    原因: {sug['reason']}")

print("\n🎉 测试成功！")
