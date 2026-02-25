#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量生成器 - 为会话生成双向量embeddings
"""
from pathlib import Path
from typing import List, Tuple
from .client import GoogleEmbeddingClient
from .enricher import TextEnricher


class DualVectorGenerator:
    """
    双向量生成器

    为每个会话生成两个向量：
    1. 内容向量 (content_embedding): 85%权重
    2. 上下文向量 (context_embedding): 15%权重

    最佳实践：
    - 使用动态batch（基于token数，避免超过API限制）
    - 单个文本限制: 2,048 tokens
    - 单次请求限制: 20,000 tokens
    """

    def __init__(self, embedding_client: GoogleEmbeddingClient = None):
        """
        Args:
            embedding_client: Google Embedding客户端，如果为None则自动创建
        """
        self.embedding_client = embedding_client or GoogleEmbeddingClient()
        self.text_enricher = TextEnricher()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        估算文本的token数

        对于中文文本，粗略估计为 1.5 tokens/字符

        Args:
            text: 输入文本

        Returns:
            估算的token数
        """
        return int(len(text) * 1.5)

    def create_dynamic_batches(
        self,
        sessions: List,
        max_tokens_per_batch: int = 19000
    ) -> List[Tuple[int, int]]:
        """
        创建动态batch（基于token数而非固定session数）

        根据每个session的实际token数动态调整batch大小，
        确保每个batch的总token数不超过API限制。

        Args:
            sessions: ConversationSession对象列表（已完成文本富化）
            max_tokens_per_batch: 每个batch的最大token数（默认19,000，留1000 buffer）

        Returns:
            batch索引列表 [(start_idx, end_idx), ...]
        """
        batches = []
        current_start = 0
        current_tokens = 0

        for i, session in enumerate(sessions):
            # 估算当前session的token数（content + context）
            content_tokens = self.estimate_tokens(session.content_text)
            context_tokens = self.estimate_tokens(session.context_text)
            session_tokens = content_tokens + context_tokens

            # 如果加入当前session会超过限制，且当前batch非空，则结束当前batch
            if current_tokens + session_tokens > max_tokens_per_batch and i > current_start:
                batches.append((current_start, i))
                current_start = i
                current_tokens = session_tokens
            else:
                current_tokens += session_tokens

        # 添加最后一个batch
        if current_start < len(sessions):
            batches.append((current_start, len(sessions)))

        return batches

    def generate(self, sessions: List, use_dynamic_batch: bool = True, batch_size: int = 10) -> List:
        """
        为会话列表生成双向量

        Args:
            sessions: ConversationSession对象列表
            use_dynamic_batch: 是否使用动态batch（推荐True，避免token限制错误）
            batch_size: 固定批处理大小（仅当use_dynamic_batch=False时使用）

        Returns:
            包含embeddings的sessions列表（原地修改）
        """
        print(f"\n[INFO] 开始生成双向量embeddings...")
        print(f"      - 内容向量权重: 85%")
        print(f"      - 上下文向量权重: 15%")
        print(f"      - Batch策略: {'动态batch（基于token数）' if use_dynamic_batch else f'固定batch（{batch_size}）'}")

        # 1. 文本富化
        print(f"\n[INFO] 开始双文本富化（内容向量 + 上下文向量）...")
        for i, session in enumerate(sessions):
            content_text, context_text = self.text_enricher.enrich_session(session)
            session.content_text = content_text
            session.context_text = context_text
            if (i + 1) % 100 == 0:
                print(f"   进度: {i+1}/{len(sessions)}")

        print(f"[OK] 文本富化完成")

        # 2. 创建batches
        if use_dynamic_batch:
            print(f"\n[INFO] 创建动态batches（目标: <19,000 tokens/batch）...")
            batch_ranges = self.create_dynamic_batches(sessions)
            print(f"[OK] 创建 {len(batch_ranges)} 个动态batches")

            # 统计batch大小
            batch_sizes = [end - start for start, end in batch_ranges]
            print(f"      - 最小: {min(batch_sizes)} sessions")
            print(f"      - 最大: {max(batch_sizes)} sessions")
            print(f"      - 平均: {sum(batch_sizes)/len(batch_sizes):.1f} sessions")
        else:
            # 固定batch
            batch_ranges = [(i, min(i + batch_size, len(sessions)))
                          for i in range(0, len(sessions), batch_size)]

        # 3. 批量生成embeddings
        print(f"\n[INFO] 批量生成embeddings...")
        total_processed = 0
        failed_count = 0

        for batch_idx, (start, end) in enumerate(batch_ranges):
            batch = sessions[start:end]

            # 分别生成内容和上下文embedding
            content_texts = [s.content_text for s in batch]
            context_texts = [s.context_text for s in batch]

            content_embeddings = self.embedding_client.get_embeddings(content_texts)
            context_embeddings = self.embedding_client.get_embeddings(context_texts)

            # 保存到session对象
            for session, content_emb, context_emb in zip(batch, content_embeddings, context_embeddings):
                session.content_embedding = content_emb
                session.context_embedding = context_emb

                # 检查是否为零向量（API失败）
                import numpy as np
                if np.all(np.array(content_emb) == 0):
                    failed_count += 1

            total_processed += len(batch)

            if (batch_idx + 1) % 100 == 0:
                print(f"   进度: {batch_idx+1}/{len(batch_ranges)} batches ({total_processed}/{len(sessions)} sessions)")

        print(f"[OK] 双向量生成完成:")
        print(f"      - 总sessions: {len(sessions)}")
        print(f"      - 成功: {len(sessions) - failed_count}")
        print(f"      - 失败: {failed_count}")

        return sessions
