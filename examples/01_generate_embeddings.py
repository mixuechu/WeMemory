#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例1：为微信对话生成向量库

功能：
1. 加载微信聊天记录（JSON格式）
2. 切分为会话片段
3. 生成双向量embeddings
4. 保存向量库到文件
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from dotenv import load_dotenv

# 导入模块
from data_loader import WeChatParser, SessionBuilder
from embedding import DualVectorGenerator
from retrieval import SimpleVectorStore

# 加载环境变量
load_dotenv()


def generate_embeddings_for_conversation(
    conversation_file: Path,
    output_file: Path
):
    """
    为单个对话生成向量库

    Args:
        conversation_file: 微信对话JSON文件
        output_file: 输出向量库文件（.pkl）
    """
    print("="*80)
    print(f"为对话生成向量库: {conversation_file.name}")
    print("="*80)

    # 1. 加载对话
    print("\n[步骤1] 加载对话...")
    messages, metadata = WeChatParser.load_conversation(conversation_file)
    print(f"  对话名称: {metadata['name']}")
    print(f"  总消息数: {len(messages)}")

    # 2. 切分会话片段
    print("\n[步骤2] 切分会话片段...")
    builder = SessionBuilder(
        time_gap_minutes=30,
        min_messages=3,
        max_messages=20
    )
    sessions = builder.split_into_sessions(messages, metadata)
    print(f"  生成会话片段: {len(sessions)}个")

    # 3. 生成双向量
    print("\n[步骤3] 生成双向量embeddings...")
    generator = DualVectorGenerator()
    sessions = generator.generate(sessions, batch_size=10)

    # 4. 保存到向量库
    print("\n[步骤4] 保存向量库...")
    vector_store = SimpleVectorStore(dimension=768)

    for session in sessions:
        vector_store.add(
            content_embedding=session.content_embedding,
            context_embedding=session.context_embedding,
            metadata={
                'session_id': session.session_id,
                'session_type': session.session_type,
                'conversation_name': session.conversation_name,
                'conversation_type': session.conversation_type,
                'start_timestamp': int(session.start_time.timestamp()),
                'end_timestamp': int(session.end_time.timestamp()),
                'year': session.start_time.year,
                'month': session.start_time.month,
                'participants': session.participants,
                'message_count': len(session.messages),
                'content_text': session.content_text,
                'context_text': session.context_text
            }
        )

    vector_store.save(str(output_file))

    print("\n"+"="*80)
    print("完成！向量库已生成")
    print(f"  文件位置: {output_file}")
    print(f"  向量数量: {len(sessions)}")
    print("="*80)


if __name__ == "__main__":
    # 示例：处理alex_li对话
    conversation_file = Path("chat_data_filtered/alex_li/alex_li.json")
    output_file = Path("vector_stores/alex_li_dual.pkl")

    # 确保输出目录存在
    output_file.parent.mkdir(exist_ok=True)

    # 生成向量库
    generate_embeddings_for_conversation(conversation_file, output_file)
