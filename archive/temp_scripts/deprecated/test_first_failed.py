#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试第一个失败的对话"""
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

# 加载数据
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
persons, person_index, conversation_persons = db['persons'], db['person_index'], db['conversation_persons']

conv = "Ai机器人研发"
names = list(conversation_persons[conv])

print(f"对话: {conv}")
print(f"Person数量: {len(names)}")

info = []
for n in names:
    insts = [persons[i] for i in person_index.get(n, []) if persons[i]['conversation'] == conv]
    if insts:
        aliases = set()
        for i in insts:
            if i.get('aliases'): aliases.update(i['aliases'])
        info.append({'name': n, 'count': len(insts), 'aliases': list(aliases)[:5]})

PROMPT = """分析微信对话Person实体，判断哪些应该合并。
对话：{conv}
Person列表：
{list}
规则：1.同一人不同称呼合并 2.明确关系词合并 3.不同人不合并
返回JSON（不用markdown）：{{"merge_groups":[{{"suggested_name":"名字","reason":"原因","variants":["名1","名2"]}}]}}
无需合并返回：{{"merge_groups":[]}}"""

prompt = PROMPT.format(
    conv=conv,
    list="\n".join([f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})" for p in info])
)

print(f"Prompt长度: {len(prompt)} 字符\n")
print("调用AI...")

try:
    resp = model.generate_content(prompt, generation_config={"temperature": 0.1, "max_output_tokens": 32768})

    # 检查响应元信息
    print(f"\nCandidates数量: {len(resp.candidates)}")
    if resp.candidates:
        candidate = resp.candidates[0]
        print(f"Finish reason: {candidate.finish_reason}")
        print(f"Safety ratings: {candidate.safety_ratings}")

    # 尝试获取文本
    try:
        response_text = resp.text
        print(f"\n成功获取响应，长度: {len(response_text)} 字符")
    except Exception as e:
        print(f"\n无法通过resp.text获取: {e}")
        print("尝试从candidates获取...")
        try:
            response_text = resp.candidates[0].content.parts[0].text
            print(f"从candidates获取成功，长度: {len(response_text)} 字符")
        except Exception as e2:
            print(f"从candidates也失败: {e2}")
            print("\n完整的response对象:")
            print(resp)
            sys.exit(1)

    # 保存完整响应
    with open('first_failed_full_response.txt', 'w', encoding='utf-8') as f:
        f.write(response_text)
    print("完整响应已保存到: first_failed_full_response.txt")

    # 尝试解析JSON
    print("\n尝试解析JSON...")
    # 移除markdown
    text = re.sub(r'^```json\s*', '', response_text.strip())
    text = re.sub(r'\s*```$', '', text.strip())

    try:
        data = json.loads(text)
        print("JSON解析成功!")
        print(f"merge_groups数量: {len(data.get('merge_groups', []))}")
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print(f"错误位置: 第{e.lineno}行, 第{e.colno}列")
        print(f"错误附近的内容:")
        lines = text.split('\n')
        start = max(0, e.lineno - 3)
        end = min(len(lines), e.lineno + 2)
        for i in range(start, end):
            marker = ">>> " if i == e.lineno - 1 else "    "
            print(f"{marker}{i+1}: {lines[i]}")

except Exception as e:
    print(f"调用AI失败: {e}")
    import traceback
    traceback.print_exc()
