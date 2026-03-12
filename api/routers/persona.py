#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persona API 路由 - AI数字人对话
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated, Optional, List
from pydantic import BaseModel, Field

from persona import PersonaAgent
from api.services.recall_service import RecallService
from api.auth import verify_api_key


router = APIRouter(prefix="/api/persona", tags=["persona"])

# 全局服务实例
_recall_service: RecallService = None
_persona_agents: dict = {}  # 缓存PersonaAgent实例


def set_recall_service(service: RecallService):
    """设置RecallService实例"""
    global _recall_service
    _recall_service = service


def get_recall_service() -> RecallService:
    """获取RecallService实例"""
    if _recall_service is None:
        raise HTTPException(
            status_code=503,
            detail="服务未就绪，向量库加载中..."
        )
    return _recall_service


def preload_all_personas():
    """
    预加载所有可用的PersonaAgent实例

    在API启动时调用，一次性创建所有人物的Agent
    """
    if _recall_service is None:
        print("[Persona] RecallService未初始化，跳过预加载")
        return

    # 获取所有对话名称
    metadata_list = _recall_service.vector_store.metadata

    # 收集所有conversation_name
    conversation_names = set()
    for meta in metadata_list:
        conv_name = meta.get('conversation_name', '')
        if conv_name:
            conversation_names.add(conv_name)

    print(f"[Persona] 发现 {len(conversation_names)} 个对话，开始预加载PersonaAgent...")

    # 为每个对话创建PersonaAgent实例
    count = 0
    for person_name in sorted(conversation_names):
        try:
            _persona_agents[person_name] = PersonaAgent(
                person_name=person_name,
                recall_service=_recall_service
            )
            count += 1
            if count <= 5 or count % 20 == 0:  # 只打印前5个和每20个
                print(f"[Persona] [{count}/{len(conversation_names)}] 已加载: {person_name}")
        except Exception as e:
            print(f"[Persona] 加载 {person_name} 失败: {e}")

    print(f"[Persona] ✓ 预加载完成！共加载 {len(_persona_agents)} 个PersonaAgent实例")


def get_persona_agent(person_name: str) -> PersonaAgent:
    """获取PersonaAgent实例（从预加载的实例中）"""
    if person_name not in _persona_agents:
        # 如果预加载中没有，动态创建一个
        print(f"[API] PersonaAgent '{person_name}' 不在预加载列表中，动态创建...")
        _persona_agents[person_name] = PersonaAgent(
            person_name=person_name,
            recall_service=_recall_service
        )
    return _persona_agents[person_name]


# ========== Request/Response Models ==========

class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class PersonaChatRequest(BaseModel):
    """AI数字人对话请求"""
    person_name: str = Field(..., description="人物名称（如'老婆'、'Alex'）")
    user_message: str = Field(..., description="用户输入的消息")
    session_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="会话历史（可选）"
    )
    top_k: int = Field(
        default=5,
        description="检索多少条相关记忆作为学习样本"
    )


class PersonaChatResponse(BaseModel):
    """AI数字人对话响应"""
    request_id: str
    person_name: str
    response: str  # 原始完整回复
    messages: List[str] = Field(
        description="拆分后的消息列表（用<MSG>分隔），前端可以像真实微信一样逐条显示"
    )
    memories_used: List[dict]
    processing_time_ms: float


# ========== API Endpoints ==========

@router.post(
    "/chat",
    response_model=PersonaChatResponse,
    summary="与AI数字人对话",
    description="""
    基于真实聊天记录，创建该人物的AI数字人。
    
    核心功能：
    1. 检索该人物在类似场景下的真实对话
    2. 将真实对话作为Few-shot examples
    3. 让LLM学习风格和知识，以该人物的口吻回复
    
    示例：
    ```json
    {
        "person_name": "老婆",
        "user_message": "最近工作怎么样？",
        "top_k": 5
    }
    ```
    
    返回该人物风格的回复，就像真的在和她聊天一样。
    """
)
async def chat_with_persona(
    request: PersonaChatRequest,
    service: Annotated[RecallService, Depends(get_recall_service)],
    verified: bool = Depends(verify_api_key)
):
    """与AI数字人对话"""
    try:
        # 获取或创建PersonaAgent
        agent = get_persona_agent(request.person_name)
        
        # 转换session_history格式
        session_history = None
        if request.session_history:
            session_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.session_history
            ]
        
        # 生成回复
        result = agent.chat(
            user_message=request.user_message,
            session_history=session_history,
            top_k=request.top_k
        )
        
        return PersonaChatResponse(
            request_id=str(uuid.uuid4()),
            person_name=result['person_name'],
            response=result['response'],
            messages=result['messages'],
            memories_used=result['memories_used'],
            processing_time_ms=result['processing_time_ms']
        )
    
    except Exception as e:
        print(f"[API] Persona chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"AI数字人对话失败: {str(e)}"
        )


@router.get(
    "/available",
    summary="获取可用的AI数字人列表",
    description="返回向量库中所有对话的列表，包括对话名称和实际参与者"
)
async def get_available_personas(
    service: Annotated[RecallService, Depends(get_recall_service)],
    verified: bool = Depends(verify_api_key)
):
    """获取可用的AI数字人列表"""
    try:
        # 从向量库metadata中提取对话信息
        metadata_list = service.vector_store.metadata

        # 获取entity_alias_map（用于查找正式名字）
        alias_to_canonical = getattr(service, 'alias_to_canonical', {})

        # 统计每个conversation的信息
        conv_info = {}

        for meta in metadata_list:
            conv_name = meta.get('conversation_name', '')
            participants = meta.get('participants', [])

            if conv_name not in conv_info:
                conv_info[conv_name] = {
                    'conversation_name': conv_name,
                    'memory_count': 0,
                    'participants': set()
                }

            conv_info[conv_name]['memory_count'] += 1
            conv_info[conv_name]['participants'].update(participants)

        # 转换为列表格式
        personas = []
        for conv_name, info in conv_info.items():
            # 查找正式名字（canonical name）
            canonical_name = alias_to_canonical.get(conv_name.lower(), conv_name)

            personas.append({
                'conversation_name': conv_name,
                'canonical_name': canonical_name,  # 正式名字
                'display_name': canonical_name if canonical_name != conv_name else conv_name,
                'memory_count': info['memory_count'],
                'participants': sorted(list(info['participants']))
            })

        # 按记忆数量排序
        personas.sort(key=lambda x: x['memory_count'], reverse=True)

        return {
            "total_conversations": len(personas),
            "available_personas": personas,
            "usage_note": "可以使用 conversation_name 或 canonical_name 来创建AI数字人"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取人物列表失败: {str(e)}"
        )

@router.get(
    "/{person_name}/profile",
    summary="获取人物核心人设",
    description="返回人物的核心三元组（关系、重要事件），用于构建数字人人设"
)
async def get_persona_profile(
    person_name: str,
    service: Annotated[RecallService, Depends(get_recall_service)],
    verified: bool = Depends(verify_api_key)
):
    """获取人物核心人设（5-10条核心三元组）"""
    try:
        from api.services.triplet_search_service import TripletSearchService
        from pathlib import Path

        # 初始化三元组搜索服务
        triplet_store_path = Path("vector_stores/triplets")
        if not triplet_store_path.exists():
            raise HTTPException(status_code=503, detail="三元组服务不可用")

        triplet_service = TripletSearchService(str(triplet_store_path))

        # 搜索该人物与用户的关系三元组
        result = triplet_service.search(
            query=f"{person_name}和米雪川",  # 查询人物与用户的关系
            top_k=30,  # 搜索更多候选
            min_score=0.4  # 适中阈值
        )

        # 过滤和排序：优先显示重要关系类型
        important_relationships = []  # 配偶、家人等重要关系
        other_relationships = []      # 其他关系
        important_events = []         # 重要事件

        # 关键词过滤：排除不重要的关系
        unimportant_keywords = ['位于', '在酒店', '在北京', '在成都', '在广州', '在西安']

        for triplet in result['triplets']:
            text = triplet['text']

            # 跳过不重要的"位于"关系
            if any(keyword in text for keyword in unimportant_keywords):
                continue

            if triplet['type'] == 'relationship':
                # 优先级：配偶 > 家人 > 工作 > 其他
                if any(word in text for word in ['配偶', '老婆', '老公', '妻子', '丈夫', '结婚']):
                    important_relationships.insert(0, triplet)  # 插在最前面
                elif any(word in text for word in ['父', '母', '妈', '爸', '子', '女', '姐', '弟', '哥', '妹']):
                    important_relationships.append(triplet)
                elif any(word in text for word in ['工作', '公司', '职位']):
                    important_relationships.append(triplet)
                else:
                    other_relationships.append(triplet)
            elif triplet['type'] == 'event':
                # 优先选择包含重要信息的事件
                if any(word in text for word in ['结婚', '工作', '生日', '纪念']):
                    important_events.insert(0, triplet)
                else:
                    important_events.append(triplet)

        # 核心人设：最多5条关系 + 3条事件
        core_triplets = (important_relationships + other_relationships)[:5] + important_events[:3]

        return {
            "person_name": person_name,
            "core_knowledge": [
                {
                    "text": t['text'],
                    "type": t['type'],
                    "importance": "core"
                } for t in core_triplets
            ],
            "total_count": len(core_triplets),
            "usage_note": "这些是核心人设信息，应预置到System Prompt中"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取人物人设失败: {str(e)}"
        )
