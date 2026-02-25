#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录解析器
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from .models import Message


class WeChatParser:
    """微信聊天记录JSON解析器"""

    @staticmethod
    def load_conversation(file_path: Path) -> tuple:
        """
        加载微信对话文件

        Args:
            file_path: 对话JSON文件路径

        Returns:
            (messages, metadata) 元组
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages = WeChatParser.parse_messages(data['messages'])
        metadata = data.get('meta', {})

        return messages, metadata

    @staticmethod
    def parse_messages(raw_messages: List[dict]) -> List[Message]:
        """
        解析原始消息列表

        Args:
            raw_messages: 原始消息字典列表

        Returns:
            Message对象列表
        """
        messages = []
        for m in raw_messages:
            messages.append(Message(
                sender=m['sender'],
                sender_name=m['accountName'],
                timestamp=datetime.fromtimestamp(m['timestamp']),
                content=m.get('content', ''),
                msg_type=m['type']
            ))
        return messages
