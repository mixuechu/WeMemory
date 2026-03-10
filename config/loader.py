"""
配置加载模块

功能：
1. 加载 YAML 配置文件
2. 环境变量替换（${VAR} 语法）
3. 配置验证
4. 配置合并（default.yaml + user.yaml）

使用示例：
    from config.loader import load_config

    # 加载默认配置
    config = load_config()

    # 加载自定义配置
    config = load_config('config/production.yaml')

    # 访问配置
    project_id = config.vertex_ai.project_id
    embedding_model = config.vertex_ai.embedding.model
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class ConfigError(Exception):
    """配置错误异常"""
    pass


class ConfigDict(dict):
    """
    支持点号访问的配置字典

    示例：
        config = ConfigDict({'a': {'b': 1}})
        print(config.a.b)  # 1
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = ConfigDict(value)

    def __getattr__(self, key):
        try:
            value = self[key]
            return value
        except KeyError:
            raise AttributeError(f"配置键不存在: {key}")

    def __setattr__(self, key, value):
        self[key] = value

    def get_nested(self, path: str, default: Any = None) -> Any:
        """
        获取嵌套配置值

        Args:
            path: 点号分隔的路径，如 "vertex_ai.embedding.model"
            default: 默认值

        Returns:
            配置值或默认值
        """
        keys = path.split('.')
        value = self

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


class ConfigLoader:
    """配置加载器"""

    # 环境变量替换正则表达式
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            base_dir: 基础目录，默认为项目根目录
        """
        if base_dir is None:
            # 假设此文件在 config/loader.py
            self.base_dir = Path(__file__).parent.parent
        else:
            self.base_dir = Path(base_dir)

        self.config_dir = self.base_dir / 'config'

    def load(self, config_file: Optional[str] = None) -> ConfigDict:
        """
        加载配置文件

        Args:
            config_file: 配置文件路径，默认为 config/default.yaml

        Returns:
            ConfigDict 对象
        """
        # 确定配置文件路径
        if config_file is None:
            config_path = self.config_dir / 'default.yaml'
        else:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.base_dir / config_path

        # 检查文件是否存在
        if not config_path.exists():
            raise ConfigError(f"配置文件不存在: {config_path}")

        # 加载 YAML
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML 解析失败: {e}")

        # 环境变量替换
        config = self._replace_env_vars(raw_config)

        # 转换为 ConfigDict
        config = ConfigDict(config)

        # 检查是否有 user.yaml 覆盖配置
        user_config_path = self.config_dir / 'user.yaml'
        if user_config_path.exists():
            config = self._merge_configs(config, user_config_path)

        return config

    def _replace_env_vars(self, obj: Any) -> Any:
        """
        递归替换环境变量

        Args:
            obj: 配置对象（dict, list, str 等）

        Returns:
            替换后的对象
        """
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._replace_env_var_string(obj)
        else:
            return obj

    def _replace_env_var_string(self, value: str) -> Any:
        """
        替换字符串中的环境变量

        支持格式：
        - ${VAR} - 必需，不存在会报错
        - ${VAR:default} - 可选，不存在使用默认值

        Args:
            value: 包含环境变量的字符串

        Returns:
            替换后的值
        """
        def replacer(match):
            var_expr = match.group(1)

            # 检查是否有默认值
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = var_expr.strip()
                default_value = None

            # 获取环境变量
            env_value = os.environ.get(var_name)

            if env_value is None:
                if default_value is not None:
                    return default_value
                else:
                    raise ConfigError(
                        f"环境变量 {var_name} 未设置。"
                        f"请在 .env 文件或环境中设置此变量。"
                    )

            return env_value

        # 替换所有环境变量
        result = self.ENV_VAR_PATTERN.sub(replacer, value)

        # 尝试转换类型
        return self._convert_type(result)

    def _convert_type(self, value: str) -> Any:
        """
        尝试将字符串转换为适当的类型

        Args:
            value: 字符串值

        Returns:
            转换后的值
        """
        # 布尔值
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False

        # 整数
        try:
            return int(value)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 保持字符串
        return value

    def _merge_configs(self, base_config: ConfigDict, user_config_path: Path) -> ConfigDict:
        """
        合并用户配置

        Args:
            base_config: 基础配置
            user_config_path: 用户配置文件路径

        Returns:
            合并后的配置
        """
        # 加载用户配置
        try:
            with open(user_config_path, 'r', encoding='utf-8') as f:
                raw_user_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"用户配置 YAML 解析失败: {e}")

        # 环境变量替换
        user_config = self._replace_env_vars(raw_user_config)

        # 深度合并
        merged = self._deep_merge(dict(base_config), user_config)

        return ConfigDict(merged)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        深度合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


# 全局配置加载器实例
_loader = ConfigLoader()


def load_config(config_file: Optional[str] = None) -> ConfigDict:
    """
    加载配置（便捷函数）

    Args:
        config_file: 配置文件路径，默认为 config/default.yaml

    Returns:
        ConfigDict 对象

    示例：
        config = load_config()
        print(config.vertex_ai.project_id)
    """
    return _loader.load(config_file)


def validate_config(config: ConfigDict) -> tuple[bool, list[str]]:
    """
    验证配置完整性

    Args:
        config: 配置对象

    Returns:
        (是否有效, 错误列表)
    """
    errors = []

    # 检查必需的顶层键
    required_keys = ['vertex_ai', 'paths', 'pipeline', 'api', 'logging']
    for key in required_keys:
        if key not in config:
            errors.append(f"缺少必需的配置节: {key}")

    # 检查 Vertex AI 配置
    if 'vertex_ai' in config:
        vertex_ai = config.vertex_ai

        if 'project_id' not in vertex_ai:
            errors.append("缺少 vertex_ai.project_id")
        elif not vertex_ai.project_id:
            errors.append("vertex_ai.project_id 为空，请设置 GOOGLE_CLOUD_PROJECT 环境变量")

        if 'embedding' in vertex_ai:
            if 'model' not in vertex_ai.embedding:
                errors.append("缺少 vertex_ai.embedding.model")
        else:
            errors.append("缺少 vertex_ai.embedding 配置节")

    # 检查路径配置
    if 'paths' in config:
        paths = config.paths

        required_paths = ['input_data', 'vector_stores', 'knowledge_graph']
        for path_key in required_paths:
            if path_key not in paths:
                errors.append(f"缺少 paths.{path_key}")

    # 检查 API 配置
    if 'api' in config:
        api = config.api

        if 'port' in api and not isinstance(api.port, int):
            errors.append("api.port 必须是整数")

        if 'host' not in api:
            errors.append("缺少 api.host")

    return len(errors) == 0, errors


if __name__ == '__main__':
    """测试配置加载"""
    try:
        # 加载配置
        config = load_config()

        print("✅ 配置加载成功！")
        print(f"\n项目ID: {config.vertex_ai.project_id}")
        print(f"Embedding模型: {config.vertex_ai.embedding.model}")
        print(f"API端口: {config.api.port}")

        # 验证配置
        is_valid, errors = validate_config(config)

        if is_valid:
            print("\n✅ 配置验证通过！")
        else:
            print("\n❌ 配置验证失败：")
            for error in errors:
                print(f"  - {error}")

    except ConfigError as e:
        print(f"❌ 配置错误: {e}")
