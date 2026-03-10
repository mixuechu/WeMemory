"""
对话数据清洗模块

功能：
1. 过滤系统消息
2. 移除重复消息
3. 按时间间隔分割会话
4. 质量评估和过滤
5. 统计清洗效果

使用示例：
    from data_loader.cleaner import ConversationCleaner

    cleaner = ConversationCleaner(
        min_messages=3,
        max_time_gap_minutes=30,
        quality_threshold=0.5
    )

    cleaned = cleaner.clean(conversation_data)
    stats = cleaner.get_stats()
"""

import json
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime


class ConversationCleaner:
    """对话清洗器"""

    def __init__(
        self,
        min_messages: int = 3,
        max_time_gap_minutes: int = 30,
        quality_threshold: float = 0.5,
        filter_message_types: Optional[List[int]] = None,
        remove_duplicates: bool = True,
        filter_empty_media: bool = True,
        whitelist_names: Optional[List[str]] = None
    ):
        """
        初始化清洗器

        Args:
            min_messages: 最小消息数量（少于此数量的对话会被过滤）
            max_time_gap_minutes: 最大时间间隔（分钟），超过则分割会话
            quality_threshold: 质量阈值（0-1），低于此值的对话会被过滤
            filter_message_types: 要过滤的消息类型列表（默认只过滤80-系统消息）
            remove_duplicates: 是否移除重复消息
            filter_empty_media: 是否过滤纯媒体占位符的对话
            whitelist_names: 白名单对话名称（不会被过滤）
        """
        self.min_messages = min_messages
        self.max_time_gap_seconds = max_time_gap_minutes * 60
        self.quality_threshold = quality_threshold
        self.filter_message_types = filter_message_types or [80]  # 默认过滤系统消息
        self.remove_duplicates = remove_duplicates
        self.filter_empty_media = filter_empty_media
        self.whitelist_names = set(whitelist_names or [])

        # 统计信息
        self.stats = {
            'original_messages': 0,
            'filtered_messages': 0,
            'removed_system_messages': 0,
            'removed_duplicates': 0,
            'removed_low_quality': 0,
            'sessions_created': 0,
            'conversations_filtered': 0
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'ConversationCleaner':
        """
        从配置创建清洗器

        Args:
            config: 配置字典（来自 config.pipeline.data_cleaning）

        Returns:
            ConversationCleaner 实例
        """
        return cls(
            min_messages=config.get('min_messages', 3),
            max_time_gap_minutes=config.get('max_time_gap_minutes', 30),
            quality_threshold=config.get('quality_threshold', 0.5),
            filter_message_types=config.get('filter_message_types', [80]),
            remove_duplicates=config.get('remove_duplicates', True)
        )

    def clean(self, conversation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        清洗单个对话

        Args:
            conversation: ChatLab 格式的对话数据

        Returns:
            清洗后的对话，如果对话被过滤则返回 None
        """
        if 'messages' not in conversation:
            return None

        conversation_name = conversation.get('meta', {}).get('name', 'unknown')

        # 白名单检查
        if conversation_name in self.whitelist_names:
            return conversation

        messages = conversation['messages']
        self.stats['original_messages'] += len(messages)

        # 1. 过滤系统消息
        messages = self._filter_system_messages(messages)

        # 2. 移除重复
        if self.remove_duplicates:
            messages = self._remove_duplicates(messages)

        # 3. 分割会话
        sessions = self._split_sessions(messages)

        # 4. 质量过滤
        high_quality_sessions = []
        for session in sessions:
            if len(session) >= self.min_messages:
                quality_score = self._calculate_quality_score(session)
                if quality_score >= self.quality_threshold:
                    high_quality_sessions.append({
                        'messages': session,
                        'quality_score': quality_score
                    })
                else:
                    self.stats['removed_low_quality'] += len(session)

        # 如果没有高质量会话，过滤整个对话
        if not high_quality_sessions:
            self.stats['conversations_filtered'] += 1
            return None

        # 统计
        self.stats['sessions_created'] += len(high_quality_sessions)
        total_cleaned = sum(len(s['messages']) for s in high_quality_sessions)
        self.stats['filtered_messages'] += total_cleaned

        # 构建清洗后的对话
        cleaned_conversation = conversation.copy()

        # 如果只有一个会话，保持原格式
        if len(high_quality_sessions) == 1:
            cleaned_conversation['messages'] = high_quality_sessions[0]['messages']
            cleaned_conversation['quality_score'] = high_quality_sessions[0]['quality_score']
        else:
            # 多个会话，使用会话格式
            cleaned_conversation['sessions'] = [
                {
                    'session_id': i + 1,
                    'quality_score': s['quality_score'],
                    'messages': s['messages']
                }
                for i, s in enumerate(high_quality_sessions)
            ]
            # 移除顶层 messages（已分割为 sessions）
            cleaned_conversation.pop('messages', None)

        return cleaned_conversation

    def _filter_system_messages(self, messages: List[Dict]) -> List[Dict]:
        """过滤系统消息"""
        filtered = []
        for msg in messages:
            msg_type = msg.get('type', 0)
            if msg_type not in self.filter_message_types:
                filtered.append(msg)
            else:
                self.stats['removed_system_messages'] += 1

        return filtered

    def _remove_duplicates(self, messages: List[Dict]) -> List[Dict]:
        """移除重复消息"""
        seen = set()
        unique_messages = []

        for msg in messages:
            # 使用 sender, timestamp, content 作为唯一键
            key = (
                msg.get('sender', ''),
                msg.get('timestamp', 0),
                msg.get('content', '')
            )

            if key not in seen:
                seen.add(key)
                unique_messages.append(msg)
            else:
                self.stats['removed_duplicates'] += 1

        return unique_messages

    def _split_sessions(self, messages: List[Dict]) -> List[List[Dict]]:
        """按时间间隔分割会话"""
        if not messages:
            return []

        sessions = []
        current_session = [messages[0]]

        for i in range(1, len(messages)):
            prev_msg = messages[i - 1]
            curr_msg = messages[i]

            prev_time = prev_msg.get('timestamp', 0)
            curr_time = curr_msg.get('timestamp', 0)

            time_gap = curr_time - prev_time

            if time_gap > self.max_time_gap_seconds:
                # 时间间隔过大，分割会话
                sessions.append(current_session)
                current_session = [curr_msg]
            else:
                current_session.append(curr_msg)

        # 添加最后一个会话
        if current_session:
            sessions.append(current_session)

        return sessions

    def _calculate_quality_score(self, messages: List[Dict]) -> float:
        """
        计算对话质量分数

        评分维度：
        - 平均消息长度（30%）
        - 发送者多样性（25%）
        - 时间跨度（20%）
        - 实质内容比例（25%）

        Returns:
            质量分数 (0-1)
        """
        if not messages:
            return 0.0

        # 1. 平均消息长度分数
        avg_length_score = self._score_avg_message_length(messages)

        # 2. 发送者多样性分数
        diversity_score = self._score_sender_diversity(messages)

        # 3. 时间跨度分数
        time_span_score = self._score_time_span(messages)

        # 4. 实质内容比例分数
        content_ratio_score = self._score_content_ratio(messages)

        # 加权平均
        quality_score = (
            0.30 * avg_length_score +
            0.25 * diversity_score +
            0.20 * time_span_score +
            0.25 * content_ratio_score
        )

        return round(quality_score, 2)

    def _score_avg_message_length(self, messages: List[Dict]) -> float:
        """评分：平均消息长度"""
        total_length = sum(len(msg.get('content', '')) for msg in messages)
        avg_length = total_length / len(messages) if messages else 0

        # 评分曲线：0-5字=0分，5-20字线性增长，20字以上=1分
        if avg_length <= 5:
            return 0.0
        elif avg_length >= 20:
            return 1.0
        else:
            return (avg_length - 5) / 15

    def _score_sender_diversity(self, messages: List[Dict]) -> float:
        """评分：发送者多样性"""
        senders = set(msg.get('sender', '') for msg in messages)
        sender_count = len(senders)

        # 评分：1个发送者=0分，2个=0.5分，3个及以上=1分
        if sender_count == 1:
            return 0.0
        elif sender_count == 2:
            return 0.5
        else:
            return 1.0

    def _score_time_span(self, messages: List[Dict]) -> float:
        """评分：时间跨度"""
        if len(messages) < 2:
            return 0.0

        timestamps = [msg.get('timestamp', 0) for msg in messages]
        time_span_seconds = max(timestamps) - min(timestamps)

        # 评分曲线：<1分钟=0分，1-10分钟线性增长，>10分钟=1分
        time_span_minutes = time_span_seconds / 60

        if time_span_minutes < 1:
            return 0.0
        elif time_span_minutes >= 10:
            return 1.0
        else:
            return (time_span_minutes - 1) / 9

    def _score_content_ratio(self, messages: List[Dict]) -> float:
        """评分：实质内容比例（非媒体占位符）"""
        if not messages:
            return 0.0

        # 媒体占位符模式
        media_patterns = ['[图片]', '[语音]', '[视频]', '[文件]', '[表情]', '[链接]', '[小程序]']

        text_messages = 0
        for msg in messages:
            content = msg.get('content', '').strip()
            # 如果不是纯媒体占位符，算作实质内容
            if content and not any(content == pattern for pattern in media_patterns):
                text_messages += 1

        ratio = text_messages / len(messages)

        # 评分曲线：<30%=0分，30-70%线性增长，>70%=1分
        if ratio < 0.3:
            return 0.0
        elif ratio >= 0.7:
            return 1.0
        else:
            return (ratio - 0.3) / 0.4

    def get_stats(self) -> Dict[str, Any]:
        """获取清洗统计信息"""
        removed_total = (
            self.stats['removed_system_messages'] +
            self.stats['removed_duplicates'] +
            self.stats['removed_low_quality']
        )

        return {
            **self.stats,
            'removed_total': removed_total,
            'retention_rate': (
                self.stats['filtered_messages'] / self.stats['original_messages']
                if self.stats['original_messages'] > 0 else 0
            )
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'original_messages': 0,
            'filtered_messages': 0,
            'removed_system_messages': 0,
            'removed_duplicates': 0,
            'removed_low_quality': 0,
            'sessions_created': 0,
            'conversations_filtered': 0
        }


def clean_conversation_file(
    input_path: str,
    output_path: str,
    cleaner: Optional[ConversationCleaner] = None
) -> Dict[str, Any]:
    """
    清洗单个对话文件

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        cleaner: 清洗器实例（可选）

    Returns:
        清洗统计信息
    """
    if cleaner is None:
        cleaner = ConversationCleaner()

    # 加载对话
    with open(input_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)

    # 清洗
    cleaned = cleaner.clean(conversation)

    if cleaned is None:
        return {'skipped': True, 'reason': 'filtered'}

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    return {'skipped': False, 'stats': cleaner.get_stats()}
