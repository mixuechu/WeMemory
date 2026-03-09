#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量生成模块 - 生成双向量embeddings
"""
from .client import GoogleEmbeddingClient
from .enricher import TextEnricher
from .generator import DualVectorGenerator

__all__ = [
    'GoogleEmbeddingClient',
    'TextEnricher',
    'DualVectorGenerator',
]
