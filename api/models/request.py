#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 请求模型
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class RecallRequest(BaseModel):
    """
    记忆联想请求

    这是核心功能：根据当前上下文，联想到相关的历史记忆
    """
    context: str = Field(
        ...,
        description="当前对话上下文或触发信息",
        min_length=1,
        example="明天要和张三讨论AI项目的进展"
    )

    recall_type: Literal["auto", "semantic", "temporal", "people"] = Field(
        default="auto",
        description="联想类型：auto(自动), semantic(语义), temporal(时序), people(人物)"
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="返回记忆数量"
    )

    include_context: bool = Field(
        default=True,
        description="是否包含上下文增强信息"
    )

    min_relevance: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="最小相关性阈值"
    )

    time_range: Optional[dict] = Field(
        default=None,
        description="时间范围过滤 {'start': timestamp, 'end': timestamp}",
        example={"start": 1704067200, "end": 1735689600}
    )


class TopicAssociationRequest(BaseModel):
    """主题关联请求"""
    topic: str = Field(
        ...,
        description="主题关键词或描述",
        example="AI项目"
    )

    top_k: int = Field(default=10, ge=1, le=50)
    min_relevance: float = Field(default=0.3, ge=0.0, le=1.0)


class PeopleAssociationRequest(BaseModel):
    """人物关联请求"""
    person: str = Field(
        ...,
        description="人物姓名",
        example="张三"
    )

    top_k: int = Field(default=10, ge=1, le=50)
    include_mentions: bool = Field(
        default=True,
        description="是否包含提及该人物的对话"
    )


class TemporalAssociationRequest(BaseModel):
    """时序联想请求"""
    reference_time: int = Field(
        ...,
        description="参考时间戳",
        example=1708012800
    )

    direction: Literal["before", "after", "around"] = Field(
        default="around",
        description="时间方向：before(之前), after(之后), around(前后)"
    )

    time_window: int = Field(
        default=7,
        ge=1,
        le=365,
        description="时间窗口（天）"
    )

    top_k: int = Field(default=10, ge=1, le=50)


class SimpleSearchRequest(BaseModel):
    """
    简单搜索请求（兼容性功能）

    注：这是为了兼容传统搜索需求，
    推荐使用 RecallRequest 以获得更好的联想效果
    """
    query: str = Field(
        ...,
        description="搜索关键词",
        min_length=1
    )

    top_k: int = Field(default=5, ge=1, le=20)

    filters: Optional[dict] = Field(
        default=None,
        description="过滤条件"
    )


class FeedbackRequest(BaseModel):
    """
    联想质量反馈（未来功能）

    用于改进联想算法
    """
    request_id: str = Field(..., description="请求ID")
    memory_id: str = Field(..., description="记忆ID")
    relevance_score: int = Field(..., ge=1, le=5, description="相关性评分 1-5")
    comment: Optional[str] = Field(default=None, description="反馈意见")
