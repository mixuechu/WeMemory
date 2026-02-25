#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆联想路由
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from api.models.request import (
    RecallRequest,
    TopicAssociationRequest,
    PeopleAssociationRequest,
    TemporalAssociationRequest,
    SimpleSearchRequest
)
from api.models.response import (
    RecallResponse,
    TopicAssociationResponse,
    PeopleAssociationResponse,
    TemporalAssociationResponse,
    SearchResponse,
    ErrorResponse
)
from api.services.recall_service import RecallService


router = APIRouter(prefix="/api", tags=["recall"])

# 全局服务实例（在 main.py 中初始化）
_recall_service: RecallService = None


def get_recall_service() -> RecallService:
    """获取联想服务实例"""
    if _recall_service is None:
        raise HTTPException(
            status_code=503,
            detail="服务未就绪，向量库加载中..."
        )
    return _recall_service


def set_recall_service(service: RecallService):
    """设置联想服务实例"""
    global _recall_service
    _recall_service = service


@router.post(
    "/recall",
    response_model=RecallResponse,
    summary="记忆联想",
    description="""
    核心功能：根据当前上下文，智能联想相关的历史记忆。

    这不是简单的搜索，而是模拟人类记忆的联想过程：
    - 一个线索可以触发多个相关记忆
    - 自动识别联想类型（语义/时序/人物）
    - 提供联想原因说明

    示例：
    输入："明天要和张三讨论AI项目"
    联想到：
    - 上次和张三讨论AI项目的对话
    - 其他关于AI项目的讨论
    - 张三参与的其他会议
    """
)
async def recall_memories(
    request: RecallRequest,
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """记忆联想"""
    try:
        result = service.recall(
            context=request.context,
            recall_type=request.recall_type,
            top_k=request.top_k,
            min_relevance=request.min_relevance,
            time_range=request.time_range
        )

        return RecallResponse(
            request_id=str(uuid.uuid4()),
            memories=result['memories'],
            total_count=result['total_count'],
            associations=result['associations'],
            recall_strategy=result['recall_strategy'],
            processing_time_ms=result['processing_time_ms']
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"联想失败: {str(e)}"
        )


@router.post(
    "/associate/topic",
    response_model=TopicAssociationResponse,
    summary="主题关联",
    description="找到与特定主题相关的所有记忆"
)
async def associate_by_topic(
    request: TopicAssociationRequest,
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """主题关联"""
    try:
        result = service.recall_by_topic(
            topic=request.topic,
            top_k=request.top_k,
            min_relevance=request.min_relevance
        )

        return TopicAssociationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"主题关联失败: {str(e)}"
        )


@router.post(
    "/associate/people",
    response_model=PeopleAssociationResponse,
    summary="人物关联",
    description="找到与特定人物相关的记忆"
)
async def associate_by_people(
    request: PeopleAssociationRequest,
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """人物关联"""
    try:
        result = service.recall_by_people(
            person=request.person,
            top_k=request.top_k,
            include_mentions=request.include_mentions
        )

        return PeopleAssociationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"人物关联失败: {str(e)}"
        )


@router.post(
    "/associate/temporal",
    response_model=TemporalAssociationResponse,
    summary="时序联想",
    description="找到时间上相关的记忆（之前/之后/前后）"
)
async def associate_by_time(
    request: TemporalAssociationRequest,
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """时序联想"""
    try:
        result = service.recall_by_time(
            reference_time=request.reference_time,
            direction=request.direction,
            time_window=request.time_window,
            top_k=request.top_k
        )

        return TemporalAssociationResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"时序联想失败: {str(e)}"
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="简单搜索（兼容性）",
    description="""
    简单的关键词搜索功能。

    ⚠️ 注意：这是为了兼容传统搜索需求，
    推荐使用 /api/recall 以获得更好的联想效果。
    """
)
async def simple_search(
    request: SimpleSearchRequest,
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """简单搜索"""
    try:
        result = service.simple_search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        return SearchResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索失败: {str(e)}"
        )
