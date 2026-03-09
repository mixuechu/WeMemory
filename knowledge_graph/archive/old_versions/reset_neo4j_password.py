#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重置Neo4j密码

使用方法：
1. 停止Neo4j服务
2. 运行此脚本
3. 启动Neo4j服务
"""

import sys
import io
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("Neo4j密码重置工具")
print("=" * 80)
print()

# 常见Neo4j数据目录位置
possible_paths = [
    Path.home() / "AppData/Local/Neo4j/Relate/Data/dbmss",
    Path.home() / "AppData/Roaming/Neo4j Desktop/Application/relate-data/dbmss",
    Path("C:/Neo4j/data/dbms"),
    Path("C:/Program Files/Neo4j/data/dbms"),
]

print("搜索Neo4j auth文件...")
auth_file = None

for base_path in possible_paths:
    if base_path.exists():
        print(f"检查: {base_path}")
        for auth_path in base_path.rglob("auth"):
            if auth_path.is_file():
                print(f"  找到auth文件: {auth_path}")
                auth_file = auth_path
                break
    if auth_file:
        break

if not auth_file:
    print("\n❌ 未找到Neo4j auth文件")
    print("\n请手动查找auth文件位置:")
    print("  1. 打开Neo4j Desktop")
    print("  2. 选择数据库 -> Manage -> Open Folder")
    print("  3. 找到 data/dbms/auth 文件")
    print("  4. 删除该文件")
    print("  5. 重启Neo4j")
    print("  6. 使用默认密码 neo4j/neo4j 登录")
    sys.exit(1)

print(f"\n✅ 找到auth文件: {auth_file}")
print("\n重置步骤:")
print("  1. 停止Neo4j服务")
print(f"  2. 删除文件: {auth_file}")
print("  3. 启动Neo4j服务")
print("  4. 使用默认密码 neo4j/neo4j 登录")
print()

response = input("是否立即删除auth文件？(yes/no): ")
if response.lower() == 'yes':
    try:
        auth_file.unlink()
        print(f"\n✅ 已删除: {auth_file}")
        print("\n下一步:")
        print("  1. 重启Neo4j服务")
        print("  2. 使用密码 neo4j/neo4j 登录")
    except Exception as e:
        print(f"\n❌ 删除失败: {e}")
        print("请手动删除该文件")
else:
    print("\n已取消")
