#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeMemory API - 记忆联想服务

这不是一个简单的搜索API，而是一个智能的记忆联想服务。
就像人类记忆一样，一个线索可以触发多个相关记忆。
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import recall, system, persona, comprehensive
from api.services.recall_service import RecallService
from api.services.triplet_search_service import TripletSearchService

# 加载环境变量
load_dotenv()


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动和关闭时的处理

    启动时：加载向量库
    关闭时：清理资源
    """
    print("=" * 70)
    print("WeMemory API 启动中...")
    print("=" * 70)

    # 获取向量库路径
    vector_store_path = os.getenv(
        "VECTOR_STORE_PATH",
        "vector_stores/conversations/embeddings.pkl"
    )

    if not os.path.exists(vector_store_path):
        print(f"[ERROR] 向量库文件不存在: {vector_store_path}")
        print("请先运行: python scripts/generate_embeddings.py")
        sys.exit(1)

    # 初始化联想服务
    print(f"\n加载向量库: {vector_store_path}")
    service = RecallService(vector_store_path)

    # 设置全局服务实例
    recall.set_recall_service(service)
    persona.set_recall_service(service)  # Persona也需要RecallService

    # 初始化三元组搜索服务
    triplet_store_path = os.getenv(
        "TRIPLET_STORE_PATH",
        "vector_stores/triplets"
    )

    if os.path.exists(triplet_store_path):
        print(f"\n加载三元组向量库: {triplet_store_path}")
        try:
            triplet_service = TripletSearchService(triplet_store_path)
            comprehensive.set_services(service, triplet_service)
            print("✓ 三元组搜索服务已启动")
        except Exception as e:
            print(f"[WARNING] 三元组服务初始化失败: {e}")
            print("综合搜索功能将不可用")
    else:
        print(f"[WARNING] 三元组向量库不存在: {triplet_store_path}")
        print("综合搜索功能将不可用")

    # 预加载所有PersonaAgent实例
    print("\n" + "=" * 70)
    print("预加载 PersonaAgent 实例...")
    print("=" * 70)
    persona.preload_all_personas()

    print("\n" + "=" * 70)
    print("✓ WeMemory API 启动成功！")
    print("=" * 70)
    print(f"文档地址: http://localhost:{os.getenv('API_PORT', 8000)}/docs")
    print("=" * 70 + "\n")

    yield  # 应用运行期间

    # 关闭时清理
    print("\nWeMemory API 关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="WeMemory API",
    description="""
    # WeMemory - 智能记忆联想服务

    ## 核心概念

    这不是一个简单的"搜索" API，而是一个**记忆联想**服务。

    ### 什么是记忆联想？

    就像人类记忆一样：
    - **输入**：一个线索或当前上下文
    - **处理**：智能联想相关记忆
    - **输出**：相关的记忆片段 + 联想原因

    ### 与传统搜索的区别

    **传统搜索**：
    ```
    输入: "AI项目"
    输出: 包含"AI项目"的对话
    ```

    **记忆联想**：
    ```
    输入: "明天要和张三讨论新功能"
    联想到:
      → 上次讨论这个功能的对话（语义关联）
      → 参与讨论的人是谁（人物关联）
      → 相关的其他会议（主题关联）
      → 时间上临近的对话（时序关联）
    ```

    ## 主要功能

    1. **记忆联想** (`/api/recall`) - 核心功能
    2. **主题关联** (`/api/associate/topic`) - 按主题联想
    3. **人物关联** (`/api/associate/people`) - 按人物联想
    4. **时序联想** (`/api/associate/temporal`) - 按时间联想

    ## 技术特点

    - 🧠 **智能联想**：自动识别联想类型
    - ⚡ **高性能**：FAISS HNSW 索引，毫秒级响应
    - 🎯 **混合检索**：BM25 + 向量检索
    - 💾 **缓存优化**：相同请求自动缓存
    - 📊 **完整文档**：Swagger UI + ReDoc

    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(recall.router)
app.include_router(system.router)
app.include_router(persona.router)
app.include_router(comprehensive.router)


# 根路径
@app.get("/", tags=["root"])
async def root():
    """根路径 - API 基本信息"""
    return {
        "name": "WeMemory API",
        "version": "1.0.0",
        "description": "智能记忆联想服务",
        "docs": "/docs",
        "health": "/api/health",
        "stats": "/api/stats"
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "服务器内部错误",
            "detail": str(exc) if os.getenv("DEBUG") else None
        }
    )


if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload
    )
