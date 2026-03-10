#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从person_merge_suggestions_ai.html解析第一版合并建议"""
import json
import re
from bs4 import BeautifulSoup

print("解析第一版HTML...")

with open('person_merge_suggestions_ai.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# 找到所有对话卡片
conversation_cards = soup.find_all('div', class_='conversation-card')
print(f"找到 {len(conversation_cards)} 个对话")

results = []

for card_idx, card in enumerate(conversation_cards):
    # 获取对话名称
    header = card.find('div', class_='conversation-header')
    h3 = header.find('h3')
    conv_name = h3.text.strip() if h3 else f"未知对话{card_idx}"

    # 获取所有合并组
    merge_groups = card.find_all('div', class_='merge-group')

    groups = []
    for group in merge_groups:
        # 获取建议名称
        strong = group.find('strong')
        suggested_name = strong.text.replace('建议合并为:', '').strip() if strong else ""

        # 获取原因
        reason_div = group.find('div', class_='merge-reason')
        reason = reason_div.text.replace('原因:', '').strip() if reason_div else ""

        # 获取所有variants
        variants = []
        variant_items = group.find_all('span', class_='variant-name')
        for v in variant_items:
            variant_name = v.text.strip()
            if variant_name:
                variants.append(variant_name)

        # 获取别名（从variant-info中提取）
        # 格式：出现1次|别名:xxx
        variant_details = []
        variant_divs = group.find_all('div', class_='variant-item')
        for vdiv in variant_divs:
            name_span = vdiv.find('span', class_='variant-name')
            info_span = vdiv.find('span', class_='variant-info')

            if name_span and info_span:
                name = name_span.text.strip()
                info_text = info_span.text

                # 解析info：出现X次|别名:Y,Z
                count = 1
                aliases = []

                if '出现' in info_text and '次' in info_text:
                    count_match = re.search(r'出现(\d+)次', info_text)
                    if count_match:
                        count = int(count_match.group(1))

                if '别名:' in info_text:
                    alias_part = info_text.split('别名:')[1]
                    aliases = [a.strip() for a in alias_part.split(',') if a.strip()]

                variant_details.append({
                    'name': name,
                    'count': count,
                    'aliases': aliases
                })

        if variants:
            groups.append({
                'suggested_name': suggested_name,
                'reason': reason,
                'variants': variants,
                'variant_details': variant_details
            })

    if groups:
        results.append({
            'conversation': conv_name,
            'merge_groups': groups
        })

print(f"解析完成: {len(results)} 个对话，共 {sum(len(r['merge_groups']) for r in results)} 个合并组")

# 保存结果
output_file = 'first_batch_merge_suggestions.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"已保存到: {output_file}")
