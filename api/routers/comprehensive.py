#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合搜索路由 - 同时搜索聊天记录和知识图谱
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

from api.services.recall_service import RecallService
from api.services.triplet_search_service import TripletSearchService
from api.auth import verify_api_key


router = APIRouter(prefix="/api/comprehensive", tags=["comprehensive"])

# 全局服务实例
_recall_service: RecallService = None
_triplet_service: TripletSearchService = None


def set_services(recall_service: RecallService, triplet_service: TripletSearchService):
    """设置服务实例"""
    global _recall_service, _triplet_service
    _recall_service = recall_service
    _triplet_service = triplet_service


# Request Models
class ComprehensiveSearchRequest(BaseModel):
    """综合搜索请求"""
    query: str = Field(..., description="搜索查询")
    recall_type: Literal["auto", "semantic", "temporal", "people"] = Field(
        default="auto",
        description="聊天记录召回类型"
    )
    top_k_memories: int = Field(default=5, ge=1, le=20, description="返回的聊天记录数量")
    top_k_triplets: int = Field(default=5, ge=1, le=20, description="返回的三元组数量")
    min_memory_relevance: float = Field(default=0.3, ge=0.0, le=1.0, description="聊天记录最小相关度")
    min_triplet_score: float = Field(default=0.3, ge=0.0, le=1.0, description="三元组最小相似度")


# Response Models
class MemoryResult(BaseModel):
    """聊天记录结果"""
    memory_id: str
    content: str
    relevance_score: float
    recall_reason: str
    timestamp: int
    conversation_name: str
    participants: List[str]


class TripletResult(BaseModel):
    """三元组结果"""
    text: str
    type: str
    score: float
    metadata: Dict[str, Any]


class ComprehensiveSearchResponse(BaseModel):
    """综合搜索响应"""
    request_id: str
    memories: List[MemoryResult]
    triplets: List[TripletResult]
    total_memories: int
    total_triplets: int
    processing_time_ms: float


@router.post(
    "/search",
    response_model=ComprehensiveSearchResponse,
    summary="综合搜索",
    description="""
    综合搜索功能：同时搜索聊天记录和知识图谱三元组。

    这个端点会：
    1. 在聊天记录向量库中搜索相关对话
    2. 在知识图谱三元组中搜索相关关系和事实
    3. 合并返回所有相关信息

    适用场景：
    - 查询个人信息：同时获取聊天记录和知识图谱中的关系信息
    - 查询人际关系：获取三元组关系 + 相关对话
    - 查询事件：获取结构化事实 + 对话详情
    """
)
async def comprehensive_search(
    request: ComprehensiveSearchRequest,
    verified: bool = Depends(verify_api_key)
):
    """综合搜索 - 同时搜索聊天记录和三元组"""
    if not _recall_service or not _triplet_service:
        raise HTTPException(
            status_code=503,
            detail="服务未就绪"
        )

    try:
        import time
        start_time = time.time()

        # 1. 搜索聊天记录
        memory_result = _recall_service.recall(
            context=request.query,
            recall_type=request.recall_type,
            top_k=request.top_k_memories,
            min_relevance=request.min_memory_relevance
        )

        # 2. 搜索三元组
        triplet_result = _triplet_service.search(
            query=request.query,
            top_k=request.top_k_triplets,
            min_score=request.min_triplet_score
        )

        processing_time = (time.time() - start_time) * 1000

        return ComprehensiveSearchResponse(
            request_id=str(uuid.uuid4()),
            memories=[
                MemoryResult(
                    memory_id=m['memory_id'],
                    content=m['content'],
                    relevance_score=m['relevance_score'],
                    recall_reason=m['recall_reason'],
                    timestamp=m['timestamp'],
                    conversation_name=m['conversation_name'],
                    participants=m['participants']
                ) for m in memory_result['memories']
            ],
            triplets=[
                TripletResult(
                    text=t['text'],
                    type=t['type'],
                    score=t['score'],
                    metadata=t['metadata']
                ) for t in triplet_result['triplets']
            ],
            total_memories=memory_result['total_count'],
            total_triplets=triplet_result['total_count'],
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"综合搜索失败: {str(e)}"
        )


# 新增：人物知识查询
class PersonaKnowledgeRequest(BaseModel):
    """人物知识查询请求"""
    person_name: str = Field(..., description="人物姓名")
    top_k: int = Field(default=10, ge=1, le=50, description="返回的三元组数量")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="最小相似度")


class PersonaKnowledgeResponse(BaseModel):
    """人物知识查询响应"""
    person_name: str
    triplets: List[TripletResult]
    total_count: int
    processing_time_ms: float


@router.post(
    "/persona/knowledge",
    response_model=PersonaKnowledgeResponse,
    summary="人物知识查询",
    description="""
    查询与特定人物相关的知识图谱信息。

    这个端点会：
    1. 搜索包含该人物的所有三元组（关系、事件等）
    2. 按相关度排序返回

    适用场景：
    - Persona 数字人模式：获取该人物的关系、背景、事件
    - 人物画像：了解某个人的完整信息
    """
)
async def get_persona_knowledge(
    request: PersonaKnowledgeRequest,
    verified: bool = Depends(verify_api_key)
):
    """获取人物相关的知识图谱三元组"""
    if not _triplet_service:
        raise HTTPException(
            status_code=503,
            detail="三元组服务未就绪"
        )

    try:
        import time
        start_time = time.time()

        # 搜索包含该人物的三元组
        triplet_result = _triplet_service.search(
            query=request.person_name,
            top_k=request.top_k,
            min_score=request.min_score
        )

        processing_time = (time.time() - start_time) * 1000

        return PersonaKnowledgeResponse(
            person_name=request.person_name,
            triplets=[
                TripletResult(
                    text=t['text'],
                    type=t['type'],
                    score=t['score'],
                    metadata=t['metadata']
                ) for t in triplet_result['triplets']
            ],
            total_count=triplet_result['total_count'],
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"人物知识查询失败: {str(e)}"
        )
