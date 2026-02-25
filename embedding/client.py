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

        # 使用已验证可用的模型
        model_name = "text-embedding-004"
        self.model = TextEmbeddingModel.from_pretrained(model_name)
        self.dimension = 768

        print(f"[INFO] Google Vertex AI initialized successfully")
        print(f"[INFO] Project: {project_id}, Region: {location}")
        print(f"[INFO] Model: {model_name} (dimension: 768)")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成embeddings

        Args:
            texts: 文本列表

        Returns:
            embedding向量列表，每个向量768维
        """
        batch_size = 250  # Google API限制：最多250个文本/请求
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            try:
                embeddings_response = self.model.get_embeddings(batch)
                batch_embeddings = [emb.values for emb in embeddings_response]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"[ERROR] Embedding失败: {e}")
                # 返回零向量作为fallback
                all_embeddings.extend([[0.0] * 768 for _ in batch])

        return all_embeddings
