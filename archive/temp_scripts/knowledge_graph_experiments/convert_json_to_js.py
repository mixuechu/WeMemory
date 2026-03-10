#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将JSON文件转换为JS文件，避免CORS限制"""
import json

print("[1/2] 正在转换 merged_entities_by_conversation.json...")
with open('merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('merged_entities_data.js', 'w', encoding='utf-8') as f:
    f.write('// 自动生成的JS数据文件\n')
    f.write('window.MERGED_ENTITIES_DATA = ')
    json.dump(data, f, ensure_ascii=False)
    f.write(';\n')

print("[OK] 已生成 merged_entities_data.js")

print("\n[2/2] 正在转换 person_details_index.json...")
with open('person_details_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('person_details_data.js', 'w', encoding='utf-8') as f:
    f.write('// 自动生成的JS数据文件\n')
    f.write('window.PERSON_DETAILS_DATA = ')
    json.dump(data, f, ensure_ascii=False)
    f.write(';\n')

print("[OK] 已生成 person_details_data.js")

print("\n完成！现在可以直接双击打开HTML文件了")
