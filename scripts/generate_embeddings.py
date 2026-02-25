#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一向量生成脚本 - 整合所有最佳实践

最佳实践：
1. 双层vector（content 85% + context 15%）
2. 滑动message分片（30分钟gap，3-20条消息）
3. 动态batch（基于token数，避免API限制）
4. 分片保存策略（每个对话单独保存，不在内存累积）
5. 保留所有shard（方便增量更新和调试）
6. BM25 + FAISS HNSW混合检索
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import gc
import pickle
from datetime import datetime
from dotenv import load_dotenv

from data_loader import WeChatDataLoader, SessionBuilder
from embedding import DualVectorGenerator, GoogleEmbeddingClient
from retrieval import HybridVectorStore

# 加载环境变量
load_dotenv()


def generate_all_embeddings(
    excel_file: str,
    output_dir: str = "vector_stores",
    shard_dir: str = "vector_stores/shards",
    use_dynamic_batch: bool = True,
    keep_shards: bool = True
):
    """
    生成所有对话的embeddings（分片保存策略）

    Args:
        excel_file: Excel文件路径
        output_dir: 输出目录
        shard_dir: 分片文件目录
        use_dynamic_batch: 使用动态batch（推荐True）
        keep_shards: 合并后保留分片文件（推荐True）
    """
    output_path = Path(output_dir)
    shard_path = Path(shard_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    shard_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("微信记忆系统 - 向量生成")
    print("=" * 80)
    print(f"Excel文件: {excel_file}")
    print(f"输出目录: {output_dir}")
    print(f"分片目录: {shard_dir}")
    print(f"动态batch: {use_dynamic_batch}")
    print(f"保留分片: {keep_shards}")
    print("=" * 80)

    # 1. 加载数据
    print("\n[1] 加载微信数据...")
    loader = WeChatDataLoader()
    conversations = loader.load_from_excel(excel_file)
    print(f"[OK] 加载 {len(conversations)} 个对话")

    # 2. 初始化组件
    print("\n[2] 初始化组件...")
    session_builder = SessionBuilder(
        time_gap_minutes=30,  # 30分钟gap
        min_messages=3,       # 最小3条消息
        max_messages=20       # 最大20条消息
    )
    embedding_client = GoogleEmbeddingClient()
    vector_generator = DualVectorGenerator(embedding_client)
    print("[OK] 组件初始化完成")

    # 3. 逐个对话处理（分片保存策略）
    print("\n[3] 开始处理对话（分片保存策略）...")
    start_time = datetime.now()

    for idx, conv in enumerate(conversations):
        conv_start = datetime.now()

        print(f"\n{'='*70}")
        print(f"[{idx+1}/{len(conversations)}] 对话: {conv.name}")
        print(f"消息数: {len(conv.messages):,}")

        # 3.1 会话切分（滑动窗口）
        conv_meta = {
            'name': conv.name,
            'type': conv.type
        }
        sessions = session_builder.split_into_sessions(conv.messages, conv_meta)

        if len(sessions) == 0:
            print(f"[WARNING] 没有生成任何会话片段，跳过")
            continue

        # 3.2 生成双向量（动态batch）
        sessions = vector_generator.generate(
            sessions,
            use_dynamic_batch=use_dynamic_batch
        )

        # 3.3 保存为独立shard（不累积在内存）
        shard_file = shard_path / f"shard_{idx:04d}.pkl"
        shard_data = {
            'content_embeddings': [s.content_embedding for s in sessions],
            'context_embeddings': [s.context_embedding for s in sessions],
            'metadata': [
                {
                    'session_id': s.session_id,
                    'conversation_name': s.conversation_name,
                    'conversation_type': s.conversation_type,
                    'participants': s.participants,
                    'start_timestamp': s.start_time.timestamp(),
                    'end_timestamp': s.end_time.timestamp(),
                    'message_count': len(s.messages),
                    'session_type': s.session_type,
                    'content_text': s.content_text,
                    'context_text': s.context_text
                }
                for s in sessions
            ]
        }

        with open(shard_file, 'wb') as f:
            pickle.dump(shard_data, f)

        # 释放内存
        del sessions, shard_data
        gc.collect()

        conv_time = (datetime.now() - conv_start).total_seconds()
        print(f"[OK] 已保存: {shard_file.name} ({conv_time:.1f}秒)")

    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n[OK] 全部对话处理完成，耗时: {total_time/60:.1f}分钟")

    # 4. 合并所有shards
    print("\n[4] 合并所有分片...")
    merge_start = datetime.now()

    all_content = []
    all_context = []
    all_metadata = []

    shard_files = sorted(shard_path.glob("shard_*.pkl"))
    print(f"找到 {len(shard_files)} 个分片文件")

    for i, shard_file in enumerate(shard_files):
        with open(shard_file, 'rb') as f:
            shard_data = pickle.load(f)

        all_content.extend(shard_data['content_embeddings'])
        all_context.extend(shard_data['context_embeddings'])
        all_metadata.extend(shard_data['metadata'])

        if (i + 1) % 100 == 0:
            print(f"   合并进度: {i+1}/{len(shard_files)}")

    print(f"[OK] 合并完成，总sessions: {len(all_metadata):,}")

    # 5. 保存最终向量库（不构建索引，节省内存）
    print("\n[5] 保存最终向量库...")
    final_file = output_path / "conversations.pkl"

    final_data = {
        'content_embeddings': all_content,
        'context_embeddings': all_context,
        'metadata': all_metadata
    }

    with open(final_file, 'wb') as f:
        pickle.dump(final_data, f)

    file_size = final_file.stat().st_size / 1024 / 1024 / 1024
    print(f"[OK] 已保存: {final_file} ({file_size:.2f} GB)")

    merge_time = (datetime.now() - merge_start).total_seconds()
    print(f"[OK] 合并耗时: {merge_time:.1f}秒")

    # 6. 清理（可选）
    if not keep_shards:
        print("\n[6] 清理分片文件...")
        for shard_file in shard_files:
            shard_file.unlink()
        print(f"[OK] 已删除 {len(shard_files)} 个分片文件")
    else:
        print(f"\n[6] 保留分片文件（共 {len(shard_files)} 个）")

    # 7. 总结
    print("\n" + "=" * 80)
    print("生成完成！")
    print("=" * 80)
    print(f"总sessions: {len(all_metadata):,}")
    print(f"最终文件: {final_file}")
    print(f"分片目录: {shard_dir} ({'已保留' if keep_shards else '已清理'})")
    print(f"总耗时: {(datetime.now() - start_time).total_seconds()/60:.1f}分钟")
    print("\n注意:")
    print("  - 索引未构建（节省内存），使用时会自动构建")
    print("  - 使用 scripts/test_search.py 测试搜索功能")
    print("=" * 80)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成微信对话的向量embeddings")
    parser.add_argument(
        "--excel",
        type=str,
        default="聊天记录excel/messages.xlsx",
        help="Excel文件路径（默认: 聊天记录excel/messages.xlsx）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="vector_stores",
        help="输出目录（默认: vector_stores）"
    )
    parser.add_argument(
        "--no-dynamic-batch",
        action="store_true",
        help="禁用动态batch（不推荐）"
    )
    parser.add_argument(
        "--no-keep-shards",
        action="store_true",
        help="合并后删除分片文件（不推荐）"
    )

    args = parser.parse_args()

    generate_all_embeddings(
        excel_file=args.excel,
        output_dir=args.output,
        shard_dir=f"{args.output}/shards",
        use_dynamic_batch=not args.no_dynamic_batch,
        keep_shards=not args.no_keep_shards
    )


if __name__ == "__main__":
    main()
