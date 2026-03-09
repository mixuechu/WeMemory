#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试批量清理器 - 不设置stdout"""

# 不设置stdout，直接导入
import sys
import json
import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account

print("步骤1: 加载环境变量...")
load_dotenv(dotenv_path='../.env')

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

print("步骤2: 初始化Vertexai...")
creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

print("步骤3: 创建模型...")
model = GenerativeModel("gemini-2.5-flash")

print("步骤4: 测试LLM调用...")

# 测试简单调用
test_pairs = [
    {
        'id': 0,
        'person1': {'name': 'Hunter', 'conversation_name': '吉月', 'aliases': [], 'relationships_count': 5},
        'person2': {'name': 'hunter', 'conversation_name': '吉月', 'aliases': [], 'relationships_count': 3}
    },
    {
        'id': 1,
        'person1': {'name': 'Thomas', 'conversation_name': '吉月', 'aliases': [], 'relationships_count': 4},
        'person2': {'name': 'thomas', 'conversation_name': '吉月', 'aliases': [], 'relationships_count': 2}
    }
]

prompt = """你是知识图谱实体去重专家。我会给你一批Person实体对，请判断每一对是否应该合并。

待判断的实体对：

【实体对 0】
  实体1: 姓名=Hunter, 对话=吉月, 关系数=5
  实体2: 姓名=hunter, 对话=吉月, 关系数=3

【实体对 1】
  实体1: 姓名=Thomas, 对话=吉月, 关系数=4
  实体2: 姓名=thomas, 对话=吉月, 关系数=2

请返回JSON数组：
[
  {
    "id": 0,
    "action": "merge" 或 "keep_separate",
    "confidence": 0.0-1.0,
    "reason": "简短理由",
    "target": "person1" 或 "person2"
  },
  {
    "id": 1,
    "action": "merge" 或 "keep_separate",
    "confidence": 0.0-1.0,
    "reason": "简短理由",
    "target": "person1" 或 "person2"
  }
]
"""

print("调用LLM...")
response = model.generate_content(prompt)
result_text = response.text.strip()

print("\nLLM响应:")
print(result_text)

# 提取JSON
if '```json' in result_text:
    result_text = result_text.split('```json')[1].split('```')[0].strip()
elif '```' in result_text:
    result_text = result_text.split('```')[1].split('```')[0].strip()

print("\n提取的JSON:")
print(result_text)

results = json.loads(result_text)
print(f"\n✅ 成功解析JSON，返回 {len(results)} 个判断")

for r in results:
    print(f"\n实体对 {r['id']}:")
    print(f"  动作: {r['action']}")
    print(f"  置信度: {r['confidence']}")
    print(f"  理由: {r['reason']}")
    if r.get('target'):
        print(f"  保留: {r['target']}")

print("\n✅ 批量LLM调用测试成功！")
