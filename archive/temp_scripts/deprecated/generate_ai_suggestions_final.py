#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, pickle, re
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

with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
persons, person_index, conversation_persons = db['persons'], db['person_index'], db['conversation_persons']

PROMPT = """分析微信对话Person实体，判断哪些应该合并。
对话：{conv}
Person列表：
{list}
规则：1.同一人不同称呼合并 2.明确关系词合并 3.不同人不合并
返回JSON（不用markdown）：{{"merge_groups":[{{"suggested_name":"名字","reason":"原因","variants":["名1","名2"]}}]}}
无需合并返回：{{"merge_groups":[]}}"""

def parse_json(text):
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except:
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try: return json.loads(m.group(0))
            except: pass
    return None

success, failed, results = 0, 0, []

def analyze(conv, names):
    global success, failed
    if len(names) < 2: return None
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

    try:
        resp = model.generate_content(prompt, generation_config={"temperature": 0.1, "max_output_tokens": 4096})
        data = parse_json(resp.text)
        if not data:
            failed += 1
            return None

        groups = data.get('merge_groups', [])
        if not groups:
            success += 1
            return None

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
            # 只保留有2个或以上variant的组
            if len(details) >= 2:
                valid_groups.append(g)

        success += 1
        if not valid_groups:
            return None
        return {'conversation': conv, 'total_persons': len(names), 'merge_groups': valid_groups}
    except Exception as e:
        failed += 1
        return None

print("开始处理676个对话...")
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(analyze, c, list(n)): c for c, n in conversation_persons.items()}
    for i, f in enumerate(as_completed(futures), 1):
        if i % 50 == 0:
            print(f"进度: {i}/676 (成功:{success}, 失败:{failed})")
        r = f.result()
        if r: results.append(r)

print(f"\n完成！成功:{success}, 失败:{failed}, 有建议:{len(results)}, 总组数:{sum(len(s['merge_groups']) for s in results)}")

results.sort(key=lambda x: len(x['merge_groups']), reverse=True)

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>Person合并建议-AI</title><style>
*{{box-sizing:border-box}}body{{font-family:"Microsoft YaHei",Arial;margin:0;padding:20px;background:#f5f5f5}}
.container{{max-width:1400px;margin:0 auto;background:white;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
h1{{color:#333;border-bottom:3px solid #4CAF50;padding-bottom:10px}}
.stats{{background:#e8f5e9;padding:15px;border-radius:5px;margin-bottom:20px}}
.controls{{margin-bottom:20px;padding:15px;background:#f9f9f9;border-radius:5px}}
.conversation-card{{border:1px solid #ddd;border-radius:5px;margin-bottom:15px;overflow:hidden}}
.conversation-header{{background:#f5f5f5;padding:12px 15px;cursor:pointer;display:flex;justify-content:space-between;align-items:center}}
.conversation-header:hover{{background:#e0e0e0}}
.conversation-header h3{{margin:0;color:#333}}
.conversation-badge{{background:#2196F3;color:white;padding:3px 10px;border-radius:12px;font-size:12px}}
.conversation-content{{display:none;padding:15px;background:white}}
.conversation-content.active{{display:block}}
.merge-group{{border-left:3px solid #4CAF50;margin-bottom:15px;padding:10px;background:#f9f9f9}}
.merge-reason{{color:#666;font-size:13px;font-style:italic;margin-top:5px}}
.variant-item{{margin:5px 0;padding:5px;background:white;border-radius:3px}}
.variant-name{{font-weight:bold;color:#1976D2}}
.variant-info{{font-size:12px;color:#666;margin-left:10px}}
.decision-buttons{{margin-top:10px;display:flex;gap:8px}}
.btn{{padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:13px}}
.btn-approve{{background:#4CAF50;color:white}}.btn-reject{{background:#f44336;color:white}}
.selected-approve{{background:#c8e6c9!important}}.selected-reject{{background:#ffcdd2!important}}
.save-btn{{background:#2196F3;color:white;padding:12px 24px;font-size:16px;border:none;border-radius:4px;cursor:pointer;margin-top:20px}}
input[type="text"]{{padding:8px;width:300px;border:1px solid #ddd;border-radius:4px}}
.expand-all{{padding:8px 16px;background:#9E9E9E;color:white;border:none;border-radius:4px;cursor:pointer;margin-left:10px}}
</style></head><body><div class="container">
<h1>Person合并建议-AI生成</h1>
<div class="stats"><strong>统计：</strong>有建议对话:{len(results)}|总组数:{sum(len(s['merge_groups']) for s in results)}|
已批准:<span id="approved-count">0</span>|已拒绝:<span id="rejected-count">0</span></div>
<div class="controls">
<input type="text" id="search" placeholder="搜索...">
<button class="expand-all" onclick="expandAll()">展开全部</button>
<button class="expand-all" onclick="collapseAll()">收起全部</button></div>
<div id="conversations-container">"""

for idx, s in enumerate(results):
    html += f"""<div class="conversation-card"><div class="conversation-header" onclick="toggleConversation({idx})">
    <div><h3>{s['conversation']}</h3><small>共{s['total_persons']}个Person|{len(s['merge_groups'])}组建议</small></div>
    <span class="conversation-badge">{len(s['merge_groups'])}组</span></div>
    <div class="conversation-content" id="conv-{idx}">"""
    for gid, g in enumerate(s['merge_groups']):
        html += f"""<div class="merge-group" id="group-{idx}-{gid}" data-decision="">
        <strong>建议合并为:{g['suggested_name']}</strong>
        <div class="merge-reason">原因:{g['reason']}</div><div style="margin-top:8px;">"""
        for v in g.get('variant_details', []):
            html += f"""<div class="variant-item"><span class="variant-name">{v['name']}</span>
            <span class="variant-info">出现{v['count']}次|别名:{', '.join(v['aliases'][:3]) if v['aliases'] else '无'}</span></div>"""
        html += f"""</div><div class="decision-buttons">
        <button class="btn btn-approve" onclick="setDecision('{idx}-{gid}','approve')">批准</button>
        <button class="btn btn-reject" onclick="setDecision('{idx}-{gid}','reject')">拒绝</button></div></div>"""
    html += """</div></div>"""

html += f"""</div><button class="save-btn" onclick="saveDecisions()">保存决定到JSON</button></div>
<script>
let decisions={{}};
function toggleConversation(i){{document.getElementById('conv-'+i).classList.toggle('active')}}
function expandAll(){{document.querySelectorAll('.conversation-content').forEach(e=>e.classList.add('active'))}}
function collapseAll(){{document.querySelectorAll('.conversation-content').forEach(e=>e.classList.remove('active'))}}
function setDecision(id,d){{const g=document.getElementById('group-'+id);decisions[id]=d;
g.classList.remove('selected-approve','selected-reject');
if(d==='approve')g.classList.add('selected-approve');else g.classList.add('selected-reject');
updateStats()}}
function updateStats(){{
const a=Object.values(decisions).filter(d=>d==='approve').length;
const r=Object.values(decisions).filter(d=>d==='reject').length;
document.getElementById('approved-count').textContent=a;
document.getElementById('rejected-count').textContent=r}}
function saveDecisions(){{
const result={{decisions:decisions,summary:{{total:{sum(len(s['merge_groups']) for s in results)},
approved:Object.values(decisions).filter(d=>d==='approve').length,
rejected:Object.values(decisions).filter(d=>d==='reject').length}}}};
const blob=new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}});
const url=URL.createObjectURL(blob);const a=document.createElement('a');
a.href=url;a.download='merge_decisions_ai.json';a.click();URL.revokeObjectURL(url);
alert('已保存!\\n批准:'+result.summary.approved+'|拒绝:'+result.summary.rejected)}}
document.getElementById('search').addEventListener('input',function(e){{
const s=e.target.value.toLowerCase();
document.querySelectorAll('.conversation-card').forEach(c=>{{
c.style.display=c.textContent.toLowerCase().includes(s)?'':'none'}})}})</script></body></html>"""

Path('person_merge_suggestions_ai.html').write_text(html, encoding='utf-8')
print(f"\nHTML已生成: person_merge_suggestions_ai.html")
