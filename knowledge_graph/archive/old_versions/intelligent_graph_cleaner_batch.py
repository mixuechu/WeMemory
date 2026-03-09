#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能图谱清理 - 批量LLM判断版本"""

import sys
import io
import json
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 导入Gemini API
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from dotenv import load_dotenv

# 导入图谱管理器
from graph_manager import GraphManager

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv(dotenv_path='../.env')

# Gemini配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

MODEL_NAME = "gemini-2.5-flash"


class IntelligentGraphCleanerBatch:
    """智能图谱清理器 - 批量LLM判断版本"""

    def __init__(self):
        """初始化"""
        self.gm = GraphManager()
        self.model = GenerativeModel(MODEL_NAME)
        self.analysis_results = {
            'auto_actions': [],
            'llm_suggestions': [],
            'needs_review': [],
            'timestamp': datetime.now().isoformat()
        }

    def close(self):
        """关闭连接"""
        self.gm.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 批量LLM调用 ====================

    def batch_ask_llm_merge_decisions(self, person_pairs: List[Dict]) -> List[Dict]:
        """批量判断实体对是否应该合并

        Args:
            person_pairs: [
                {
                    'id': 0,
                    'person1': {name, conversation_name, aliases, relationships_count},
                    'person2': {name, conversation_name, aliases, relationships_count}
                },
                ...
            ]

        Returns:
            [
                {
                    'id': 0,
                    'action': 'merge' | 'keep_separate',
                    'confidence': 0.95,
                    'reason': '理由',
                    'target': 'person1' | 'person2'
                },
                ...
            ]
        """
        if not person_pairs:
            return []

        # 构建批量prompt
        prompt = """你是知识图谱实体去重专家。我会给你一批Person实体对，请判断每一对是否应该合并。

判断规则：
1. 如果是同一个人（大小写不同、昵称/全名、格式不一致），应该合并
2. 如果是不同的人，应该保持独立
3. 如果不确定，建议保持独立（宁可拆分过细）

待判断的实体对：

"""
        # 添加所有实体对
        for pair in person_pairs:
            p1 = pair['person1']
            p2 = pair['person2']
            prompt += f"""
【实体对 {pair['id']}】
  实体1: 姓名={p1['name']}, 对话={p1['conversation_name']}, 别名={p1.get('aliases', [])}, 关系数={p1.get('relationships_count', 0)}
  实体2: 姓名={p2['name']}, 对话={p2['conversation_name']}, 别名={p2.get('aliases', [])}, 关系数={p2.get('relationships_count', 0)}
"""

        prompt += """
请返回JSON数组格式，每个元素对应一个实体对的判断：
[
  {
    "id": 0,
    "action": "merge" 或 "keep_separate",
    "confidence": 0.0-1.0,
    "reason": "简短判断理由（一句话）",
    "target": "person1" 或 "person2" (如果merge，建议保留哪个名字，通常保留首字母大写的、完整的、规范的)
  },
  ...
]

重要：
1. 必须返回所有实体对的判断
2. id必须和输入对应
3. 只返回JSON数组，不要其他内容
"""

        try:
            print(f"  🤖 批量调用LLM判断 {len(person_pairs)} 对实体...")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # 提取JSON
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            results = json.loads(result_text)
            print(f"  ✅ LLM返回 {len(results)} 个判断")
            return results

        except Exception as e:
            print(f"  ❌ 批量LLM调用失败: {e}")
            # 返回默认值（保持独立）
            return [{
                'id': pair['id'],
                'action': 'keep_separate',
                'confidence': 0.0,
                'reason': f'LLM调用失败: {str(e)}',
                'target': None
            } for pair in person_pairs]

    def batch_ask_llm_delete_decisions(self, persons: List[Dict]) -> List[Dict]:
        """批量判断实体是否应该删除

        Args:
            persons: [
                {
                    'id': 0,
                    'name': '...',
                    'conversation_name': '...',
                    'aliases': [...],
                    'relationships_count': 0,
                    'reason': '...'
                },
                ...
            ]

        Returns:
            [
                {
                    'id': 0,
                    'action': 'delete' | 'keep',
                    'confidence': 0.95,
                    'reason': '理由'
                },
                ...
            ]
        """
        if not persons:
            return []

        # 构建批量prompt
        prompt = """你是知识图谱数据清理专家。我会给你一批Person实体，请判断每个实体是否应该删除。

应该删除的情况：
1. 纯数字ID（如：10, 168）- 无法识别具体人物
2. 泛指描述（如：医生、律师、路人、某人）- 太模糊无价值
3. 代词（如：他、她、你）- 不应该作为实体
4. 格式错误（如：的妈妈、第三方）- 缺少所属者
5. 无任何关系且名字无信息量

应该保留的情况：
1. 有明确姓名（中文名、英文名）
2. 有关系且名字有一定信息量
3. 虽然只有少数关系，但是明确的人物（如：古天乐、周润发）

待判断的实体：

"""
        # 添加所有实体
        for person in persons:
            prompt += f"""
【实体 {person['id']}】
  姓名: {person['name']}
  对话: {person['conversation_name']}
  别名: {person.get('aliases', [])}
  关系数: {person.get('relationships_count', 0)}
  原因标记: {person.get('reason', '')}
"""

        prompt += """
请返回JSON数组格式，每个元素对应一个实体的判断：
[
  {
    "id": 0,
    "action": "delete" 或 "keep",
    "confidence": 0.0-1.0,
    "reason": "简短判断理由（一句话）"
  },
  ...
]

重要：
1. 必须返回所有实体的判断
2. id必须和输入对应
3. 只返回JSON数组，不要其他内容
"""

        try:
            print(f"  🤖 批量调用LLM判断 {len(persons)} 个实体...")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # 提取JSON
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            results = json.loads(result_text)
            print(f"  ✅ LLM返回 {len(results)} 个判断")
            return results

        except Exception as e:
            print(f"  ❌ 批量LLM调用失败: {e}")
            # 返回默认值（保留）
            return [{
                'id': person['id'],
                'action': 'keep',
                'confidence': 0.0,
                'reason': f'LLM调用失败，默认保留: {str(e)}'
            } for person in persons]

    # ==================== 分析流程 ====================

    def analyze_duplicates(self, similarity_threshold: float = 0.85, auto_merge_exact: bool = True):
        """分析重复实体"""
        print("\n" + "=" * 80)
        print("【步骤1】分析重复实体")
        print("=" * 80)

        duplicates = self.gm.find_duplicate_persons(similarity_threshold)
        print(f"\n找到 {len(duplicates)} 对可能重复的实体")

        # 分类：自动处理 vs 需要LLM判断
        auto_merge = []
        need_llm = []

        for dup in duplicates:
            p1_name, p1_conv = dup['person1']
            p2_name, p2_conv = dup['person2']

            # 规则1: 大小写完全相同 → 自动合并
            if auto_merge_exact and p1_name.lower() == p2_name.lower() and p1_name != p2_name:
                target = p1_name if p1_name[0].isupper() else p2_name
                source = p2_name if target == p1_name else p1_name

                auto_merge.append({
                    'source': [source, p1_conv],
                    'target': [target, p1_conv],
                    'reason': '大小写不同，自动合并',
                    'confidence': 1.0
                })
            else:
                # 需要LLM判断
                need_llm.append({
                    'person1': dup['person1'],
                    'person2': dup['person2'],
                    'reason': dup['reason']
                })

        print(f"\n分类结果:")
        print(f"  自动合并: {len(auto_merge)} 对")
        print(f"  需要LLM判断: {len(need_llm)} 对")

        # 记录自动操作
        for merge in auto_merge:
            self.analysis_results['auto_actions'].append({
                'type': 'merge',
                **merge
            })

        # 批量LLM判断
        if need_llm:
            # 准备批量输入
            person_pairs = []
            for i, item in enumerate(need_llm):
                p1_name, p1_conv = item['person1']
                p2_name, p2_conv = item['person2']

                person_pairs.append({
                    'id': i,
                    'person1': self._get_person_info(p1_name, p1_conv),
                    'person2': self._get_person_info(p2_name, p2_conv)
                })

            # 批量调用LLM
            decisions = self.batch_ask_llm_merge_decisions(person_pairs)

            # 处理结果
            for decision in decisions:
                idx = decision['id']
                if idx >= len(need_llm):
                    continue

                item = need_llm[idx]
                p1_name, p1_conv = item['person1']
                p2_name, p2_conv = item['person2']

                if decision['action'] == 'merge':
                    target_name = p1_name if decision.get('target') == 'person1' else p2_name
                    source_name = p2_name if target_name == p1_name else p1_name

                    if decision['confidence'] >= 0.9:
                        # 高置信度 → 自动执行
                        self.analysis_results['llm_suggestions'].append({
                            'type': 'merge',
                            'source': [source_name, p1_conv],
                            'target': [target_name, p1_conv],
                            'reason': decision['reason'],
                            'confidence': decision['confidence'],
                            'auto_execute': True
                        })
                    else:
                        # 低置信度 → 需要审核
                        self.analysis_results['needs_review'].append({
                            'type': 'merge',
                            'person1': [p1_name, p1_conv],
                            'person2': [p2_name, p2_conv],
                            'suggestion': decision
                        })

        print(f"\n重复实体分析完成")

    def analyze_low_value_persons(self, auto_delete_rules: bool = True):
        """分析低价值实体"""
        print("\n" + "=" * 80)
        print("【步骤2】分析低价值实体")
        print("=" * 80)

        # 获取候选
        isolated = self.gm.find_isolated_persons()
        low_value = self.gm.find_low_value_persons()

        # 合并去重
        all_candidates = {}
        for p in isolated + low_value:
            key = (p['name'], p['conversation_name'])
            if key not in all_candidates:
                all_candidates[key] = p

        print(f"\n找到 {len(all_candidates)} 个候选实体")

        # 分类：自动处理 vs 需要LLM判断
        auto_delete = []
        need_llm = []

        for key, person in all_candidates.items():
            name, conv = key

            # 规则1: 纯数字ID + 无关系 → 自动删除
            if auto_delete_rules and name.isdigit() and person.get('relationships', 0) == 0:
                auto_delete.append({
                    'person': [name, conv],
                    'reason': '纯数字ID且无任何关系',
                    'confidence': 1.0
                })
                continue

            # 规则2: 孤立节点 + 明显无用 → 自动删除
            if auto_delete_rules and person.get('relationships', 0) == 0:
                useless_patterns = ['第三方', '某人', '某', '未知', '路人', '的妈妈', '的爸爸']
                if any(pattern in name for pattern in useless_patterns):
                    auto_delete.append({
                        'person': [name, conv],
                        'reason': '孤立节点且为泛指/格式错误',
                        'confidence': 1.0
                    })
                    continue

            # 其他情况 → LLM判断
            need_llm.append({
                'name': name,
                'conversation_name': conv,
                'reason': person.get('reason', '')
            })

        print(f"\n分类结果:")
        print(f"  自动删除: {len(auto_delete)} 个")
        print(f"  需要LLM判断: {len(need_llm)} 个")

        # 记录自动操作
        for delete in auto_delete:
            self.analysis_results['auto_actions'].append({
                'type': 'delete',
                **delete
            })

        # 批量LLM判断
        if need_llm:
            # 准备批量输入
            persons = []
            for i, item in enumerate(need_llm):
                person_info = self._get_person_info(item['name'], item['conversation_name'])
                person_info['id'] = i
                person_info['reason'] = item['reason']
                persons.append(person_info)

            # 批量调用LLM
            decisions = self.batch_ask_llm_delete_decisions(persons)

            # 处理结果
            for decision in decisions:
                idx = decision['id']
                if idx >= len(need_llm):
                    continue

                item = need_llm[idx]
                name = item['name']
                conv = item['conversation_name']

                if decision['action'] == 'delete':
                    if decision['confidence'] >= 0.9:
                        # 高置信度 → 自动执行
                        self.analysis_results['llm_suggestions'].append({
                            'type': 'delete',
                            'person': [name, conv],
                            'reason': decision['reason'],
                            'confidence': decision['confidence'],
                            'auto_execute': True
                        })
                    else:
                        # 低置信度 → 需要审核
                        self.analysis_results['needs_review'].append({
                            'type': 'delete',
                            'person': [name, conv],
                            'suggestion': decision
                        })

        print(f"\n低价值实体分析完成")

    def _get_person_info(self, name: str, conversation_name: str) -> Dict:
        """获取Person实体详细信息"""
        with self.gm.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                OPTIONAL MATCH (p)-[r]-()
                RETURN p.name as name,
                       p.conversation_name as conversation_name,
                       p.aliases as aliases,
                       count(r) as relationships_count
            """, name=name, conv=conversation_name)

            record = result.single()
            if record:
                return {
                    'name': record['name'],
                    'conversation_name': record['conversation_name'],
                    'aliases': record['aliases'] or [],
                    'relationships_count': record['relationships_count']
                }
            else:
                return {
                    'name': name,
                    'conversation_name': conversation_name,
                    'aliases': [],
                    'relationships_count': 0
                }

    # ==================== 生成和执行 ====================

    def generate_operations_script(self, output_file: str = "graph_cleanup_operations.json"):
        """生成操作脚本"""
        print("\n" + "=" * 80)
        print("【步骤3】生成操作脚本")
        print("=" * 80)

        merges = []
        deletes = []

        for action in self.analysis_results['auto_actions']:
            if action['type'] == 'merge':
                merges.append({
                    'source': action['source'],
                    'target': action['target'],
                    'reason': action['reason'],
                    'confidence': action['confidence']
                })
            elif action['type'] == 'delete':
                deletes.append({
                    'person': action['person'],
                    'reason': action['reason'],
                    'confidence': action['confidence']
                })

        for suggestion in self.analysis_results['llm_suggestions']:
            if suggestion.get('auto_execute'):
                if suggestion['type'] == 'merge':
                    merges.append({
                        'source': suggestion['source'],
                        'target': suggestion['target'],
                        'reason': suggestion['reason'],
                        'confidence': suggestion['confidence']
                    })
                elif suggestion['type'] == 'delete':
                    deletes.append({
                        'person': suggestion['person'],
                        'reason': suggestion['reason'],
                        'confidence': suggestion['confidence']
                    })

        operations = {
            'merges': [{'source': m['source'], 'target': m['target']} for m in merges],
            'deletes': [d['person'] for d in deletes],
            'aliases': [],
            '_metadata': {
                'generated_at': self.analysis_results['timestamp'],
                'total_merges': len(merges),
                'total_deletes': len(deletes),
                'needs_review': len(self.analysis_results['needs_review'])
            },
            '_details': {
                'merges': merges,
                'deletes': deletes
            }
        }

        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(operations, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 操作脚本已生成: {output_path}")
        print(f"  合并操作: {len(merges)} 个")
        print(f"  删除操作: {len(deletes)} 个")
        print(f"  需要审核: {len(self.analysis_results['needs_review'])} 个")

        # 保存完整报告
        analysis_path = output_path.with_name(f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)

        print(f"  完整报告: {analysis_path}")

        return str(output_path)

    def execute_cleanup(self, operations_file: str, dry_run: bool = False):
        """执行清理"""
        print("\n" + "=" * 80)
        print(f"【步骤4】执行清理 {'(DRY RUN)' if dry_run else ''}")
        print("=" * 80)

        results = self.gm.execute_batch_operations(operations_file, dry_run=dry_run)

        print(f"\n清理结果:")
        print(f"  合并操作: {len(results['merges'])} 个")
        print(f"  删除操作: {len(results['deletes'])} 个")

        if dry_run:
            print(f"\n⚠️  这是DRY RUN，未实际执行。")

        return results


def main():
    """主函数"""
    print("=" * 80)
    print("智能图谱清理工具 - 批量版本")
    print("=" * 80)

    with IntelligentGraphCleanerBatch() as cleaner:
        # 步骤1: 分析重复实体
        cleaner.analyze_duplicates(similarity_threshold=0.85, auto_merge_exact=True)

        # 步骤2: 分析低价值实体
        cleaner.analyze_low_value_persons(auto_delete_rules=True)

        # 步骤3: 生成操作脚本
        operations_file = cleaner.generate_operations_script()

        # 步骤4: DRY RUN
        print("\n" + "=" * 80)
        print("开始DRY RUN（预览影响）")
        print("=" * 80)
        cleaner.execute_cleanup(operations_file, dry_run=True)

        # 询问是否执行
        print("\n" + "=" * 80)
        response = input("是否执行真实清理？(yes/no): ")
        if response.lower() == 'yes':
            cleaner.execute_cleanup(operations_file, dry_run=False)
            print("\n✅ 清理完成！")
        else:
            print("\n已取消。")


if __name__ == '__main__':
    main()
