"""
Pipeline 模块

端到端数据处理流程：
1. 数据清洗
2. Embedding 生成
3. 知识抽取
4. 知识图谱构建
"""

from pipeline.base import BasePipeline, BatchPipeline, PipelineCheckpoint

__all__ = [
    'BasePipeline',
    'BatchPipeline',
    'PipelineCheckpoint'
]
