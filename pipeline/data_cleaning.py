"""
数据清洗 Pipeline

功能：
- 加载原始对话数据
- 应用清洗策略
- 保存清洗后的数据

使用示例：
    from pipeline.data_cleaning import DataCleaningPipeline
    from config.loader import load_config

    config = load_config()
    pipeline = DataCleaningPipeline(config)
    stats = pipeline.run()
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.base import BasePipeline
from data_loader.cleaner import ConversationCleaner


class DataCleaningPipeline(BasePipeline):
    """数据清洗 Pipeline"""

    def __init__(
        self,
        config: Dict[str, Any],
        input_dir: Path = None,
        output_dir: Path = None,
        **kwargs
    ):
        """
        初始化数据清洗 Pipeline

        Args:
            config: 配置字典
            input_dir: 输入目录（原始数据）
            output_dir: 输出目录（清洗后数据）
        """
        super().__init__("data_cleaning", config, **kwargs)

        # 设置路径
        if input_dir is None:
            input_dir = Path(config.get('paths', {}).get('input_data', 'data/conversations/chat_data_filtered'))
        if output_dir is None:
            output_dir = Path('data/conversations/cleaned')

        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建清洗器
        cleaning_config = config.get('pipeline', {}).get('data_cleaning', {})
        self.cleaner = ConversationCleaner.from_config(cleaning_config)

        self.logger.info(f"输入目录: {self.input_dir}")
        self.logger.info(f"输出目录: {self.output_dir}")

    def get_items(self) -> List[Path]:
        """获取所有对话文件"""
        json_files = list(self.input_dir.rglob('*.json'))
        self.logger.info(f"找到 {len(json_files)} 个对话文件")
        return json_files

    def process_item(self, item: Path) -> Any:
        """
        处理单个对话文件

        Args:
            item: 对话文件路径

        Returns:
            清洗结果
        """
        # 加载对话
        with open(item, 'r', encoding='utf-8') as f:
            conversation = json.load(f)

        # 清洗
        cleaned = self.cleaner.clean(conversation)

        if cleaned is None:
            self.logger.debug(f"对话被过滤: {item.name}")
            self.stats['skipped_items'] += 1
            return None

        # 计算输出路径（保持相对路径结构）
        rel_path = item.relative_to(self.input_dir)
        output_path = self.output_dir / rel_path

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存清洗后的数据
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        self.logger.debug(f"已清洗: {item.name} -> {output_path}")

        return cleaned

    def get_cleaning_stats(self) -> Dict[str, Any]:
        """获取清洗统计信息"""
        cleaner_stats = self.cleaner.get_stats()

        return {
            **self.stats,
            'cleaning': cleaner_stats
        }
