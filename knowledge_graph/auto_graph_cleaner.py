#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动图谱清理器 - 完全自动化版本"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 导入必要的库
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from neo4j import GraphDatabase

# 加载环境变量
load_dotenv(dotenv_path='../.env')

# Gemini配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

MODEL_NAME = "gemini-2.5-flash"


class AutoGraphCleaner:
    """自动图谱清理器"""

    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.driver.verify_connectivity()
        self.model = GenerativeModel(MODEL_NAME)
        self.results = {
            'auto_merges': [],
            'auto_deletes': [],
            'llm_merges': [],
            'llm_deletes': [],
            'timestamp': datetime.now().isoformat()
        }
        print(f"[+] Connected to Neo4j: {NEO4J_URI}")

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 查找问题 ====================

    def find_duplicates(self, threshold=0.85):
        """查找重复实体"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                RETURN p.name as name, p.conversation_name as conv
                ORDER BY conv, name
            """)
            persons = [(r['name'], r['conv']) for r in result]

        from difflib import SequenceMatcher
        from collections import defaultdict

        duplicates = []
        conv_groups = defaultdict(list)
        for name, conv in persons:
            conv_groups[conv].append(name)

        for conv, names in conv_groups.items():
            for i, name1 in enumerate(names):
                for name2 in names[i+1:]:
                    if name1.lower() == name2.lower():
                        duplicates.append({
                            'person1': (name1, conv),
                            'person2': (name2, conv),
                            'type': 'case_diff'
                        })
                    else:
                        similarity = SequenceMatcher(None, name1, name2).ratio()
                        if similarity >= threshold:
                            duplicates.append({
                                'person1': (name1, conv),
                                'person2': (name2, conv),
                                'type': 'similar',
                                'similarity': similarity
                            })

        return duplicates

    def find_low_value_persons(self):
        """查找低价值实体（基础规则筛选）"""
        candidates = []
        seen = set()

        with self.driver.session() as session:
            # 孤立节点
            result = session.run("""
                MATCH (p:Person)
                WHERE NOT (p)-[]-()
                RETURN p.name as name, p.conversation_name as conv
            """)
            for r in result:
                key = (r['name'], r['conv'])
                if key not in seen:
                    candidates.append({
                        'name': r['name'],
                        'conv': r['conv'],
                        'relationships': 0,
                        'reason': 'isolated'
                    })
                    seen.add(key)

            # 关系数少的节点
            result = session.run("""
                MATCH (p:Person)-[r]-()
                WITH p, count(r) as rel_count
                WHERE rel_count <= 2
                RETURN p.name as name, p.conversation_name as conv, rel_count
            """)
            for r in result:
                key = (r['name'], r['conv'])
                if key not in seen:
                    candidates.append({
                        'name': r['name'],
                        'conv': r['conv'],
                        'relationships': r['rel_count'],
                        'reason': 'low_rel'
                    })
                    seen.add(key)

        return candidates

    def get_all_persons_for_generic_check(self):
        """获取所有Person节点用于泛指词检查"""
        all_persons = []

        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[r]-()
                WITH p, count(r) as rel_count
                RETURN p.name as name, p.conversation_name as conv, rel_count
                ORDER BY rel_count DESC
            """)

            for r in result:
                all_persons.append({
                    'name': r['name'],
                    'conv': r['conv'],
                    'relationships': r['rel_count']
                })

        return all_persons

    # ==================== 自动规则 ====================

    def auto_process_duplicates(self, duplicates):
        """自动处理重复实体"""
        case_diff = [d for d in duplicates if d['type'] == 'case_diff']
        similar = [d for d in duplicates if d['type'] == 'similar']

        print(f"\n[1] Processing duplicates: {len(duplicates)} pairs")
        print(f"    - Case diff (auto): {len(case_diff)}")
        print(f"    - Similar (LLM): {len(similar)}")

        # 自动合并大小写
        for dup in case_diff:
            p1, p2 = dup['person1'][0], dup['person2'][0]
            target = p1 if p1[0].isupper() else p2
            source = p2 if target == p1 else p1
            conv = dup['person1'][1]

            self.results['auto_merges'].append({
                'source': [source, conv],
                'target': [target, conv],
                'reason': 'case_diff'
            })

        return similar

    def auto_process_low_value(self, candidates):
        """自动处理低价值实体（仅基本规则）"""
        auto_delete = []
        need_llm = []

        for c in candidates:
            # 规则1: 纯数字 + 孤立节点
            if c['name'].isdigit() and c['relationships'] == 0:
                auto_delete.append(c)
                continue

            # 其他都交给LLM判断
            need_llm.append(c)

        print(f"\n[2] Processing low-value entities: {len(candidates)} candidates")
        print(f"    - Auto delete (pure numbers): {len(auto_delete)}")
        print(f"    - Need LLM: {len(need_llm)}")

        for c in auto_delete:
            self.results['auto_deletes'].append({
                'person': [c['name'], c['conv']],
                'reason': 'isolated_number'
            })

        return need_llm

    # ==================== LLM批量判断 ====================

    def llm_judge_merges(self, pairs):
        """LLM批量判断合并"""
        if not pairs:
            return

        print(f"\n[3] LLM judging {len(pairs)} merge candidates...")

        # 构建批量prompt
        prompt = """你是知识图谱实体去重专家。请判断以下Person实体对是否应该合并。

规则：
1. 同一个人（大小写、昵称/全名、格式不一致）→ 合并
2. 不同的人 → 保持独立
3. 不确定 → 保持独立

待判断的实体对：

"""
        person_pairs = []
        for i, pair in enumerate(pairs):
            p1_name, p1_conv = pair['person1']
            p2_name, p2_conv = pair['person2']

            person_pairs.append({
                'id': i,
                'person1': {'name': p1_name, 'conversation_name': p1_conv},
                'person2': {'name': p2_name, 'conversation_name': p2_conv}
            })

            prompt += f"""
【实体对 {i}】
  实体1: {p1_name} ({p1_conv})
  实体2: {p2_name} ({p2_conv})
"""

        prompt += """
返回JSON数组，每个元素：
{
  "id": 序号,
  "action": "merge" 或 "keep_separate",
  "confidence": 0.0-1.0,
  "reason": "简短理由（一句话）",
  "target": "person1" 或 "person2" (如果merge，保留哪个)
}

只返回JSON数组，不要其他内容。
"""

        # 调用LLM
        response = self.model.generate_content(prompt)
        result_text = response.text.strip()

        # 提取JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        decisions = json.loads(result_text)

        # 处理结果
        for decision in decisions:
            idx = decision['id']
            if idx >= len(pairs):
                continue

            pair = pairs[idx]
            p1_name, p1_conv = pair['person1']
            p2_name, p2_conv = pair['person2']

            if decision['action'] == 'merge' and decision['confidence'] >= 0.9:
                target_name = p1_name if decision.get('target') == 'person1' else p2_name
                source_name = p2_name if target_name == p1_name else p1_name

                self.results['llm_merges'].append({
                    'source': [source_name, p1_conv],
                    'target': [target_name, p1_conv],
                    'reason': decision['reason'],
                    'confidence': decision['confidence']
                })

        print(f"    - LLM suggested {len(self.results['llm_merges'])} merges")

    def llm_judge_generic_persons(self, all_persons):
        """LLM批量判断泛指/无意义实体"""
        if not all_persons:
            return []

        print(f"\n[3.5] LLM judging {len(all_persons)} persons for generic/meaningless names...")

        # 构建批量prompt
        prompt = """你是知识图谱质量专家。请从以下Person实体列表中，识别出所有**泛指/无意义**的实体。

**应该删除的泛指/无意义实体**：

1. **代词和泛指词**：
   - 代词：他、她、你、我、他们、她们、人家、别人、有人、谁、那个人
   - 泛指：某人、某女士、某男士、某个人、某位、第三方、第三方人物、未知人物、匿名人士
   - 描述性泛指：对话中的对方、那位朋友、某个同事、那个同学、某位亲戚、一个朋友

2. **占位符和无意义标识**：
   - 英文占位符：Unnamed Person、Unnamed Male、Unnamed Female、Someone、Person A、Person B
   - 中文占位符：无名氏、不明人士、未指明人物、神秘人、匿名者
   - 带编号：朋友A、朋友B、同学A、室友A、女性A、男士B

3. **单独关系词（缺少所属者）**：
   - 朋友、同事、同学、室友、老师、医生、律师、司机（单独出现，没有"XX的"前缀）
   - 注意：如果是"张三的朋友"、"吉月的同学"则**不删除**（有明确归属）

**应该保留的有价值实体**：
- 有明确姓名：张三、Hunter、米雪川
- 有明确归属关系：吉月的妈妈、米雪川的弟弟、张三的朋友
- 注意：即使关系数为0，只要有明确姓名或归属，就保留

待判断的实体：

"""
        # 添加所有实体
        for i, p in enumerate(all_persons):
            prompt += f"【{i}】{p['name']} (对话:{p['conv']}, 关系数:{p['relationships']})\n"

        prompt += """
返回JSON数组，只包含**应该删除**的实体ID：
[
  {
    "id": 实体序号,
    "name": "实体名",
    "reason": "删除理由（代词/泛指/占位符/单独关系词）",
    "confidence": 0.0-1.0
  }
]

只返回JSON数组，不要其他内容。
"""

        # 调用LLM
        response = self.model.generate_content(prompt)
        result_text = response.text.strip()

        # 提取JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        try:
            decisions = json.loads(result_text)
        except:
            print(f"    - LLM response parsing failed, skipping generic check")
            return []

        # 处理结果
        generic_to_delete = []
        for decision in decisions:
            idx = decision['id']
            if idx >= len(all_persons):
                continue

            p = all_persons[idx]

            if decision['confidence'] >= 0.85:  # 高置信度才删除
                generic_to_delete.append({
                    'name': p['name'],
                    'conv': p['conv'],
                    'relationships': p['relationships'],
                    'reason': decision['reason'],
                    'confidence': decision['confidence']
                })

        print(f"    - LLM identified {len(generic_to_delete)} generic/meaningless persons")
        return generic_to_delete

    def llm_judge_deletes(self, candidates):
        """LLM批量判断删除"""
        if not candidates:
            return

        print(f"\n[4] LLM judging {len(candidates)} delete candidates...")

        # 构建批量prompt
        prompt = """你是知识图谱清理专家。请判断以下Person实体是否应该删除。

应该删除：
1. 纯数字ID、泛指词、代词
2. 无任何关系且名字无意义

应该保留：
1. 有明确姓名
2. 有关系且名字有意义

待判断的实体：

"""
        persons = []
        for i, c in enumerate(candidates):
            persons.append({
                'id': i,
                'name': c['name'],
                'conversation_name': c['conv'],
                'relationships_count': c['relationships']
            })

            prompt += f"""
【实体 {i}】
  姓名: {c['name']} ({c['conv']})
  关系数: {c['relationships']}
  原因: {c['reason']}
"""

        prompt += """
返回JSON数组，每个元素：
{
  "id": 序号,
  "action": "delete" 或 "keep",
  "confidence": 0.0-1.0,
  "reason": "简短理由"
}

只返回JSON数组。
"""

        # 调用LLM
        response = self.model.generate_content(prompt)
        result_text = response.text.strip()

        # 提取JSON
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()

        decisions = json.loads(result_text)

        # 处理结果
        for decision in decisions:
            idx = decision['id']
            if idx >= len(candidates):
                continue

            c = candidates[idx]

            if decision['action'] == 'delete' and decision['confidence'] >= 0.9:
                self.results['llm_deletes'].append({
                    'person': [c['name'], c['conv']],
                    'reason': decision['reason'],
                    'confidence': decision['confidence']
                })

        print(f"    - LLM suggested {len(self.results['llm_deletes'])} deletes")

    # ==================== 执行清理 ====================

    def execute_merges(self, merges, dry_run=False):
        """执行合并操作"""
        if not merges:
            return

        print(f"\n[5] Executing {len(merges)} merges {'(DRY RUN)' if dry_run else ''}...")

        for merge in merges:
            src_name, src_conv = merge['source']
            tgt_name, tgt_conv = merge['target']

            if dry_run:
                print(f"    - Would merge: {src_name} -> {tgt_name}")
                continue

            # 执行合并
            with self.driver.session() as session:
                # 获取关系类型
                rel_types = session.run("""
                    MATCH (s:Person {name: $src, conversation_name: $conv})-[r]-()
                    RETURN DISTINCT type(r) as rel_type
                """, src=src_name, conv=src_conv)

                for record in rel_types:
                    rel_type = record['rel_type']

                    # 转移出边
                    session.run(f"""
                        MATCH (s:Person {{name: $src, conversation_name: $conv}})-[r:{rel_type}]->(other)
                        MATCH (t:Person {{name: $tgt, conversation_name: $conv}})
                        WHERE NOT (t)-[:{rel_type}]->(other)
                        MERGE (t)-[r2:{rel_type}]->(other)
                        SET r2 = properties(r)
                        DELETE r
                    """, src=src_name, tgt=tgt_name, conv=src_conv)

                    # 转移入边
                    session.run(f"""
                        MATCH (other)-[r:{rel_type}]->(s:Person {{name: $src, conversation_name: $conv}})
                        MATCH (t:Person {{name: $tgt, conversation_name: $conv}})
                        WHERE NOT (other)-[:{rel_type}]->(t)
                        MERGE (other)-[r2:{rel_type}]->(t)
                        SET r2 = properties(r)
                        DELETE r
                    """, src=src_name, tgt=tgt_name, conv=src_conv)

                # 添加别名
                session.run("""
                    MATCH (t:Person {name: $tgt, conversation_name: $conv})
                    SET t.aliases = coalesce(t.aliases, []) + $src
                """, tgt=tgt_name, conv=tgt_conv, src=src_name)

                # 删除源节点
                session.run("""
                    MATCH (s:Person {name: $src, conversation_name: $conv})
                    DELETE s
                """, src=src_name, conv=src_conv)

            print(f"    - Merged: {src_name} -> {tgt_name}")

    def execute_deletes(self, deletes, dry_run=False):
        """执行删除操作"""
        if not deletes:
            return

        print(f"\n[6] Executing {len(deletes)} deletes {'(DRY RUN)' if dry_run else ''}...")

        for delete in deletes:
            name, conv = delete['person']

            if dry_run:
                print(f"    - Would delete: {name}")
                continue

            with self.driver.session() as session:
                session.run("""
                    MATCH (p:Person {name: $name, conversation_name: $conv})
                    DETACH DELETE p
                """, name=name, conv=conv)

            print(f"    - Deleted: {name}")

    # ==================== 主流程 ====================

    def run(self, dry_run=False):
        """运行完整清理流程"""
        print("=" * 80)
        print("Auto Graph Cleaner - Fully Automated")
        print("=" * 80)

        # 1. 查找问题
        duplicates = self.find_duplicates()
        low_value = self.find_low_value_persons()

        # 2. 自动处理（基础规则）
        similar_pairs = self.auto_process_duplicates(duplicates)
        llm_delete_candidates = self.auto_process_low_value(low_value)

        # 3. LLM判断泛指/无意义实体（从全部Person中检查）
        all_persons = self.get_all_persons_for_generic_check()
        generic_persons = self.llm_judge_generic_persons(all_persons)

        # 将泛指词加入删除列表
        for p in generic_persons:
            self.results['llm_deletes'].append({
                'person': [p['name'], p['conv']],
                'reason': f"泛指/无意义: {p['reason']}",
                'confidence': p['confidence']
            })

        # 4. LLM批量判断合并和删除
        self.llm_judge_merges(similar_pairs)
        self.llm_judge_deletes(llm_delete_candidates)

        # 5. 执行清理
        all_merges = self.results['auto_merges'] + self.results['llm_merges']
        all_deletes = self.results['auto_deletes'] + self.results['llm_deletes']

        self.execute_merges(all_merges, dry_run=dry_run)
        self.execute_deletes(all_deletes, dry_run=dry_run)

        # 6. 保存结果
        output_file = f"cleanup_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 80}")
        print(f"Summary:")
        print(f"  Auto merges: {len(self.results['auto_merges'])}")
        print(f"  LLM merges: {len(self.results['llm_merges'])}")
        print(f"  Auto deletes: {len(self.results['auto_deletes'])}")
        print(f"  LLM deletes: {len(self.results['llm_deletes'])}")
        print(f"    - Including generic/meaningless: {len(generic_persons)}")
        print(f"  Results saved: {output_file}")
        print(f"{'=' * 80}")


if __name__ == '__main__':
    import sys

    dry_run = '--dry-run' in sys.argv

    with AutoGraphCleaner() as cleaner:
        cleaner.run(dry_run=dry_run)
