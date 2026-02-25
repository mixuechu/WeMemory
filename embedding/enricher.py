#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本富化器 - 为会话添加上下文信息
"""
from datetime import datetime
from typing import List


class TextEnricher:
    """
    文本富化器

    双向量策略：
    1. 内容向量 (content_text): 纯对话内容
    2. 上下文向量 (context_text): 时间、参与者等元信息
    """

    def enrich_session(self, session) -> tuple:
        """
        为会话生成双文本（内容 + 上下文）

        Args:
            session: ConversationSession对象

        Returns:
            (content_text, context_text) 元组
        """
        # 1. 纯对话内容（用于主向量）
        dialogue = self._format_dialogue(session.messages)

        # 2. 上下文信息（用于辅助向量）
        dt = session.start_time
        period = '上午' if dt.hour < 12 else '下午' if dt.hour < 18 else '晚上'
        participants_str = ', '.join(session.participants)

        context = f"{dt.year}年{dt.month}月{dt.day}日{period} 参与者：{participants_str}"

        return dialogue, context

    def _format_time(self, dt: datetime) -> str:
        """格式化时间"""
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = weekdays[dt.weekday()]
        period = '上午' if dt.hour < 12 else '下午' if dt.hour < 18 else '晚上'
        return f"{dt.year}年{dt.month}月{dt.day}日 {weekday} {period}{dt.hour}:{dt.minute:02d}"

    def _format_dialogue(self, messages) -> str:
        """
        格式化对话内容

        Args:
            messages: Message对象列表

        Returns:
            格式化的对话文本
        """
        lines = []
        for msg in messages:
            # 清理昵称（去除括号内容）
            name = msg.sender_name.split('(')[0].split('（')[0].strip()
            # 限制单条消息长度
            content = msg.content[:200]
            if len(msg.content) > 200:
                content += "..."
            lines.append(f"{name}: {content}")
        return '\n'.join(lines)

    def _calc_duration(self, session) -> str:
        """计算会话持续时间"""
        delta = session.end_time - session.start_time
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return "不到1分钟"

        minutes = total_seconds // 60

        if minutes < 60:
            return f"{minutes}分钟"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}小时{mins}分钟" if mins > 0 else f"{hours}小时"
