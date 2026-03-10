"""
Pipeline 基础类

提供统一的 Pipeline 接口，包括：
- 日志记录
- 进度保存（checkpoint）
- 断点续传
- 错误处理和重试
- 进度显示

所有 Pipeline 阶段都应继承此类。
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from tqdm import tqdm


class PipelineCheckpoint:
    """Pipeline 检查点管理器"""

    def __init__(self, checkpoint_dir: Path, pipeline_name: str):
        """
        初始化检查点管理器

        Args:
            checkpoint_dir: 检查点目录
            pipeline_name: Pipeline 名称
        """
        self.checkpoint_dir = checkpoint_dir
        self.pipeline_name = pipeline_name
        self.checkpoint_file = checkpoint_dir / f"{pipeline_name}_checkpoint.json"

        # 确保目录存在
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: Dict[str, Any]):
        """
        保存检查点

        Args:
            state: 要保存的状态字典
        """
        checkpoint_data = {
            'pipeline_name': self.pipeline_name,
            'timestamp': datetime.now().isoformat(),
            'state': state
        }

        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    def load(self) -> Optional[Dict[str, Any]]:
        """
        加载检查点

        Returns:
            检查点状态，如果不存在则返回 None
        """
        if not self.checkpoint_file.exists():
            return None

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            return checkpoint_data.get('state')
        except Exception as e:
            logging.warning(f"加载检查点失败: {e}")
            return None

    def exists(self) -> bool:
        """检查检查点是否存在"""
        return self.checkpoint_file.exists()

    def clear(self):
        """清除检查点"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()


class BasePipeline(ABC):
    """Pipeline 基础类"""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        checkpoint_dir: Optional[Path] = None,
        enable_checkpoint: bool = True
    ):
        """
        初始化 Pipeline

        Args:
            name: Pipeline 名称
            config: 配置字典
            checkpoint_dir: 检查点目录
            enable_checkpoint: 是否启用检查点
        """
        self.name = name
        self.config = config
        self.enable_checkpoint = enable_checkpoint

        # 设置日志
        self.logger = self._setup_logger()

        # 设置检查点
        if checkpoint_dir is None:
            checkpoint_dir = Path('.checkpoints')
        self.checkpoint = PipelineCheckpoint(checkpoint_dir, name)

        # 统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_items': 0,
            'processed_items': 0,
            'failed_items': 0,
            'skipped_items': 0
        }

    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(f"pipeline.{self.name}")
        logger.setLevel(logging.INFO)

        # 避免重复添加 handler
        if not logger.handlers:
            # 控制台 handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 文件 handler
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f'pipeline_{self.name}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            # 格式
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

        return logger

    @abstractmethod
    def process_item(self, item: Any) -> Any:
        """
        处理单个项目（需要子类实现）

        Args:
            item: 要处理的项目

        Returns:
            处理后的结果
        """
        pass

    @abstractmethod
    def get_items(self) -> List[Any]:
        """
        获取要处理的项目列表（需要子类实现）

        Returns:
            项目列表
        """
        pass

    def save_checkpoint(self, processed_indices: List[int], custom_state: Optional[Dict] = None):
        """
        保存检查点

        Args:
            processed_indices: 已处理的项目索引列表
            custom_state: 自定义状态
        """
        if not self.enable_checkpoint:
            return

        state = {
            'processed_indices': processed_indices,
            'stats': self.stats,
            'custom_state': custom_state or {}
        }

        self.checkpoint.save(state)
        self.logger.debug(f"已保存检查点: {len(processed_indices)} 个项目已处理")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        加载检查点

        Returns:
            检查点状态，如果不存在则返回 None
        """
        if not self.enable_checkpoint:
            return None

        state = self.checkpoint.load()
        if state:
            self.logger.info(f"找到检查点: {len(state.get('processed_indices', []))} 个项目已处理")
        return state

    def run(
        self,
        resume: bool = True,
        checkpoint_interval: int = 10
    ) -> Dict[str, Any]:
        """
        运行 Pipeline

        Args:
            resume: 是否从检查点恢复
            checkpoint_interval: 检查点保存间隔

        Returns:
            执行统计信息
        """
        self.stats['start_time'] = datetime.now().isoformat()

        # 获取所有项目
        items = self.get_items()
        self.stats['total_items'] = len(items)

        self.logger.info(f"开始执行 Pipeline: {self.name}")
        self.logger.info(f"总项目数: {len(items)}")

        # 加载检查点
        processed_indices = []
        if resume and self.checkpoint.exists():
            checkpoint_state = self.load_checkpoint()
            if checkpoint_state:
                processed_indices = checkpoint_state.get('processed_indices', [])
                self.stats = checkpoint_state.get('stats', self.stats)
                self.logger.info(f"从检查点恢复，跳过已处理的 {len(processed_indices)} 个项目")

        # 处理项目
        processed_indices_set = set(processed_indices)

        with tqdm(total=len(items), desc=self.name, initial=len(processed_indices)) as pbar:
            for i, item in enumerate(items):
                # 跳过已处理的项目
                if i in processed_indices_set:
                    continue

                try:
                    # 处理项目
                    self.process_item(item)

                    # 更新统计
                    self.stats['processed_items'] += 1
                    processed_indices.append(i)

                    # 保存检查点
                    if (self.stats['processed_items'] % checkpoint_interval == 0):
                        self.save_checkpoint(processed_indices)

                except Exception as e:
                    self.logger.error(f"处理项目 {i} 失败: {e}")
                    self.stats['failed_items'] += 1

                    # 如果失败，也保存检查点（避免重复处理失败项目）
                    if self.enable_checkpoint:
                        processed_indices.append(i)

                pbar.update(1)

        # 最终检查点
        if self.enable_checkpoint:
            self.save_checkpoint(processed_indices)

        # 完成
        self.stats['end_time'] = datetime.now().isoformat()
        self.logger.info(f"Pipeline 完成: {self.name}")
        self.logger.info(f"处理成功: {self.stats['processed_items']}/{self.stats['total_items']}")
        self.logger.info(f"处理失败: {self.stats['failed_items']}")

        return self.stats

    def clear_checkpoint(self):
        """清除检查点"""
        self.checkpoint.clear()
        self.logger.info("检查点已清除")


class BatchPipeline(BasePipeline):
    """批量处理 Pipeline（支持批量API调用）"""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        batch_size: int = 10,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        **kwargs
    ):
        """
        初始化批量 Pipeline

        Args:
            name: Pipeline 名称
            config: 配置字典
            batch_size: 批量大小
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        super().__init__(name, config, **kwargs)
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    def process_batch(self, batch: List[Any]) -> List[Any]:
        """
        处理一批项目（需要子类实现）

        Args:
            batch: 项目批次

        Returns:
            处理后的结果列表
        """
        pass

    def process_item(self, item: Any) -> Any:
        """单项处理（批量Pipeline使用process_batch）"""
        return self.process_batch([item])[0]

    def run_batch(
        self,
        resume: bool = True,
        checkpoint_interval: int = 5
    ) -> Dict[str, Any]:
        """
        批量运行 Pipeline

        Args:
            resume: 是否从检查点恢复
            checkpoint_interval: 检查点保存间隔（批次数）

        Returns:
            执行统计信息
        """
        self.stats['start_time'] = datetime.now().isoformat()

        # 获取所有项目
        items = self.get_items()
        self.stats['total_items'] = len(items)

        self.logger.info(f"开始执行批量 Pipeline: {self.name}")
        self.logger.info(f"总项目数: {len(items)}, 批量大小: {self.batch_size}")

        # 加载检查点
        processed_indices = []
        if resume and self.checkpoint.exists():
            checkpoint_state = self.load_checkpoint()
            if checkpoint_state:
                processed_indices = checkpoint_state.get('processed_indices', [])
                self.stats = checkpoint_state.get('stats', self.stats)

        processed_indices_set = set(processed_indices)

        # 创建批次
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch_indices = list(range(i, min(i + self.batch_size, len(items))))
            # 过滤已处理的项目
            batch_indices = [idx for idx in batch_indices if idx not in processed_indices_set]
            if batch_indices:
                batches.append((batch_indices, [items[idx] for idx in batch_indices]))

        self.logger.info(f"创建 {len(batches)} 个批次")

        # 处理批次
        with tqdm(total=len(batches), desc=f"{self.name} (批次)") as pbar:
            for batch_num, (batch_indices, batch_items) in enumerate(batches):
                retry_count = 0
                success = False

                while retry_count < self.max_retries and not success:
                    try:
                        # 处理批次
                        self.process_batch(batch_items)

                        # 更新统计
                        self.stats['processed_items'] += len(batch_items)
                        processed_indices.extend(batch_indices)

                        success = True

                    except Exception as e:
                        retry_count += 1
                        self.logger.error(
                            f"批次 {batch_num} 处理失败 (尝试 {retry_count}/{self.max_retries}): {e}"
                        )

                        if retry_count < self.max_retries:
                            self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                            time.sleep(self.retry_delay)
                        else:
                            self.logger.error(f"批次 {batch_num} 处理失败，已达最大重试次数")
                            self.stats['failed_items'] += len(batch_items)

                # 保存检查点
                if (batch_num + 1) % checkpoint_interval == 0:
                    self.save_checkpoint(processed_indices)

                pbar.update(1)

        # 最终检查点
        if self.enable_checkpoint:
            self.save_checkpoint(processed_indices)

        self.stats['end_time'] = datetime.now().isoformat()
        self.logger.info(f"批量 Pipeline 完成: {self.name}")
        self.logger.info(f"处理成功: {self.stats['processed_items']}/{self.stats['total_items']}")
        self.logger.info(f"处理失败: {self.stats['failed_items']}")

        return self.stats
