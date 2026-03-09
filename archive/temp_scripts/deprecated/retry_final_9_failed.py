#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重试最后9个失败的对话 - 使用更严格的prompt"""
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

# 最后9个失败的对话
failed_convs = [
    "GAIDN AI 出海交流群",
    "一个娘炮，一个Japan和两个直男",
    "丈八一路店",
    "妈",
    "我爱我家",
    "柴家大院",
    "米府",
    "米💞雪",
    "老米家"
]

print(f"将重试最后 {len(failed_convs)} 个失败的对话\n")

# 更严格的prompt，强调只返回JSON
PROMPT = """请分析以下微信对话的Person实体，判断哪些应该合并。

对话名称：{conv}

Person列表：
{list}

合并规则：
1. 同一人不同称呼应合并（如"张三"和"小张"）
2. 明确关系词应合并（如"张三的妻子"和"李四"，如果李四的别名包含"张三的妻子"）
3. 不同人绝对不要合并

**重要**：
- 你的回复必须ONLY包含JSON，不要有任何其他文字
- 不要用markdown格式包裹
- 直接以{{开头

返回格式：
{{"merge_groups":[{{"suggested_name":"建议名称","reason":"合并原因","variants":["名字1","名字2"]}}]}}

如果无需合并，返回：
{{"merge_groups":[]}}"""

def parse_json(text):
    """改进的JSON解析"""
    # 移除所有markdown标记
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'^```\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())

    # 查找第一个{的位置，忽略之前的所有文字
    first_brace = text.find('{')
    if first_brace > 0:
        text = text[first_brace:]

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 提取完整的JSON对象（处理可能被截断的情况）
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
                    # 修复常见JSON错误
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
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

    print(f"处理: {conv} ({len(names)} 个Person)")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,  # 降到0以获得更确定的输出
                    "max_output_tokens": 32768
                }
            )

            # 获取响应文本
            try:
                response_text = resp.text
            except Exception as e:
                if "Multiple content parts" in str(e):
                    try:
                        response_text = resp.candidates[0].content.parts[0].text
                    except:
                        print(f"  尝试 {attempt+1}/{max_retries}: 无法获取响应")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            raise
                else:
                    raise

            data = parse_json(response_text)

            if not data:
                print(f"  尝试 {attempt+1}/{max_retries}: JSON解析失败")
                if attempt == max_retries - 1:
                    failed += 1
                    # 保存完整响应用于调试
                    debug_file = f"debug_{conv.replace('/', '_').replace(':', '_')}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    failed_details.append({
                        'conv': conv,
                        'reason': 'JSON解析失败',
                        'debug_file': debug_file
                    })
                    print(f"  [X] 失败 (已保存到 {debug_file})")
                    return None
                time.sleep(2)
                continue

            groups = data.get('merge_groups', [])
            if not groups:
                success += 1
                no_merge += 1
                print(f"  [OK] 成功: 无需合并")
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
                print(f"  [OK] 成功: 无需合并 (过滤后)")
                return None

            print(f"  [OK] 成功: {len(valid_groups)} 个合并组")
            return {'conversation': conv, 'total_persons': len(names), 'merge_groups': valid_groups}

        except Exception as e:
            print(f"  尝试 {attempt+1}/{max_retries}: 异常 {str(e)[:100]}")
            if attempt == max_retries - 1:
                failed += 1
                failed_details.append({'conv': conv, 'reason': str(e)[:200]})
                print(f"  [X] 失败: {str(e)[:100]}")
                return None
            time.sleep(2)

    return None

# 逐个处理
for i, conv in enumerate(failed_convs, 1):
    print(f"\n[{i}/{len(failed_convs)}]")
    r = analyze(conv)
    if r:
        results.append(r)
    time.sleep(1)  # 避免API限流

print(f"\n{'='*60}")
print(f"处理完成！")
print(f"  成功: {success}")
print(f"  失败: {failed}")
print(f"  无需合并: {no_merge}")
print(f"  有合并建议: {len(results)}")
print(f"  总合并组数: {sum(len(s['merge_groups']) for s in results)}")

# 保存结果
with open('final_9_retry_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

if failed_details:
    with open('final_9_still_failed.json', 'w', encoding='utf-8') as f:
        json.dump(failed_details, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存: final_9_retry_results.json")
if failed_details:
    print(f"仍然失败的详情: final_9_still_failed.json")
    print(f"\n仍然失败的对话 ({len(failed_details)}个):")
    for d in failed_details:
        print(f"  - {d['conv']}")
