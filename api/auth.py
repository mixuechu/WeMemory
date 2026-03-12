#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 认证
"""
import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    验证API Key

    Args:
        api_key: 从请求头中提取的API Key

    Returns:
        验证通过返回True

    Raises:
        HTTPException: API Key无效或缺失
    """
    expected_key = os.getenv("API_KEY")

    # 如果未配置API_KEY，则不进行验证（兼容开发环境）
    if not expected_key:
        return True

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Please provide X-API-Key header."
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

    return True
