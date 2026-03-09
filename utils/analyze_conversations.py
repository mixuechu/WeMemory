#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析聊天记录，识别低价值对话
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass
import time
import re

def clean_text_for_console(text: str) -> str:
    """清理文本，移除emoji和特殊字符"""
    # 移除emoji
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # 表情符号
                               u"\U0001F300-\U0001F5FF"  # 符号 & 象形文字
                               u"\U0001F680-\U0001F6FF"  # 交通 & 地图符号
                               u"\U0001F1E0-\U0001F1FF"  # 旗帜
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    # 移除其他无法打印的字符
    text = text.encode('gbk', errors='ignore').decode('gbk')
    return text

@dataclass
class ConversationInfo:
    folder_name: str
    file_path: str
    name: str
    type: str  # 'private' or 'group'
    message_count: int
    text_message_count: int
    last_message_time: datetime
    days_since_last_message: int
    first_message_time: datetime
    participants: List[str]

def parse_conversation_file(file_path: Path) -> ConversationInfo:
    """解析单个对话JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta = data.get('meta', {})
        messages = data.get('messages', [])
        members = data.get('members', [])

        # 过滤出文本消息
        text_messages = [m for m in messages if m.get('type') == 0]

        # 获取最后一条消息时间
        if messages:
            last_timestamp = messages[-1].get('timestamp', 0)
            first_timestamp = messages[0].get('timestamp', 0)
            last_time = datetime.fromtimestamp(last_timestamp)
            first_time = datetime.fromtimestamp(first_timestamp)
        else:
            last_time = datetime(2000, 1, 1)
            first_time = datetime(2000, 1, 1)

        days_since = (datetime.now() - last_time).days

        # 获取参与者名称
        participant_names = [m.get('accountName', '') for m in members]

        return ConversationInfo(
            folder_name=file_path.parent.name,
            file_path=str(file_path),
            name=meta.get('name', 'Unknown'),
            type=meta.get('type', 'unknown'),
            message_count=len(messages),
            text_message_count=len(text_messages),
            last_message_time=last_time,
            days_since_last_message=days_since,
            first_message_time=first_time,
            participants=participant_names
        )

    except Exception as e:
        print(f"[ERROR] 解析失败 {file_path}: {e}")
        return None

def find_all_conversation_files(root_dir: Path) -> List[Path]:
    """找出所有对话JSON文件"""
    json_files = []

    # 扫描根目录下的所有文件夹
    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['__pycache__']:
            # 跳过文档和脚本文件
            if item.name.endswith('.md') or item.name.endswith('.py'):
                continue

            # 在每个文件夹中查找同名JSON文件
            json_file = item / f"{item.name}.json"
            if json_file.exists():
                json_files.append(json_file)
            else:
                # 可能是包含对话的父文件夹，继续往下搜索一层
                if item.is_dir():
                    for sub_item in item.iterdir():
                        if sub_item.is_dir():
                            sub_json_file = sub_item / f"{sub_item.name}.json"
                            if sub_json_file.exists():
                                json_files.append(sub_json_file)

    return json_files

def analyze_conversations(root_dir: str):
    """分析所有对话"""
    root_path = Path(root_dir)

    print("[INFO] 扫描对话文件...")
    json_files = find_all_conversation_files(root_path)
    print(f"[INFO] 找到 {len(json_files)} 个对话文件\n")

    # 解析所有文件
    print("[INFO] 解析对话数据...")
    conversations = []
    for i, file_path in enumerate(json_files, 1):
        if i % 100 == 0:
            print(f"   进度: {i}/{len(json_files)}")

        conv = parse_conversation_file(file_path)
        if conv:
            conversations.append(conv)

    print(f"[OK] 成功解析 {len(conversations)} 个对话\n")

    # 分类统计
    group_chats = [c for c in conversations if c.type == 'group']
    private_chats = [c for c in conversations if c.type == 'private']

    print("=" * 80)
    print("[统计] 数据统计")
    print("=" * 80)
    print(f"总对话数: {len(conversations)}")
    print(f"  - 群聊: {len(group_chats)}")
    print(f"  - 私聊: {len(private_chats)}")
    print(f"  - 其他: {len(conversations) - len(group_chats) - len(private_chats)}")
    print()

    # 条件1: 超过10天没人说话的群聊
    DAYS_THRESHOLD = 10
    inactive_groups = [
        g for g in group_chats
        if g.days_since_last_message > DAYS_THRESHOLD
    ]
    inactive_groups.sort(key=lambda x: x.days_since_last_message, reverse=True)

    print("=" * 80)
    print(f"[结果1] 超过{DAYS_THRESHOLD}天没人说话的群聊: {len(inactive_groups)}")
    print("=" * 80)

    # 显示前20个
    for i, group in enumerate(inactive_groups[:20], 1):
        clean_name = clean_text_for_console(group.name[:40])
        print(f"{i:3d}. [{group.days_since_last_message:4d}天] "
              f"{clean_name:<40} "
              f"(共{group.message_count:4d}条消息)")

    if len(inactive_groups) > 20:
        print(f"... 还有 {len(inactive_groups) - 20} 个群聊未显示")

    # 保存详细列表
    with open('inactive_groups.txt', 'w', encoding='utf-8') as f:
        f.write(f"超过{DAYS_THRESHOLD}天没人说话的群聊 (共{len(inactive_groups)}个)\n")
        f.write("=" * 100 + "\n\n")
        for i, group in enumerate(inactive_groups, 1):
            f.write(f"{i}. 【{group.days_since_last_message}天前】 {group.name}\n")
            f.write(f"   文件夹: {group.folder_name}\n")
            f.write(f"   消息数: {group.message_count} (文本: {group.text_message_count})\n")
            f.write(f"   最后活跃: {group.last_message_time.strftime('%Y-%m-%d')}\n")
            f.write(f"   路径: {group.file_path}\n")
            f.write("\n")

    print(f"\n[保存] 详细列表已保存到: inactive_groups.txt\n")

    # 条件2: 总对话小于20句的私聊
    MESSAGE_THRESHOLD = 20
    low_activity_private = [
        p for p in private_chats
        if p.text_message_count < MESSAGE_THRESHOLD
    ]
    low_activity_private.sort(key=lambda x: x.text_message_count)

    print("=" * 80)
    print(f"[结果2] 总对话少于{MESSAGE_THRESHOLD}条的私聊: {len(low_activity_private)}")
    print("=" * 80)

    # 显示前20个
    for i, chat in enumerate(low_activity_private[:20], 1):
        clean_name = clean_text_for_console(chat.name[:40])
        print(f"{i:3d}. [{chat.text_message_count:3d}条] "
              f"{clean_name:<40} "
              f"(最后活跃: {chat.last_message_time.strftime('%Y-%m-%d')})")

    if len(low_activity_private) > 20:
        print(f"... 还有 {len(low_activity_private) - 20} 个私聊未显示")

    # 保存详细列表
    with open('low_activity_private.txt', 'w', encoding='utf-8') as f:
        f.write(f"总对话少于{MESSAGE_THRESHOLD}条的私聊 (共{len(low_activity_private)}个)\n")
        f.write("=" * 100 + "\n\n")
        for i, chat in enumerate(low_activity_private, 1):
            f.write(f"{i}. 【{chat.text_message_count}条消息】 {chat.name}\n")
            f.write(f"   文件夹: {chat.folder_name}\n")
            f.write(f"   总消息数: {chat.message_count} (文本: {chat.text_message_count})\n")
            f.write(f"   首次对话: {chat.first_message_time.strftime('%Y-%m-%d')}\n")
            f.write(f"   最后对话: {chat.last_message_time.strftime('%Y-%m-%d')}\n")
            f.write(f"   路径: {chat.file_path}\n")
            f.write("\n")

    print(f"\n[保存] 详细列表已保存到: low_activity_private.txt\n")

    # 综合统计
    print("=" * 80)
    print("[汇总] 清理建议统计")
    print("=" * 80)

    total_to_remove = len(inactive_groups) + len(low_activity_private)

    # 计算文件大小（估算）
    inactive_groups_size = sum(g.message_count for g in inactive_groups)
    low_private_size = sum(p.message_count for p in low_activity_private)
    total_messages = sum(c.message_count for c in conversations)

    if len(conversations) > 0:
        removal_percentage = total_to_remove/len(conversations)*100
    else:
        removal_percentage = 0

    print(f"建议清理的对话数: {total_to_remove} / {len(conversations)} ({removal_percentage:.1f}%)")
    print(f"  - 不活跃群聊: {len(inactive_groups)}")
    print(f"  - 低活跃私聊: {len(low_activity_private)}")
    print()
    if total_messages > 0:
        message_percentage = (inactive_groups_size + low_private_size)/total_messages*100
    else:
        message_percentage = 0

    print(f"涉及的消息数: {inactive_groups_size + low_private_size:,} / {total_messages:,} "
          f"({message_percentage:.1f}%)")
    print(f"  - 不活跃群聊消息: {inactive_groups_size:,}")
    print(f"  - 低活跃私聊消息: {low_private_size:,}")
    print()

    # 生成删除脚本
    print("=" * 80)
    print("[脚本] 生成删除脚本")
    print("=" * 80)

    # Windows批处理脚本
    with open('delete_low_value_conversations.bat', 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo 警告：此脚本将删除低价值对话文件夹\n')
        f.write('echo 请确认您已经备份了重要数据！\n')
        f.write('echo.\n')
        f.write('pause\n\n')
        f.write('echo 开始删除...\n\n')

        for group in inactive_groups:
            folder_path = Path(group.file_path).parent
            f.write(f'rmdir /S /Q "{folder_path}"\n')

        for chat in low_activity_private:
            folder_path = Path(chat.file_path).parent
            f.write(f'rmdir /S /Q "{folder_path}"\n')

        f.write('\necho 删除完成！\n')
        f.write('pause\n')

    # Bash脚本（用于Git Bash或WSL）
    with open('delete_low_value_conversations.sh', 'w', encoding='utf-8') as f:
        f.write('#!/bin/bash\n\n')
        f.write('echo "警告：此脚本将删除低价值对话文件夹"\n')
        f.write('echo "请确认您已经备份了重要数据！"\n')
        f.write('read -p "输入 yes 继续: " confirm\n\n')
        f.write('if [ "$confirm" != "yes" ]; then\n')
        f.write('    echo "取消删除"\n')
        f.write('    exit 1\n')
        f.write('fi\n\n')
        f.write('echo "开始删除..."\n\n')

        for group in inactive_groups:
            folder_path = Path(group.file_path).parent
            # 转换Windows路径为Unix风格
            unix_path = str(folder_path).replace('\\', '/')
            f.write(f'rm -rf "{unix_path}"\n')

        for chat in low_activity_private:
            folder_path = Path(chat.file_path).parent
            unix_path = str(folder_path).replace('\\', '/')
            f.write(f'rm -rf "{unix_path}"\n')

        f.write('\necho "删除完成！"\n')

    print("[OK] 已生成删除脚本:")
    print("   - delete_low_value_conversations.bat (Windows)")
    print("   - delete_low_value_conversations.sh (Git Bash/WSL)")
    print()
    print("[警告] 请先审查生成的列表文件，确认无误后再执行删除脚本！")
    print()

    # 生成保留列表
    keep_conversations = [
        c for c in conversations
        if c not in inactive_groups and c not in low_activity_private
    ]

    with open('conversations_to_keep.txt', 'w', encoding='utf-8') as f:
        f.write(f"保留的对话 (共{len(keep_conversations)}个)\n")
        f.write("=" * 100 + "\n\n")

        # 按消息数排序
        keep_conversations.sort(key=lambda x: x.message_count, reverse=True)

        for i, conv in enumerate(keep_conversations, 1):
            f.write(f"{i}. {conv.name}\n")
            f.write(f"   类型: {conv.type}\n")
            f.write(f"   消息数: {conv.message_count} (文本: {conv.text_message_count})\n")
            f.write(f"   最后活跃: {conv.last_message_time.strftime('%Y-%m-%d')} "
                   f"({conv.days_since_last_message}天前)\n")
            f.write("\n")

    print(f"[保存] 保留对话列表已保存到: conversations_to_keep.txt")
    print()

if __name__ == "__main__":
    # 当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 80)
    print("微信聊天记录分析工具")
    print("=" * 80)
    print(f"工作目录: {current_dir}")
    print()

    analyze_conversations(current_dir)

    print("=" * 80)
    print("[完成] 分析完成！")
    print("=" * 80)
