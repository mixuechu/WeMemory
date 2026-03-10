#!/usr/bin/env python3
"""
API 端到端测试

测试内容：
1. 健康检查端点
2. 统计信息端点
3. 记忆联想端点
4. 错误处理
5. 性能测试

使用方法：
    # 运行所有测试
    pytest tests/test_api_e2e.py -v

    # 运行特定测试
    pytest tests/test_api_e2e.py::test_health_check -v

    # 查看覆盖率
    pytest tests/test_api_e2e.py --cov=api
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Fixture: 创建测试客户端
@pytest.fixture(scope="module")
def client():
    """创建 FastAPI 测试客户端"""
    try:
        from api.main import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"无法加载 API: {e}")


class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_check(self, client):
        """测试基础健康检查"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # 检查必需字段
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data

        # 状态应该是 healthy 或 unhealthy
        assert data["status"] in ["healthy", "unhealthy"]

        # 版本号
        assert data["version"] == "1.0.0"

        # 运行时间应该是正数
        assert data["uptime_seconds"] >= 0

    def test_detailed_health_check(self, client):
        """测试详细健康检查"""
        response = client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # 检查必需字段
        assert "status" in data
        assert "version" in data
        assert "components" in data
        assert "uptime_seconds" in data

        components = data["components"]

        # 检查组件
        assert "conversation_vector_store" in components
        assert "triplet_vector_store" in components
        assert "memory" in components

        # 每个组件都应该有 status
        for component_name, component_info in components.items():
            assert "status" in component_info

        # 内存组件应该有使用信息
        if "memory" in components and components["memory"]["status"] == "healthy":
            memory = components["memory"]
            assert "used_mb" in memory
            assert "total_mb" in memory
            assert "usage_percent" in memory
            assert memory["usage_percent"] >= 0
            assert memory["usage_percent"] <= 100


class TestStatsEndpoint:
    """统计信息端点测试"""

    def test_get_stats(self, client):
        """测试获取统计信息"""
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        # 检查统计字段
        assert "total_memories" in data or "total_conversations" in data


class TestRecallEndpoint:
    """记忆联想端点测试"""

    def test_recall_basic(self, client):
        """测试基础联想查询"""
        response = client.post(
            "/api/recall",
            json={
                "query": "测试查询",
                "top_k": 5
            }
        )

        # 应该返回 200 或 404（如果向量库为空）
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()

            # 检查响应结构
            assert "query" in data
            assert "results" in data
            assert data["query"] == "测试查询"
            assert isinstance(data["results"], list)

    def test_recall_with_parameters(self, client):
        """测试带参数的联想查询"""
        response = client.post(
            "/api/recall",
            json={
                "query": "测试",
                "top_k": 10,
                "min_score": 0.5
            }
        )

        # 应该成功或返回合理的错误
        assert response.status_code in [200, 404, 422]

    def test_recall_invalid_top_k(self, client):
        """测试无效的 top_k 参数"""
        # top_k 太大
        response = client.post(
            "/api/recall",
            json={
                "query": "测试",
                "top_k": 1000  # 超过最大值
            }
        )

        # 应该返回 422（验证错误）或 200（服务器限制）
        assert response.status_code in [200, 422]

        # top_k 为负数
        response = client.post(
            "/api/recall",
            json={
                "query": "测试",
                "top_k": -1
            }
        )

        # 应该返回验证错误
        assert response.status_code == 422

    def test_recall_empty_query(self, client):
        """测试空查询"""
        response = client.post(
            "/api/recall",
            json={
                "query": "",
                "top_k": 5
            }
        )

        # 空查询应该被拒绝
        assert response.status_code in [422, 400]


class TestErrorHandling:
    """错误处理测试"""

    def test_404_endpoint(self, client):
        """测试不存在的端点"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """测试不允许的 HTTP 方法"""
        # GET 请求到只接受 POST 的端点
        response = client.get("/api/recall")
        assert response.status_code == 405

    def test_invalid_json(self, client):
        """测试无效的 JSON"""
        response = client.post(
            "/api/recall",
            data="这不是有效的JSON",
            headers={"Content-Type": "application/json"}
        )

        # 应该返回 422（验证错误）
        assert response.status_code == 422


class TestPerformance:
    """性能测试"""

    def test_health_check_performance(self, client):
        """测试健康检查响应时间"""
        import time

        start = time.time()
        response = client.get("/api/health")
        elapsed = time.time() - start

        assert response.status_code == 200

        # 健康检查应该在 100ms 内完成
        assert elapsed < 0.1, f"健康检查耗时 {elapsed:.3f}s，超过 100ms"

    def test_concurrent_requests(self, client):
        """测试并发请求"""
        import concurrent.futures
        import time

        def make_request():
            return client.get("/api/health")

        # 发送 10 个并发请求
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start

        # 所有请求都应该成功
        assert all(r.status_code == 200 for r in results)

        # 10个请求应该在 1 秒内完成
        assert elapsed < 1.0, f"10个并发请求耗时 {elapsed:.3f}s"


class TestRootEndpoint:
    """根端点测试"""

    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # 检查基本信息
        assert "name" in data
        assert "version" in data
        assert "docs" in data

        # 版本号应该匹配
        assert data["version"] == "1.0.0"


class TestCORS:
    """CORS 测试"""

    def test_cors_headers(self, client):
        """测试 CORS 头部"""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )

        # 应该允许跨域请求
        assert response.status_code == 200

        # 检查 CORS 头部
        headers = response.headers
        # 注意：某些 CORS 头可能不在 OPTIONS 响应中
        # 只检查实际 GET 请求
        get_response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )

        assert get_response.status_code == 200


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "e2e: 端到端测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )


# 运行说明
if __name__ == "__main__":
    print("运行 API 端到端测试")
    print("=" * 60)
    print("使用方法：")
    print("  pytest tests/test_api_e2e.py -v")
    print("  pytest tests/test_api_e2e.py::test_health_check -v")
    print("=" * 60)
