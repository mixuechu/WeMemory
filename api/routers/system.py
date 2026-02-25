#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统路由（统计、健康检查等）
"""
import time
from fastapi import APIRouter, Depends
from typing import Annotated

from api.models.response import StatsResponse, HealthResponse
from api.services.recall_service import RecallService


router = APIRouter(prefix="/api", tags=["system"])

# 服务启动时间
_start_time = time.time()


# 依赖注入（从 recall 路由导入）
from api.routers.recall import get_recall_service


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="向量库统计",
    description="获取向量库的统计信息（总记忆数、对话数、时间范围等）"
)
async def get_stats(
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """获取统计信息"""
    stats = service.get_stats()
    return StatsResponse(**stats)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查API服务和向量库的健康状态"
)
async def health_check(
    service: Annotated[RecallService, Depends(get_recall_service)]
):
    """健康检查"""
    try:
        # 检查向量库是否已加载
        vector_store_loaded = service.vector_store is not None

        status = "healthy" if vector_store_loaded else "unhealthy"

        return HealthResponse(
            status=status,
            version="1.0.0",
            vector_store_loaded=vector_store_loaded,
            uptime_seconds=time.time() - _start_time
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            vector_store_loaded=False,
            uptime_seconds=time.time() - _start_time
        )
