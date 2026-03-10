#!/usr/bin/env python3
"""
Pipeline 主控脚本

功能：
- 执行端到端数据处理流程
- 支持分步执行或全流程执行
- 显示进度和统计信息
- 支持断点续传

Pipeline 阶段：
1. data_cleaning - 数据清洗
2. embedding - 向量生成
3. knowledge_extraction - 知识抽取
4. graph_building - 图谱构建

使用方法：
    # 执行特定阶段
    python scripts/run_pipeline.py --step data_cleaning

    # 执行全流程
    python scripts/run_pipeline.py --all

    # 从头开始（清除检查点）
    python scripts/run_pipeline.py --step data_cleaning --fresh

    # 查看当前进度
    python scripts/run_pipeline.py --status
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.loader import load_config
from pipeline.data_cleaning import DataCleaningPipeline
from pipeline.embedding import EmbeddingPipeline


class PipelineOrchestrator:
    """Pipeline 编排器"""

    AVAILABLE_STEPS = [
        'data_cleaning',
        'embedding',
        'knowledge_extraction',
        'graph_building'
    ]

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化编排器

        Args:
            config_file: 配置文件路径
        """
        self.config = load_config(config_file)
        self.checkpoint_dir = Path(self.config.paths.checkpoints)

    def run_step(self, step: str, resume: bool = True, **kwargs):
        """
        执行单个步骤

        Args:
            step: 步骤名称
            resume: 是否从检查点恢复
            **kwargs: 额外参数

        Returns:
            执行统计信息
        """
        print("=" * 70)
        print(f"执行 Pipeline 步骤: {step}")
        print("=" * 70)
        print()

        if step == 'data_cleaning':
            return self._run_data_cleaning(resume, **kwargs)
        elif step == 'embedding':
            return self._run_embedding(resume, **kwargs)
        elif step == 'knowledge_extraction':
            return self._run_knowledge_extraction(resume, **kwargs)
        elif step == 'graph_building':
            return self._run_graph_building(resume, **kwargs)
        else:
            raise ValueError(f"未知的步骤: {step}")

    def _run_data_cleaning(self, resume: bool = True, **kwargs):
        """执行数据清洗"""
        pipeline = DataCleaningPipeline(
            self.config,
            checkpoint_dir=self.checkpoint_dir,
            **kwargs
        )

        stats = pipeline.run(resume=resume)

        # 显示清洗统计
        cleaning_stats = pipeline.get_cleaning_stats()

        print()
        print("=" * 70)
        print("数据清洗统计")
        print("=" * 70)
        print(f"总对话数: {stats['total_items']}")
        print(f"处理成功: {stats['processed_items']}")
        print(f"处理失败: {stats['failed_items']}")
        print(f"过滤对话: {stats['skipped_items']}")
        print()

        if 'cleaning' in cleaning_stats:
            cs = cleaning_stats['cleaning']
            print("清洗详情:")
            print(f"  原始消息: {cs['original_messages']}")
            print(f"  清洗后: {cs['filtered_messages']}")
            print(f"  移除系统消息: {cs['removed_system_messages']}")
            print(f"  移除重复: {cs['removed_duplicates']}")
            print(f"  移除低质量: {cs['removed_low_quality']}")
            print(f"  保留率: {cs.get('retention_rate', 0):.1%}")
            print()

        return stats

    def _run_embedding(self, resume: bool = True, **kwargs):
        """执行向量生成"""
        from pipeline.embedding import EmbeddingPipeline

        pipeline = EmbeddingPipeline(
            config=self.config,
            checkpoint_dir=self.checkpoint_dir,
            **kwargs
        )
        pipeline.run(resume=resume)

        return {
            'status': 'completed',
            'vectors_generated': len(pipeline.vector_store.metadata) if hasattr(pipeline, 'vector_store') else 0
        }

    def _run_knowledge_extraction(self, resume: bool = True, **kwargs):
        """执行知识抽取（待实现）"""
        print("⚠️  Knowledge Extraction Pipeline 暂未实现")
        print("请参考: knowledge_graph/ 目录中的脚本")
        return {}

    def _run_graph_building(self, resume: bool = True, **kwargs):
        """执行图谱构建（待实现）"""
        print("⚠️  Graph Building Pipeline 暂未实现")
        print("请参考: knowledge_graph/ 目录中的脚本")
        return {}

    def run_all(self, resume: bool = True):
        """执行全流程"""
        print("=" * 70)
        print("执行完整 Pipeline 流程")
        print("=" * 70)
        print()

        all_stats = {}

        for step in self.AVAILABLE_STEPS:
            try:
                print(f"\n[步骤 {step}]")
                stats = self.run_step(step, resume=resume)
                all_stats[step] = stats

                print(f"✅ {step} 完成")
                print()

            except Exception as e:
                print(f"❌ {step} 失败: {e}")
                print()

                # 询问是否继续
                response = input("是否继续下一步骤？ [y/N] ")
                if response.lower() != 'y':
                    break

        print("=" * 70)
        print("Pipeline 流程完成")
        print("=" * 70)

        return all_stats

    def show_status(self):
        """显示当前进度"""
        print("=" * 70)
        print("Pipeline 进度状态")
        print("=" * 70)
        print()

        for step in self.AVAILABLE_STEPS:
            checkpoint_file = self.checkpoint_dir / f"{step}_checkpoint.json"

            if checkpoint_file.exists():
                try:
                    import json
                    with open(checkpoint_file, 'r') as f:
                        checkpoint = json.load(f)

                    state = checkpoint.get('state', {})
                    stats = state.get('stats', {})

                    print(f"[{step}]")
                    print(f"  状态: ✅ 有检查点")
                    print(f"  时间: {checkpoint.get('timestamp', 'N/A')}")
                    print(f"  进度: {stats.get('processed_items', 0)}/{stats.get('total_items', 0)}")
                    print()
                except:
                    print(f"[{step}]")
                    print(f"  状态: ⚠️  检查点损坏")
                    print()
            else:
                print(f"[{step}]")
                print(f"  状态: ⬜ 未开始")
                print()

    def clear_checkpoint(self, step: Optional[str] = None):
        """
        清除检查点

        Args:
            step: 要清除的步骤，None 表示清除所有
        """
        if step:
            checkpoint_file = self.checkpoint_dir / f"{step}_checkpoint.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                print(f"✅ 已清除 {step} 的检查点")
            else:
                print(f"⚠️  {step} 没有检查点")
        else:
            # 清除所有检查点
            for step_name in self.AVAILABLE_STEPS:
                checkpoint_file = self.checkpoint_dir / f"{step_name}_checkpoint.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
            print("✅ 已清除所有检查点")


def main():
    parser = argparse.ArgumentParser(
        description='WeMemory Pipeline 主控脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行数据清洗
  python scripts/run_pipeline.py --step data_cleaning

  # 执行全流程
  python scripts/run_pipeline.py --all

  # 从头开始（清除检查点）
  python scripts/run_pipeline.py --step data_cleaning --fresh

  # 查看进度
  python scripts/run_pipeline.py --status

  # 清除所有检查点
  python scripts/run_pipeline.py --clear
        """
    )

    parser.add_argument(
        '--step',
        type=str,
        choices=['data_cleaning', 'embedding', 'knowledge_extraction', 'graph_building'],
        help='要执行的步骤'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='执行全流程'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='配置文件路径'
    )

    parser.add_argument(
        '--fresh',
        action='store_true',
        help='从头开始（清除检查点）'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='显示当前进度'
    )

    parser.add_argument(
        '--clear',
        action='store_true',
        help='清除所有检查点'
    )

    args = parser.parse_args()

    # 创建编排器
    orchestrator = PipelineOrchestrator(args.config)

    # 显示状态
    if args.status:
        orchestrator.show_status()
        return

    # 清除检查点
    if args.clear:
        orchestrator.clear_checkpoint()
        return

    # 执行步骤
    if args.step:
        if args.fresh:
            orchestrator.clear_checkpoint(args.step)

        stats = orchestrator.run_step(args.step, resume=not args.fresh)

        print()
        print("✅ Pipeline 执行完成")
        print()
        return

    # 执行全流程
    if args.all:
        if args.fresh:
            orchestrator.clear_checkpoint()

        stats = orchestrator.run_all(resume=not args.fresh)

        print()
        print("✅ 全流程执行完成")
        print()
        return

    # 没有指定操作，显示帮助
    parser.print_help()


if __name__ == '__main__':
    main()
