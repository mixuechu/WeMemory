#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话切分器 - 将消息流切分为会话片段
"""
import hashlib
from datetime import timedelta
from typing import List
from .models import Message, ConversationSession


class SessionBuilder:
    """
    会话片段构建器

    采用混合滑动窗口策略：
    1. Phase 1: 严格分割 - 按时间间隔和消息数量分割
    2. Phase 2: 创建主sessions
    3. Phase 3: 创建边界overlaps - 跨越分割点的重叠片段
    """

    def __init__(
        self,
        time_gap_minutes: int = 30,
        min_messages: int = 3,
        max_messages: int = 20
    ):
        """
        Args:
            time_gap_minutes: 时间间隔阈值（分钟），超过此间隔则分割
            min_messages: 最小消息数，少于此数量的片段会被丢弃
            max_messages: 最大消息数，超过此数量会强制分割
        """
        self.time_gap = timedelta(minutes=time_gap_minutes)
        self.min_messages = min_messages
        self.max_messages = max_messages

    def split_into_sessions(
        self,
        messages: List[Message],
        conv_meta: dict
    ) -> List[ConversationSession]:
        """
        将消息流切分为会话片段（混合策略：严格分割 + 边界重叠）

        Args:
            messages: 消息列表
            conv_meta: 对话元数据（name, type等）

        Returns:
            会话片段列表
        """
        sessions = []
        current_batch = []
        batches = []  # 先收集所有严格分割的batches

        print(f"[INFO] 开始切分会话，总消息数: {len(messages)}")
        print(f"[INFO] 使用混合滑动窗口策略")

        # Phase 1: 严格分割
        for i, msg in enumerate(messages):
            # 只处理文本消息
            if msg.msg_type != 0:
                continue

            if not msg.content or len(msg.content.strip()) == 0:
                continue

            should_split = False

            if current_batch:
                time_since_last = msg.timestamp - current_batch[-1].timestamp

                if time_since_last > self.time_gap:
                    should_split = True
                elif len(current_batch) >= self.max_messages:
                    should_split = True

            if should_split and len(current_batch) >= self.min_messages:
                batches.append(current_batch)
                current_batch = []

            current_batch.append(msg)

            if (i + 1) % 10000 == 0:
                print(f"   处理进度: {i+1}/{len(messages)}, 已生成batches: {len(batches)}")

        if len(current_batch) >= self.min_messages:
            batches.append(current_batch)

        print(f"[INFO] Phase 1完成: 严格分割生成 {len(batches)} 个batches")

        # Phase 2: 创建主sessions
        for i, batch in enumerate(batches):
            session = self._build_session(batch, conv_meta, session_type='main')
            sessions.append(session)

        # Phase 3: 创建边界overlaps
        overlap_window = 5  # 每侧取5条消息
        overlap_count = 0

        for i in range(len(batches) - 1):
            prev_batch = batches[i]
            next_batch = batches[i + 1]

            # 检查时间间隔，如果太长就不创建overlap
            time_gap = next_batch[0].timestamp - prev_batch[-1].timestamp
            if time_gap > timedelta(hours=2):  # 超过2小时不创建overlap
                continue

            # 创建overlap: 前batch的后N条 + 后batch的前N条
            overlap_msgs = prev_batch[-overlap_window:] + next_batch[:overlap_window]

            if len(overlap_msgs) >= self.min_messages:
                overlap_session = self._build_session(overlap_msgs, conv_meta, session_type='overlap')
                sessions.append(overlap_session)
                overlap_count += 1

        print(f"[INFO] Phase 2完成: 创建 {overlap_count} 个边界overlaps")
        print(f"[OK] 切分完成，总计生成 {len(sessions)} 个会话片段")
        print(f"      - 主sessions: {len(batches)}")
        print(f"      - 边界overlaps: {overlap_count}")
        return sessions

    def _build_session(
        self,
        messages: List[Message],
        conv_meta: dict,
        session_type: str = 'main'
    ) -> ConversationSession:
        """
        构建会话片段对象

        Args:
            messages: 消息列表
            conv_meta: 对话元数据
            session_type: 'main' 或 'overlap'

        Returns:
            ConversationSession对象
        """
        # 生成唯一session_id
        session_id = hashlib.md5(
            f"{session_type}_{messages[0].timestamp.timestamp()}_{messages[-1].timestamp.timestamp()}".encode()
        ).hexdigest()

        # 提取参与者
        participants = list(set(m.sender_name for m in messages))

        session = ConversationSession(
            session_id=session_id,
            conversation_name=conv_meta['name'],
            conversation_type=conv_meta['type'],
            participants=participants,
            start_time=messages[0].timestamp,
            end_time=messages[-1].timestamp,
            messages=messages,
            session_type=session_type
        )

        return session
