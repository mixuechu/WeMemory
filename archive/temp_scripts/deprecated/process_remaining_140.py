#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""处理剩余140个对话"""
import os, sys, json, pickle, re, time
from pathlib import Path
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

def safe_print(msg):
    """安全打印"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

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

# 加载140个待处理对话
with open('truly_missing_140.json', 'r', encoding='utf-8') as f:
    missing_list = json.load(f)

# 分类：需要批处理的(>350 Persons)和普通处理的
large_convs = []  # 需要批处理
normal_convs = []  # 普通处理

for item in missing_list:
    conv_name = item['name']
    person_count = len(conversation_persons.get(conv_name, []))
    if person_count >= 350:
        large_convs.append(conv_name)
    elif person_count >= 2:
        normal_convs.append(conv_name)

safe_print(f"待处理对话总数: {len(missing_list)}")
safe_print(f"  需要批处理 (>=350 Persons): {len(large_convs)}")
safe_print(f"  普通处理 (2-349 Persons): {len(normal_convs)}")
safe_print(f"  跳过 (<2 Persons): {len(missing_list) - len(large_convs) - len(normal_convs)}\n")

BATCH_SIZE = 100

PROMPT = """请分析以下微信对话的Person实体，判断哪些应该合并。

对话名称：{conv}
{batch_info}
Person列表：
{list}

合并规则：
1. 同一人不同称呼应合并
2. 明确关系词应合并
3. 不同人绝对不要合并

**重要**：
- 只返回JSON，不要有其他文字
- 不要用markdown格式
- 直接以{{开头

返回格式：
{{"merge_groups":[{{"suggested_name":"名称","reason":"原因","variants":["名1","名2"]}}]}}

如果无需合并：
{{"merge_groups":[]}}"""

def parse_json(text):
    """解析JSON"""
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'^```\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())

    first_brace = text.find('{')
    if first_brace > 0:
        text = text[first_brace:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

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
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    return json.loads(json_str)
                except:
                    pass

    return None

results = []
success, failed, no_merge = 0, 0, 0

# ============ 批处理函数 ============
def analyze_batch(conv, names_batch, batch_num, total_batches):
    """分析一批Person"""
    info = []
    for n in names_batch:
        insts = [persons[i] for i in person_index.get(n, []) if persons[i]['conversation'] == conv]
        if insts:
            aliases = set()
            for i in insts:
                if i.get('aliases'): aliases.update(i['aliases'])
            info.append({'name': n, 'count': len(insts), 'aliases': list(aliases)[:5]})

    batch_info = f"当前批次：第{batch_num}批（共{total_batches}批）" if total_batches > 1 else ""

    prompt = PROMPT.format(
        conv=conv,
        batch_info=batch_info,
        list="\n".join([f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})" for p in info])
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 32768
                }
            )

            try:
                response_text = resp.text
            except Exception as e:
                if "Multiple content parts" in str(e):
                    try:
                        response_text = resp.candidates[0].content.parts[0].text
                    except:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            raise
                else:
                    raise

            data = parse_json(response_text)

            if not data:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None

            groups = data.get('merge_groups', [])
            if not groups:
                return []

            # 添加详细信息
            valid_groups = []
            all_names = set(names_batch)
            for g in groups:
                details = []
                for v in g.get('variants', []):
                    if v in all_names:
                        insts = [persons[i] for i in person_index.get(v, []) if persons[i]['conversation'] == conv]
                        aliases = set()
                        for i in insts:
                            if i.get('aliases'): aliases.update(i['aliases'])
                        details.append({'name': v, 'count': len(insts), 'aliases': list(aliases)[:5]})
                g['variant_details'] = details
                if len(details) >= 2:
                    valid_groups.append(g)

            return valid_groups

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None

    return None

def analyze_large_batch(conv):
    """批处理大对话"""
    global success, failed, no_merge

    names = list(conversation_persons[conv])

    if len(names) < 2:
        no_merge += 1
        return None

    # 分批
    batches = []
    for i in range(0, len(names), BATCH_SIZE):
        batches.append(names[i:i+BATCH_SIZE])

    total_batches = len(batches)
    all_merge_groups = []
    batch_failed = 0

    for batch_num, batch in enumerate(batches, 1):
        batch_groups = analyze_batch(conv, batch, batch_num, total_batches)

        if batch_groups is None:
            batch_failed += 1
            continue
        elif len(batch_groups) > 0:
            all_merge_groups.extend(batch_groups)

        time.sleep(1)

    if all_merge_groups:
        success += 1
        return {
            'conversation': conv,
            'total_persons': len(names),
            'merge_groups': all_merge_groups
        }
    elif batch_failed == total_batches:
        failed += 1
        return None
    else:
        no_merge += 1
        return None

# ============ 普通处理函数 ============
def analyze_normal(conv):
    """普通处理（一次性）"""
    global success, failed, no_merge

    names = list(conversation_persons.get(conv, []))

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
        batch_info="",
        list="\n".join([f"- {p['name']} (出现{p['count']}次, 别名: {', '.join(p['aliases']) if p['aliases'] else '无'})" for p in info])
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 32768
                }
            )

            try:
                response_text = resp.text
            except Exception as e:
                if "Multiple content parts" in str(e):
                    try:
                        response_text = resp.candidates[0].content.parts[0].text
                    except:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            raise
                else:
                    raise

            data = parse_json(response_text)

            if not data:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    failed += 1
                    return None

            groups = data.get('merge_groups', [])
            if not groups:
                no_merge += 1
                return None

            # 添加详细信息
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

            groups = [g for g in groups if len(g.get('variant_details', [])) >= 2]

            if groups:
                success += 1
                return {
                    'conversation': conv,
                    'total_persons': len(names),
                    'merge_groups': groups
                }
            else:
                no_merge += 1
                return None

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                failed += 1
                return None

    failed += 1
    return None

# ============ 处理批处理对话（顺序执行） ============
if large_convs:
    safe_print(f"=== 开始批处理 {len(large_convs)} 个大对话 ===\n")
    for i, conv in enumerate(large_convs, 1):
        safe_print(f"[{i}/{len(large_convs)}] {conv[:30]}... ({len(conversation_persons.get(conv, []))} Persons)")
        r = analyze_large_batch(conv)
        if r:
            results.append(r)
            safe_print(f"  ✓ {len(r['merge_groups'])} 个合并组")
        else:
            safe_print(f"  - 无结果")

        # 保存中间结果
        with open('remaining_140_temp.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    safe_print(f"\n批处理完成: 成功{success}, 失败{failed}, 无需合并{no_merge}\n")

# ============ 处理普通对话（并发） ============
if normal_convs:
    safe_print(f"=== 开始并发处理 {len(normal_convs)} 个普通对话 ===\n")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze_normal, conv): conv for conv in normal_convs}
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            if r:
                results.append(r)

            if i % 20 == 0 or i == len(normal_convs):
                safe_print(f"进度: {i}/{len(normal_convs)} (成功:{success}, 失败:{failed}, 无需合并:{no_merge})")

            # 定期保存
            if i % 20 == 0:
                with open('remaining_140_temp.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

# ============ 最终保存 ============
safe_print(f"\n{'='*60}")
safe_print(f"处理完成！")
safe_print(f"  成功: {success}")
safe_print(f"  失败: {failed}")
safe_print(f"  无需合并: {no_merge}")
safe_print(f"  有合并建议: {len(results)}")
safe_print(f"  总合并组数: {sum(len(r['merge_groups']) for r in results)}")

# 保存新处理的140个对话结果
with open('remaining_140_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

safe_print(f"\n新结果已保存: remaining_140_results.json")

# 合并所有结果
with open('final_supplement_results.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

all_results = existing + results
all_results.sort(key=lambda x: len(x['merge_groups']), reverse=True)

with open('all_191_results.json', 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

safe_print(f"\n所有结果已合并: all_191_results.json")
safe_print(f"  总对话数: {len(all_results)}")
safe_print(f"  总合并组数: {sum(len(r['merge_groups']) for r in all_results)}")
