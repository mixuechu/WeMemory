#!/usr/bin/env python3
"""
ChatLab格式验证脚本

验证WeFlow导出的ChatLab格式数据是否符合规范。

使用方法:
    python scripts/validate_chatlab_format.py <json_file_path>
    python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


class ChatLabValidator:
    """ChatLab格式验证器"""

    REQUIRED_TOP_LEVEL_KEYS = ["chatlab", "meta", "members", "messages"]
    REQUIRED_CHATLAB_KEYS = ["version", "exportedAt", "generator"]
    REQUIRED_META_KEYS = ["name", "platform", "type"]
    REQUIRED_MEMBER_KEYS = ["platformId", "accountName"]
    REQUIRED_MESSAGE_KEYS = ["sender", "accountName", "timestamp", "type", "content"]

    VALID_CHAT_TYPES = ["private", "group"]
    VALID_MESSAGE_TYPES = [0, 1, 3, 34, 43, 47, 49, 80, 99]

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_file(self, file_path: Path) -> bool:
        """验证单个JSON文件"""
        self.errors = []
        self.warnings = []

        # 1. 检查文件是否存在
        if not file_path.exists():
            self.errors.append(f"文件不存在: {file_path}")
            return False

        # 2. 尝试解析JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON解析失败: {e}")
            return False
        except Exception as e:
            self.errors.append(f"文件读取失败: {e}")
            return False

        # 3. 验证数据结构
        self._validate_structure(data)

        return len(self.errors) == 0

    def _validate_structure(self, data: Dict[str, Any]):
        """验证数据结构"""
        # 检查顶层键
        for key in self.REQUIRED_TOP_LEVEL_KEYS:
            if key not in data:
                self.errors.append(f"缺少必需的顶层键: {key}")

        if self.errors:
            return  # 如果顶层结构有问题，后续检查无意义

        # 验证 chatlab 部分
        self._validate_chatlab(data["chatlab"])

        # 验证 meta 部分
        self._validate_meta(data["meta"])

        # 验证 members 部分
        self._validate_members(data["members"])

        # 验证 messages 部分
        self._validate_messages(data["messages"])

    def _validate_chatlab(self, chatlab: Dict[str, Any]):
        """验证 chatlab 元数据"""
        for key in self.REQUIRED_CHATLAB_KEYS:
            if key not in chatlab:
                self.errors.append(f"chatlab 缺少必需键: {key}")

        if "version" in chatlab and not isinstance(chatlab["version"], str):
            self.errors.append("chatlab.version 应为字符串类型")

        if "exportedAt" in chatlab and not isinstance(chatlab["exportedAt"], int):
            self.errors.append("chatlab.exportedAt 应为整数时间戳")

        if "generator" in chatlab and chatlab["generator"] != "WeFlow":
            self.warnings.append(f"generator 不是 'WeFlow': {chatlab['generator']}")

    def _validate_meta(self, meta: Dict[str, Any]):
        """验证 meta 对话信息"""
        for key in self.REQUIRED_META_KEYS:
            if key not in meta:
                self.errors.append(f"meta 缺少必需键: {key}")

        if "type" in meta:
            if meta["type"] not in self.VALID_CHAT_TYPES:
                self.errors.append(
                    f"meta.type 必须是 {self.VALID_CHAT_TYPES} 之一，当前值: {meta['type']}"
                )

            # 群聊必须有 groupId
            if meta["type"] == "group" and "groupId" not in meta:
                self.errors.append("群聊 (type: group) 必须包含 groupId 字段")

        if "platform" in meta and meta["platform"] != "wechat":
            self.warnings.append(f"platform 不是 'wechat': {meta['platform']}")

    def _validate_members(self, members: List[Dict[str, Any]]):
        """验证 members 参与者列表"""
        if not isinstance(members, list):
            self.errors.append("members 应为列表类型")
            return

        if len(members) < 1:
            self.errors.append("members 列表不能为空")
            return

        for i, member in enumerate(members):
            for key in self.REQUIRED_MEMBER_KEYS:
                if key not in member:
                    self.errors.append(f"members[{i}] 缺少必需键: {key}")

    def _validate_messages(self, messages: List[Dict[str, Any]]):
        """验证 messages 消息列表"""
        if not isinstance(messages, list):
            self.errors.append("messages 应为列表类型")
            return

        if len(messages) == 0:
            self.warnings.append("messages 列表为空")

        for i, message in enumerate(messages):
            # 检查必需字段
            for key in self.REQUIRED_MESSAGE_KEYS:
                if key not in message:
                    self.errors.append(f"messages[{i}] 缺少必需键: {key}")

            # 验证消息类型
            if "type" in message:
                msg_type = message["type"]
                if not isinstance(msg_type, int):
                    self.errors.append(f"messages[{i}].type 应为整数类型")
                elif msg_type not in self.VALID_MESSAGE_TYPES:
                    self.warnings.append(
                        f"messages[{i}].type 未知类型: {msg_type} (可能是新类型)"
                    )

            # 验证时间戳
            if "timestamp" in message and not isinstance(message["timestamp"], int):
                self.errors.append(f"messages[{i}].timestamp 应为整数时间戳")

    def get_report(self) -> str:
        """获取验证报告"""
        lines = []

        if self.errors:
            lines.append("❌ 错误 (Errors):")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.warnings:
            lines.append("\n⚠️  警告 (Warnings):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if not self.errors and not self.warnings:
            lines.append("✅ 验证通过！数据格式完全符合 ChatLab 规范")

        return "\n".join(lines)


def validate_directory(dir_path: Path) -> Tuple[int, int, int]:
    """
    验证目录下所有JSON文件

    Returns:
        (总数, 通过数, 失败数)
    """
    json_files = list(dir_path.rglob("*.json"))

    if not json_files:
        print(f"❌ 目录中没有找到JSON文件: {dir_path}")
        return 0, 0, 0

    total = len(json_files)
    passed = 0
    failed = 0

    print(f"📁 找到 {total} 个JSON文件，开始验证...\n")

    for i, json_file in enumerate(json_files, 1):
        print(f"[{i}/{total}] 验证: {json_file.name}")

        validator = ChatLabValidator()
        is_valid = validator.validate_file(json_file)

        if is_valid:
            print("  ✅ 通过")
            passed += 1
        else:
            print(f"  ❌ 失败 ({len(validator.errors)} 个错误)")
            failed += 1

            # 显示前3个错误
            for error in validator.errors[:3]:
                print(f"     - {error}")
            if len(validator.errors) > 3:
                print(f"     ... 还有 {len(validator.errors) - 3} 个错误")

        print()

    return total, passed, failed


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  验证单个文件:")
        print("    python scripts/validate_chatlab_format.py <file.json>")
        print("  验证目录:")
        print("    python scripts/validate_chatlab_format.py <directory>")
        print("\n示例:")
        print("    python scripts/validate_chatlab_format.py examples/data_samples/chatlab_format_private_chat.json")
        print("    python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"❌ 路径不存在: {path}")
        sys.exit(1)

    print("=" * 60)
    print("ChatLab 格式验证工具")
    print("=" * 60)
    print()

    if path.is_file():
        # 验证单个文件
        print(f"📄 验证文件: {path}\n")

        validator = ChatLabValidator()
        is_valid = validator.validate_file(path)

        print(validator.get_report())
        print()

        if is_valid:
            print("✅ 验证成功！")
            sys.exit(0)
        else:
            print("❌ 验证失败！")
            sys.exit(1)

    elif path.is_dir():
        # 验证目录
        total, passed, failed = validate_directory(path)

        print("=" * 60)
        print("验证汇总")
        print("=" * 60)
        print(f"总计: {total} 个文件")
        print(f"✅ 通过: {passed} 个")
        print(f"❌ 失败: {failed} 个")
        print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")

        sys.exit(0 if failed == 0 else 1)

    else:
        print(f"❌ 不支持的路径类型: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
