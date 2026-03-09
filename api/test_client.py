#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 客户端测试示例
"""
import requests
import json
from datetime import datetime


class WeMemoryClient:
    """WeMemory API 客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def recall(
        self,
        context: str,
        recall_type: str = "auto",
        top_k: int = 5,
        min_relevance: float = 0.3
    ):
        """
        记忆联想

        Args:
            context: 当前对话上下文或触发信息
            recall_type: 联想类型（auto/semantic/temporal/people）
            top_k: 返回记忆数量
            min_relevance: 最小相关性阈值

        Returns:
            联想结果
        """
        url = f"{self.base_url}/api/recall"
        payload = {
            "context": context,
            "recall_type": recall_type,
            "top_k": top_k,
            "min_relevance": min_relevance
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def associate_by_topic(self, topic: str, top_k: int = 10):
        """主题关联"""
        url = f"{self.base_url}/api/associate/topic"
        payload = {"topic": topic, "top_k": top_k}

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def associate_by_people(self, person: str, top_k: int = 10):
        """人物关联"""
        url = f"{self.base_url}/api/associate/people"
        payload = {"person": person, "top_k": top_k}

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, top_k: int = 5):
        """简单搜索"""
        url = f"{self.base_url}/api/search"
        payload = {"query": query, "top_k": top_k}

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_stats(self):
        """获取统计信息"""
        url = f"{self.base_url}/api/stats"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def health_check(self):
        """健康检查"""
        url = f"{self.base_url}/api/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


def main():
    """测试示例"""
    print("=" * 70)
    print("WeMemory API 客户端测试")
    print("=" * 70)

    # 初始化客户端
    client = WeMemoryClient()

    # 1. 健康检查
    print("\n[1] 健康检查...")
    health = client.health_check()
    print(f"    状态: {health['status']}")
    print(f"    版本: {health['version']}")
    print(f"    运行时间: {health['uptime_seconds']:.1f}秒")

    # 2. 获取统计信息
    print("\n[2] 向量库统计...")
    stats = client.get_stats()
    print(f"    总记忆数: {stats['total_memories']:,}")
    print(f"    总对话数: {stats['total_conversations']:,}")
    print(f"    索引类型: {stats['index_type']}")

    # 3. 记忆联想（核心功能）
    print("\n[3] 记忆联想测试...")
    context = "讨论AI项目的进展"
    result = client.recall(context, top_k=3)

    print(f"\n    上下文: '{context}'")
    print(f"    联想策略: {result['recall_strategy']}")
    print(f"    处理时间: {result['processing_time_ms']:.1f}ms")
    print(f"    找到 {result['total_count']} 个相关记忆:\n")

    for i, memory in enumerate(result['memories'], 1):
        print(f"    {i}. 相关度: {memory['relevance_score']:.3f}")
        print(f"       原因: {memory['recall_reason']}")
        print(f"       对话: {memory['conversation_name']}")
        print(f"       时间: {datetime.fromtimestamp(memory['timestamp']).strftime('%Y-%m-%d %H:%M')}")
        print(f"       内容: {memory['content'][:80]}...")
        print()

    # 4. 主题关联
    print("\n[4] 主题关联测试...")
    topic_result = client.associate_by_topic("AI", top_k=3)
    print(f"    主题: {topic_result['topic']}")
    print(f"    找到 {topic_result['total_count']} 个相关记忆")

    # 5. 关联信息
    print("\n[5] 联想关联信息...")
    associations = result['associations']
    print(f"    相关人物: {', '.join(associations['people'][:5])}")
    print(f"    相关主题: {associations['topics'][:3]}")
    print(f"    时间上下文: {associations.get('time_context', 'N/A')}")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] 无法连接到 API 服务")
        print("请先启动服务: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
