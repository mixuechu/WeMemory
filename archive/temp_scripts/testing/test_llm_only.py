#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仅测试LLM调用"""

import sys
import io
import json
import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv(dotenv_path='../.env')

# Gemini配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

model = GenerativeModel("gemini-2.5-flash")

print("测试LLM判断实体合并...")
print("=" * 80)

# 测试案例1: Hunter vs hunter
person1 = {
    'name': 'Hunter',
    'conversation_name': '吉月',
    'aliases': [],
    'relationships_count': 5
}

person2 = {
    'name': 'hunter',
    'conversation_name': '吉月',
    'aliases': [],
    'relationships_count': 3
}

prompt = f"""你是知识图谱实体去重专家。请判断以下两个Person实体是否应该合并。

实体1:
  姓名: {person1['name']}
  对话: {person1['conversation_name']}
  关系数: {person1['relationships_count']}

实体2:
  姓名: {person2['name']}
  对话: {person2['conversation_name']}
  关系数: {person2['relationships_count']}

判断规则：
1. 如果是同一个人（大小写不同、昵称/全名、格式不一致），应该合并
2. 如果是不同的人，应该保持独立

请返回JSON格式：
{{
  "action": "merge" 或 "keep_separate",
  "confidence": 0.0-1.0,
  "reason": "判断理由",
  "target": "person1" 或 "person2" (如果merge，建议保留哪个名字，通常保留首字母大写的)
}}
"""

print(f"查询: {person1['name']} vs {person2['name']}")
print("调用LLM...")

response = model.generate_content(prompt)
result_text = response.text.strip()

print(f"\nLLM原始响应:")
print(result_text)

# 提取JSON
if '```json' in result_text:
    result_text = result_text.split('```json')[1].split('```')[0].strip()
elif '```' in result_text:
    result_text = result_text.split('```')[1].split('```')[0].strip()

print(f"\n提取的JSON:")
print(result_text)

result = json.loads(result_text)
print(f"\n解析结果:")
print(json.dumps(result, ensure_ascii=False, indent=2))

print("\n✅ 测试成功！")
