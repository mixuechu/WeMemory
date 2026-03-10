#!/usr/bin/env python3
"""
配置验证脚本

功能：
1. 验证配置文件格式是否正确
2. 检查必需的环境变量是否设置
3. 测试 Vertex AI API 连接
4. 提供友好的错误提示和解决建议

使用方法：
    python scripts/validate_config.py
    python scripts/validate_config.py --config config/production.yaml
    python scripts/validate_config.py --test-api
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.loader import load_config, validate_config, ConfigError


def check_environment_variables():
    """检查必需的环境变量"""
    print("=" * 60)
    print("检查环境变量")
    print("=" * 60)
    print()

    required_vars = {
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud 项目 ID',
    }

    optional_vars = {
        'GOOGLE_APPLICATION_CREDENTIALS': 'Google Cloud 凭证文件路径',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON': 'Google Cloud 凭证 JSON',
        'GOOGLE_REGION': 'Google Cloud 区域',
        'LOG_LEVEL': '日志级别',
        'DEBUG': '调试模式',
    }

    errors = []
    warnings = []

    # 检查必需变量
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}")
            print(f"   {description}: {value}")
        else:
            errors.append(f"❌ {var} 未设置 ({description})")

    print()

    # 检查可选变量
    print("可选环境变量:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            # 对凭证信息只显示前20个字符
            if 'CREDENTIALS' in var or 'KEY' in var:
                display_value = value[:20] + '...'
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ⬜ {var}: 未设置 ({description})")

    print()

    # 检查凭证配置
    cred_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    cred_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if not cred_file and not cred_json:
        warnings.append(
            "⚠️  未设置 Google Cloud 凭证\n"
            "   请设置以下环境变量之一：\n"
            "   - GOOGLE_APPLICATION_CREDENTIALS (凭证文件路径)\n"
            "   - GOOGLE_APPLICATION_CREDENTIALS_JSON (JSON 字符串)"
        )
    elif cred_file and not Path(cred_file).exists():
        errors.append(
            f"❌ 凭证文件不存在: {cred_file}\n"
            f"   请检查 GOOGLE_APPLICATION_CREDENTIALS 路径是否正确"
        )

    return errors, warnings


def check_configuration(config_file=None):
    """检查配置文件"""
    print("=" * 60)
    print("检查配置文件")
    print("=" * 60)
    print()

    try:
        # 加载配置
        if config_file:
            print(f"📄 加载配置: {config_file}")
        else:
            print("📄 加载配置: config/default.yaml")

        config = load_config(config_file)
        print("✅ 配置文件加载成功")
        print()

        # 验证配置
        is_valid, errors = validate_config(config)

        if is_valid:
            print("✅ 配置验证通过")
            print()
        else:
            print("❌ 配置验证失败：")
            for error in errors:
                print(f"  - {error}")
            print()
            return False, []

        # 显示关键配置
        print("关键配置信息:")
        print(f"  Google Cloud Project: {config.vertex_ai.project_id}")
        print(f"  Region: {config.vertex_ai.region}")
        print(f"  Embedding 模型: {config.vertex_ai.embedding.model}")
        print(f"  知识抽取模型: {config.vertex_ai.extraction.model}")
        print(f"  API 端口: {config.api.port}")
        print(f"  日志级别: {config.logging.level}")
        print()

        return True, []

    except ConfigError as e:
        print(f"❌ 配置错误: {e}")
        print()
        return False, [str(e)]


def check_paths(config):
    """检查配置的路径是否存在"""
    print("=" * 60)
    print("检查数据路径")
    print("=" * 60)
    print()

    paths_to_check = {
        'input_data': '输入数据目录',
        'vector_stores': '向量库目录',
        'knowledge_graph': '知识图谱目录',
        'logs': '日志目录',
        'checkpoints': '检查点目录',
    }

    warnings = []

    for path_key, description in paths_to_check.items():
        if path_key in config.paths:
            path = Path(config.paths[path_key])

            if path.exists():
                # 检查是否为目录
                if path.is_dir():
                    # 计算文件数量
                    file_count = len(list(path.glob('**/*')))
                    print(f"✅ {description}: {path} ({file_count} 个文件)")
                else:
                    print(f"⚠️  {description}: {path} (不是目录)")
                    warnings.append(f"{description} 应该是目录: {path}")
            else:
                print(f"⚠️  {description}: {path} (不存在，将自动创建)")
                warnings.append(f"{description} 不存在: {path}")

    print()
    return warnings


def test_vertex_ai_connection(config):
    """测试 Vertex AI API 连接"""
    print("=" * 60)
    print("测试 Vertex AI 连接")
    print("=" * 60)
    print()

    try:
        # 尝试导入 Google Cloud 库
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel
        except ImportError:
            print("❌ 缺少 Google Cloud 依赖")
            print("   请安装：pip install google-cloud-aiplatform")
            print()
            return False

        # 初始化 Vertex AI
        print(f"初始化 Vertex AI...")
        print(f"  Project: {config.vertex_ai.project_id}")
        print(f"  Region: {config.vertex_ai.region}")

        vertexai.init(
            project=config.vertex_ai.project_id,
            location=config.vertex_ai.region
        )
        print("✅ Vertex AI 初始化成功")
        print()

        # 测试 Embedding 模型
        print(f"测试 Embedding 模型: {config.vertex_ai.embedding.model}")

        model = TextEmbeddingModel.from_pretrained(config.vertex_ai.embedding.model)

        # 生成测试 embedding
        test_text = "这是一个测试文本"
        embeddings = model.get_embeddings([test_text])

        if embeddings and len(embeddings) > 0:
            embedding_dim = len(embeddings[0].values)
            print(f"✅ Embedding 模型测试成功")
            print(f"   维度: {embedding_dim}")
            print(f"   预期: {config.vertex_ai.embedding.dimensions}")

            if embedding_dim != config.vertex_ai.embedding.dimensions:
                print(f"⚠️  警告: 实际维度与配置不符")

        print()
        return True

    except Exception as e:
        print(f"❌ Vertex AI 连接失败: {e}")
        print()
        print("可能的原因：")
        print("  1. Google Cloud 凭证未正确设置")
        print("  2. 项目 ID 或区域配置错误")
        print("  3. 服务账号权限不足（需要 Vertex AI User 角色）")
        print("  4. Vertex AI API 未启用")
        print()
        print("解决方案：")
        print("  1. 检查 .env 文件中的 GOOGLE_CLOUD_PROJECT")
        print("  2. 检查 GOOGLE_APPLICATION_CREDENTIALS 或 GOOGLE_APPLICATION_CREDENTIALS_JSON")
        print("  3. 访问 https://console.cloud.google.com/vertex-ai 启用 API")
        print("  4. 确认服务账号具有 Vertex AI User 角色")
        print()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='验证 WeMemory 配置',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径（默认: config/default.yaml）'
    )

    parser.add_argument(
        '--test-api',
        action='store_true',
        help='测试 Vertex AI API 连接（需要网络和有效凭证）'
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("WeMemory 配置验证工具")
    print("=" * 60)
    print()

    all_errors = []
    all_warnings = []

    # 1. 检查环境变量
    env_errors, env_warnings = check_environment_variables()
    all_errors.extend(env_errors)
    all_warnings.extend(env_warnings)

    # 2. 检查配置文件
    config_valid, config_errors = check_configuration(args.config)
    all_errors.extend(config_errors)

    if not config_valid:
        print("=" * 60)
        print("验证结果：失败")
        print("=" * 60)
        print()
        sys.exit(1)

    # 重新加载配置用于后续检查
    config = load_config(args.config)

    # 3. 检查路径
    path_warnings = check_paths(config)
    all_warnings.extend(path_warnings)

    # 4. 测试 API 连接（可选）
    if args.test_api:
        api_success = test_vertex_ai_connection(config)
        if not api_success:
            all_errors.append("Vertex AI API 连接测试失败")

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)
    print()

    if all_errors:
        print("❌ 错误 (Errors):")
        for error in all_errors:
            print(f"  {error}")
        print()

    if all_warnings:
        print("⚠️  警告 (Warnings):")
        for warning in all_warnings:
            print(f"  {warning}")
        print()

    if not all_errors and not all_warnings:
        print("✅ 所有检查通过！配置完全正确。")
        print()
        print("下一步:")
        print("  1. 导出微信数据: 参见 docs/data-export.md")
        print("  2. 生成向量库: 参见 docs/embedding.md")
        print("  3. 启动服务: python -m api.main")
        print()
        sys.exit(0)
    elif all_errors:
        print("❌ 验证失败！请修复上述错误后重试。")
        print()
        print("常见问题排查：")
        print("  1. 确认已复制 .env.example 为 .env")
        print("  2. 在 .env 中填入正确的 GOOGLE_CLOUD_PROJECT")
        print("  3. 设置 Google Cloud 凭证（JSON 或文件路径）")
        print()
        sys.exit(1)
    else:
        print("⚠️  配置基本正确，但存在一些警告。")
        print("   建议修复警告项以获得最佳体验。")
        print()
        sys.exit(0)


if __name__ == '__main__':
    main()
