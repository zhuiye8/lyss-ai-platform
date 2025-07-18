"""
Auth Service 安全核心模块
实现密码哈希验证和安全相关功能
严格遵循 docs/auth_service.md 和 docs/STANDARDS.md 规范
"""

from passlib.context import CryptContext
# from passlib.exc import VerifyError  # VerifyError可能不在所有版本中可用

from .exceptions import InvalidCredentialsError


class PasswordManager:
    """密码管理器 - 负责密码哈希验证"""

    def __init__(self):
        # 密码上下文配置 - 使用bcrypt算法，12轮加密
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12,
        )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证明文密码与哈希密码是否匹配

        Args:
            plain_password: 明文密码
            hashed_password: 数据库中存储的哈希密码

        Returns:
            bool: 密码验证结果

        Raises:
            InvalidCredentialsError: 密码验证失败时抛出
        """
        try:
            if not plain_password or not hashed_password:
                return False

            # 使用passlib验证密码
            is_valid = self.pwd_context.verify(plain_password, hashed_password)
            return is_valid

        except Exception as e:
            # passlib验证异常或其他异常情况
            if "verify" in str(e).lower() or "hash" in str(e).lower():
                # 密码验证格式错误
                return False
            # 其他异常情况
            raise InvalidCredentialsError(
                message="密码验证过程中发生错误",
                details={"error": str(e)},
            )

    def hash_password(self, password: str) -> str:
        """
        生成密码哈希值（仅供测试使用，生产环境由Tenant Service负责）

        Args:
            password: 明文密码

        Returns:
            str: 哈希后的密码
        """
        return self.pwd_context.hash(password)

    def verify_password_strength(self, password: str) -> bool:
        """
        验证密码强度（基础验证）
        详细的密码策略由Tenant Service负责

        Args:
            password: 要验证的密码

        Returns:
            bool: 密码是否符合基本要求
        """
        if not password:
            return False

        # 基本长度要求
        if len(password) < 8:
            return False

        # 包含字母和数字
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)

        return has_letter and has_digit


# 全局密码管理器实例
password_manager = PasswordManager()