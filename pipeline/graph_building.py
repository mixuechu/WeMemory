#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph Building Pipeline (Simplified)

NOTE: This is a simplified implementation for demonstration.
For production, implement full triplet generation and embedding.
"""
import sys
import json
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.base import BasePipeline
from config.loader import load_config


class GraphBuildingPipeline(BasePipeline):
    """图谱构建 Pipeline (简化版)"""

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
            name="graph_building",
            config=config,
            **kwargs
        )

        self.config = config

        # 设置路径
        self.input_file = Path(config.get('paths', {}).get('knowledge_graph_curated', 'data/knowledge_graph/curated_kg.json'))
        self.output_dir = Path(config.get('paths', {}).get('knowledge_graph', 'data/knowledge_graph'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Graph Building Pipeline] 初始化完成")
        print(f"  输入文件: {self.input_file}")
        print(f"  输出目录: {self.output_dir}")
        print()
        print("  ⚠️  注意: 当前为简化实现")
        print("  完整实现需要:")
        print("    - 从知识图谱生成三元组")
        print("    - 为三元组生成向量嵌入")
        print("    - 构建 FAISS 索引用于三元组搜索")

    def get_items(self) -> List[str]:
        """获取待处理的项目

        Returns:
            单项列表（因为只处理一个知识图谱文件）
        """
        if not self.input_file.exists():
            print(f"[WARNING] 知识图谱文件不存在: {self.input_file}")
            print("          请先运行 knowledge_extraction 步骤")
            return []

        return ['build_graph']

    def process_item(self, item: str) -> Dict[str, Any]:
        """构建图谱

        Args:
            item: 项目标识

        Returns:
            处理结果字典
        """
        try:
            # 加载知识图谱
            with open(self.input_file, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)

            conversations = kg_data.get('conversations', [])

            if not conversations:
                return {
                    'status': 'skipped',
                    'reason': 'no_conversations'
                }

            # 简化版: 创建基本三元组
            triplets = []
            triplet_id = 0

            for conv in conversations:
                conv_name = conv.get('conversation_name', 'Unknown')
                participants = conv.get('participants', [])

                # 为每个参与者创建三元组
                for participant in participants:
                    triplet = {
                        'id': triplet_id,
                        'type': 'relationship',
                        'text': f"{participant} 参与了对话 {conv_name}",
                        'metadata': {
                            'subject': participant,
                            'relation_type': 'PARTICIPATES_IN',
                            'object': conv_name,
                            'conversation_name': conv_name
                        }
                    }
                    triplets.append(triplet)
                    triplet_id += 1

            # 保存三元组
            triplets_data = {
                'triplets': triplets,
                'metadata': {
                    'total_triplets': len(triplets),
                    'total_conversations': len(conversations),
                    'extraction_type': 'simplified',
                    'note': '简化版实现 - 仅创建基本参与关系三元组'
                }
            }

            output_file = self.output_dir / "triplets.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(triplets_data, f, ensure_ascii=False, indent=2)

            print(f"\n{'='*70}")
            print(f"图谱构建统计 (简化版)")
            print(f"{'='*70}")
            print(f"输入对话: {len(conversations)}")
            print(f"生成三元组: {len(triplets)}")
            print(f"\n[Graph Building] 保存三元组...")
            print(f"  输出文件: {output_file}")
            print(f"  ✅ 三元组已保存")
            print()
            print("  ⚠️  注意: 这是简化实现")
            print("  生产环境应实现:")
            print("    - 丰富的关系类型（家庭、工作、社交）")
            print("    - 事件三元组")
            print("    - 三元组向量嵌入")
            print("    - FAISS 索引构建")

            return {
                'status': 'success',
                'triplets': len(triplets),
                'conversations': len(conversations)
            }

        except Exception as e:
            print(f"[ERROR] 图谱构建失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'failed',
                'error': str(e)
            }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Graph Building Pipeline")
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--fresh', action='store_true', help='从头开始（清除检查点）')

    args = parser.parse_args()

    # 创建并运行 Pipeline
    pipeline = GraphBuildingPipeline(config_file=args.config)
    pipeline.run(resume=not args.fresh)


if __name__ == "__main__":
    main()
