#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统路由（统计、健康检查等）
"""
import os
import sys
import time
import psutil
from pathlib import Path
from fastapi import APIRouter, Depends
from typing import Annotated, Dict, Any

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
    """基础健康检查"""
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


@router.get(
    "/health/detailed",
    summary="详细健康检查",
    description="获取详细的系统健康状态，包括向量库、索引、内存使用等"
)
async def detailed_health_check(
    service: Annotated[RecallService, Depends(get_recall_service)]
) -> Dict[str, Any]:
    """详细健康检查"""
    components = {}

    # 1. 检查对话向量库
    try:
        if hasattr(service, 'vector_store') and service.vector_store is not None:
            vs = service.vector_store
            components['conversation_vector_store'] = {
                'status': 'healthy',
                'total_memories': len(vs.embeddings) if hasattr(vs, 'embeddings') else 0,
                'index_type': 'HNSW' if hasattr(vs, 'index') else 'None',
                'dimensions': vs.embeddings[0].shape[0] if (hasattr(vs, 'embeddings') and len(vs.embeddings) > 0) else 0
            }
        else:
            components['conversation_vector_store'] = {
                'status': 'unhealthy',
                'error': 'Vector store not loaded'
            }
    except Exception as e:
        components['conversation_vector_store'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    # 2. 检查三元组向量库（如果存在）
    triplet_path = Path('vector_stores/triplets/embeddings.pkl')
    if triplet_path.exists():
        try:
            components['triplet_vector_store'] = {
                'status': 'healthy',
                'file_exists': True,
                'file_size_mb': round(triplet_path.stat().st_size / (1024 * 1024), 2)
            }
        except Exception as e:
            components['triplet_vector_store'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    else:
        components['triplet_vector_store'] = {
            'status': 'not_configured',
            'message': 'Triplet vector store not found (optional)'
        }

    # 3. 检查内存使用
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_used_mb = memory_info.rss / (1024 * 1024)

        # 获取系统总内存
        virtual_memory = psutil.virtual_memory()
        total_memory_mb = virtual_memory.total / (1024 * 1024)
        memory_percent = (memory_used_mb / total_memory_mb) * 100

        components['memory'] = {
            'status': 'healthy' if memory_percent < 80 else 'warning',
            'used_mb': round(memory_used_mb, 2),
            'total_mb': round(total_memory_mb, 2),
            'usage_percent': round(memory_percent, 2)
        }
    except Exception as e:
        components['memory'] = {
            'status': 'unknown',
            'error': str(e)
        }

    # 4. 检查磁盘空间（数据目录）
    try:
        data_path = Path('data')
        if data_path.exists():
            disk_usage = psutil.disk_usage(str(data_path))
            components['disk'] = {
                'status': 'healthy' if disk_usage.percent < 90 else 'warning',
                'free_gb': round(disk_usage.free / (1024 ** 3), 2),
                'total_gb': round(disk_usage.total / (1024 ** 3), 2),
                'usage_percent': disk_usage.percent
            }
        else:
            components['disk'] = {
                'status': 'unknown',
                'message': 'Data directory not found'
            }
    except Exception as e:
        components['disk'] = {
            'status': 'unknown',
            'error': str(e)
        }

    # 整体状态判断
    unhealthy_components = [
        name for name, info in components.items()
        if info.get('status') == 'unhealthy'
    ]

    overall_status = 'unhealthy' if unhealthy_components else 'healthy'

    return {
        'status': overall_status,
        'version': '1.0.0',
        'components': components,
        'uptime_seconds': round(time.time() - _start_time, 2),
        'unhealthy_components': unhealthy_components if unhealthy_components else None
    }
