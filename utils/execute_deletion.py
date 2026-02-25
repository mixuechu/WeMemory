#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行删除低价值对话
"""

import os
import shutil
from pathlib import Path
import json

def delete_low_value_conversations():
    """删除低价值对话文件夹"""

    root_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # 读取分析结果
    with open('inactive_groups.txt', 'r', encoding='utf-8') as f:
        inactive_content = f.read()

    with open('low_activity_private.txt', 'r', encoding='utf-8') as f:
        low_activity_content = f.read()

    # 提取路径
    folders_to_delete = []

    # 从inactive_groups.txt提取
    for line in inactive_content.split('\n'):
        if line.strip().startswith('路径:'):
            json_path = line.split('路径:')[1].strip()
            folder_path = Path(json_path).parent
            folders_to_delete.append(folder_path)

    # 从low_activity_private.txt提取
    for line in low_activity_content.split('\n'):
        if line.strip().startswith('路径:'):
            json_path = line.split('路径:')[1].strip()
            folder_path = Path(json_path).parent
            folders_to_delete.append(folder_path)

    print(f"准备删除 {len(folders_to_delete)} 个文件夹")
    print("=" * 80)

    deleted_count = 0
    failed_count = 0

    for i, folder in enumerate(folders_to_delete, 1):
        if folder.exists():
            try:
                shutil.rmtree(folder)
                deleted_count += 1
                if i % 50 == 0:
                    print(f"进度: {i}/{len(folders_to_delete)} - 已删除: {deleted_count}")
            except Exception as e:
                print(f"删除失败: {folder.name} - {e}")
                failed_count += 1
        else:
            print(f"文件夹不存在: {folder}")

    print("=" * 80)
    print(f"删除完成！")
    print(f"  成功删除: {deleted_count}")
    print(f"  失败: {failed_count}")
    print(f"  总计: {len(folders_to_delete)}")

if __name__ == "__main__":
    print("=" * 80)
    print("开始删除低价值对话文件夹")
    print("=" * 80)
    delete_low_value_conversations()
