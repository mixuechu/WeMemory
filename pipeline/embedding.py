#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Generation Pipeline

处理清洗后的对话数据，生成向量嵌入并保存到向量库。
"""
import sys
import pickle
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.base import BasePipeline
from data_loader import SessionBuilder, WeChatParser
from embedding import DualVectorGenerator, GoogleEmbeddingClient
from retrieval import HybridVectorStore
from config.loader import load_config


class EmbeddingPipeline(BasePipeline):
    """向量生成 Pipeline"""

    def __init__(self, config=None, config_file: str = None, **kwargs):
        """初始化 Pipeline

        Args:
            config: 配置字典（可选）
            config_file: 配置文件路径（可选）
            **kwargs: 额外参数
        """
        # 加载配置
        if config is None:
            config = load_config(config_file)

        super().__init__(
            name="embedding",
            config=config,
            **kwargs
        )

        self.config = config
        self.results = []  # Store results for on_complete

        # 设置路径
        self.input_dir = Path(self.config.paths.cleaned_data or "data/conversations/cleaned")
        self.output_dir = Path(self.config.paths.vector_stores_conversations)

        # 初始化组件
        self.session_builder = SessionBuilder(
            time_gap_minutes=30,
            min_messages=3,
            max_messages=20
        )
        self.embedding_client = GoogleEmbeddingClient()
        self.vector_generator = DualVectorGenerator(self.embedding_client)

        # 向量库
        self.vector_store = HybridVectorStore(dimension=768, use_faiss=True)

        print(f"[Embedding Pipeline] 初始化完成")
        print(f"  输入目录: {self.input_dir}")
        print(f"  输出目录: {self.output_dir}")

    def get_items(self) -> List[Path]:
        """获取待处理的文件列表

        Returns:
            文件路径列表
        """
        if not self.input_dir.exists():
            print(f"[ERROR] 输入目录不存在: {self.input_dir}")
            return []

        items = list(self.input_dir.glob("*.json"))
        print(f"[Embedding Pipeline] 找到 {len(items)} 个对话文件")
        return items

    def run(self, resume: bool = True, checkpoint_interval: int = 10):
        """运行 Pipeline 并调用 on_complete

        Args:
            resume: 是否从检查点恢复
            checkpoint_interval: 检查点保存间隔

        Returns:
            执行统计信息
        """
        # Run parent pipeline
        stats = super().run(resume=resume, checkpoint_interval=checkpoint_interval)

        # Call on_complete with results
        self.on_complete(self.results)

        return stats

    def process_item(self, item: Path) -> Dict[str, Any]:
        """处理单个对话文件

        Args:
            item: 对话文件路径

        Returns:
            处理结果字典
        """
        result = None
        try:
            # 1. 加载对话数据
            messages, metadata = WeChatParser.load_conversation(item)

            if not messages:
                return {
                    'status': 'skipped',
                    'reason': 'empty_conversation',
                    'file': item.name
                }

            # 2. 分割会话
            conv_meta = {
                'name': metadata.get('name', item.stem),
                'type': metadata.get('type', 'unknown'),
                'conversation_name': item.stem
            }
            sessions = self.session_builder.split_into_sessions(
                messages,
                conv_meta
            )

            if not sessions:
                return {
                    'status': 'skipped',
                    'reason': 'no_sessions',
                    'file': item.name
                }

            # 3. 生成向量
            sessions_with_embeddings = self.vector_generator.generate(sessions, use_dynamic_batch=True)

            if not sessions_with_embeddings:
                return {
                    'status': 'failed',
                    'reason': 'embedding_generation_failed',
                    'file': item.name
                }

            # 4. 添加到向量库
            for session in sessions_with_embeddings:
                # 构建元数据
                metadata = {
                    'conversation_name': conv_meta['conversation_name'],
                    'name': conv_meta['name'],
                    'type': conv_meta['type'],
                    'content_text': session.content_text,
                    'context_text': session.context_text,
                    'start_time': session.start_time.isoformat() if hasattr(session.start_time, 'isoformat') else str(session.start_time),
                    'end_time': session.end_time.isoformat() if hasattr(session.end_time, 'isoformat') else str(session.end_time),
                    'message_count': len(session.messages),
                    'session_id': session.session_id,
                    'session_type': session.session_type,
                    'participants': session.participants
                }

                self.vector_store.add(
                    content_embedding=session.content_embedding,
                    context_embedding=session.context_embedding,
                    metadata=metadata
                )

            result = {
                'status': 'success',
                'file': item.name,
                'sessions': len(sessions),
                'embeddings': len(sessions_with_embeddings)
            }

        except Exception as e:
            print(f"[ERROR] 处理文件失败 {item.name}: {e}")
            import traceback
            traceback.print_exc()
            result = {
                'status': 'failed',
                'file': item.name,
                'error': str(e)
            }

        # Store result
        self.results.append(result)
        return result

    def on_complete(self, results: List[Dict[str, Any]]) -> None:
        """Pipeline 完成后的处理

        Args:
            results: 所有处理结果
        """
        # 统计
        success = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')

        total_sessions = sum(r.get('sessions', 0) for r in results)
        total_embeddings = sum(r.get('embeddings', 0) for r in results)

        print(f"\n{'='*70}")
        print(f"向量生成统计")
        print(f"{'='*70}")
        print(f"总对话数: {len(results)}")
        print(f"处理成功: {success}")
        print(f"处理失败: {failed}")
        print(f"跳过: {skipped}")
        print(f"生成会话: {total_sessions}")
        print(f"生成向量: {total_embeddings}")

        # 保存向量库
        if total_embeddings > 0:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_file = self.output_dir / "embeddings.pkl"

            print(f"\n[Embedding Pipeline] 保存向量库...")
            print(f"  向量数: {len(self.vector_store.metadata):,}")
            print(f"  输出文件: {output_file}")

            # 构建索引
            self.vector_store.build_bm25_index()
            self.vector_store.build_faiss_index()

            # 保存
            self.vector_store.save(str(output_file))
            print(f"  ✅ 向量库已保存")
        else:
            print(f"\n[WARNING] 没有生成任何向量，跳过保存")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Embedding Generation Pipeline")
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--fresh', action='store_true', help='从头开始（清除检查点）')

    args = parser.parse_args()

    # 创建并运行 Pipeline
    pipeline = EmbeddingPipeline(config_file=args.config)
    pipeline.run(resume=not args.fresh)


if __name__ == "__main__":
    main()
