#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PersonaAgent - AI数字人核心模块

通过检索真实对话 + Few-shot Learning 实现人格克隆
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from vertexai.generative_models import GenerativeModel


class PersonaAgent:
    """
    AI数字人代理
    
    核心思路：
    1. 检索该人物在类似场景下的真实对话
    2. 将真实对话作为Few-shot examples
    3. 让LLM从例子中学习风格和知识
    4. 以该人物的风格回复
    """
    
    def __init__(self, person_name: str, recall_service):
        """
        初始化AI数字人
        
        Args:
            person_name: 人物名称（如"老婆"、"Alex"）
            recall_service: RecallService实例，用于检索记忆
        """
        self.person_name = person_name
        self.recall_service = recall_service
        
        # 加载配置
        config_path = Path(__file__).parent.parent / "config" / "default.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Gemini配置
        self.model_name = config['vertex_ai']['extraction']['model']
        self.max_tokens = config['vertex_ai']['extraction']['max_tokens']
        self.temperature = 0.7  # Persona对话需要更高的温度，让回复更自然
        
        # 初始化Gemini模型
        self.model = GenerativeModel(self.model_name)
        
        print(f"[PersonaAgent] 已初始化 {person_name} 的AI数字人")
        print(f"[PersonaAgent] 模型: {self.model_name}, Temperature: {self.temperature}")
    
    def chat(
        self,
        user_message: str,
        session_history: Optional[List[Dict]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        与AI数字人对话
        
        Args:
            user_message: 用户输入的消息
            session_history: 本次会话的历史记录 [{"role": "user/assistant", "content": "..."}]
            top_k: 检索多少条相关记忆作为Few-shot examples
        
        Returns:
            {
                "response": "AI数字人的回复",
                "memories_used": [...],  # 用于学习的记忆
                "person_name": "...",
                "processing_time_ms": ...
            }
        """
        import time
        start_time = time.time()
        
        # 1. 检索该人物在类似场景下的真实对话
        print(f"\n[PersonaAgent] 检索 {self.person_name} 在类似场景下的对话...")
        memories = self._retrieve_similar_conversations(user_message, top_k)
        
        print(f"[PersonaAgent] 检索到 {len(memories)} 条相关记忆")
        
        # 2. 构建Few-shot Prompt
        prompt = self._build_few_shot_prompt(
            user_message=user_message,
            memories=memories,
            session_history=session_history
        )
        
        # 3. 调用Gemini生成回复
        print(f"[PersonaAgent] 调用 {self.model_name} 生成回复...")
        raw_response = self._generate_response(prompt)

        # 4. 解析多条消息（用<MSG>分隔）
        messages = self._parse_messages(raw_response)

        processing_time = (time.time() - start_time) * 1000

        print(f"[PersonaAgent] 生成完成，耗时 {processing_time:.0f}ms")
        print(f"[PersonaAgent] 回复了 {len(messages)} 条消息")

        return {
            "response": raw_response,  # 原始完整回复
            "messages": messages,  # 拆分后的消息列表（供前端使用）
            "memories_used": [
                {
                    "conversation": m['conversation_name'],
                    "relevance": m['relevance_score'],
                    "content_preview": m['content'][:100] + "..."
                }
                for m in memories
            ],
            "person_name": self.person_name,
            "processing_time_ms": processing_time
        }
    
    def _retrieve_similar_conversations(
        self,
        query: str,
        top_k: int
    ) -> List[Dict]:
        """
        检索该人物在类似场景下的真实对话

        使用 RecallService.recall_for_person() 进行检索

        Args:
            query: 查询内容
            top_k: 返回多少条记忆

        Returns:
            记忆列表
        """
        # 使用专门的 recall_for_person 方法（先过滤人物，再语义搜索）
        memories = self.recall_service.recall_for_person(
            person_name=self.person_name,
            context=query,
            top_k=top_k,
            min_relevance=0.0  # PersonaAgent 不需要过滤低相关性，需要尽可能多的样本
        )

        print(f"[PersonaAgent] 检索到 {len(memories)} 条 {self.person_name} 的对话记忆")

        # 打印相关度
        for mem in memories:
            print(f"[PersonaAgent] ✓ {mem['conversation_name']}, 相关度: {mem['relevance_score']:.3f}")

        return memories
    
    def _build_few_shot_prompt(
        self,
        user_message: str,
        memories: List[Dict],
        session_history: Optional[List[Dict]] = None
    ) -> str:
        """
        构建Few-shot Learning Prompt

        核心思路：展示真实对话，让LLM学习风格和知识
        """
        # 格式化记忆为Few-shot examples
        examples = self._format_memories_as_examples(memories)

        # 格式化会话历史
        history_text = ""
        if session_history:
            history_text = "\n=== 当前会话历史 ===\n"
            for turn in session_history[-3:]:  # 只保留最近3轮
                role = "用户" if turn['role'] == 'user' else self.person_name
                history_text += f"{role}: {turn['content']}\n"
            history_text += "\n"

        # 构建完整prompt
        prompt = f"""你正在扮演 {self.person_name}。

以下是 {self.person_name} 在类似场景下的真实对话记录。
请仔细学习其中的对话风格、语气、表达方式、常用词汇、emoji使用习惯，以及涉及的知识和记忆。

注意观察真实对话中的特点：
1. 每行代表一条独立的微信消息
2. 真实聊天中，用户很少在一条消息中换行
3. 如果想表达多个想法，通常会发送多条短消息，而不是一条长消息
4. 学习她如何用词、如何表达情绪、常用什么语气词、标点符号、emoji

=== 相关记忆（供学习参考）===
{examples}

{history_text}现在，基于上述记忆中学到的风格和知识，以 {self.person_name} 的身份自然地回复。

重要规则：
- 模拟真实微信聊天习惯
- 如果需要发送多条消息，请用 <MSG> 标记分隔每条消息
- 每条消息保持简短，避免在单条消息内换行
- 不要说"根据记忆"或"我记得"，直接以她的口吻回答

示例回复格式：
- 单条消息："在呀，怎么了？"
- 多条消息："在呀<MSG>怎么了？<MSG>有什么事吗？"

用户: {user_message}
{self.person_name}:"""

        return prompt
    
    def _format_memories_as_examples(self, memories: List[Dict]) -> str:
        """
        将检索到的记忆格式化为清晰的Few-shot examples
        """
        if not memories:
            return "（暂无相关记忆）"
        
        examples = []
        for i, mem in enumerate(memories, 1):
            # 提取该人物的发言（标记为重点学习对象）
            content = mem['content']
            relevance = mem['relevance_score']
            
            examples.append(f"""
【示例 {i}】（相关度: {relevance:.2f}）
对话内容：
{content}
---
""")
        
        return "\n".join(examples)
    
    def _parse_messages(self, raw_response: str) -> List[str]:
        """
        解析多条消息（用<MSG>分隔）

        Args:
            raw_response: AI生成的原始回复

        Returns:
            消息列表
        """
        # 如果包含<MSG>分隔符，拆分为多条消息
        if '<MSG>' in raw_response:
            messages = [
                msg.strip()
                for msg in raw_response.split('<MSG>')
                if msg.strip()
            ]
        else:
            # 没有分隔符，作为单条消息
            messages = [raw_response.strip()]

        return messages

    def _generate_response(self, prompt: str) -> str:
        """
        使用Gemini生成回复
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 500,  # Persona对话不需要太长
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )

            return response.text.strip()

        except Exception as e:
            print(f"[PersonaAgent] 生成回复失败: {e}")
            return f"抱歉，我现在有点不在状态😅 ({str(e)})"
