#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量存储 - 双向量存储和检索
"""
import pickle
import numpy as np
from typing import List, Dict, Optional


class SimpleVectorStore:
    """
    双向量存储

    支持内容向量和上下文向量分离存储，
    检索时使用加权组合（content 85% + context 15%）
    """

    def __init__(self, dimension: int = 768):
        """
        Args:
            dimension: 向量维度（默认768，Google text-embedding-004）
        """
        self.dimension = dimension
        self.content_embeddings = []   # 对话内容向量
        self.context_embeddings = []   # 上下文向量
        self.metadata = []              # 元数据

    def add(self, content_embedding: List[float], context_embedding: List[float], metadata: dict):
        """
        添加双向量

        Args:
            content_embedding: 内容向量（768维）
            context_embedding: 上下文向量（768维）
            metadata: 元数据（session信息）
        """
        self.content_embeddings.append(np.array(content_embedding))
        self.context_embeddings.append(np.array(context_embedding))
        self.metadata.append(metadata)

    def search(
        self,
        query_content_embedding: List[float],
        query_context_embedding: List[float] = None,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        content_weight: float = 0.85,
        context_weight: float = 0.15
    ) -> List[Dict]:
        """
        双向量加权检索

        Args:
            query_content_embedding: 查询的内容向量
            query_context_embedding: 查询的上下文向量（可选）
            top_k: 返回前K个结果
            filters: 过滤条件（time_range, participants等）
            content_weight: 内容向量权重（默认0.85）
            context_weight: 上下文向量权重（默认0.15）

        Returns:
            检索结果列表，每个包含 score, content_score, metadata
        """
        if len(self.content_embeddings) == 0:
            return []

        # 1. 计算内容相似度
        query_content = np.array(query_content_embedding)
        content_matrix = np.vstack(self.content_embeddings)

        query_content_norm = query_content / (np.linalg.norm(query_content) + 1e-8)
        content_norm = content_matrix / (np.linalg.norm(content_matrix, axis=1, keepdims=True) + 1e-8)
        content_similarities = np.dot(content_norm, query_content_norm)

        # 2. 计算上下文相似度（如果提供）
        if query_context_embedding is not None:
            query_context = np.array(query_context_embedding)
            context_matrix = np.vstack(self.context_embeddings)

            query_context_norm = query_context / (np.linalg.norm(query_context) + 1e-8)
            context_norm = context_matrix / (np.linalg.norm(context_matrix, axis=1, keepdims=True) + 1e-8)
            context_similarities = np.dot(context_norm, query_context_norm)

            # 加权组合
            similarities = content_weight * content_similarities + context_weight * context_similarities
        else:
            # 只使用内容相似度
            similarities = content_similarities

        # 3. 应用过滤器
        valid_indices = list(range(len(self.metadata)))

        if filters:
            valid_indices = []
            for i, meta in enumerate(self.metadata):
                match = True

                # 时间范围过滤
                if 'time_range' in filters:
                    start, end = filters['time_range']
                    timestamp = meta.get('start_timestamp', 0)
                    if not (start <= timestamp <= end):
                        match = False

                # 参与者过滤
                if 'participants' in filters:
                    meta_participants = set(meta.get('participants', []))
                    filter_participants = set(filters['participants'])
                    if not filter_participants.intersection(meta_participants):
                        match = False

                if match:
                    valid_indices.append(i)

        if not valid_indices:
            return []

        # 4. 获取有效索引的相似度
        valid_similarities = similarities[valid_indices]
        valid_metadata = [self.metadata[i] for i in valid_indices]
        valid_content_sims = content_similarities[valid_indices]
        if query_context_embedding is not None:
            valid_context_sims = context_similarities[valid_indices]

        # 5. 排序
        sorted_indices = np.argsort(-valid_similarities)[:top_k]

        results = []
        for idx in sorted_indices:
            result = {
                'score': float(valid_similarities[idx]),
                'content_score': float(valid_content_sims[idx]),
                'metadata': valid_metadata[idx]
            }
            if query_context_embedding is not None:
                result['context_score'] = float(valid_context_sims[idx])
            results.append(result)

        return results

    def save(self, filepath: str):
        """
        保存双向量到文件

        Args:
            filepath: 保存路径（.pkl文件）
        """
        data = {
            'content_embeddings': [emb.tolist() for emb in self.content_embeddings],
            'context_embeddings': [emb.tolist() for emb in self.context_embeddings],
            'metadata': self.metadata
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"[INFO] 双向量库已保存到: {filepath}")
        print(f"      - 内容向量: {len(self.content_embeddings)} 个")
        print(f"      - 上下文向量: {len(self.context_embeddings)} 个")

    def load(self, filepath: str):
        """
        从文件加载双向量

        Args:
            filepath: 向量库文件路径（.pkl文件）
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        self.content_embeddings = [np.array(emb) for emb in data['content_embeddings']]
        self.context_embeddings = [np.array(emb) for emb in data['context_embeddings']]
        self.metadata = data['metadata']
        print(f"[INFO] 已加载双向量: {len(self.content_embeddings)} 个session")
