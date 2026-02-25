#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Message:
    """单条消息"""
    sender: str
    sender_name: str
    timestamp: datetime
    content: str
    msg_type: int


@dataclass
class ConversationSession:
    """会话片段 - 基本embedding单位"""
    session_id: str
    conversation_name: str
    conversation_type: str
    participants: List[str]
    start_time: datetime
    end_time: datetime
    messages: List[Message]
    enriched_text: str = ""
    embedding: Optional[List[float]] = None
    session_type: str = 'main'  # 'main' 或 'overlap'
