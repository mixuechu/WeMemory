#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Extraction Pipeline (Simplified)

NOTE: This is a simplified implementation for demonstration.
For production, implement full entity/relationship extraction using Claude on Vertex AI.
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


class KnowledgeExtractionPipeline(BasePipeline):
    """知识抽取 Pipeline (简化版)"""

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
            name="knowledge_extraction",
            config=config,
            **kwargs
        )

        self.config = config
        self.results = []

        # 设置路径
        self.input_dir = Path(config.get('paths', {}).get('cleaned_data', 'data/conversations/cleaned'))
        self.output_dir = Path(config.get('paths', {}).get('knowledge_graph', 'data/knowledge_graph'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Knowledge Extraction Pipeline] 初始化完成")
        print(f"  输入目录: {self.input_dir}")
        print(f"  输出目录: {self.output_dir}")
        print(f"  模型: {config.get('vertex_ai', {}).get('extraction', {}).get('model', 'claude-3-5-sonnet')}")
        print()
        print("  ⚠️  注意: 当前为简化实现")
        print("  完整实现需要:")
        print("    - Claude API 调用进行实体识别")
        print("    - 关系抽取")
        print("    - 事件提取")
        print("    - 实体消歧")

    def get_items(self) -> List[Path]:
        """获取待处理的文件列表

        Returns:
            文件路径列表
        """
        if not self.input_dir.exists():
            print(f"[ERROR] 输入目录不存在: {self.input_dir}")
            return []

        items = list(self.input_dir.glob("*.json"))
        print(f"[Knowledge Extraction] 找到 {len(items)} 个对话文件")
        return items

    def process_item(self, item: Path) -> Dict[str, Any]:
        """处理单个对话文件 (简化版 - 仅提取基本信息)

        Args:
            item: 对话文件路径

        Returns:
            处理结果字典
        """
        result = None
        try:
            # 加载对话数据
            with open(item, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            if not conversation or 'messages' not in conversation:
                result = {
                    'status': 'skipped',
                    'reason': 'invalid_format',
                    'file': item.name
                }
                self.results.append(result)
                return result

            # 简化版: 提取参与者作为实体
            participants = set()
            for msg in conversation['messages']:
                if 'sender' in msg:
                    participants.add(msg['sender'])
                if 'accountName' in msg:
                    participants.add(msg['accountName'])

            # 创建简化的知识图谱条目
            knowledge = {
                'conversation_name': conversation.get('meta', {}).get('name', item.stem),
                'conversation_type': conversation.get('meta', {}).get('type', 'unknown'),
                'participants': list(participants),
                'message_count': len(conversation['messages']),
                'source_file': item.name
            }

            result = {
                'status': 'success',
                'file': item.name,
                'participants': len(participants),
                'messages': len(conversation['messages']),
                'knowledge': knowledge
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

        self.results.append(result)
        return result

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

    def on_complete(self, results: List[Dict[str, Any]]) -> None:
        """Pipeline 完成后的处理

        Args:
            results: 所有处理结果
        """
        # 统计
        success = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')

        total_participants = sum(r.get('participants', 0) for r in results if r.get('status') == 'success')
        total_messages = sum(r.get('messages', 0) for r in results if r.get('status') == 'success')

        print(f"\n{'='*70}")
        print(f"知识抽取统计 (简化版)")
        print(f"{'='*70}")
        print(f"总对话数: {len(results)}")
        print(f"处理成功: {success}")
        print(f"处理失败: {failed}")
        print(f"跳过: {skipped}")
        print(f"提取参与者: {total_participants}")
        print(f"处理消息: {total_messages}")

        # 保存简化的知识图谱
        if success > 0:
            knowledge_graph = {
                'conversations': [r.get('knowledge') for r in results if r.get('status') == 'success'],
                'metadata': {
                    'total_conversations': success,
                    'total_participants': total_participants,
                    'total_messages': total_messages,
                    'extraction_type': 'simplified',
                    'note': '简化版实现 - 仅提取基本信息（参与者、消息数）'
                }
            }

            output_file = self.output_dir / "curated_kg.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)

            print(f"\n[Knowledge Extraction] 保存知识图谱...")
            print(f"  输出文件: {output_file}")
            print(f"  ✅ 知识图谱已保存")
            print()
            print("  ⚠️  注意: 这是简化实现")
            print("  生产环境应实现:")
            print("    - 使用 Claude 进行深度实体识别")
            print("    - 关系抽取（家庭、工作、社交关系）")
            print("    - 事件提取（会议、旅行、项目等）")
            print("    - 实体消歧和合并")
        else:
            print(f"\n[WARNING] 没有成功处理任何对话，跳过保存")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Extraction Pipeline")
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--fresh', action='store_true', help='从头开始（清除检查点）')

    args = parser.parse_args()

    # 创建并运行 Pipeline
    pipeline = KnowledgeExtractionPipeline(config_file=args.config)
    pipeline.run(resume=not args.fresh)


if __name__ == "__main__":
    main()
