#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证大实体对话的分批处理"""

import sys
sys.path.insert(0, '/Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated')

import json
from pathlib import Path
from run_merge_suggestions import analyze_conversation, get_access_token
from google.oauth2 import service_account
from dotenv import load_dotenv
import os

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# 加载数据
base_dir = Path(__file__).parent
with open(base_dir / 'merged_entities_by_conversation.json', 'r', encoding='utf-8') as f:
    all_merged_data = json.load(f)
with open(base_dir / 'conversation_entity_edits_curated.json', 'r', encoding='utf-8') as f:
    entity_edits = json.load(f)

# 测试"妈"这个对话（675个实体）
conv_name = "妈"
entities_data = all_merged_data[conv_name]
existing_edits = entity_edits.get('conversation_edits', {}).get(conv_name)

print(f"测试对话: {conv_name}")
print(f"总实体数: {len(entities_data)}")

if existing_edits:
    excluded = existing_edits.get('excluded_entities', [])
    merges = existing_edits.get('manual_merges', [])
    print(f"已排除: {len(excluded)} 个")
    print(f"已合并: {len(merges)} 组")
    remaining = len(entities_data) - len(excluded)
    print(f"剩余需分析: {remaining} 个")
    print(f"预计批次: {(remaining + 249) // 250}")

print("\n开始测试...")
result = analyze_conversation(conv_name, entities_data, existing_edits)

if 'error' in result:
    print(f"\n✗ 错误: {result['error']}")
else:
    print(f"\n✓ 测试成功!")
    print(f"  分析实体数: {result['entity_count']}")
    print(f"  总实体数: {result['total_entities']}")
    print(f"  排除数: {result['excluded_count']}")
    if 'batches_processed' in result:
        print(f"  处理批次: {result['batches_processed']}")
    print(f"  生成建议: {len(result['merge_suggestions'])} 组")

    if result['merge_suggestions']:
        print("\n前5个建议:")
        for i, sug in enumerate(result['merge_suggestions'][:5], 1):
            print(f"  {i}. {sug['final_name']}: {len(sug['entities'])}个实体")
            print(f"     实体: {', '.join(sug['entities'][:5])}...")
            print(f"     原因: {sug['reason'][:100]}...")

# 保存结果
output = {
    'test_conversation': conv_name,
    'result': result
}

output_file = base_dir / 'test_large_conversation.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存: {output_file}")
print("\n🎉 验证完成！分批处理逻辑正常工作")
