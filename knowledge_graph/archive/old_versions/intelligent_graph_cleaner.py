#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能图谱清理 - 使用LLM判断实体合并和删除"""

import sys
import io
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
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


class IntelligentGraphCleaner:
    """智能图谱清理器 - 使用LLM辅助判断"""

    def __init__(self):
        """初始化"""
        self.gm = GraphManager()
        self.model = GenerativeModel(MODEL_NAME)
        self.analysis_results = {
            'auto_actions': [],      # 自动操作（规则判断）
            'llm_suggestions': [],   # LLM建议
            'needs_review': [],      # 需要人工审核
            'timestamp': datetime.now().isoformat()
        }

    def close(self):
        """关闭连接"""
        self.gm.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== LLM调用 ====================

    def ask_llm_merge_decision(self, person1: Dict, person2: Dict) -> Dict:
        """让LLM判断两个实体是否应该合并

        Args:
            person1: {name, conversation_name, aliases, relationships_count, ...}
            person2: {name, conversation_name, aliases, relationships_count, ...}

        Returns:
            {
                "action": "merge" | "keep_separate",
                "confidence": 0.95,
                "reason": "理由",
                "target": "person1" | "person2" (如果merge，保留哪个)
            }
        """
        prompt = f"""你是知识图谱实体去重专家。请判断以下两个Person实体是否应该合并。

实体1:
  姓名: {person1['name']}
  对话: {person1['conversation_name']}
  别名: {person1.get('aliases', [])}
  关系数: {person1.get('relationships_count', 0)}

实体2:
  姓名: {person2['name']}
  对话: {person2['conversation_name']}
  别名: {person2.get('aliases', [])}
  关系数: {person2.get('relationships_count', 0)}

判断规则：
1. 如果是同一个人（大小写不同、昵称/全名、格式不一致），应该合并
2. 如果是不同的人，应该保持独立
3. 如果不确定，建议保持独立（宁可拆分过细）

请返回JSON格式：
{{
  "action": "merge" 或 "keep_separate",
  "confidence": 0.0-1.0,
  "reason": "判断理由",
  "target": "person1" 或 "person2" (如果merge，建议保留哪个名字，通常保留首字母大写的、完整的、规范的)
}}
"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # 提取JSON
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            print(f"  ⚠️  LLM调用失败: {e}")
            return {
                "action": "keep_separate",
                "confidence": 0.0,
                "reason": f"LLM调用失败: {str(e)}",
                "target": None
            }

    def ask_llm_delete_decision(self, person: Dict) -> Dict:
        """让LLM判断实体是否应该删除

        Args:
            person: {name, conversation_name, aliases, relationships_count, ...}

        Returns:
            {
                "action": "delete" | "keep",
                "confidence": 0.95,
                "reason": "理由"
            }
        """
        prompt = f"""你是知识图谱数据清理专家。请判断以下Person实体是否应该删除。

实体信息:
  姓名: {person['name']}
  对话: {person['conversation_name']}
  别名: {person.get('aliases', [])}
  关系数: {person.get('relationships_count', 0)}
  原因标记: {person.get('reason', '')}

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

请返回JSON格式：
{{
  "action": "delete" 或 "keep",
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}
"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # 提取JSON
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            print(f"  ⚠️  LLM调用失败: {e}")
            return {
                "action": "keep",
                "confidence": 0.0,
                "reason": f"LLM调用失败，默认保留: {str(e)}"
            }

    # ==================== 分析流程 ====================

    def analyze_duplicates(self, similarity_threshold: float = 0.85, auto_merge_exact: bool = True):
        """分析重复实体

        Args:
            similarity_threshold: 相似度阈值
            auto_merge_exact: 是否自动合并完全匹配（仅大小写不同）的实体
        """
        print("\n" + "=" * 80)
        print("【步骤1】分析重复实体")
        print("=" * 80)

        duplicates = self.gm.find_duplicate_persons(similarity_threshold)
        print(f"\n找到 {len(duplicates)} 对可能重复的实体")

        auto_merge_count = 0
        llm_judge_count = 0

        for i, dup in enumerate(duplicates, 1):
            p1_name, p1_conv = dup['person1']
            p2_name, p2_conv = dup['person2']

            print(f"\n处理 {i}/{len(duplicates)}: {p1_name} vs {p2_name}")

            # 规则1: 大小写完全相同 → 自动合并
            if auto_merge_exact and p1_name.lower() == p2_name.lower() and p1_name != p2_name:
                target = p1_name if p1_name[0].isupper() else p2_name
                source = p2_name if target == p1_name else p1_name

                self.analysis_results['auto_actions'].append({
                    'type': 'merge',
                    'source': [source, p1_conv],
                    'target': [target, p1_conv],
                    'reason': '大小写不同，自动合并',
                    'confidence': 1.0
                })

                auto_merge_count += 1
                print(f"  ✅ 自动合并: {source} → {target}")
                continue

            # 规则2: 其他情况 → LLM判断
            # 获取实体详细信息
            person1_info = self._get_person_info(p1_name, p1_conv)
            person2_info = self._get_person_info(p2_name, p2_conv)

            print(f"  🤖 调用LLM判断...")
            decision = self.ask_llm_merge_decision(person1_info, person2_info)

            if decision['action'] == 'merge':
                if decision['confidence'] >= 0.9:
                    # 高置信度 → 建议自动执行
                    target_name = p1_name if decision['target'] == 'person1' else p2_name
                    source_name = p2_name if target_name == p1_name else p1_name

                    self.analysis_results['llm_suggestions'].append({
                        'type': 'merge',
                        'source': [source_name, p1_conv],
                        'target': [target_name, p1_conv],
                        'reason': decision['reason'],
                        'confidence': decision['confidence'],
                        'auto_execute': True
                    })
                    print(f"  ✅ LLM建议合并: {source_name} → {target_name} (置信度: {decision['confidence']:.2%})")
                else:
                    # 低置信度 → 需要人工审核
                    self.analysis_results['needs_review'].append({
                        'type': 'merge',
                        'person1': [p1_name, p1_conv],
                        'person2': [p2_name, p2_conv],
                        'suggestion': decision,
                        'reason': decision['reason']
                    })
                    print(f"  ⚠️  需要审核: 置信度较低 ({decision['confidence']:.2%})")
            else:
                print(f"  ℹ️  保持独立: {decision['reason']}")

            llm_judge_count += 1

        print(f"\n重复实体分析完成:")
        print(f"  自动合并: {auto_merge_count} 对")
        print(f"  LLM判断: {llm_judge_count} 对")

    def analyze_low_value_persons(self, auto_delete_rules: bool = True):
        """分析低价值实体

        Args:
            auto_delete_rules: 是否启用自动删除规则
        """
        print("\n" + "=" * 80)
        print("【步骤2】分析低价值实体")
        print("=" * 80)

        # 获取孤立节点和低价值节点
        isolated = self.gm.find_isolated_persons()
        low_value = self.gm.find_low_value_persons()

        # 合并去重
        all_candidates = {}
        for p in isolated + low_value:
            key = (p['name'], p['conversation_name'])
            if key not in all_candidates:
                all_candidates[key] = p

        print(f"\n找到 {len(all_candidates)} 个可能的低价值实体")

        auto_delete_count = 0
        llm_judge_count = 0

        for i, (key, person) in enumerate(all_candidates.items(), 1):
            name, conv = key
            print(f"\n处理 {i}/{len(all_candidates)}: {name} ({person.get('reason', '')})")

            # 规则1: 纯数字ID + 无关系 → 自动删除
            if auto_delete_rules and name.isdigit() and person.get('relationships', 0) == 0:
                self.analysis_results['auto_actions'].append({
                    'type': 'delete',
                    'person': [name, conv],
                    'reason': '纯数字ID且无任何关系',
                    'confidence': 1.0
                })
                auto_delete_count += 1
                print(f"  ✅ 自动删除: 纯数字ID且无关系")
                continue

            # 规则2: 孤立节点 + 明显无用（第三方、某人等）→ 自动删除
            if auto_delete_rules and person.get('relationships', 0) == 0:
                useless_patterns = ['第三方', '某人', '某', '未知', '路人', '的妈妈', '的爸爸']
                if any(pattern in name for pattern in useless_patterns):
                    self.analysis_results['auto_actions'].append({
                        'type': 'delete',
                        'person': [name, conv],
                        'reason': '孤立节点且为泛指/格式错误',
                        'confidence': 1.0
                    })
                    auto_delete_count += 1
                    print(f"  ✅ 自动删除: 孤立节点且无意义")
                    continue

            # 规则3: 其他情况 → LLM判断
            person_info = self._get_person_info(name, conv)
            person_info['reason'] = person.get('reason', '')

            print(f"  🤖 调用LLM判断...")
            decision = self.ask_llm_delete_decision(person_info)

            if decision['action'] == 'delete':
                if decision['confidence'] >= 0.9:
                    # 高置信度 → 建议自动执行
                    self.analysis_results['llm_suggestions'].append({
                        'type': 'delete',
                        'person': [name, conv],
                        'reason': decision['reason'],
                        'confidence': decision['confidence'],
                        'auto_execute': True
                    })
                    print(f"  ✅ LLM建议删除: {decision['reason']} (置信度: {decision['confidence']:.2%})")
                else:
                    # 低置信度 → 需要人工审核
                    self.analysis_results['needs_review'].append({
                        'type': 'delete',
                        'person': [name, conv],
                        'suggestion': decision,
                        'reason': decision['reason']
                    })
                    print(f"  ⚠️  需要审核: 置信度较低 ({decision['confidence']:.2%})")
            else:
                print(f"  ℹ️  保留: {decision['reason']}")

            llm_judge_count += 1

        print(f"\n低价值实体分析完成:")
        print(f"  自动删除: {auto_delete_count} 个")
        print(f"  LLM判断: {llm_judge_count} 个")

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

    # ==================== 生成操作脚本 ====================

    def generate_operations_script(self, output_file: str = "graph_cleanup_operations.json"):
        """生成操作脚本JSON"""
        print("\n" + "=" * 80)
        print("【步骤3】生成操作脚本")
        print("=" * 80)

        # 合并自动操作和LLM建议（高置信度）
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

        # 生成graph_manager兼容的格式
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

        # 保存
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(operations, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 操作脚本已生成: {output_path}")
        print(f"  合并操作: {len(merges)} 个")
        print(f"  删除操作: {len(deletes)} 个")
        print(f"  需要审核: {len(self.analysis_results['needs_review'])} 个")

        # 保存完整分析结果
        analysis_path = output_path.with_name(f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)

        print(f"  完整报告: {analysis_path}")

        return str(output_path)

    # ==================== 执行清理 ====================

    def execute_cleanup(self, operations_file: str, dry_run: bool = False):
        """执行清理操作

        Args:
            operations_file: 操作脚本文件路径
            dry_run: 如果为True，只显示影响，不实际执行
        """
        print("\n" + "=" * 80)
        print(f"【步骤4】执行清理 {'(DRY RUN)' if dry_run else ''}")
        print("=" * 80)

        results = self.gm.execute_batch_operations(operations_file, dry_run=dry_run)

        print(f"\n清理结果:")
        print(f"  合并操作: {len(results['merges'])} 个")
        print(f"  删除操作: {len(results['deletes'])} 个")

        if dry_run:
            print(f"\n⚠️  这是DRY RUN，未实际执行。设置 dry_run=False 执行真实操作。")

        return results


# ==================== 使用示例 ====================

def main():
    """主函数 - 完整的智能清理流程"""
    print("=" * 80)
    print("智能图谱清理工具")
    print("=" * 80)

    with IntelligentGraphCleaner() as cleaner:
        # 步骤1: 分析重复实体
        cleaner.analyze_duplicates(
            similarity_threshold=0.85,
            auto_merge_exact=True  # 自动合并大小写不同的
        )

        # 步骤2: 分析低价值实体
        cleaner.analyze_low_value_persons(
            auto_delete_rules=True  # 启用自动删除规则
        )

        # 步骤3: 生成操作脚本
        operations_file = cleaner.generate_operations_script()

        # 步骤4: 执行清理（先dry run查看影响）
        print("\n" + "=" * 80)
        print("开始DRY RUN（预览影响）")
        print("=" * 80)
        cleaner.execute_cleanup(operations_file, dry_run=True)

        # 询问是否真实执行
        print("\n" + "=" * 80)
        response = input("是否执行真实清理？(yes/no): ")
        if response.lower() == 'yes':
            cleaner.execute_cleanup(operations_file, dry_run=False)
            print("\n✅ 清理完成！")
        else:
            print("\n已取消。操作脚本已保存，可稍后手动执行。")


if __name__ == '__main__':
    main()
