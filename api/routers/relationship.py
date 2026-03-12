#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心关系查询路由

提供轻量级的人物关系查询API，作为个人助理的Tool使用。
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel, Field

from api.services.relationship_service import RelationshipService
from api.auth import verify_api_key

router = APIRouter(prefix="/api/relationships", tags=["relationships"])

# 全局服务实例
_relationship_service: Optional[RelationshipService] = None


def set_relationship_service(service: RelationshipService):
    """设置关系服务实例"""
    global _relationship_service
    _relationship_service = service


def get_service() -> RelationshipService:
    """获取服务实例"""
    if _relationship_service is None:
        raise HTTPException(
            status_code=503,
            detail="关系服务未初始化"
        )
    return _relationship_service


# === Request/Response Models ===

class PersonRelationshipsResponse(BaseModel):
    """人物关系响应"""
    name: str = Field(..., description="人物名字")
    profile: Optional[str] = Field(None, description="人物简介")
    relationships: List[dict] = Field(..., description="关系列表")


class QueryResponse(BaseModel):
    """查询响应"""
    success: bool
    query: Optional[str] = None
    person: Optional[str] = None
    profile: Optional[str] = None
    relationships: Optional[List[dict]] = None
    message: Optional[str] = None


class FamilyTreeResponse(BaseModel):
    """家族树响应"""
    success: bool
    person: Optional[str] = None
    family: Optional[dict] = None
    message: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    total_persons: int
    total_relationships: int
    reviewed_persons: int
    export_time: str


# === Endpoints ===

@router.get(
    "/query",
    response_model=QueryResponse,
    summary="查询人物关系",
    description="""
    智能查询人物关系，支持自然语言查询。

    **示例**:
    - `赵萌`
    - `赵萌的配偶`
    - `谁是米雪川的妻子`

    **作为LLM Tool使用**:
    当用户问到某人的关系时，调用此接口获取信息。
    """
)
async def query_relationships(
    query: str = Query(..., description="查询字符串，如'赵萌'或'赵萌的配偶'"),
    max_results: int = Query(10, ge=1, le=50, description="最大返回结果数"),
    verified: bool = Depends(verify_api_key)
):
    """
    查询人物关系（智能查询）

    这是主要的查询端点，支持自然语言查询。
    LLM可以直接调用此接口来获取人物关系信息。
    """
    service = get_service()
    result = service.query_relationships(query, max_results)
    return result


@router.get(
    "/person/{person_name}",
    response_model=PersonRelationshipsResponse,
    summary="获取人物所有关系",
    description="获取指定人物的所有关系信息"
)
async def get_person_relationships(
    person_name: str,
    include_profile: bool = Query(True, description="是否包含人物简介"),
    verified: bool = Depends(verify_api_key)
):
    """获取人物所有关系"""
    service = get_service()
    result = service.get_person_relationships(person_name, include_profile)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"未找到人物: {person_name}"
        )

    return result


@router.get(
    "/family/{person_name}",
    response_model=FamilyTreeResponse,
    summary="获取家族树",
    description="获取某人的直系家属关系（配偶、父母、孩子、兄弟姐妹）"
)
async def get_family_tree(
    person_name: str,
    verified: bool = Depends(verify_api_key)
):
    """获取家族树"""
    service = get_service()
    result = service.get_family_tree(person_name)
    return result


@router.get(
    "/related/{person_name}",
    response_model=List[str],
    summary="获取相关人物",
    description="获取与某人有关系的所有人"
)
async def get_related_people(
    person_name: str,
    relation_types: Optional[str] = Query(
        None,
        description="关系类型过滤，多个用逗号分隔，如'HAS_SPOUSE,HAS_CHILD'"
    ),
    verified: bool = Depends(verify_api_key)
):
    """获取相关人物"""
    service = get_service()

    # 解析关系类型
    types_list = None
    if relation_types:
        types_list = [t.strip() for t in relation_types.split(',')]

    result = service.get_related_people(person_name, types_list)
    return result


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="获取统计信息",
    description="获取关系数据的统计信息"
)
async def get_stats(verified: bool = Depends(verify_api_key)):
    """获取统计信息"""
    service = get_service()
    return service.get_stats()


@router.get(
    "/search",
    summary="搜索人物",
    description="搜索人物（支持模糊匹配）"
)
async def search_person(
    query: str = Query(..., description="查询字符串"),
    verified: bool = Depends(verify_api_key)
):
    """搜索人物"""
    service = get_service()
    result = service.search_person(query)

    if result is None:
        return {
            "success": False,
            "query": query,
            "message": "未找到匹配的人物"
        }

    return {
        "success": True,
        "query": query,
        "matched_name": result
    }
