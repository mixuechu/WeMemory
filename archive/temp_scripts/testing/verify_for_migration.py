#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移前数据完整性验证脚本

用途：确保所有核心数据文件完整，可以安全迁移
运行：python verify_for_migration.py
"""
import os
import json
import pickle
from pathlib import Path

def check_file(path, min_size_mb=0):
    """检查文件是否存在且大小合理"""
    if not os.path.exists(path):
        return False, f"文件不存在: {path}"

    size_mb = os.path.getsize(path) / 1024 / 1024
    if size_mb < min_size_mb:
        return False, f"文件过小 ({size_mb:.2f} MB < {min_size_mb} MB): {path}"

    return True, f"OK ({size_mb:.2f} MB)"

def verify_json_loadable(path):
    """验证JSON文件可以正常加载"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, f"JSON可解析，keys: {len(data) if isinstance(data, dict) else 'N/A'}"
    except Exception as e:
        return False, f"JSON解析失败: {str(e)}"

def verify_pickle_loadable(path):
    """验证Pickle文件可以正常加载"""
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return True, f"Pickle可解析"
    except Exception as e:
        return False, f"Pickle解析失败: {str(e)}"

def count_files_in_dir(directory, pattern="*.json"):
    """统计目录中的文件数量"""
    try:
        files = list(Path(directory).glob(pattern))
        return True, f"{len(files)} 个文件"
    except Exception as e:
        return False, f"无法访问目录: {str(e)}"

def main():
    print("=" * 70)
    print(" WeChat Memory System - 迁移前数据完整性验证")
    print("=" * 70)
    print()

    base_dir = Path("D:/导出聊天记录excel")
    kg_dir = base_dir / "knowledge_graph"
    backup_dir = base_dir / "backups/before_merge_20260303_143226/batch_20260227_001822"
    vector_dir = base_dir / "vector_stores"
    api_dir = base_dir / "api"
    embedding_dir = base_dir / "embedding"

    all_passed = True

    # 1. 核心数据文件
    print("[1/5] 核心数据文件检查")
    print("-" * 70)

    core_files = [
        (kg_dir / "person_database.pkl", 9, verify_pickle_loadable),
        (kg_dir / "person_details_index.json", 300, verify_json_loadable),
        (kg_dir / "merged_entities_by_conversation.json", 5, verify_json_loadable),
    ]

    for file_path, min_size, verify_func in core_files:
        exists, msg = check_file(file_path, min_size)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path.name}: {msg}")

        if exists and verify_func:
            loadable, load_msg = verify_func(file_path)
            load_status = "✓" if loadable else "✗"
            print(f"     └─ {load_status} {load_msg}")
            all_passed = all_passed and loadable

        all_passed = all_passed and exists

    print()

    # 2. 人工编辑结果
    print("[2/5] 人工编辑结果检查")
    print("-" * 70)

    edit_files = [
        ("c:/Users/A/Downloads/conversation_entity_edits_v1.json", 0.1),
        ("c:/Users/A/Downloads/手过第一版.json", 0.01),
        ("c:/Users/A/Downloads/手过补充版.json", 0.01),
    ]

    for file_path, min_size in edit_files:
        exists, msg = check_file(file_path, min_size)
        status = "✓" if exists else "✗"
        print(f"  {status} {Path(file_path).name}: {msg}")

        if exists:
            loadable, load_msg = verify_json_loadable(file_path)
            load_status = "✓" if loadable else "✗"
            print(f"     └─ {load_status} {load_msg}")
            all_passed = all_passed and loadable

        all_passed = all_passed and exists

    print()

    # 3. 抽取备份
    print("[3/5] 原始抽取备份检查")
    print("-" * 70)

    backup_exists = backup_dir.exists()
    status = "✓" if backup_exists else "✗"
    print(f"  {status} 备份目录: {backup_dir}")

    if backup_exists:
        count_ok, count_msg = count_files_in_dir(backup_dir, "session_*.json")
        count_status = "✓" if count_ok else "✗"
        print(f"     └─ {count_status} {count_msg}")
        all_passed = all_passed and count_ok

    all_passed = all_passed and backup_exists
    print()

    # 4. 编辑工具
    print("[4/5] 编辑工具检查")
    print("-" * 70)

    tool_files = [
        (kg_dir / "conversation_entity_editor.html", 0.05),
        (kg_dir / "merged_entities_data.js", 3),
        (kg_dir / "person_details_data.js", 200),
    ]

    for file_path, min_size in tool_files:
        exists, msg = check_file(file_path, min_size)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path.name}: {msg}")
        all_passed = all_passed and exists

    print()

    # 5. 核心脚本
    print("[5/5] 核心脚本检查")
    print("-" * 70)

    scripts = [
        kg_dir / "batch_extract_all.py",
        kg_dir / "build_person_details_index_optimized.py",
        kg_dir / "merge_entities.py",
        kg_dir / "extract_first_batch_data.py",
        kg_dir / "convert_json_to_js.py",
    ]

    for script_path in scripts:
        exists = script_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {script_path.name}")
        all_passed = all_passed and exists

    print()

    # 6. 向量知识库
    print("[6/8] 向量知识库检查")
    print("-" * 70)

    vector_files = [
        (vector_dir / "conversations_complete.pkl", 1500, verify_pickle_loadable),
        (vector_dir / "all_conversations_content.faiss", 500, None),
        (vector_dir / "all_conversations_context.faiss", 500, None),
    ]

    for file_path, min_size, verify_func in vector_files:
        exists, msg = check_file(file_path, min_size)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path.name}: {msg}")

        if exists and verify_func:
            loadable, load_msg = verify_func(file_path)
            load_status = "✓" if loadable else "✗"
            print(f"     └─ {load_status} {load_msg}")
            all_passed = all_passed and loadable

        all_passed = all_passed and exists

    print()

    # 7. API服务文件
    print("[7/8] API服务检查")
    print("-" * 70)

    api_files = [
        (api_dir / "main.py", 0.001),
        (api_dir / "README.md", 0.001),
        (api_dir / "PERFORMANCE_REPORT.md", 0.001),
    ]

    for file_path, min_size in api_files:
        exists, msg = check_file(file_path, min_size)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path.name}: {msg}")
        all_passed = all_passed and exists

    print()

    # 8. Embedding模块
    print("[8/8] Embedding模块检查")
    print("-" * 70)

    embedding_files = [
        embedding_dir / "client.py",
        embedding_dir / "enricher.py",
        embedding_dir / "generator.py",
        embedding_dir / "README.md",
    ]

    for file_path in embedding_files:
        exists = file_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path.name}")
        all_passed = all_passed and exists

    print()
    print("=" * 70)

    if all_passed:
        print("✓✓✓ 所有检查通过！数据完整，可以安全迁移")
        print()
        print("数据统计:")
        print("  - 知识图谱: ~1.25 GB")
        print("  - 向量知识库: ~3.2 GB")
        print("  - 总计: ~4.5 GB")
    else:
        print("✗✗✗ 部分检查失败！请修复后再迁移")

    print("=" * 70)
    print()
    print("详细迁移指南：")
    print("  - PROJECT_STATUS.md")
    print("  - MIGRATION_CHECKLIST.md")
    print()

    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
