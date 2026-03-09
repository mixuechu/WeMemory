#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Vertex AI Embedding客户端
"""
import os
import json
from typing import List
from google.oauth2 import service_account
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


class GoogleEmbeddingClient:
    """
    Google Vertex AI Embedding客户端

    使用Google Cloud的text-embedding-004模型生成768维向量
    """

    def __init__(self):
        """
        初始化Google Vertex AI客户端

        需要环境变量：
        - VITE_GOOGLE_CLOUD_PROJECT
        - VITE_GOOGLE_CLOUD_LOCATION
        - VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON
        """
        project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
        location = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
        credentials_json_str = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

        if not all([project_id, location, credentials_json_str]):
            raise ValueError("缺少Google Cloud配置，请检查.env文件")

        # 从JSON字符串加载credentials
        credentials_dict = json.loads(credentials_json_str)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)

        # 初始化Vertex AI
        aiplatform.init(
            project=project_id,
            location=location,
            credentials=credentials
        )

        # 使用多语言优化模型（中文短文本区分度极佳）
        model_name = "text-multilingual-embedding-002"
        self.model = TextEmbeddingModel.from_pretrained(model_name)
        self.dimension = 768

        print(f"[INFO] Google Vertex AI initialized successfully")
        print(f"[INFO] Project: {project_id}, Region: {location}")
        print(f"[INFO] Model: {model_name} (dimension: 768, 多语言优化)")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        估算文本的token数（中文约1.5 tokens/字符）

        Args:
            text: 输入文本

        Returns:
            估算的token数
        """
        return int(len(text) * 1.5)

    def create_dynamic_batches(self, texts: List[str], max_tokens: int = 19000, max_instances: int = 250) -> List[List[str]]:
        """
        创建动态batch，确保每个batch不超过token和实例数限制

        Args:
            texts: 文本列表
            max_tokens: 每个batch的最大token数（默认19000，留1000 buffer）
            max_instances: 每个batch的最大实例数（默认250，Google API限制）

        Returns:
            batch列表
        """
        batches = []
        current_batch = []
        current_tokens = 0

        for text in texts:
            text_tokens = self.estimate_tokens(text)

            # 如果单个文本就超过限制，单独成batch（会失败但有fallback）
            if text_tokens > max_tokens:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                batches.append([text])
                continue

            # 检查两个限制：token数 AND 实例数
            would_exceed_tokens = current_tokens + text_tokens > max_tokens
            would_exceed_instances = len(current_batch) >= max_instances

            # 如果加入当前text会超限（任一限制），先保存当前batch
            if (would_exceed_tokens or would_exceed_instances) and current_batch:
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = text_tokens
            else:
                current_batch.append(text)
                current_tokens += text_tokens

        # 添加最后一个batch
        if current_batch:
            batches.append(current_batch)

        return batches

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成embeddings（使用动态batch避免token超限）

        Args:
            texts: 文本列表

        Returns:
            embedding向量列表，每个向量768维
        """
        # 使用动态batch策略
        batches = self.create_dynamic_batches(texts)
        all_embeddings = []

        total_batches = len(batches)
        for batch_idx, batch in enumerate(batches):
            try:
                embeddings_response = self.model.get_embeddings(batch)
                batch_embeddings = [emb.values for emb in embeddings_response]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"[ERROR] Batch {batch_idx+1}/{total_batches} 失败: {e}")
                # 返回零向量作为fallback
                all_embeddings.extend([[0.0] * 768 for _ in batch])

            # 每100个batch打印进度
            if (batch_idx + 1) % 100 == 0:
                print(f"  进度: {batch_idx+1}/{total_batches} batches")

        return all_embeddings
