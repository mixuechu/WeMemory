#!/usr/bin/env python3
"""
数据质量评估工具

功能：
1. 统计对话数量、消息数量分布
2. 评估消息质量（长度、多样性、时间跨度等）
3. 生成质量报告
4. 可视化质量分布

使用方法：
    python scripts/evaluate_data_quality.py data/conversations/chat_data_filtered/
    python scripts/evaluate_data_quality.py data/conversations/cleaned/ --output reports/quality_report.json
    python scripts/evaluate_data_quality.py data/conversations/cleaned/ --compare reports/before.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loader.cleaner import ConversationCleaner


class DataQualityEvaluator:
    """数据质量评估器"""

    def __init__(self):
        self.conversations = []
        self.stats = defaultdict(int)
        self.quality_scores = []
        self.message_lengths = []
        self.message_types = Counter()

    def load_conversations(self, data_dir: Path):
        """加载所有对话文件"""
        json_files = list(data_dir.rglob('*.json'))

        print(f"找到 {len(json_files)} 个 JSON 文件")
        print("正在加载...")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    conversation = json.load(f)

                # 验证格式
                if 'messages' in conversation or 'sessions' in conversation:
                    self.conversations.append({
                        'file': str(json_file),
                        'data': conversation
                    })
            except Exception as e:
                print(f"  ⚠️  跳过文件 {json_file.name}: {e}")

        print(f"✅ 成功加载 {len(self.conversations)} 个对话\n")

    def evaluate(self) -> Dict[str, Any]:
        """执行质量评估"""
        if not self.conversations:
            return {'error': '没有对话数据'}

        print("=" * 60)
        print("开始评估数据质量...")
        print("=" * 60)
        print()

        cleaner = ConversationCleaner()

        for conv_data in self.conversations:
            conversation = conv_data['data']

            # 统计对话
            self.stats['total_conversations'] += 1

            # 获取消息列表（兼容 messages 和 sessions 格式）
            messages = self._extract_messages(conversation)

            if not messages:
                self.stats['empty_conversations'] += 1
                continue

            # 统计消息
            self.stats['total_messages'] += len(messages)

            # 计算质量分数
            quality_score = cleaner._calculate_quality_score(messages)
            self.quality_scores.append(quality_score)

            # 统计消息长度
            for msg in messages:
                content = msg.get('content', '')
                self.message_lengths.append(len(content))

                # 统计消息类型
                msg_type = msg.get('type', 0)
                self.message_types[msg_type] += 1

            # 分类对话质量
            if quality_score >= 0.8:
                self.stats['excellent_conversations'] += 1
            elif quality_score >= 0.6:
                self.stats['good_conversations'] += 1
            elif quality_score >= 0.4:
                self.stats['fair_conversations'] += 1
            else:
                self.stats['poor_conversations'] += 1

        # 计算平均值
        if self.quality_scores:
            self.stats['avg_quality_score'] = sum(self.quality_scores) / len(self.quality_scores)

        if self.message_lengths:
            self.stats['avg_message_length'] = sum(self.message_lengths) / len(self.message_lengths)

        return self._generate_report()

    def _extract_messages(self, conversation: Dict) -> List[Dict]:
        """提取消息列表（兼容不同格式）"""
        # 格式1: 直接的 messages 列表
        if 'messages' in conversation:
            return conversation['messages']

        # 格式2: 分割为 sessions
        if 'sessions' in conversation:
            all_messages = []
            for session in conversation['sessions']:
                all_messages.extend(session.get('messages', []))
            return all_messages

        return []

    def _generate_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        report = {
            'summary': {
                'total_conversations': self.stats['total_conversations'],
                'total_messages': self.stats['total_messages'],
                'empty_conversations': self.stats['empty_conversations'],
                'avg_messages_per_conversation': (
                    self.stats['total_messages'] / self.stats['total_conversations']
                    if self.stats['total_conversations'] > 0 else 0
                ),
                'avg_quality_score': round(self.stats.get('avg_quality_score', 0), 2),
                'avg_message_length': round(self.stats.get('avg_message_length', 0), 2)
            },
            'quality_distribution': {
                'excellent': {
                    'count': self.stats['excellent_conversations'],
                    'percentage': self._percentage(
                        self.stats['excellent_conversations'],
                        self.stats['total_conversations']
                    )
                },
                'good': {
                    'count': self.stats['good_conversations'],
                    'percentage': self._percentage(
                        self.stats['good_conversations'],
                        self.stats['total_conversations']
                    )
                },
                'fair': {
                    'count': self.stats['fair_conversations'],
                    'percentage': self._percentage(
                        self.stats['fair_conversations'],
                        self.stats['total_conversations']
                    )
                },
                'poor': {
                    'count': self.stats['poor_conversations'],
                    'percentage': self._percentage(
                        self.stats['poor_conversations'],
                        self.stats['total_conversations']
                    )
                }
            },
            'message_types': dict(self.message_types),
            'quality_scores': self.quality_scores,
            'message_lengths': self.message_lengths
        }

        return report

    def _percentage(self, part: int, total: int) -> float:
        """计算百分比"""
        return round(part / total * 100, 1) if total > 0 else 0.0

    def print_report(self, report: Dict[str, Any]):
        """打印报告"""
        summary = report['summary']
        quality_dist = report['quality_distribution']

        print("=" * 60)
        print("数据质量评估报告")
        print("=" * 60)
        print()

        print("总体统计:")
        print(f"  对话数量: {summary['total_conversations']}")
        print(f"  消息总数: {summary['total_messages']}")
        print(f"  平均每对话消息数: {summary['avg_messages_per_conversation']:.1f}")
        print(f"  平均质量分数: {summary['avg_quality_score']}")
        print(f"  平均消息长度: {summary['avg_message_length']:.1f} 字符")
        print()

        print("质量分布:")
        print(f"  优秀 (≥0.8): {quality_dist['excellent']['count']} ({quality_dist['excellent']['percentage']}%)")
        print(f"  良好 (0.6-0.8): {quality_dist['good']['count']} ({quality_dist['good']['percentage']}%)")
        print(f"  一般 (0.4-0.6): {quality_dist['fair']['count']} ({quality_dist['fair']['percentage']}%)")
        print(f"  较差 (<0.4): {quality_dist['poor']['count']} ({quality_dist['poor']['percentage']}%)")
        print()

        # 消息类型分布
        print("消息类型分布:")
        type_names = {
            0: '文本',
            1: '图片',
            3: '语音',
            34: '音频',
            43: '视频',
            47: '表情',
            49: '链接/小程序',
            80: '系统消息',
            99: '转账/红包'
        }

        for msg_type, count in sorted(report['message_types'].items()):
            type_name = type_names.get(msg_type, f'未知({msg_type})')
            percentage = self._percentage(count, summary['total_messages'])
            print(f"  {type_name}: {count} ({percentage}%)")
        print()

        # 建议
        print("评估建议:")
        avg_score = summary['avg_quality_score']

        if avg_score >= 0.7:
            print("  ✅ 数据质量优秀，可以直接用于向量生成和知识抽取")
        elif avg_score >= 0.5:
            print("  ✅ 数据质量良好，建议进行基础清洗")
            print("     - 过滤系统消息")
            print("     - 移除重复")
        else:
            print("  ⚠️  数据质量较差，强烈建议进行深度清洗")
            print("     - 使用更严格的质量阈值（0.6-0.7）")
            print("     - 增加最小消息数要求（5-10条）")
            print("     - 考虑手动筛选高质量对话")

        print()


def compare_reports(before_path: Path, after_path: Path):
    """对比两份报告"""
    with open(before_path, 'r', encoding='utf-8') as f:
        before = json.load(f)

    with open(after_path, 'r', encoding='utf-8') as f:
        after = json.load(f)

    print("=" * 60)
    print("清洗效果对比")
    print("=" * 60)
    print()

    # 对话数量变化
    conv_before = before['summary']['total_conversations']
    conv_after = after['summary']['total_conversations']
    conv_change = ((conv_after - conv_before) / conv_before * 100) if conv_before > 0 else 0

    print(f"对话数量: {conv_before} → {conv_after} ({conv_change:+.1f}%)")

    # 消息数量变化
    msg_before = before['summary']['total_messages']
    msg_after = after['summary']['total_messages']
    msg_change = ((msg_after - msg_before) / msg_before * 100) if msg_before > 0 else 0

    print(f"消息总数: {msg_before} → {msg_after} ({msg_change:+.1f}%)")

    # 质量分数变化
    quality_before = before['summary']['avg_quality_score']
    quality_after = after['summary']['avg_quality_score']
    quality_change = ((quality_after - quality_before) / quality_before * 100) if quality_before > 0 else 0

    print(f"平均质量分: {quality_before:.2f} → {quality_after:.2f} ({quality_change:+.1f}%)")
    print()

    # 质量分布对比
    print("质量分布变化:")
    categories = ['excellent', 'good', 'fair', 'poor']
    labels = ['优秀', '良好', '一般', '较差']

    for cat, label in zip(categories, labels):
        pct_before = before['quality_distribution'][cat]['percentage']
        pct_after = after['quality_distribution'][cat]['percentage']
        print(f"  {label}: {pct_before:.1f}% → {pct_after:.1f}%")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='评估对话数据质量',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'data_dir',
        type=str,
        help='数据目录路径'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='输出报告路径（JSON格式）'
    )

    parser.add_argument(
        '--compare',
        type=str,
        help='对比另一份报告（用于清洗前后对比）'
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    # 创建评估器
    evaluator = DataQualityEvaluator()

    # 加载数据
    evaluator.load_conversations(data_dir)

    # 评估
    report = evaluator.evaluate()

    # 打印报告
    evaluator.print_report(report)

    # 保存报告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"✅ 报告已保存到: {output_path}")
        print()

    # 对比报告
    if args.compare:
        compare_path = Path(args.compare)
        if compare_path.exists():
            # 先保存当前报告
            temp_report = Path('/tmp/current_report.json')
            with open(temp_report, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            # 对比
            compare_reports(compare_path, temp_report)
        else:
            print(f"⚠️  对比报告不存在: {compare_path}")


if __name__ == '__main__':
    main()
