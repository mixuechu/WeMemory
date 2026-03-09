#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

name = '吉月姨的姥姥'
print(f"Testing: {name}")

match = re.match(r'^(.+?)(姨|舅|姑|叔)的(.+)$', name)
if match:
    owner, relation_short, rest = match.groups()
    relation_full = {'姨': '阿姨', '舅': '舅舅', '姑': '姑姑', '叔': '叔叔'}[relation_short]
    result = f'{owner}的{relation_full}的{rest}'
    print(f'Matched: {match.groups()}')
    print(f'Result: {result}')
else:
    print('No match')
