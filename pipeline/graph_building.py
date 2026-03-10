#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph Building Pipeline - Complete Implementation

Generates natural language triplets from knowledge graph and creates embeddings.
"""
import sys
import json
import pickle
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.base import BasePipeline
from config.loader import load_config

# 加载环境变量
env_file = project_root / '.env'
load_dotenv(env_file)


class GraphBuildingPipeline(BasePipeline):
    """图谱构建 Pipeline - 生成三元组并构建向量索引"""

    # 关系类型语义映射
    RELATION_SEMANTICS = {
        # 家庭关系
        'HAS_PARENT': '父母,亲子,家人,家庭',
        'HAS_CHILD': '孩子,亲子,家人,家庭',
        'HAS_SPOUSE': '配偶,夫妻,老公老婆,家人,家庭',
        'HAS_GRANDPARENT': '爷爷奶奶,外公外婆,祖辈,家人,家庭',
        'HAS_GRANDCHILD': '孙子孙女,外孙,后辈,家人,家庭',
        'HAS_SIBLING': '兄弟姐妹,手足,家人,家庭',
        'HAS_COUSIN': '表兄弟,堂兄弟,亲戚,家庭',
        'HAS_AUNT': '姑姑,姨妈,阿姨,亲戚,家庭',
        'HAS_UNCLE': '叔叔,伯伯,舅舅,亲戚,家庭',
        'HAS_NEPHEW': '侄子侄女,外甥,亲戚,家庭',
        'HAS_RELATIVE': '亲戚,家人,家庭',
        'HAS_PARENT_SIBLING': '叔伯姑舅姨,亲戚,家庭',
        'FAMILY_OF': '家人,家庭,亲属',

        # 工作关系
        'WORKS_AT': '工作,公司,职场,事业',
        'WORKS_AS': '职业,职位,工作,事业',
        'WORKS_WITH': '同事,合作,工作,职场',
        'WORKED_AT': '曾经工作,前公司,职场',

        # 地点关系
        'LOCATED_AT': '地点,位置,所在地',

        # 社交关系
        'FRIENDS_WITH': '朋友,社交',
        'KNOWS': '认识,熟人',
        'HAS_PARTNER': '伴侣,恋人,情侣',
        'HAS_EX_PARTNER': '前任,前男女友',

        # 事件关系
        'PARTICIPATED_IN': '参与,参加,活动',
        'DISCUSSED_WITH': '讨论,交流,对话',
        'ORGANIZES': '组织,举办,策划',
        'ATTENDS': '出席,参加,到场',
    }

    def __init__(self, config=None, config_file: str = None, **kwargs):
        """初始化 Pipeline

        Args:
            config: 配置字典（可选）
            config_file: 配置文件路径（可选）
            **kwargs: 额外参数
        """
        # 加载配置
        if config is None:
            config = load_config(config_file)

        super().__init__(
            name="graph_building",
            config=config,
            **kwargs
        )

        self.config = config

        # 设置路径
        self.input_file = Path(config.get('paths', {}).get('knowledge_graph_curated', 'data/knowledge_graph/curated_kg.json'))
        self.output_dir = Path(config.get('paths', {}).get('knowledge_graph', 'data/knowledge_graph'))
        self.vector_output_dir = Path(config.get('paths', {}).get('vector_stores', 'vector_stores')) / 'triplets'

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vector_output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 Vertex AI
        self._init_vertex_ai()

        print(f"[Graph Building Pipeline] 初始化完成")
        print(f"  输入文件: {self.input_file}")
        print(f"  输出目录: {self.output_dir}")
        print(f"  向量输出: {self.vector_output_dir}")
        print(f"  Embedding模型: text-multilingual-embedding-002")

    def _init_vertex_ai(self):
        """初始化 Vertex AI 客户端"""
        try:
            from google.oauth2 import service_account
            import vertexai
            from vertexai.language_models import TextEmbeddingModel

            # 从环境变量读取配置
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            region = os.getenv('GOOGLE_REGION', 'us-central1')
            credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

            if not all([project_id, credentials_json]):
                raise ValueError("Missing Google Cloud credentials in .env")

            # 创建凭证
            creds_dict = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)

            # 初始化 Vertex AI
            vertexai.init(project=project_id, location=region, credentials=credentials)

            # 加载模型
            self.embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")

            print(f"  ✓ Vertex AI 初始化成功 (项目: {project_id})")

        except Exception as e:
            print(f"  ✗ Vertex AI 初始化失败: {e}")
            print("  将跳过embedding生成")
            self.embedding_model = None

    def get_items(self) -> List[str]:
        """获取待处理的项目

        Returns:
            单项列表（因为只处理一个知识图谱文件）
        """
        if not self.input_file.exists():
            print(f"[WARNING] 知识图谱文件不存在: {self.input_file}")
            print("          请先运行 knowledge_extraction 步骤")
            return []

        return ['build_graph']

    def process_item(self, item: str) -> Dict[str, Any]:
        """构建图谱：生成三元组并创建向量索引

        Args:
            item: 项目标识

        Returns:
            处理结果字典
        """
        try:
            # 1. 加载知识图谱
            print(f"\n{'='*70}")
            print(f"[1/5] 加载知识图谱数据")
            print(f"{'='*70}")

            with open(self.input_file, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)

            # 检查数据格式：扁平格式 vs conversations数组格式
            if 'people' in kg_data:
                # 扁平格式
                people = kg_data.get('people', [])
                relationships = kg_data.get('relationships', [])
                events = kg_data.get('events', [])
                print(f"✓ 加载完成 (扁平格式)")
                print(f"  - People: {len(people)}")
                print(f"  - Relationships: {len(relationships)}")
                print(f"  - Events: {len(events)}")

                if not (relationships or events):
                    return {
                        'status': 'skipped',
                        'reason': 'no_relationships_or_events'
                    }

                # 从扁平格式创建conversations结构用于别名映射
                conversations = []
            else:
                # conversations数组格式
                conversations = kg_data.get('conversations', [])
                print(f"✓ 加载完成 (conversations格式): {len(conversations)} 个对话")

                if not conversations:
                    return {
                        'status': 'skipped',
                        'reason': 'no_conversations'
                    }

                people = []
                relationships = []
                events = []

            # 2. 构建实体别名映射
            print(f"\n{'='*70}")
            print(f"[2/5] 构建实体别名映射")
            print(f"{'='*70}")

            # 对于扁平格式,直接从people构建别名映射
            alias_map = self._build_alias_map_from_people(people) if people else {}
            print(f"✓ 别名映射完成: {len(alias_map)} 个实体")

            # 3. 生成三元组
            print(f"\n{'='*70}")
            print(f"[3/5] 生成自然语言三元组")
            print(f"{'='*70}")

            # 对于扁平格式,直接从relationships和events生成三元组
            triplets = self._generate_triplets_from_flat(relationships, events, alias_map)
            print(f"✓ 三元组生成完成: {len(triplets)} 条记录")

            # 保存三元组
            triplets_data = {
                'records': triplets,
                'metadata': {
                    'total_records': len(triplets),
                    'total_conversations': len(conversations),
                    'created_at': datetime.now().isoformat(),
                    'source_file': str(self.input_file)
                }
            }

            triplets_file = self.output_dir / "triplets.json"
            with open(triplets_file, 'w', encoding='utf-8') as f:
                json.dump(triplets_data, f, ensure_ascii=False, indent=2)
            print(f"  保存到: {triplets_file}")

            # 4. 生成 Embeddings
            if self.embedding_model is None:
                print(f"\n[WARNING] Embedding模型未初始化，跳过向量生成")
                return {
                    'status': 'partial_success',
                    'triplets': len(triplets),
                    'embeddings': 0
                }

            print(f"\n{'='*70}")
            print(f"[4/5] 生成 Embeddings")
            print(f"{'='*70}")

            embeddings = self._generate_embeddings(triplets)
            print(f"✓ Embeddings生成完成: {len(embeddings)} 个向量")

            # 5. 构建 FAISS 索引
            print(f"\n{'='*70}")
            print(f"[5/5] 构建 FAISS 索引")
            print(f"{'='*70}")

            faiss_index = self._build_faiss_index(embeddings)

            if faiss_index is not None:
                print(f"✓ FAISS索引构建完成")
            else:
                print(f"✗ FAISS未安装，跳过索引构建")

            # 保存 Embeddings 和索引
            self._save_embeddings(embeddings, triplets, faiss_index)

            # 统计信息
            print(f"\n{'='*70}")
            print(f"图谱构建完成")
            print(f"{'='*70}")
            print(f"对话数: {len(conversations)}")
            print(f"三元组: {len(triplets)}")
            print(f"向量维度: 768")
            print(f"输出:")
            print(f"  - 三元组: {triplets_file}")
            print(f"  - 向量库: {self.vector_output_dir}/")

            return {
                'status': 'success',
                'triplets': len(triplets),
                'embeddings': len(embeddings),
                'conversations': len(conversations)
            }

        except Exception as e:
            print(f"[ERROR] 图谱构建失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _build_alias_map_from_people(self, people: List[Dict]) -> Dict[str, List[str]]:
        """从人物列表构建实体别名映射（用于扁平格式）

        Args:
            people: 人物列表

        Returns:
            实体到别名列表的映射
        """
        alias_map = {}

        for person in people:
            name = person.get('name', '')
            if not name:
                continue

            aliases = person.get('aliases', [])
            all_names = [name] + [a for a in aliases if a]

            # 更新映射
            for n in all_names:
                if n not in alias_map:
                    alias_map[n] = []
                for other in all_names:
                    if other != n and other not in alias_map[n]:
                        alias_map[n].append(other)

        return alias_map

    def _generate_triplets_from_flat(
        self,
        relationships: List[Dict],
        events: List[Dict],
        alias_map: Dict[str, List[str]]
    ) -> List[Dict]:
        """从扁平的relationships和events列表生成三元组

        Args:
            relationships: 关系列表
            events: 事件列表
            alias_map: 别名映射

        Returns:
            三元组列表
        """
        triplets = []
        triplet_id = 0

        # 1. 处理关系三元组
        for rel in relationships:
            conv_name = rel.get('source_conversation', 'Unknown')
            triplet = self._create_relationship_triplet(
                rel, conv_name, alias_map, triplet_id
            )
            if triplet:
                triplets.append(triplet)
                triplet_id += 1

        # 2. 处理事件三元组
        for event in events:
            conv_name = event.get('source_conversation', 'Unknown')
            triplet = self._create_event_triplet(
                event, conv_name, alias_map, triplet_id
            )
            if triplet:
                triplets.append(triplet)
                triplet_id += 1

        return triplets

    def _build_alias_map(self, conversations: List[Dict]) -> Dict[str, List[str]]:
        """构建实体别名映射

        Args:
            conversations: 对话列表

        Returns:
            实体到别名列表的映射
        """
        alias_map = {}

        for conv in conversations:
            # 从人物中提取别名
            people = conv.get('people', [])
            for person in people:
                name = person.get('name', '')
                if not name:
                    continue

                aliases = person.get('aliases', [])
                all_names = [name] + aliases

                # 更新映射
                for n in all_names:
                    if n not in alias_map:
                        alias_map[n] = []
                    for other in all_names:
                        if other != n and other not in alias_map[n]:
                            alias_map[n].append(other)

        return alias_map

    def _generate_triplets(self, conversations: List[Dict], alias_map: Dict[str, List[str]]) -> List[Dict]:
        """生成自然语言三元组

        Args:
            conversations: 对话列表
            alias_map: 实体别名映射

        Returns:
            三元组列表
        """
        triplets = []
        triplet_id = 0

        for conv in conversations:
            conv_name = conv.get('conversation_name', 'Unknown')

            # 1. 处理关系三元组
            relationships = conv.get('relationships', [])
            for rel in relationships:
                triplet = self._create_relationship_triplet(
                    rel, conv_name, alias_map, triplet_id
                )
                if triplet:
                    triplets.append(triplet)
                    triplet_id += 1

            # 2. 处理事件三元组
            events = conv.get('events', [])
            for event in events:
                triplet = self._create_event_triplet(
                    event, conv_name, alias_map, triplet_id
                )
                if triplet:
                    triplets.append(triplet)
                    triplet_id += 1

            # 3. 处理参与者关系（如果没有完整的关系数据）
            if not relationships and not events:
                participants = conv.get('participants', [])
                for participant in participants:
                    triplet = {
                        'id': triplet_id,
                        'type': 'relationship',
                        'text': f"{participant} 参与了对话 {conv_name}",
                        'searchable_text': f"{participant} 参与了对话 {conv_name}",
                        'metadata': {
                            'subject': participant,
                            'relation_type': 'PARTICIPATES_IN',
                            'object': conv_name,
                            'conversation_name': conv_name
                        }
                    }
                    triplets.append(triplet)
                    triplet_id += 1

        return triplets

    def _create_relationship_triplet(
        self,
        relationship: Dict,
        conv_name: str,
        alias_map: Dict[str, List[str]],
        triplet_id: int
    ) -> Dict:
        """创建关系三元组

        Args:
            relationship: 关系数据
            conv_name: 对话名称
            alias_map: 别名映射
            triplet_id: 三元组ID

        Returns:
            三元组字典
        """
        rel_type = relationship.get('type', '')
        source = relationship.get('source', '')
        target = relationship.get('target', '')

        if not all([rel_type, source, target]):
            return None

        # 生成自然语言描述
        text = self._format_relationship(rel_type, source, target)

        # 添加语义增强
        enhancements = []

        # 添加语义标签
        if rel_type in self.RELATION_SEMANTICS:
            semantics = self.RELATION_SEMANTICS[rel_type]
            enhancements.append(f"语义标签:{semantics}")

        # 添加涉及实体
        enhancements.append(f"涉及实体:{source},{target}")

        # 添加别名
        for entity in [source, target]:
            if entity in alias_map and alias_map[entity]:
                other_names = alias_map[entity][:3]
                enhancements.append(f"{entity}别名:{','.join(other_names)}")

        # 生成searchable_text
        if enhancements:
            searchable_text = f"{text} [{'; '.join(enhancements)}]"
        else:
            searchable_text = text

        return {
            'id': triplet_id,
            'type': 'relationship',
            'text': text,
            'searchable_text': searchable_text,
            'metadata': {
                'subject': source,
                'relation_type': rel_type,
                'object': target,
                'conversation_name': conv_name
            }
        }

    def _create_event_triplet(
        self,
        event: Dict,
        conv_name: str,
        alias_map: Dict[str, List[str]],
        triplet_id: int
    ) -> Dict:
        """创建事件三元组

        Args:
            event: 事件数据
            conv_name: 对话名称
            alias_map: 别名映射
            triplet_id: 三元组ID

        Returns:
            三元组字典
        """
        event_name = event.get('name', '')
        event_type = event.get('type', '')
        participants = event.get('participants', [])
        location = event.get('location', '')
        description = event.get('description', '')
        time_ref = event.get('time_reference', '')

        if not event_name:
            return None

        # 生成自然语言描述
        text_parts = []

        if participants:
            text_parts.append(f"{', '.join(participants[:5])}")

        text_parts.append("参与了" if participants else "发生了")
        text_parts.append(event_name)

        if location:
            text_parts.append(f"在{location}")

        text = ' '.join(text_parts)

        # 添加语义增强
        enhancements = []

        if event_type:
            enhancements.append(f"事件类型:{event_type}")

        if time_ref:
            time_map = {'past': '过去', 'present': '现在', 'future': '将来'}
            time_desc = time_map.get(time_ref, time_ref)
            enhancements.append(f"时间:{time_desc}")

        if description:
            enhancements.append(f"描述:{description[:50]}")

        # 参与者别名
        for p in participants[:5]:
            if p in alias_map and alias_map[p]:
                other_names = alias_map[p][:3]
                enhancements.append(f"{p}别名:{','.join(other_names)}")

        # 生成searchable_text
        if enhancements:
            searchable_text = f"{text} [{'; '.join(enhancements)}]"
        else:
            searchable_text = text

        return {
            'id': triplet_id,
            'type': 'event',
            'text': text,
            'searchable_text': searchable_text,
            'metadata': {
                'event_name': event_name,
                'event_type': event_type,
                'participants': participants,
                'location': location,
                'description': description,
                'time_reference': time_ref,
                'conversation_name': conv_name
            }
        }

    def _format_relationship(self, rel_type: str, source: str, target: str) -> str:
        """格式化关系为自然语言

        Args:
            rel_type: 关系类型
            source: 源实体
            target: 目标实体

        Returns:
            自然语言描述
        """
        # 关系类型到中文的映射
        rel_map = {
            'KNOWS': '认识',
            'FRIENDS_WITH': '是朋友',
            'FAMILY_OF': '是家人',
            'HAS_PARENT': '的父母是',
            'HAS_CHILD': '的孩子是',
            'HAS_SPOUSE': '的配偶是',
            'HAS_SIBLING': '的兄弟姐妹是',
            'WORKS_AT': '工作于',
            'WORKS_WITH': '是同事',
            'PARTICIPATED_IN': '参与了',
            'DISCUSSED_WITH': '讨论了',
            'LOCATED_AT': '位于',
        }

        relation = rel_map.get(rel_type, rel_type.lower().replace('_', ' '))
        return f"{source} {relation} {target}"

    def _generate_embeddings(self, triplets: List[Dict]) -> List[List[float]]:
        """生成三元组的向量嵌入

        Args:
            triplets: 三元组列表

        Returns:
            向量列表
        """
        # 提取searchable_text
        texts = [t.get('searchable_text', t.get('text', '')) for t in triplets]

        print(f"  文本数量: {len(texts)}")

        # 统计文本长度
        avg_len = sum(len(t) for t in texts) / len(texts) if texts else 0
        max_len = max(len(t) for t in texts) if texts else 0
        print(f"  平均长度: {avg_len:.1f} 字符")
        print(f"  最大长度: {max_len} 字符")

        # 批量生成embeddings
        batch_size = 250  # Vertex AI限制
        all_embeddings = []

        start_time = datetime.now()

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]

            try:
                embeddings_response = self.embedding_model.get_embeddings(batch)
                batch_embeddings = [emb.values for emb in embeddings_response]
                all_embeddings.extend(batch_embeddings)

                if (i // batch_size + 1) % 5 == 0:
                    print(f"  进度: {i+len(batch)}/{len(texts)}")

            except Exception as e:
                print(f"  ✗ Batch {i//batch_size + 1} 失败: {e}")
                # 返回零向量作为fallback
                all_embeddings.extend([[0.0] * 768 for _ in batch])

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  耗时: {elapsed:.1f} 秒")
        print(f"  速度: {len(texts)/elapsed:.1f} 条/秒")

        return all_embeddings

    def _build_faiss_index(self, embeddings: List[List[float]]):
        """构建FAISS索引

        Args:
            embeddings: 向量列表

        Returns:
            FAISS索引对象或None
        """
        try:
            import faiss

            embeddings_array = np.array(embeddings).astype('float32')
            dimension = 768

            # 使用IndexFlatL2（精确搜索）
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings_array)

            print(f"  索引类型: IndexFlatL2 (精确搜索)")
            print(f"  向量数量: {index.ntotal}")
            print(f"  向量维度: {dimension}")

            return index

        except ImportError:
            return None
        except Exception as e:
            print(f"  ✗ FAISS索引构建失败: {e}")
            return None

    def _save_embeddings(
        self,
        embeddings: List[List[float]],
        triplets: List[Dict],
        faiss_index
    ):
        """保存embeddings和FAISS索引

        Args:
            embeddings: 向量列表
            triplets: 三元组列表
            faiss_index: FAISS索引对象
        """
        # 统计
        events = [t for t in triplets if t['type'] == 'event']
        relationships = [t for t in triplets if t['type'] == 'relationship']

        # 保存embeddings为pickle
        output_data = {
            'embeddings': embeddings,
            'metadata': triplets,
            'info': {
                'model': 'text-multilingual-embedding-002',
                'dimension': 768,
                'total_records': len(triplets),
                'events': len(events),
                'relationships': len(relationships),
                'created_at': datetime.now().isoformat()
            }
        }

        pkl_file = self.vector_output_dir / 'embeddings.pkl'
        with open(pkl_file, 'wb') as f:
            pickle.dump(output_data, f)

        file_size = pkl_file.stat().st_size / (1024 * 1024)
        print(f"\n✓ Embeddings已保存:")
        print(f"  文件: {pkl_file}")
        print(f"  大小: {file_size:.2f} MB")

        # 保存FAISS索引
        if faiss_index is not None:
            try:
                import faiss

                faiss_file = self.vector_output_dir / 'index.faiss'
                faiss.write_index(faiss_index, str(faiss_file))

                index_size = faiss_file.stat().st_size / (1024 * 1024)
                print(f"\n✓ FAISS索引已保存:")
                print(f"  文件: {faiss_file}")
                print(f"  大小: {index_size:.2f} MB")
            except Exception as e:
                print(f"  ✗ FAISS索引保存失败: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Graph Building Pipeline")
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--fresh', action='store_true', help='从头开始（清除检查点）')

    args = parser.parse_args()

    # 创建并运行 Pipeline
    pipeline = GraphBuildingPipeline(config_file=args.config)
    pipeline.run(resume=not args.fresh)


if __name__ == "__main__":
    main()
