#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分批处理Person数量特别多的对话"""
import os, sys, json, pickle, re, time
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

# 需要分批处理的大对话
large_convs = [
    "丈八一路店",
    "妈",
    "我爱我家",
    "柴家大院",
    "米府",
    "米💞雪",
    "老米家"
]

print(f"将分批处理 {len(large_convs)} 个大对话\n")

BATCH_SIZE = 100  # 每批处理100个Person

PROMPT = """请分析以下微信对话的Person实体，判断哪些应该合并。

对话名称：{conv}
当前批次：第{batch_num}批（共{total_batches}批）

Person列表（本批次）：
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

    # 提取完整JSON对象
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

success, failed, results = 0, 0, []

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

    prompt = PROMPT.format(
        conv=conv,
        batch_num=batch_num,
        total_batches=total_batches,
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
                print(f"    批次{batch_num}失败: {str(e)[:100]}")
                return None

    return None

def analyze_large_conv(conv):
    """分批分析大对话"""
    global success, failed

    names = list(conversation_persons[conv])
    try:
        print(f"\n处理: {conv}")
    except UnicodeEncodeError:
        # Windows console can't handle emojis, use ascii encoding
        print(f"\n处理: {conv.encode('ascii', 'replace').decode('ascii')}")
    print(f"  Person总数: {len(names)}")

    if len(names) < 2:
        print(f"  跳过: Person数量<2")
        return None

    # 分批
    batches = []
    for i in range(0, len(names), BATCH_SIZE):
        batches.append(names[i:i+BATCH_SIZE])

    total_batches = len(batches)
    print(f"  分为 {total_batches} 批处理 (每批最多{BATCH_SIZE}个Person)")

    all_merge_groups = []

    for batch_num, batch in enumerate(batches, 1):
        print(f"    批次 {batch_num}/{total_batches} ({len(batch)} 个Person)...", end=" ")
        sys.stdout.flush()

        batch_groups = analyze_batch(conv, batch, batch_num, total_batches)

        if batch_groups is None:
            print("失败")
            failed += 1
            continue
        elif len(batch_groups) == 0:
            print("无需合并")
        else:
            print(f"找到 {len(batch_groups)} 个合并组")
            all_merge_groups.extend(batch_groups)

        time.sleep(1)  # 避免API限流

    if all_merge_groups:
        success += 1
        try:
            print(f"  [OK] 成功: 共 {len(all_merge_groups)} 个合并组")
        except UnicodeEncodeError:
            print(f"  [OK] Success: {len(all_merge_groups)} merge groups")
        return {
            'conversation': conv,
            'total_persons': len(names),
            'merge_groups': all_merge_groups
        }
    else:
        success += 1
        try:
            print(f"  [OK] 成功: 无需合并")
        except UnicodeEncodeError:
            print(f"  [OK] Success: no merge needed")
        return None

# 处理每个大对话
for i, conv in enumerate(large_convs, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(large_convs)}]")

    r = analyze_large_conv(conv)
    if r:
        results.append(r)

    # 保存中间结果（防止崩溃丢失）
    with open('large_conversations_results_temp.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"\n处理完成！")
print(f"  成功: {success}")
print(f"  失败: {failed}")
print(f"  有合并建议: {len(results)}")
print(f"  总合并组数: {sum(len(s['merge_groups']) for s in results)}")

# 保存结果
with open('large_conversations_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存: large_conversations_results.json")
