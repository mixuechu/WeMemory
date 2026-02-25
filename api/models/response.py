#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 响应模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """单个记忆片段"""
    memory_id: str = Field(..., description="记忆唯一ID")
    content: str = Field(..., description="记忆内容")
    relevance_score: float = Field(..., description="相关性分数 (0-1)")
    recall_reason: str = Field(..., description="联想原因说明")

    # 元信息
    timestamp: int = Field(..., description="时间戳")
    conversation_name: str = Field(..., description="对话名称")
    participants: List[str] = Field(..., description="参与者列表")

    # 上下文信息（可选）
    context_before: Optional[str] = Field(None, description="前文上下文")
    context_after: Optional[str] = Field(None, description="后文上下文")

    # 关联信息
    related_memories: Optional[List[str]] = Field(
        None,
        description="相关记忆ID列表"
    )


class AssociationInfo(BaseModel):
    """联想信息汇总"""
    people: List[str] = Field(default_factory=list, description="相关人物")
    topics: List[str] = Field(default_factory=list, description="相关主题")
    locations: Optional[List[str]] = Field(default_factory=list, description="相关地点")
    time_context: Optional[str] = Field(None, description="时间上下文说明")


class RecallResponse(BaseModel):
    """记忆联想响应"""
    request_id: str = Field(..., description="请求ID（用于追踪和反馈）")
    memories: List[MemoryItem] = Field(..., description="联想到的记忆列表")
    total_count: int = Field(..., description="返回记忆数量")

    # 联想元信息
    associations: AssociationInfo = Field(..., description="联想关联信息")
    recall_strategy: str = Field(..., description="使用的联想策略")

    # 性能指标
    processing_time_ms: float = Field(..., description="处理时间（毫秒）")


class TopicAssociationResponse(BaseModel):
    """主题关联响应"""
    topic: str = Field(..., description="主题")
    memories: List[MemoryItem] = Field(..., description="相关记忆")
    total_count: int = Field(..., description="记忆数量")
    topic_summary: Optional[str] = Field(None, description="主题摘要")


class PeopleAssociationResponse(BaseModel):
    """人物关联响应"""
    person: str = Field(..., description="人物姓名")
    memories: List[MemoryItem] = Field(..., description="相关记忆")
    total_count: int = Field(..., description="记忆数量")

    # 人物信息（未来扩展：来自知识图谱）
    person_info: Optional[Dict[str, Any]] = Field(
        None,
        description="人物信息（关系、职业等）"
    )


class TemporalAssociationResponse(BaseModel):
    """时序联想响应"""
    reference_time: int = Field(..., description="参考时间")
    direction: str = Field(..., description="时间方向")
    memories: List[MemoryItem] = Field(..., description="相关记忆")
    total_count: int = Field(..., description="记忆数量")
    timeline_summary: Optional[str] = Field(None, description="时间线摘要")


class SearchResponse(BaseModel):
    """简单搜索响应（兼容性）"""
    query: str = Field(..., description="搜索查询")
    results: List[MemoryItem] = Field(..., description="搜索结果")
    total_count: int = Field(..., description="结果数量")


class StatsResponse(BaseModel):
    """向量库统计响应"""
    total_memories: int = Field(..., description="总记忆数量")
    total_conversations: int = Field(..., description="总对话数量")
    date_range: Dict[str, int] = Field(..., description="时间范围")
    vector_dimension: int = Field(..., description="向量维度")
    index_type: str = Field(..., description="索引类型")
    last_updated: Optional[int] = Field(None, description="最后更新时间")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态: healthy/unhealthy")
    version: str = Field(..., description="API版本")
    vector_store_loaded: bool = Field(..., description="向量库是否已加载")
    uptime_seconds: float = Field(..., description="运行时间（秒）")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细信息")
    request_id: Optional[str] = Field(None, description="请求ID")
