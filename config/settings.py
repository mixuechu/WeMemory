#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Google Cloud配置
GOOGLE_PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
GOOGLE_LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_CREDENTIALS_JSON = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

# Embedding配置
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768
EMBEDDING_BATCH_SIZE = 10

# Session切分配置
SESSION_TIME_GAP_MINUTES = 30
SESSION_MIN_MESSAGES = 3
SESSION_MAX_MESSAGES = 20

# 双向量权重
CONTENT_WEIGHT = 0.85
CONTEXT_WEIGHT = 0.15

# 混合检索权重（经过评测得出）
BM25_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5

# 目录配置
DATA_DIR = "chat_data_filtered"
VECTOR_STORE_DIR = "vector_stores"
LOG_DIR = "logs"
