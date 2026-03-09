#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选超过一年没有对话的私聊
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass
import shutil

@dataclass
class ConversationInfo:
    folder_name: str
    file_path: str
    name: str
    type: str
    message_count: int
    text_message_count: int
    last_message_time: datetime
    days_since_last_message: int

def parse_conversation_file(file_path: Path) -> ConversationInfo:
    """解析单个对话JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta = data.get('meta', {})
        messages = data.get('messages', [])

        # 过滤出文本消息
        text_messages = [m for m in messages if m.get('type') == 0]

        # 获取最后一条消息时间
        if messages:
            last_timestamp = messages[-1].get('timestamp', 0)
            last_time = datetime.fromtimestamp(last_timestamp)
        else:
            last_time = datetime(2000, 1, 1)

        days_since = (datetime.now() - last_time).days

        return ConversationInfo(
            folder_name=file_path.parent.name,
            file_path=str(file_path),
            name=meta.get('name', 'Unknown'),
            type=meta.get('type', 'unknown'),
            message_count=len(messages),
            text_message_count=len(text_messages),
            last_message_time=last_time,
            days_since_last_message=days_since
        )

    except Exception as e:
        print(f"[ERROR] 解析失败 {file_path}: {e}")
        return None

def find_all_conversation_files(root_dir: Path) -> List[Path]:
    """找出所有对话JSON文件"""
    json_files = []

    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # 在每个文件夹中查找同名JSON文件
            json_file = item / f"{item.name}.json"
            if json_file.exists():
                json_files.append(json_file)
            else:
                # 可能是包含对话的父文件夹
                if item.is_dir():
                    for sub_item in item.iterdir():
                        if sub_item.is_dir():
                            sub_json_file = sub_item / f"{sub_item.name}.json"
                            if sub_json_file.exists():
                                json_files.append(sub_json_file)

    return json_files

def clean_text_for_console(text: str) -> str:
    """清理文本用于控制台显示"""
    import re
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"
                               u"\U0001F300-\U0001F5FF"
                               u"\U0001F680-\U0001F6FF"
                               u"\U0001F1E0-\U0001F1FF"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    text = text.encode('gbk', errors='ignore').decode('gbk')
    return text

def main():
    print("=" * 80)
    print("筛选超过一年没有对话的私聊")
    print("=" * 80)

    # 扫描chat_data_filtered目录
    root_dir = Path("chat_data_filtered")

    if not root_dir.exists():
        print(f"[ERROR] 目录不存在: {root_dir}")
        return

    print(f"[INFO] 扫描目录: {root_dir}")
    json_files = find_all_conversation_files(root_dir)
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

    # 筛选私聊
    private_chats = [c for c in conversations if c.type == 'private']
    print(f"[INFO] 私聊总数: {len(private_chats)}")

    # 筛选超过365天（1年）没有对话的私聊
    DAYS_THRESHOLD = 365
    old_private_chats = [
        p for p in private_chats
        if p.days_since_last_message > DAYS_THRESHOLD
    ]
    old_private_chats.sort(key=lambda x: x.days_since_last_message, reverse=True)

    print("=" * 80)
    print(f"[结果] 超过 {DAYS_THRESHOLD} 天没有对话的私聊: {len(old_private_chats)}")
    print("=" * 80)

    # 显示前20个
    for i, chat in enumerate(old_private_chats[:20], 1):
        clean_name = clean_text_for_console(chat.name[:40])
        print(f"{i:3d}. [{chat.days_since_last_message:4d}天] "
              f"{clean_name:<40} "
              f"(共{chat.message_count:4d}条消息, 最后: {chat.last_message_time.strftime('%Y-%m-%d')})")

    if len(old_private_chats) > 20:
        print(f"... 还有 {len(old_private_chats) - 20} 个私聊未显示")

    # 保存详细列表
    with open('old_private_chats_to_delete.txt', 'w', encoding='utf-8') as f:
        f.write(f"超过{DAYS_THRESHOLD}天没有对话的私聊 (共{len(old_private_chats)}个)\n")
        f.write("=" * 100 + "\n\n")
        for i, chat in enumerate(old_private_chats, 1):
            f.write(f"{i}. 【{chat.days_since_last_message}天前】 {chat.name}\n")
            f.write(f"   文件夹: {chat.folder_name}\n")
            f.write(f"   消息数: {chat.message_count} (文本: {chat.text_message_count})\n")
            f.write(f"   最后对话: {chat.last_message_time.strftime('%Y-%m-%d')}\n")
            f.write(f"   路径: {chat.file_path}\n")
            f.write("\n")

    print(f"\n[保存] 详细列表已保存到: old_private_chats_to_delete.txt\n")

    # 统计信息
    total_messages_to_remove = sum(c.message_count for c in old_private_chats)
    total_messages = sum(c.message_count for c in conversations)

    print("=" * 80)
    print("[统计] 删除预览")
    print("=" * 80)
    print(f"将删除的私聊数: {len(old_private_chats)} / {len(private_chats)} ({len(old_private_chats)/len(private_chats)*100:.1f}%)")
    print(f"将删除的消息数: {total_messages_to_remove:,} / {total_messages:,} ({total_messages_to_remove/total_messages*100:.1f}%)")
    print()

    # 询问确认
    print("=" * 80)
    print("[确认] 是否执行删除？")
    print("=" * 80)
    confirm = input("输入 'yes' 确认删除，其他任意键取消: ")

    if confirm.lower() == 'yes':
        print("\n[执行] 开始删除...")
        deleted_count = 0
        failed_count = 0

        for i, chat in enumerate(old_private_chats, 1):
            folder_path = Path(chat.file_path).parent
            if folder_path.exists():
                try:
                    shutil.rmtree(folder_path)
                    deleted_count += 1
                    if i % 50 == 0:
                        print(f"   进度: {i}/{len(old_private_chats)} - 已删除: {deleted_count}")
                except Exception as e:
                    print(f"   [ERROR] 删除失败: {folder_path.name} - {e}")
                    failed_count += 1

        print("\n" + "=" * 80)
        print("[完成] 删除完成！")
        print("=" * 80)
        print(f"成功删除: {deleted_count}")
        print(f"失败: {failed_count}")
        print(f"总计: {len(old_private_chats)}")

        # 生成删除报告
        with open('删除报告_一年无对话私聊.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("删除超过一年没有对话的私聊 - 报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"删除时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"删除条件: 超过 {DAYS_THRESHOLD} 天没有对话的私聊\n\n")
            f.write(f"删除数量: {deleted_count} 个\n")
            f.write(f"失败数量: {failed_count} 个\n")
            f.write(f"删除消息数: {total_messages_to_remove:,} 条\n")
            f.write("=" * 80 + "\n")

        print(f"\n[保存] 删除报告已保存到: 删除报告_一年无对话私聊.txt")
    else:
        print("\n[取消] 删除操作已取消")

    print()

if __name__ == "__main__":
    main()
