#!/usr/bin/env python3
"""
对话清洗脚本

功能：清洗微信对话数据，过滤低质量内容

使用方法：
    # 清洗单个文件
    python scripts/clean_conversation.py input.json --output cleaned.json

    # 批量清洗目录
    python scripts/clean_conversation.py data/conversations/raw/ \\
        --output data/conversations/cleaned/ \\
        --min-messages 3 \\
        --quality-threshold 0.5

    # 使用配置文件
    python scripts/clean_conversation.py data/conversations/raw/ \\
        --output data/conversations/cleaned/ \\
        --config config/default.yaml
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loader.cleaner import ConversationCleaner
from config.loader import load_config


def clean_single_file(
    input_path: Path,
    output_path: Path,
    cleaner: ConversationCleaner
) -> Tuple[bool, str]:
    """
    清洗单个文件

    Returns:
        (是否成功, 消息)
    """
    try:
        # 加载对话
        with open(input_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)

        # 清洗
        cleaned = cleaner.clean(conversation)

        if cleaned is None:
            return False, "对话被过滤（质量不达标）"

        # 创建输出目录
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        return True, "清洗成功"

    except Exception as e:
        return False, f"处理失败: {e}"


def clean_directory(
    input_dir: Path,
    output_dir: Path,
    cleaner: ConversationCleaner
) -> dict:
    """
    批量清洗目录

    Returns:
        统计信息
    """
    # 查找所有 JSON 文件
    json_files = list(input_dir.rglob('*.json'))

    print(f"找到 {len(json_files)} 个 JSON 文件")
    print("开始清洗...\n")

    stats = {
        'total': len(json_files),
        'success': 0,
        'filtered': 0,
        'failed': 0
    }

    for i, json_file in enumerate(json_files, 1):
        # 计算相对路径
        rel_path = json_file.relative_to(input_dir)
        output_path = output_dir / rel_path

        print(f"[{i}/{len(json_files)}] {json_file.name}")

        success, message = clean_single_file(json_file, output_path, cleaner)

        if success:
            stats['success'] += 1
            print(f"  ✅ {message}")
        elif "过滤" in message:
            stats['filtered'] += 1
            print(f"  ⬜ {message}")
        else:
            stats['failed'] += 1
            print(f"  ❌ {message}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='清洗微信对话数据',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'input',
        type=str,
        help='输入文件或目录'
    )

    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='输出文件或目录'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='配置文件路径'
    )

    parser.add_argument(
        '--min-messages',
        type=int,
        help='最小消息数（覆盖配置）'
    )

    parser.add_argument(
        '--quality-threshold',
        type=float,
        help='质量阈值（覆盖配置）'
    )

    parser.add_argument(
        '--max-time-gap',
        type=int,
        help='最大时间间隔（分钟，覆盖配置）'
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"❌ 输入路径不存在: {input_path}")
        sys.exit(1)

    print("=" * 60)
    print("WeMemory 对话清洗工具")
    print("=" * 60)
    print()

    # 创建清洗器
    if args.config:
        # 从配置文件加载
        config = load_config(args.config)
        cleaner = ConversationCleaner.from_config(config.pipeline.data_cleaning)
        print(f"📄 使用配置: {args.config}")
    else:
        # 使用默认配置或命令行参数
        cleaner = ConversationCleaner(
            min_messages=args.min_messages or 3,
            max_time_gap_minutes=args.max_time_gap or 30,
            quality_threshold=args.quality_threshold or 0.5
        )
        print("📄 使用默认配置")

    print(f"🔧 清洗参数:")
    print(f"   最小消息数: {cleaner.min_messages}")
    print(f"   时间间隔: {cleaner.max_time_gap_seconds // 60} 分钟")
    print(f"   质量阈值: {cleaner.quality_threshold}")
    print()

    # 执行清洗
    if input_path.is_file():
        # 单文件模式
        print(f"📁 输入: {input_path}")
        print(f"📁 输出: {output_path}\n")

        success, message = clean_single_file(input_path, output_path, cleaner)

        if success:
            print(f"✅ {message}")
            print()

            # 显示统计
            stats = cleaner.get_stats()
            print("清洗统计:")
            print(f"  原始消息: {stats['original_messages']}")
            print(f"  清洗后: {stats['filtered_messages']}")
            print(f"  移除系统消息: {stats['removed_system_messages']}")
            print(f"  移除重复: {stats['removed_duplicates']}")
            print(f"  移除低质量: {stats['removed_low_quality']}")
            print(f"  保留率: {stats['retention_rate']:.1%}")
            print()

            sys.exit(0)
        else:
            print(f"❌ {message}")
            sys.exit(1)

    elif input_path.is_dir():
        # 目录模式
        print(f"📁 输入目录: {input_path}")
        print(f"📁 输出目录: {output_path}\n")

        stats = clean_directory(input_path, output_path, cleaner)

        print()
        print("=" * 60)
        print("清洗完成")
        print("=" * 60)
        print()
        print(f"总计: {stats['total']} 个文件")
        print(f"✅ 成功: {stats['success']}")
        print(f"⬜ 过滤: {stats['filtered']}")
        print(f"❌ 失败: {stats['failed']}")
        print()

        # 显示总体统计
        cleaner_stats = cleaner.get_stats()
        print("总体统计:")
        print(f"  原始消息: {cleaner_stats['original_messages']}")
        print(f"  清洗后: {cleaner_stats['filtered_messages']}")
        print(f"  保留率: {cleaner_stats['retention_rate']:.1%}")
        print(f"  创建会话: {cleaner_stats['sessions_created']}")
        print()

        if stats['success'] > 0:
            print("✅ 清洗成功！")
            print()
            print("下一步:")
            print("  1. 评估清洗效果:")
            print(f"     python scripts/evaluate_data_quality.py {output_path}")
            print()
            print("  2. 生成向量库:")
            print("     参见: docs/embedding.md")
            print()
            sys.exit(0)
        else:
            print("❌ 所有文件清洗失败")
            sys.exit(1)

    else:
        print(f"❌ 不支持的路径类型: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
