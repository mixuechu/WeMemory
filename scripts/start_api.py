#!/usr/bin/env python3
"""
API 服务启动脚本

功能：
1. 检查向量库是否存在
2. 验证配置
3. 启动 FastAPI 服务
4. 提供友好的错误提示

使用方法：
    python scripts/start_api.py
    python scripts/start_api.py --port 9000
    python scripts/start_api.py --reload  # 开发模式
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_vector_stores() -> tuple[bool, list[str]]:
    """
    检查向量库文件是否存在

    Returns:
        (是否通过, 错误列表)
    """
    errors = []

    # 必需的向量库
    conversation_vs = Path('vector_stores/conversations/embeddings.pkl')
    if not conversation_vs.exists():
        errors.append(
            f"对话向量库不存在: {conversation_vs}\n"
            f"  请先生成向量库：python scripts/generate_embeddings.py"
        )

    # 可选的三元组向量库
    triplet_vs = Path('vector_stores/triplets/embeddings.pkl')
    if not triplet_vs.exists():
        print(f"⚠️  三元组向量库不存在（可选）: {triplet_vs}")
        print(f"   如需知识图谱查询，请运行：python knowledge_graph/embedding_generator.py")
        print()

    return len(errors) == 0, errors


def check_configuration() -> tuple[bool, list[str]]:
    """
    检查配置是否正确

    Returns:
        (是否通过, 错误列表)
    """
    errors = []

    # 检查环境变量文件
    env_file = Path('.env')
    if not env_file.exists():
        errors.append(
            ".env 文件不存在\n"
            "  请复制并配置：cp .env.example .env"
        )

    # 检查必需的环境变量
    required_vars = ['GOOGLE_CLOUD_PROJECT']
    for var in required_vars:
        if not os.environ.get(var):
            errors.append(
                f"环境变量 {var} 未设置\n"
                f"  请在 .env 文件中设置此变量"
            )

    return len(errors) == 0, errors


def start_api(host: str = '0.0.0.0', port: int = 8000, reload: bool = False):
    """启动 API 服务"""
    try:
        import uvicorn
    except ImportError:
        print("❌ 缺少 uvicorn 依赖")
        print("   请安装：pip install uvicorn")
        sys.exit(1)

    print("=" * 70)
    print("WeMemory API 启动中...")
    print("=" * 70)
    print()

    # 显示配置
    print("配置信息:")
    print(f"  主机: {host}")
    print(f"  端口: {port}")
    print(f"  热重载: {'启用' if reload else '禁用'}")
    print()

    # 显示访问地址
    print("=" * 70)
    print("服务地址:")
    print(f"  主页: http://localhost:{port}/")
    print(f"  API文档: http://localhost:{port}/docs")
    print(f"  健康检查: http://localhost:{port}/api/health")
    print("=" * 70)
    print()

    # 启动服务
    try:
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='启动 WeMemory API 服务',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='监听地址（默认: 0.0.0.0）'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='端口号（默认: 8000）'
    )

    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用热重载（开发模式）'
    )

    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='跳过启动检查（不推荐）'
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("WeMemory API 启动脚本")
    print("=" * 70)
    print()

    # 执行检查（除非跳过）
    if not args.skip_checks:
        print("执行启动检查...\n")

        # 1. 检查向量库
        print("[1/2] 检查向量库...")
        vs_ok, vs_errors = check_vector_stores()

        if not vs_ok:
            print("❌ 向量库检查失败：")
            for error in vs_errors:
                print(f"\n{error}\n")
            sys.exit(1)
        else:
            print("✅ 向量库检查通过")
            print()

        # 2. 检查配置
        print("[2/2] 检查配置...")
        config_ok, config_errors = check_configuration()

        if not config_ok:
            print("❌ 配置检查失败：")
            for error in config_errors:
                print(f"\n{error}\n")
            print("💡 提示：运行 python scripts/validate_config.py 进行详细检查")
            print()
            sys.exit(1)
        else:
            print("✅ 配置检查通过")
            print()

        print("=" * 70)
        print("所有检查通过！准备启动服务...")
        print("=" * 70)
        print()

    # 从环境变量或命令行参数获取配置
    host = args.host or os.getenv('API_HOST', '0.0.0.0')
    port = args.port or int(os.getenv('API_PORT', '8000'))
    reload = args.reload or os.getenv('DEBUG', 'false').lower() == 'true'

    # 启动服务
    start_api(host=host, port=port, reload=reload)


if __name__ == '__main__':
    main()
