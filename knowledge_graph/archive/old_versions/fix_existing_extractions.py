#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复已提取的数据：规范化实体命名、删除伪Topics"""

import json
import sys
import io
import re
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# 伪Topics关键词（氛围、情绪类）
FAKE_TOPIC_PATTERNS = [
    r'轻松.*交流',
    r'幽默.*交流',
    r'友好.*沟通',
    r'愉快.*对话',
    r'闲聊',
    r'日常.*聊天',
    r'轻松.*氛围',
]

# 无效Person实体（代词、泛指）- 应该直接删除
INVALID_PERSON_PATTERNS = [
    r'^他$',
    r'^她$',
    r'^某人',
    r'^第三方人物',
    r'^未成年人$',
    r'^亲戚$',  # 单独的"亲戚"太泛指
    r'^小孩$',  # 泛指
    r'^家人$',  # 泛指
    r'^爱人$',  # 泛指
    r'^对象$',  # 泛指
    r'^男友$',  # 泛指
    r'^女友$',  # 泛指
    r'所提及的.*人$',  # 如"吉月所提及的生病的人"
    r'^.*家小两口$',  # 如"吉月家小两口"
]

# 家人关系同义词映射（统一用常见中文词）
FAMILY_SYNONYM_MAP = {
    '母亲': '妈妈',
    'mother': '妈妈',
    'mom': '妈妈',
    'Mother': '妈妈',
    'Mom': '妈妈',
    '父亲': '爸爸',
    'father': '爸爸',
    'dad': '爸爸',
    'Father': '爸爸',
    'Dad': '爸爸',
    'brother': '弟弟',  # 简化处理
    'Brother': '弟弟',
}


def is_invalid_person(name: str) -> bool:
    """判断是否为无效Person实体（代词、泛指）"""
    for pattern in INVALID_PERSON_PATTERNS:
        if re.search(pattern, name):
            return True
    return False


def normalize_person_name(name: str, conversation_name: str) -> str:
    """规范化人物名称

    规则：
    1. 删除无效实体（返回None）
    2. 清理格式：.的、_的、's、之、她的、他的 → 的
    3. 同义词替换：母亲→妈妈、father→爸爸、爸→爸爸
    4. 规范化家人关系："弟弟" → "XX的弟弟"
    5. 处理口语化：我老娘 → XX的妈妈

    返回None表示应该删除该实体
    """
    original_name = name

    # 1. 检查是否为无效实体
    if is_invalid_person(name):
        return None

    # 2. 清理格式混乱
    # "吉月.的妈妈" → "吉月的妈妈"
    name = re.sub(r'\.的', '的', name)
    # "吉月_的妈妈" → "吉月的妈妈"
    name = re.sub(r'_的', '的', name)
    # "吉月之的弟弟" → "吉月的弟弟"
    name = re.sub(r'之的', '的', name)
    # "吉月's 的弟弟" → "吉月的弟弟"
    name = re.sub(r"'s\s*的", '的', name)
    # "吉月她的妈妈" → "吉月的妈妈"
    name = re.sub(r'她的', '的', name)
    name = re.sub(r'他的', '的', name)
    # "吉月's mother" → "吉月 mother"（后续处理）
    name = re.sub(r"'s\s+", ' ', name)
    # "吉月's亲戚" → "吉月亲戚"
    name = re.sub(r"'s", '', name)

    # 处理"大的舅舅"这种格式错误 → 删除
    if re.match(r'^[大小老]的', name):
        return None

    # 处理"吉月大的舅舅"这种格式 → 删除
    if re.search(r'[大小老]的[舅姨姑]', name):
        return None

    # 3. 口语化处理
    # "我老娘" → "妈妈"
    name = re.sub(r'^我老娘$', '妈妈', name)
    name = re.sub(r'^我老爸$', '爸爸', name)

    # 4. 先处理特殊的复杂格式（优先级高）
    # "吉月姨的姥姥" → "吉月的阿姨的姥姥"
    match = re.match(r'^(.+?)(姨|舅|姑|叔)的(.+)$', name)
    if match:
        owner, relation_short, rest = match.groups()
        relation_full = {'姨': '阿姨', '舅': '舅舅', '姑': '姑姑', '叔': '叔叔'}[relation_short]
        return f"{owner}的{relation_full}的{rest}"

    # 5. 处理一般的"XX的YY"格式中的同义词和缩写
    if '的' in name:
        parts = name.split('的', 1)  # 只分一次
        if len(parts) == 2:
            owner, relation = parts

            # 清理owner中的异常字符
            owner = owner.strip()

            # 替换同义词
            relation_map = {
                '母亲': '妈妈', 'mother': '妈妈', 'mom': '妈妈',
                'Mother': '妈妈', 'Mom': '妈妈', '妈': '妈妈',
                '父亲': '爸爸', 'father': '爸爸', 'dad': '爸爸',
                'Father': '爸爸', 'Dad': '爸爸', '爸': '爸爸',
                'brother': '弟弟', 'Brother': '弟弟', '弟': '弟弟',
                '姥': '姥姥', '爷': '爷爷', '舅': '舅舅',
            }

            if relation in relation_map:
                relation = relation_map[relation]

            # 特殊处理：结婚对象、子女等 → 统一格式但不修改
            # 但如果relation是泛指词，删除
            invalid_relations = ['家人', '亲戚', '爱人', '对象', '男友', '女友']
            if relation in invalid_relations:
                return None

            return f"{owner}的{relation}"

    # 6. 处理"XX mother"这种英文格式
    for synonym, standard in FAMILY_SYNONYM_MAP.items():
        if synonym.lower() in ['mother', 'mom', 'father', 'dad', 'brother']:
            # "吉月 mother" → "吉月的妈妈"
            pattern = rf'^(.+?)\s+{synonym}$'
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                owner = match.group(1)
                return f"{owner}的{standard}"

    # 7. 处理缺"的"的情况：吉月母亲、吉月儿子、吉月弟弟女朋友
    # 检测格式：{对话名}{关系词}

    # 7.1 先检查泛指词（应该删除）
    invalid_suffixes = ['亲戚', '男友', '女友', '对象', '爱人', '家人']
    for suffix in invalid_suffixes:
        if name.endswith(suffix) and len(name) > len(suffix):
            # "吉月亲戚" → 删除
            return None

    # 7.2 处理正常的家人关系词
    family_keywords = ['母亲', '父亲', '妈妈', '爸爸', '弟弟', '姐姐', '哥哥', '妹妹',
                      '爷爷', '奶奶', '姥姥', '姥爷', '舅舅', '阿姨', '叔叔',
                      '儿子', '女儿', '孩子', '小孩']

    for keyword in family_keywords:
        # "吉月母亲" → "吉月的妈妈"
        if name.endswith(keyword) and len(name) > len(keyword):
            owner = name[:-len(keyword)]
            # 同义词映射
            relation = keyword
            if keyword == '母亲': relation = '妈妈'
            elif keyword == '父亲': relation = '爸爸'
            return f"{owner}的{relation}"

    # 8. 特殊处理：吉月弟女朋友 → 吉月的弟弟的女朋友
    match = re.match(r'^(.+?)(弟|姐|哥|妹)(.+)$', name)
    if match:
        owner, relation_short, rest = match.groups()
        relation_full = {'弟': '弟弟', '姐': '姐姐', '哥': '哥哥', '妹': '妹妹'}[relation_short]
        return f"{owner}的{relation_full}的{rest}"

    # 9. 规范化家人关系（无前缀的情况）
    family_relations = {
        '弟弟': '弟弟', '弟': '弟弟',
        '妈妈': '妈妈', '妈': '妈妈', '我妈': '妈妈',
        '爸爸': '爸爸', '爸': '爸爸', '我爸': '爸爸',
        '姐姐': '姐姐', '姐': '姐姐',
        '哥哥': '哥哥', '哥': '哥哥',
        '妹妹': '妹妹', '妹': '妹妹',
        '爷爷': '爷爷', '爷': '爷爷',
        '奶奶': '奶奶',
        '姥姥': '姥姥', '姥': '姥姥',
        '姥爷': '姥爷',
        '舅舅': '舅舅', '舅': '舅舅',
        '阿姨': '阿姨',
        '叔叔': '叔叔',
    }

    for relation_key, relation_full in family_relations.items():
        # 完全匹配（如："弟弟"、"我妈"）
        if name == relation_key:
            return f"{conversation_name}的{relation_full}"

    # 10. 其他情况直接返回
    return name


def is_fake_topic(topic_name: str) -> bool:
    """判断是否为伪Topic（氛围、情绪类）"""
    for pattern in FAKE_TOPIC_PATTERNS:
        if re.search(pattern, topic_name):
            return True
    return False


def fix_extraction(data: dict) -> dict:
    """修复单个提取结果"""
    if not data.get('success'):
        return data

    conv_name = data['conversation']['conversation_name']
    entities = data['entities']

    # 1. 规范化人物名称
    fixed_people = []
    name_mapping = {}  # 旧名称 -> 新名称
    deleted_names = set()  # 被删除的名称

    for person in entities.get('people', []):
        old_name = person['name']
        new_name = normalize_person_name(old_name, conv_name)

        # None表示应该删除
        if new_name is None:
            deleted_names.add(old_name)
            continue

        person['name'] = new_name
        fixed_people.append(person)

        if old_name != new_name:
            name_mapping[old_name] = new_name

    entities['people'] = fixed_people

    # 2. 删除伪Topics
    real_topics = []
    removed_topics = []

    for topic in entities.get('topics', []):
        if is_fake_topic(topic['name']):
            removed_topics.append(topic['name'])
        else:
            real_topics.append(topic)

    entities['topics'] = real_topics

    # 3. 更新关系中的人名
    fixed_relationships = []
    for rel in entities.get('relationships', []):
        # 删除涉及被删除实体的关系
        if rel['source'] in deleted_names or rel['target'] in deleted_names:
            continue

        # 删除涉及伪Topic的关系
        if rel.get('target_type') == 'Topic' and rel['target'] in removed_topics:
            continue

        # 更新source
        if rel['source'] in name_mapping:
            rel['source'] = name_mapping[rel['source']]

        # 更新target
        if rel['target'] in name_mapping:
            rel['target'] = name_mapping[rel['target']]

        fixed_relationships.append(rel)

    entities['relationships'] = fixed_relationships

    # 4. 更新Event中的participants
    for event in entities.get('events', []):
        fixed_participants = []
        for participant in event.get('participants', []):
            # 跳过被删除的实体
            if participant in deleted_names:
                continue

            if participant in name_mapping:
                fixed_participants.append(name_mapping[participant])
            else:
                fixed_participants.append(participant)
        event['participants'] = fixed_participants

    return data


def process_directory(input_dir: Path, output_dir: Path = None):
    """处理整个目录"""
    if output_dir is None:
        output_dir = input_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(input_dir.glob("session_*.json"))

    print(f"处理目录: {input_dir}")
    print(f"文件数: {len(files)}")
    print()

    stats = {
        'total': 0,
        'name_normalized': 0,
        'fake_topics_removed': 0,
        'invalid_persons_removed': 0,
    }

    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 记录修改前
        old_people = {p['name'] for p in data.get('entities', {}).get('people', [])} if data.get('success') else set()
        old_topics = {t['name'] for t in data.get('entities', {}).get('topics', [])} if data.get('success') else set()

        # 修复
        fixed_data = fix_extraction(data)

        # 记录修改后
        new_people = {p['name'] for p in fixed_data.get('entities', {}).get('people', [])} if fixed_data.get('success') else set()
        new_topics = {t['name'] for t in fixed_data.get('entities', {}).get('topics', [])} if fixed_data.get('success') else set()

        # 统计
        stats['total'] += 1
        if old_people != new_people:
            stats['name_normalized'] += 1
        if len(old_people) > len(new_people):
            stats['invalid_persons_removed'] += (len(old_people) - len(new_people))
        if len(old_topics) > len(new_topics):
            stats['fake_topics_removed'] += 1

        # 保存
        output_file = output_dir / f.name
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(fixed_data, file, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("修复统计:")
    print(f"  总文件数: {stats['total']}")
    print(f"  规范化人名的文件: {stats['name_normalized']}")
    print(f"  删除无效实体: {stats['invalid_persons_removed']} 个")
    print(f"  删除伪Topics的文件: {stats['fake_topics_removed']}")
    print()


def main():
    """主函数"""
    print("=" * 80)
    print("修复已提取的数据")
    print("=" * 80)
    print()

    # 修复JY
    jy_dir = Path("../extractions/test_jy_only")
    if jy_dir.exists():
        process_directory(jy_dir)

    # 修复吉月
    jiyue_dir = Path("../extractions/test_jiyue_only")
    if jiyue_dir.exists():
        process_directory(jiyue_dir)

    print("=" * 80)
    print("✅ 修复完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
