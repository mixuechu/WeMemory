#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, pickle, re
from pathlib import Path
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')
vertexai.init(
    project=os.getenv("VITE_GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("VITE_GOOGLE_CLOUD_LOCATION"),
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    )
)
model = GenerativeModel("gemini-2.5-flash")

with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
persons, person_index, conversation_persons = db['persons'], db['person_index'], db['conversation_persons']

# 选择第一个对话
test_conv = list(conversation_persons.items())[0]
conv_name, person_names = test_conv[0], list(test_conv[1])

print(f"测试对话: {conv_name}")
print(f"Person数量: {len(person_names)}\n")

# 收集信息
info = []
for n in person_names:
    insts = [persons[i] for i in person_index.get(n, []) if persons[i]['conversation'] == conv_name]
    if insts:
        aliases = set()
        for i in insts:
            if i.get('aliases'): aliases.update(i['aliases'])
        info.append({'name': n, 'count': len(insts), 'aliases': list(aliases)[:5]})

prompt = f"""分析微信对话Person实体，判断哪些应该合并。
对话：{conv_name}
Person列表：
{chr(10).join([f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})" for p in info[:20]])}
... (共{len(info)}个)

规则：1.同一人不同称呼合并 2.明确关系词合并 3.不同人不合并
返回JSON（不用markdown）：{{"merge_groups":[{{"suggested_name":"名字","reason":"原因","variants":["名1","名2"]}}]}}
无需合并返回：{{"merge_groups":[]}}"""

print("调用AI...")
resp = model.generate_content(prompt, generation_config={"temperature": 0.1, "max_output_tokens": 4096})

print("\n=== AI原始响应 ===")
print(resp.text[:1000])
print("\n...")

# 解析JSON
text = re.sub(r'^```json\s*', '', resp.text.strip())
text = re.sub(r'\s*```$', '', text)

try:
    data = json.loads(text)
    print(f"\n[OK] JSON解析成功！")
    print(f"合并组数: {len(data['merge_groups'])}\n")

    # 检查前5组
    for i, g in enumerate(data['merge_groups'][:5], 1):
        print(f"组{i}: {g['suggested_name']}")
        print(f"  原因: {g['reason'][:60]}...")
        print(f"  包含: {g['variants'][:5]}")

        # 检查是否有问题（比如把XXX和XXX的YYY合并）
        variants = g['variants']
        for v1 in variants:
            for v2 in variants:
                if v1 != v2 and (f"{v1}的" in v2 or f"{v2}的" in v1):
                    print(f"  [WARNING] 可能有问题: '{v1}' 和 '{v2}'")
        print()

    print("\n结论: AI建议看起来", "合理" if len(data['merge_groups']) > 0 and len(data['merge_groups']) < 50 else "需要检查")

except json.JSONDecodeError as e:
    print(f"\n[ERROR] JSON解析失败: {e}")
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        print(f"提取到JSON对象，长度: {len(m.group(0))}")
