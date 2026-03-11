#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆联想服务

核心概念：不是简单的搜索，而是智能的记忆联想
就像人类记忆一样，一个线索可以触发多个相关记忆
"""
import time
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient


class RecallService:
    """
    记忆联想服务

    负责根据上下文智能联想相关记忆
    """

    def __init__(self, vector_store_path: str):
        """
        初始化联想服务

        Args:
            vector_store_path: 向量库文件路径
        """
        print(f"[RecallService] 初始化中...")
        start_time = time.time()

        # 加载向量库
        self.vector_store = HybridVectorStore(dimension=768, use_faiss=True)
        self.vector_store.load(vector_store_path)

        # 构建索引
        self.vector_store.build_bm25_index()
        self.vector_store.build_faiss_index()

        # 初始化 embedding 客户端
        self.embedding_client = GoogleEmbeddingClient()

        # 缓存（简单的内存缓存）
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1小时

        # 加载实体别名映射
        self._load_entity_alias_map()

        # 构建人名 -> 记忆索引的映射（用于快速查找特定人物的对话）
        print(f"[RecallService] 构建人名索引...")
        self._person_to_indices = self._build_person_index()
        print(f"[RecallService] 人名索引构建完成，共 {len(self._person_to_indices)} 个人物")

        load_time = time.time() - start_time
        print(f"[RecallService] 初始化完成，耗时: {load_time:.2f}秒")
        print(f"[RecallService] 向量库大小: {len(self.vector_store.metadata):,} 个记忆")

    def _load_entity_alias_map(self):
        """
        加载实体别名映射

        从 data/knowledge_graph/entity_alias_map.json 加载别名映射表
        """
        alias_map_path = Path(__file__).parent.parent.parent / "data" / "knowledge_graph" / "entity_alias_map.json"

        if not alias_map_path.exists():
            print(f"[RecallService] 警告：未找到实体别名映射文件: {alias_map_path}")
            self.entity_alias_map = {}
            self.alias_to_canonical = {}
            return

        try:
            with open(alias_map_path, 'r', encoding='utf-8') as f:
                self.entity_alias_map = json.load(f)

            # 构建反向映射：别名 -> 主实体名
            self.alias_to_canonical = {}
            for canonical_name, aliases in self.entity_alias_map.items():
                for alias in aliases:
                    # 不区分大小写
                    self.alias_to_canonical[alias.lower()] = canonical_name

            print(f"[RecallService] 加载实体别名映射: {len(self.entity_alias_map)} 个实体, {len(self.alias_to_canonical)} 个别名")
        except Exception as e:
            print(f"[RecallService] 警告：加载实体别名映射失败: {e}")
            self.entity_alias_map = {}
            self.alias_to_canonical = {}

    def _resolve_entity_alias(self, name: str) -> str:
        """
        解析实体别名到主实体名

        Args:
            name: 输入的人名（可能是别名）

        Returns:
            主实体名（如果找到），否则返回原名
        """
        if not name:
            return name

        # 不区分大小写查找
        name_lower = name.lower()
        canonical = self.alias_to_canonical.get(name_lower)

        if canonical:
            if canonical != name:
                print(f"[RecallService] 别名解析: '{name}' -> '{canonical}'")
            return canonical

        # 没找到别名映射，返回原名
        return name

    def _build_person_index(self) -> Dict[str, List[int]]:
        """
        构建人名 -> 记忆索引的映射

        由于所有对话都是单聊（用户 + 一个好友），可以用 conversation_name 建立索引
        这样查找特定人物的对话时，从 O(n) 降到 O(1)

        Returns:
            {person_name: [idx1, idx2, ...]}
        """
        person_to_indices = {}

        for idx, meta in enumerate(self.vector_store.metadata):
            conv_name = meta.get('conversation_name', '')
            if conv_name:
                # 解析别名到主实体名
                canonical_name = self._resolve_entity_alias(conv_name)

                if canonical_name not in person_to_indices:
                    person_to_indices[canonical_name] = []
                person_to_indices[canonical_name].append(idx)

        return person_to_indices

    def _get_timestamp(self, metadata: dict) -> int:
        """
        从metadata中获取timestamp（兼容新旧格式）

        新格式: start_time (ISO字符串)
        旧格式: start_timestamp (整数)
        """
        if 'start_timestamp' in metadata:
            return int(metadata['start_timestamp'])
        elif 'start_time' in metadata:
            from dateutil import parser
            dt = parser.parse(metadata['start_time'])
            return int(dt.timestamp())
        else:
            return 0

    def recall_for_person(
        self,
        person_name: str,
        context: str,
        top_k: int = 5,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        针对特定人物的记忆检索（用于 PersonaAgent）

        策略：先过滤出该人物的所有对话，再在其中进行语义搜索

        Args:
            person_name: 人物名称（可以是别名，会自动解析）
            context: 查询上下文
            top_k: 返回记忆数量
            min_relevance: 最小相关性阈值（默认0，PersonaAgent需要尽可能多的样本）

        Returns:
            记忆列表
        """
        import numpy as np

        # 0. 解析别名到主实体名
        canonical_name = self._resolve_entity_alias(person_name)

        # 1. 从索引中快速获取该人物的所有对话索引（O(1) 查找）
        person_indices = self._person_to_indices.get(canonical_name, [])

        if len(person_indices) == 0:
            print(f"[RecallService] 警告：未找到 {canonical_name} (原输入: {person_name}) 的任何对话记忆")
            return []

        print(f"[RecallService] 从索引中找到 {len(person_indices)} 条 {canonical_name} 的对话记忆")

        # 2. 生成查询向量
        query_embedding = self.embedding_client.get_embeddings([context])[0]

        # 3. 在该人物的对话中计算相似度
        similarities = []
        content_embeddings = self.vector_store.content_embeddings
        all_metadata = self.vector_store.metadata

        for idx in person_indices:
            # 计算余弦相似度
            content_emb = content_embeddings[idx]
            similarity = np.dot(query_embedding, content_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(content_emb)
            )

            # 应用相关性阈值
            if similarity >= min_relevance:
                similarities.append((idx, similarity, all_metadata[idx]))

        # 4. 按相似度排序，取 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:top_k]

        # 5. 格式化为标准记忆格式
        memories = []
        for idx, score, meta in top_results:
            memory = {
                'content': meta['content_text'],
                'relevance_score': float(score),
                'conversation_name': meta['conversation_name'],
                'participants': meta.get('participants', []),
                'timestamp': self._get_timestamp(meta)
            }
            memories.append(memory)

        return memories

    def recall(
        self,
        context: str,
        recall_type: str = "auto",
        top_k: int = 5,
        min_relevance: float = 0.3,
        time_range: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        核心功能：记忆联想

        根据当前上下文，联想到相关的历史记忆

        Args:
            context: 当前对话上下文或触发信息
            recall_type: 联想类型（auto/semantic/temporal/people）
            top_k: 返回记忆数量
            min_relevance: 最小相关性阈值
            time_range: 时间范围过滤

        Returns:
            联想结果字典
        """
        start_time = time.time()

        # 检查缓存
        cache_key = self._generate_cache_key(context, recall_type, top_k)
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result['timestamp'] < self._cache_ttl:
                print(f"[RecallService] 缓存命中: {cache_key[:16]}...")
                return cached_result['data']

        # 生成查询向量
        query_embedding = self.embedding_client.get_embeddings([context])[0]

        # 根据联想类型选择策略
        if recall_type == "auto":
            strategy = self._auto_recall_strategy(context)
        else:
            strategy = recall_type

        # 构建过滤器
        filters = self._build_filters(time_range)

        # 执行向量检索
        raw_results = self.vector_store.hybrid_search(
            query_content_embedding=query_embedding,
            query_text=context,
            top_k=top_k * 2,  # 获取更多结果用于后处理
            filters=filters
        )

        # 过滤低相关性结果
        filtered_results = [
            r for r in raw_results
            if r['score'] >= min_relevance
        ][:top_k]

        # 生成联想原因
        memories = []
        for result in filtered_results:
            reason = self._generate_recall_reason(
                result,
                context,
                strategy
            )

            memory = {
                'memory_id': self._generate_memory_id(result),
                'content': result['metadata']['content_text'],
                'relevance_score': float(result['score']),
                'recall_reason': reason,
                'timestamp': self._get_timestamp(result['metadata']),
                'conversation_name': result['metadata']['conversation_name'],
                'participants': result['metadata']['participants'],
            }
            memories.append(memory)

        # 提取关联信息
        associations = self._extract_associations(memories, context)

        # 构建结果
        result = {
            'memories': memories,
            'total_count': len(memories),
            'associations': associations,
            'recall_strategy': strategy,
            'processing_time_ms': (time.time() - start_time) * 1000
        }

        # 缓存结果
        self._cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }

        return result

    def recall_by_topic(
        self,
        topic: str,
        top_k: int = 10,
        min_relevance: float = 0.3
    ) -> Dict[str, Any]:
        """
        主题关联

        找到与特定主题相关的所有记忆

        Args:
            topic: 主题关键词或描述
            top_k: 返回记忆数量
            min_relevance: 最小相关性阈值

        Returns:
            主题关联结果
        """
        # 使用 recall 的语义模式
        result = self.recall(
            context=f"关于{topic}的讨论",
            recall_type="semantic",
            top_k=top_k,
            min_relevance=min_relevance
        )

        return {
            'topic': topic,
            'memories': result['memories'],
            'total_count': result['total_count']
        }

    def recall_by_people(
        self,
        person: str,
        top_k: int = 10,
        include_mentions: bool = True
    ) -> Dict[str, Any]:
        """
        人物关联

        找到与特定人物相关的记忆

        Args:
            person: 人物姓名
            top_k: 返回记忆数量
            include_mentions: 是否包含提及该人物的对话

        Returns:
            人物关联结果
        """
        # 使用 recall 的人物模式
        result = self.recall(
            context=f"与{person}的对话或提到{person}的讨论",
            recall_type="people",
            top_k=top_k
        )

        # 如果不包含提及，只保留直接对话
        if not include_mentions:
            result['memories'] = [
                m for m in result['memories']
                if person in m.get('participants', [])
            ]
            result['total_count'] = len(result['memories'])

        return {
            'person': person,
            'memories': result['memories'],
            'total_count': result['total_count']
        }

    def recall_by_time(
        self,
        reference_time: int,
        direction: str = "around",
        time_window: int = 7,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        时序联想

        找到时间上相关的记忆

        Args:
            reference_time: 参考时间戳
            direction: 时间方向（before/after/around）
            time_window: 时间窗口（天）
            top_k: 返回记忆数量

        Returns:
            时序联想结果
        """
        # 计算时间范围
        ref_dt = datetime.fromtimestamp(reference_time)

        if direction == "before":
            end_time = reference_time
            start_time = (ref_dt - timedelta(days=time_window)).timestamp()
        elif direction == "after":
            start_time = reference_time
            end_time = (ref_dt + timedelta(days=time_window)).timestamp()
        else:  # around
            start_time = (ref_dt - timedelta(days=time_window)).timestamp()
            end_time = (ref_dt + timedelta(days=time_window)).timestamp()

        time_range = {
            'start': int(start_time),
            'end': int(end_time)
        }

        # 使用 recall 的时序模式
        result = self.recall(
            context=f"在 {ref_dt.strftime('%Y-%m-%d')} 前后的对话",
            recall_type="temporal",
            top_k=top_k,
            time_range=time_range
        )

        return {
            'reference_time': reference_time,
            'direction': direction,
            'memories': result['memories'],
            'total_count': result['total_count']
        }

    def simple_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        简单搜索（兼容性功能）

        注：推荐使用 recall() 以获得更好的联想效果

        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            搜索结果
        """
        query_embedding = self.embedding_client.get_embeddings([query])[0]

        results = self.vector_store.hybrid_search(
            query_content_embedding=query_embedding,
            query_text=query,
            top_k=top_k,
            filters=filters
        )

        memories = []
        for result in results:
            memory = {
                'memory_id': self._generate_memory_id(result),
                'content': result['metadata']['content_text'],
                'relevance_score': float(result['score']),
                'recall_reason': "关键词匹配",
                'timestamp': self._get_timestamp(result['metadata']),
                'conversation_name': result['metadata']['conversation_name'],
                'participants': result['metadata']['participants'],
            }
            memories.append(memory)

        return {
            'query': query,
            'results': memories,
            'total_count': len(memories)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计信息"""
        metadata_list = self.vector_store.metadata

        # 时间范围
        timestamps = [self._get_timestamp(m) for m in metadata_list]
        date_range = {
            'earliest': int(min(timestamps)) if timestamps else 0,
            'latest': int(max(timestamps)) if timestamps else 0
        }

        # 对话数量（去重）
        conversations = set(m['conversation_name'] for m in metadata_list)

        return {
            'total_memories': len(metadata_list),
            'total_conversations': len(conversations),
            'date_range': date_range,
            'vector_dimension': self.vector_store.dimension,
            'index_type': 'FAISS HNSW' if self.vector_store.faiss_built else 'Linear'
        }

    # ========== 私有辅助方法 ==========

    def _auto_recall_strategy(self, context: str) -> str:
        """
        自动选择联想策略

        根据上下文内容，智能选择最合适的联想策略
        """
        context_lower = context.lower()

        # 简单的规则匹配（未来可以用 LLM 优化）
        if any(word in context_lower for word in ["谁", "who", "人"]):
            return "people"
        elif any(word in context_lower for word in ["什么时候", "when", "之前", "之后"]):
            return "temporal"
        else:
            return "semantic"

    def _build_filters(self, time_range: Optional[Dict]) -> Optional[Dict]:
        """构建过滤器"""
        if not time_range:
            return None

        return {
            'time_range': (
                time_range.get('start', 0),
                time_range.get('end', int(time.time()))
            )
        }

    def _generate_recall_reason(
        self,
        result: Dict,
        context: str,
        strategy: str
    ) -> str:
        """
        生成联想原因说明

        解释为什么这个记忆被联想到
        """
        score = result['score']
        bm25_score = result.get('bm25_score', 0)
        vector_score = result.get('vector_score', 0)

        reasons = []

        # 基于分数组成判断
        if bm25_score > 0.5:
            reasons.append("关键词匹配")
        if vector_score > 0.7:
            reasons.append("语义相似")

        # 基于策略
        if strategy == "people":
            reasons.append("相关人物")
        elif strategy == "temporal":
            reasons.append("时间相近")
        elif strategy == "semantic":
            if not reasons:
                reasons.append("主题相关")

        reason_text = " + ".join(reasons) if reasons else "综合匹配"
        return f"{reason_text} (相关度: {score:.2f})"

    def _extract_associations(
        self,
        memories: List[Dict],
        context: str
    ) -> Dict[str, Any]:
        """
        提取关联信息

        从联想到的记忆中提取共同的人物、主题等
        """
        # 提取所有参与者
        all_participants = set()
        for memory in memories:
            all_participants.update(memory.get('participants', []))

        # 简单的主题提取（未来可以用 LLM 优化）
        # 目前只返回对话名称作为主题
        topics = list(set(
            m['conversation_name']
            for m in memories
        ))[:5]  # 最多5个

        return {
            'people': list(all_participants),
            'topics': topics,
            'time_context': self._generate_time_context(memories)
        }

    def _generate_time_context(self, memories: List[Dict]) -> Optional[str]:
        """生成时间上下文说明"""
        if not memories:
            return None

        timestamps = [m['timestamp'] for m in memories]
        earliest = min(timestamps)
        latest = max(timestamps)

        earliest_date = datetime.fromtimestamp(earliest).strftime('%Y-%m-%d')
        latest_date = datetime.fromtimestamp(latest).strftime('%Y-%m-%d')

        if earliest_date == latest_date:
            return f"都在 {earliest_date}"
        else:
            return f"时间跨度：{earliest_date} 至 {latest_date}"

    def _generate_memory_id(self, result: Dict) -> str:
        """生成记忆唯一ID"""
        metadata = result['metadata']
        unique_str = f"{metadata['conversation_name']}_{self._get_timestamp(metadata)}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]

    def _generate_cache_key(
        self,
        context: str,
        recall_type: str,
        top_k: int
    ) -> str:
        """生成缓存键"""
        key_str = f"{context}_{recall_type}_{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()
