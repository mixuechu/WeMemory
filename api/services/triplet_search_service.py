#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三元组搜索服务

负责在知识图谱三元组中搜索相关信息
使用混合检索：BM25（精确关键词） + 向量搜索（语义）
支持实体别名解析
"""
import time
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
import jieba

from embedding import GoogleEmbeddingClient


class TripletSearchService:
    """
    三元组搜索服务

    在自然语言三元组向量库中搜索相关知识
    采用混合检索策略：BM25 + 向量搜索
    """

    def __init__(self, vector_store_path: str):
        """
        初始化三元组搜索服务

        Args:
            vector_store_path: 三元组向量库目录路径（包含 embeddings.pkl 和 index.faiss）
        """
        print(f"[TripletSearch] 初始化中...")
        start_time = time.time()

        vector_store_path = Path(vector_store_path)

        # 加载metadata
        embeddings_path = vector_store_path / "embeddings.pkl"
        if not embeddings_path.exists():
            raise FileNotFoundError(f"三元组向量库不存在: {embeddings_path}")

        with open(embeddings_path, 'rb') as f:
            data = pickle.load(f)

        self.records = data['metadata']

        # 加载FAISS索引
        index_path = vector_store_path / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS索引不存在: {index_path}")

        self.index = faiss.read_index(str(index_path))

        # 初始化embedding客户端
        self.embedding_client = GoogleEmbeddingClient()

        # 构建BM25索引
        print(f"[TripletSearch] 构建BM25索引...")
        self._build_bm25_index()

        # 加载实体别名映射
        print(f"[TripletSearch] 加载实体别名映射...")
        self._load_entity_alias_map()

        load_time = time.time() - start_time
        print(f"[TripletSearch] 初始化完成，耗时: {load_time:.2f}秒")
        print(f"[TripletSearch] 三元组数量: {len(self.records):,}")

    def _build_bm25_index(self):
        """构建BM25索引用于关键词匹配"""
        # 对每个三元组文本进行分词
        tokenized_corpus = []
        for record in self.records:
            text = record['text']
            # 使用jieba分词
            tokens = list(jieba.cut(text))
            tokenized_corpus.append(tokens)

        # 创建BM25索引
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.tokenized_corpus = tokenized_corpus
        print(f"[TripletSearch] BM25索引构建完成")

    def _load_entity_alias_map(self):
        """加载实体别名映射"""
        alias_map_path = Path(__file__).parent.parent.parent / "data" / "knowledge_graph" / "entity_alias_map.json"

        if not alias_map_path.exists():
            print(f"[TripletSearch] 警告：未找到实体别名映射文件: {alias_map_path}")
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

            print(f"[TripletSearch] 加载实体别名映射: {len(self.entity_alias_map)} 个实体, {len(self.alias_to_canonical)} 个别名")
        except Exception as e:
            print(f"[TripletSearch] 警告：加载实体别名映射失败: {e}")
            self.entity_alias_map = {}
            self.alias_to_canonical = {}

    def search(self, query: str, top_k: int = 5, min_score: float = 0.3,
               bm25_weight: float = 0.4, vector_weight: float = 0.6) -> Dict[str, Any]:
        """
        混合搜索：BM25 + 向量检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_score: 最小相似度阈值（0-1）
            bm25_weight: BM25权重（默认0.4）
            vector_weight: 向量搜索权重（默认0.6）

        Returns:
            搜索结果字典
        """
        start_time = time.time()

        # 查询预处理：替换代词
        processed_query = self._preprocess_query(query)

        # 别名扩展：生成包含所有别名的查询变体
        expanded_queries = self._expand_aliases(processed_query)

        # 对所有查询变体进行搜索，合并结果
        all_hybrid_scores = {}

        for query_variant in expanded_queries:
            # 1. 向量检索
            query_embeddings = self.embedding_client.get_embeddings([query_variant])
            query_vector = np.array(query_embeddings).astype('float32')

            # 检索更多候选（用于混合排序）
            search_k = min(top_k * 10, len(self.records))
            distances, indices = self.index.search(query_vector, search_k)

            # 2. BM25检索
            query_tokens = list(jieba.cut(query_variant))
            bm25_scores = self.bm25.get_scores(query_tokens)

            # 3. 混合打分
            # 归一化向量距离为分数 (0-1)
            vector_scores = {}
            for dist, idx in zip(distances[0], indices[0]):
                vector_scores[idx] = 1.0 / (1.0 + float(dist))

            # 归一化BM25分数 (0-1)
            max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
            bm25_normalized = {i: score / max_bm25 for i, score in enumerate(bm25_scores)}

            # 计算混合分数
            for idx in range(len(self.records)):
                vec_score = vector_scores.get(idx, 0.0)
                bm25_score = bm25_normalized.get(idx, 0.0)

                # 加权融合
                hybrid_score = (vector_weight * vec_score) + (bm25_weight * bm25_score)

                # 合并分数：取最高分（多个查询可能匹配同一三元组）
                if idx not in all_hybrid_scores or hybrid_score > all_hybrid_scores[idx]:
                    all_hybrid_scores[idx] = hybrid_score

        # 按混合分数排序
        sorted_indices = sorted(all_hybrid_scores.keys(), key=lambda x: all_hybrid_scores[x], reverse=True)

        # 4. 构建结果
        results = []
        for idx in sorted_indices[:top_k]:
            score = all_hybrid_scores[idx]

            if score < min_score:
                continue

            record = self.records[idx]
            results.append({
                'text': record['text'],
                'type': record['type'],
                'score': score,
                'metadata': record.get('metadata', {})
            })

        processing_time = (time.time() - start_time) * 1000

        return {
            'triplets': results,
            'total_count': len(results),
            'processing_time_ms': processing_time
        }

    def _preprocess_query(self, query: str) -> str:
        """
        预处理查询：只替换代词（我 -> 用户名）

        不再做别名解析，因为：
        - 当用户问"我老婆是谁"时，不应该把"老婆"替换成具体名字
        - 别名解析应该在数据端完成（三元组去重时已处理）

        Args:
            query: 原始查询

        Returns:
            处理后的查询
        """
        processed = query

        # 只替换代词
        # TODO: 从配置或环境变量读取用户名
        pronoun_replacements = {
            '我的': '用户的',
            '我': '用户',
        }
        for old, new in pronoun_replacements.items():
            processed = processed.replace(old, new)

        if processed != query:
            print(f"[TripletSearch] 查询预处理: '{query}' -> '{processed}'")

        return processed

    def _expand_aliases(self, query: str) -> List[str]:
        """
        别名扩展：为查询中的实体生成所有别名变体

        例如："用户和朋友A讨论工作" →
             ["用户和朋友A讨论工作", "用户和朋友A别名1讨论工作", "用户和朋友A别名2讨论工作"]

        Args:
            query: 预处理后的查询

        Returns:
            扩展后的查询列表（包含原查询）
        """
        expanded = [query]  # 始终包含原查询

        # 遍历所有实体的别名
        for canonical_name, aliases in self.entity_alias_map.items():
            # 检查查询中是否包含该实体的任何别名
            for alias in aliases:
                if alias.lower() in query.lower():
                    # 生成其他别名的查询变体
                    for other_alias in aliases:
                        if other_alias != alias:
                            # 替换别名（保持大小写）
                            variant = query.replace(alias, other_alias)
                            if variant not in expanded:
                                expanded.append(variant)
                    break  # 找到一个匹配就跳出

        if len(expanded) > 1:
            print(f"[TripletSearch] 别名扩展: 从1个查询 -> {len(expanded)}个变体")
            print(f"  原查询: {query}")
            for variant in expanded[1:4]:  # 只显示前3个
                print(f"  变体: {variant}")
            if len(expanded) > 4:
                print(f"  ... 还有{len(expanded)-4}个变体")

        return expanded
