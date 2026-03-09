#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新处理失败的53个对话"""
import os, sys, json, pickle, re, time
from pathlib import Path
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# 加载失败的对话
with open('failed_conversations.json', 'r', encoding='utf-8') as f:
    failed_list = json.load(f)

failed_convs = [item['conv'] for item in failed_list]
print(f"将重新处理 {len(failed_convs)} 个失败的对话")

PROMPT = """分析微信对话Person实体，判断哪些应该合并。
对话：{conv}
Person列表：
{list}
规则：1.同一人不同称呼合并 2.明确关系词合并 3.不同人不合并
返回JSON（不用markdown）：{{"merge_groups":[{{"suggested_name":"名字","reason":"原因","variants":["名1","名2"]}}]}}
无需合并返回：{{"merge_groups":[]}}"""

def parse_json(text):
    """改进的JSON解析，更加宽容"""
    # 移除markdown标记
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    text = re.sub(r'^```\s*', '', text.strip())

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        pass

    # 提取第一个完整的JSON对象
    brace_count = 0
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                try:
                    json_str = text[start_idx:i+1]
                    # 修复常见的JSON错误
                    json_str = re.sub(r',\s*}', '}', json_str)  # 移除末尾逗号
                    json_str = re.sub(r',\s*]', ']', json_str)  # 移除数组末尾逗号
                    return json.loads(json_str)
                except:
                    pass

    return None

success, failed, no_merge, results = 0, 0, 0, []
failed_details = []

def analyze(conv):
    global success, failed, no_merge

    names = list(conversation_persons[conv])
    if len(names) < 2:
        no_merge += 1
        return None

    info = []
    for n in names:
        insts = [persons[i] for i in person_index.get(n, []) if persons[i]['conversation'] == conv]
        if insts:
            aliases = set()
            for i in insts:
                if i.get('aliases'): aliases.update(i['aliases'])
            info.append({'name': n, 'count': len(insts), 'aliases': list(aliases)[:5]})

    prompt = PROMPT.format(
        conv=conv,
        list="\n".join([f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})" for p in info])
    )

    # 重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(prompt, generation_config={"temperature": 0.1, "max_output_tokens": 32768})
            data = parse_json(resp.text)

            if not data:
                if attempt == max_retries - 1:
                    failed += 1
                    # 保存完整的响应用于调试
                    failed_details.append({
                        'conv': conv,
                        'reason': 'JSON解析失败',
                        'response_preview': resp.text[:500],
                        'full_response_length': len(resp.text)
                    })
                    return None
                time.sleep(1)
                continue

            groups = data.get('merge_groups', [])
            if not groups:
                success += 1
                no_merge += 1
                return None

            # 添加详细信息并过滤
            valid_groups = []
            for g in groups:
                details = []
                for v in g.get('variants', []):
                    if v in names:
                        insts = [persons[i] for i in person_index.get(v, []) if persons[i]['conversation'] == conv]
                        aliases = set()
                        for i in insts:
                            if i.get('aliases'): aliases.update(i['aliases'])
                        details.append({'name': v, 'count': len(insts), 'aliases': list(aliases)[:5]})
                g['variant_details'] = details
                if len(details) >= 2:
                    valid_groups.append(g)

            success += 1
            if not valid_groups:
                no_merge += 1
                return None
            return {'conversation': conv, 'total_persons': len(names), 'merge_groups': valid_groups}

        except Exception as e:
            if attempt == max_retries - 1:
                failed += 1
                failed_details.append({'conv': conv, 'reason': str(e)[:200]})
                return None
            time.sleep(1)

    return None

print("开始重新处理...")
print(f"使用10线程并发，每个对话最多重试3次\n")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(analyze, conv): conv for conv in failed_convs}
    for i, f in enumerate(as_completed(futures), 1):
        if i % 10 == 0 or i == len(failed_convs):
            print(f"进度: {i}/{len(failed_convs)} (成功:{success}, 失败:{failed}, 无需合并:{no_merge})")
        r = f.result()
        if r: results.append(r)

print(f"\n处理完成！")
print(f"  成功: {success}")
print(f"  失败: {failed}")
print(f"  无需合并: {no_merge}")
print(f"  有合并建议: {len(results)}")
print(f"  总合并组数: {sum(len(s['merge_groups']) for s in results)}")

if failed > 0:
    print(f"\n仍然失败的对话数: {failed}")

# 保存重新处理的结果
with open('retry_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

if failed_details:
    with open('still_failed_conversations.json', 'w', encoding='utf-8') as f:
        json.dump(failed_details, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存: retry_results.json")
if failed_details:
    print(f"仍然失败的详情: still_failed_conversations.json")
