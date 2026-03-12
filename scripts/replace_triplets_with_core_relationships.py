#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用核心关系替换三元组中的垃圾关系数据

保留：事件三元组（高质量）
替换：关系三元组 → 核心关系（手动审核）
"""
import json
from pathlib import Path
from datetime import datetime

def main():
    # 路径
    triplets_path = Path("data/knowledge_graph/triplets.json")
    core_rel_path = Path("data/relationships/core_relationships.json")
    output_path = Path("data/knowledge_graph/triplets.json")
    backup_path = Path("data/knowledge_graph/triplets_backup_before_core_replacement.json")

    print("=" * 70)
    print("用核心关系替换三元组中的关系数据")
    print("=" * 70)

    # 1. 备份原始三元组
    print(f"\n1. 备份原始三元组到: {backup_path}")
    with open(triplets_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)

    print(f"   原始三元组: {len(original_data['records'])} 条")

    # 2. 加载核心关系
    print(f"\n2. 加载核心关系: {core_rel_path}")
    with open(core_rel_path, 'r', encoding='utf-8') as f:
        core_data = json.load(f)

    print(f"   核心人物: {len(core_data['persons'])} 人")
    print(f"   核心关系: {core_data['statistics']['total_relationships_kept']} 条")

    # 3. 过滤三元组：只保留事件，删除关系
    print(f"\n3. 过滤三元组：保留事件，删除关系")
    events = [r for r in original_data['records'] if r['type'] == 'event']
    old_relationships = [r for r in original_data['records'] if r['type'] == 'relationship']

    print(f"   保留事件: {len(events)} 条")
    print(f"   删除旧关系: {len(old_relationships)} 条")

    # 4. 转换核心关系为三元组格式
    print(f"\n4. 转换核心关系为三元组格式")
    new_relationships = []

    for person in core_data['persons']:
        for rel in person.get('relationships', []):
            triplet = {
                "id": rel['id'],
                "type": "relationship",
                "text": rel['text'],
                "metadata": {
                    "subject": rel['metadata']['subject'],
                    "relation_type": rel['metadata']['relation_type'],
                    "object": rel['metadata']['object'],
                    "object_type": rel['metadata']['object_type'],
                    "conversation": rel['metadata'].get('conversation', 'core_relationship'),
                    "context": rel['metadata'].get('context', ''),
                    "source": "core_relationships_manual_reviewed"
                }
            }
            new_relationships.append(triplet)

    print(f"   转换核心关系: {len(new_relationships)} 条")

    # 5. 合并：事件 + 核心关系
    final_records = events + new_relationships

    print(f"\n5. 合并数据")
    print(f"   事件三元组: {len(events)} 条")
    print(f"   核心关系三元组: {len(new_relationships)} 条")
    print(f"   总计: {len(final_records)} 条")

    # 6. 更新元数据
    new_metadata = {
        "version": "triplets_with_core_relationships_v1",
        "generated_at": datetime.now().isoformat(),
        "description": "事件三元组（LLM清理） + 核心关系（手动审核）",
        "event_count": len(events),
        "relationship_count": len(new_relationships),
        "total_count": len(final_records),
        "event_source": "llm_cleaned_triplets",
        "relationship_source": "core_relationships_manual_reviewed",
        "original_triplet_metadata": original_data['metadata'],
        "core_relationship_metadata": core_data['statistics']
    }

    # 7. 保存新数据
    final_data = {
        "metadata": new_metadata,
        "records": final_records
    }

    print(f"\n6. 保存新三元组到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("✓ 替换完成！")
    print("=" * 70)
    print(f"\n统计:")
    print(f"  - 原始三元组: {len(original_data['records'])} 条")
    print(f"  - 新三元组: {len(final_records)} 条")
    print(f"    - 事件: {len(events)} 条")
    print(f"    - 核心关系: {len(new_relationships)} 条")
    print(f"\n变化:")
    print(f"  - 删除旧关系: {len(old_relationships)} 条")
    print(f"  - 添加核心关系: {len(new_relationships)} 条")
    print(f"  - 净变化: {len(final_records) - len(original_data['records'])} 条")

    print(f"\n备份: {backup_path}")
    print(f"\n下一步: 重新生成向量embeddings")
    print(f"  python scripts/generate_triplet_embeddings.py")

if __name__ == "__main__":
    main()
