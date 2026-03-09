#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单个对话的合并建议
"""
import os
import sys
import json
import pickle
from pathlib import Path
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# 初始化Vertex AI
project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json_str = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")
credentials_dict = json.loads(credentials_json_str)
credentials = service_account.Credentials.from_service_account_info(credentials_dict)
vertexai.init(project=project_id, location=location, credentials=credentials)
model = GenerativeModel("gemini-2.5-flash")

# 加载数据
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

# 选择一个对话测试
test_conv = list(conversation_persons.items())[0]
conv_name = test_conv[0]
person_names = list(test_conv[1])

print(f"测试对话: {conv_name}")
print(f"Person数量: {len(person_names)}")

# 收集详细信息
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

person_list_str = "\n".join([
    f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})"
    for p in person_info
])

# Prompt
prompt = f"""分析以下微信对话中的Person实体，判断哪些应该合并。

对话名称：{conv_name}

Person列表：
{person_list_str}

规则：
1. 同一个人的不同称呼应该合并（如"张三"和"张三律师"）
2. 关系称呼如果明确指向同一个人应该合并（如"米雪川的妈妈"和"米雪川妈妈"）
3. 不要把不同的人合并（如"张三"和"张三的老公"是两个人）

请返回JSON格式（不要用markdown代码块包裹）：
{{
  "merge_groups": [
    {{
      "suggested_name": "建议使用的名字",
      "reason": "合并原因",
      "variants": ["人名1", "人名2"]
    }}
  ]
}}

如果没有需要合并的，返回：{{"merge_groups": []}}
"""

print("\n调用AI...")
response = model.generate_content(
    prompt,
    generation_config={"temperature": 0.1, "max_output_tokens": 4096}
)

# 保存原始响应
output_file = Path('test_ai_response.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=== PROMPT ===\n")
    f.write(prompt)
    f.write("\n\n=== AI RESPONSE ===\n")
    f.write(response.text)

print(f"\n结果已保存到: {output_file}")
print("\n=== AI响应 ===")
print(response.text)
