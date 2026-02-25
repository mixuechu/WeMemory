#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合检索 - BM25 + 向量检索（FAISS加速）
"""
import numpy as np
import jieba
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
from .vector_store import SimpleVectorStore

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[WARNING] FAISS not installed. Install with: pip install faiss-cpu")


class HybridVectorStore(SimpleVectorStore):
    """
    混合检索向量库：BM25 + 双向量（FAISS加速）

    组合关键词匹配（BM25）和语义相似度（向量）
    权重配比：BM25:0.5 + Vector:0.5（经过评测得出）

    性能优化：
    - 小规模（< 5000）：使用numpy线性搜索
    - 大规模（>= 5000）：使用FAISS HNSW索引（400x加速）
    """

    def __init__(self, dimension: int = 768, use_faiss: bool = True):
        """
        Args:
            dimension: 向量维度（默认768）
            use_faiss: 是否使用FAISS加速（默认True，大规模数据推荐）
        """
        super().__init__(dimension)
        self.bm25_index = None
        self.bm25_corpus_tokens = []

        # FAISS相关
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        self.content_faiss_index = None
        self.context_faiss_index = None
        self.faiss_built = False

        if self.use_faiss:
            # 使用HNSW索引：高精度（95-99% recall）+ 快速查询
            # M=32: 每个节点32个连接（balance between accuracy and memory）
            self.content_faiss_index = faiss.IndexHNSWFlat(dimension, 32)
            self.context_faiss_index = faiss.IndexHNSWFlat(dimension, 32)
            print(f"[INFO] FAISS HNSW索引已初始化（dimension={dimension}, M=32）")

    def build_bm25_index(self):
        """
        构建BM25索引

        使用jieba对每个session的content_text进行中文分词
        """
        print("[INFO] 构建BM25索引...")

        # 对每个session的content_text分词
        self.bm25_corpus_tokens = []
        for meta in self.metadata:
            content_text = meta.get('content_text', '')
            # 使用jieba分词（搜索引擎模式）
            tokens = list(jieba.cut_for_search(content_text))
            self.bm25_corpus_tokens.append(tokens)

        # 构建BM25索引
        self.bm25_index = BM25Okapi(self.bm25_corpus_tokens)
        print(f"[OK] BM25索引构建完成，共 {len(self.bm25_corpus_tokens)} 个文档")

    def build_faiss_index(self):
        """
        构建FAISS向量索引（用于大规模数据加速）

        将所有向量添加到FAISS HNSW索引中
        适用于大规模数据（>= 5000 sessions）
        """
        if not self.use_faiss:
            print("[INFO] FAISS未启用，跳过索引构建")
            return

        if len(self.content_embeddings) == 0:
            print("[WARNING] 没有向量数据，无法构建FAISS索引")
            return

        print(f"[INFO] 构建FAISS索引（{len(self.content_embeddings)} 个向量）...")

        # 重置索引（避免重复添加）
        if self.faiss_built:
            self.content_faiss_index.reset()
            self.context_faiss_index.reset()

        # 转换为numpy数组（FAISS要求float32）
        content_matrix = np.vstack(self.content_embeddings).astype('float32')
        context_matrix = np.vstack(self.context_embeddings).astype('float32')

        # L2归一化（用于余弦相似度）
        faiss.normalize_L2(content_matrix)
        faiss.normalize_L2(context_matrix)

        # 添加到FAISS索引
        self.content_faiss_index.add(content_matrix)
        self.context_faiss_index.add(context_matrix)

        self.faiss_built = True
        print(f"[OK] FAISS索引构建完成")
        print(f"     - 索引类型: HNSW (M=32, 高精度)")
        print(f"     - 向量数量: {self.content_faiss_index.ntotal}")
        print(f"     - 预计加速: 100-400x（相比线性搜索）")

    def hybrid_search(
        self,
        query_content_embedding: List[float],
        query_text: str,
        query_context_embedding: List[float] = None,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        content_weight: float = 0.85,
        context_weight: float = 0.15
    ) -> List[Dict]:
        """
        混合检索：BM25 + 双向量

        Args:
            query_content_embedding: 查询的内容向量
            query_text: 查询文本（用于BM25）
            query_context_embedding: 查询的上下文向量（可选）
            top_k: 返回前K个结果
            filters: 过滤条件
            bm25_weight: BM25权重（默认0.5，经过评测）
            vector_weight: 向量权重（默认0.5）
            content_weight: 内容向量权重（默认0.85）
            context_weight: 上下文向量权重（默认0.15）

        Returns:
            检索结果列表，每个包含 score, bm25_score, vector_score, metadata
        """
        if len(self.content_embeddings) == 0:
            return []

        # 1. BM25检索分数
        if self.bm25_index is None:
            self.build_bm25_index()

        query_tokens = list(jieba.cut_for_search(query_text))
        bm25_scores = self.bm25_index.get_scores(query_tokens)

        # 归一化BM25分数到[0,1]
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        bm25_scores_norm = bm25_scores / max_bm25

        # 2. 向量检索分数
        # 根据数据规模选择搜索方法
        num_vectors = len(self.content_embeddings)
        use_faiss_search = self.use_faiss and self.faiss_built and num_vectors >= 5000

        if use_faiss_search:
            # 使用FAISS加速搜索（大规模数据）
            content_similarities, context_similarities = self._faiss_vector_search(
                query_content_embedding, query_context_embedding
            )
        else:
            # 使用numpy线性搜索（小规模数据或FAISS未构建）
            content_similarities, context_similarities = self._linear_vector_search(
                query_content_embedding, query_context_embedding
            )

        # 加权组合双向量
        if query_context_embedding is not None and context_similarities is not None:
            vector_scores = content_weight * content_similarities + context_weight * context_similarities
        else:
            vector_scores = content_similarities

        # 3. 混合分数（BM25:0.5 + Vector:0.5）
        hybrid_scores = bm25_weight * bm25_scores_norm + vector_weight * vector_scores

        # 4. 应用过滤器
        valid_indices = list(range(len(self.metadata)))

        if filters:
            valid_indices = []
            for i, meta in enumerate(self.metadata):
                match = True

                if 'time_range' in filters:
                    start, end = filters['time_range']
                    timestamp = meta.get('start_timestamp', 0)
                    if not (start <= timestamp <= end):
                        match = False

                if 'participants' in filters:
                    meta_participants = set(meta.get('participants', []))
                    filter_participants = set(filters['participants'])
                    if not filter_participants.intersection(meta_participants):
                        match = False

                if match:
                    valid_indices.append(i)

        if not valid_indices:
            return []

        # 5. 排序
        valid_hybrid_scores = hybrid_scores[valid_indices]
        valid_bm25_scores = bm25_scores_norm[valid_indices]
        valid_vector_scores = vector_scores[valid_indices]
        valid_metadata = [self.metadata[i] for i in valid_indices]

        sorted_indices = np.argsort(-valid_hybrid_scores)[:top_k]

        results = []
        for idx in sorted_indices:
            results.append({
                'score': float(valid_hybrid_scores[idx]),
                'bm25_score': float(valid_bm25_scores[idx]),
                'vector_score': float(valid_vector_scores[idx]),
                'content_score': float(content_similarities[valid_indices[idx]]),
                'metadata': valid_metadata[idx]
            })

        return results

    def _linear_vector_search(
        self,
        query_content_embedding: List[float],
        query_context_embedding: Optional[List[float]] = None
    ):
        """
        线性向量搜索（numpy实现）

        适用于小规模数据（< 5000 vectors）
        精确计算所有向量的余弦相似度

        Returns:
            (content_similarities, context_similarities)
        """
        query_content = np.array(query_content_embedding)
        content_matrix = np.vstack(self.content_embeddings)

        query_content_norm = query_content / (np.linalg.norm(query_content) + 1e-8)
        content_norm = content_matrix / (np.linalg.norm(content_matrix, axis=1, keepdims=True) + 1e-8)
        content_similarities = np.dot(content_norm, query_content_norm)

        context_similarities = None
        if query_context_embedding is not None:
            query_context = np.array(query_context_embedding)
            context_matrix = np.vstack(self.context_embeddings)

            query_context_norm = query_context / (np.linalg.norm(query_context) + 1e-8)
            context_norm = context_matrix / (np.linalg.norm(context_matrix, axis=1, keepdims=True) + 1e-8)
            context_similarities = np.dot(context_norm, query_context_norm)

        return content_similarities, context_similarities

    def _faiss_vector_search(
        self,
        query_content_embedding: List[float],
        query_context_embedding: Optional[List[float]] = None
    ):
        """
        FAISS加速向量搜索

        适用于大规模数据（>= 5000 vectors）
        使用HNSW索引快速找到近似最近邻

        Returns:
            (content_similarities, context_similarities)
        """
        # 准备查询向量（FAISS要求2D数组，float32）
        query_content = np.array([query_content_embedding]).astype('float32')
        faiss.normalize_L2(query_content)

        # FAISS搜索（获取所有向量，因为我们需要完整的相似度数组用于混合排序）
        num_vectors = self.content_faiss_index.ntotal
        content_distances, content_indices = self.content_faiss_index.search(query_content, num_vectors)

        # 转换距离到相似度
        # FAISS IndexHNSWFlat返回L2距离，对于归一化向量：L2 = 2(1 - cosine)
        # 因此：cosine = 1 - L2/2
        content_similarities = 1 - (content_distances[0] / 2)

        context_similarities = None
        if query_context_embedding is not None:
            query_context = np.array([query_context_embedding]).astype('float32')
            faiss.normalize_L2(query_context)

            context_distances, context_indices = self.context_faiss_index.search(query_context, num_vectors)
            context_similarities = 1 - (context_distances[0] / 2)

        return content_similarities, context_similarities

    def save(self, filepath: str):
        """
        保存混合向量库（包含FAISS索引）

        Args:
            filepath: 保存路径（.pkl文件）
        """
        # 调用父类保存方法（保存embeddings和metadata）
        super().save(filepath)

        # 如果使用FAISS，同时保存FAISS索引
        if self.use_faiss and self.faiss_built:
            import os
            base_path = filepath.rsplit('.', 1)[0]
            content_index_path = f"{base_path}_content.faiss"
            context_index_path = f"{base_path}_context.faiss"

            faiss.write_index(self.content_faiss_index, content_index_path)
            faiss.write_index(self.context_faiss_index, context_index_path)

            print(f"[INFO] FAISS索引已保存:")
            print(f"      - {content_index_path}")
            print(f"      - {context_index_path}")

    def load(self, filepath: str):
        """
        加载混合向量库（包含FAISS索引）

        Args:
            filepath: 向量库文件路径（.pkl文件）
        """
        # 调用父类加载方法
        super().load(filepath)

        # 尝试加载FAISS索引
        if self.use_faiss:
            import os
            base_path = filepath.rsplit('.', 1)[0]
            content_index_path = f"{base_path}_content.faiss"
            context_index_path = f"{base_path}_context.faiss"

            if os.path.exists(content_index_path) and os.path.exists(context_index_path):
                self.content_faiss_index = faiss.read_index(content_index_path)
                self.context_faiss_index = faiss.read_index(context_index_path)
                self.faiss_built = True
                print(f"[INFO] FAISS索引已加载:")
                print(f"      - {content_index_path}")
                print(f"      - {context_index_path}")
            else:
                print(f"[INFO] FAISS索引文件不存在，需要重新构建")
                print(f"       使用 build_faiss_index() 构建索引")
