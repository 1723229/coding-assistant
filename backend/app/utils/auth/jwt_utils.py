"""
JWT Utilities

Provides JWT token generation and validation utilities.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
import jwt
import secrets
from app.config.settings import JWTConfig as ConfigJWTConfig


class JWTConfig:
    """JWT Configuration with security validation"""

    # Security requirements
    MIN_KEY_LENGTH = 32
    REQUIRED_ALGORITHM = "HS256"

    # Load from config
    SECRET_KEY = ConfigJWTConfig.SECRET_KEY
    REFRESH_SECRET_KEY = ConfigJWTConfig.REFRESH_SECRET_KEY
    ALGORITHM = ConfigJWTConfig.ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = ConfigJWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = ConfigJWTConfig.REFRESH_TOKEN_EXPIRE_DAYS
    AUTO_REFRESH_ENABLED = ConfigJWTConfig.AUTO_REFRESH_ENABLED
    REFRESH_THRESHOLD_MINUTES = ConfigJWTConfig.REFRESH_THRESHOLD_MINUTES

    @classmethod
    def validate_security_settings(cls) -> None:
        """
        验证JWT安全设置

        Raises:
            ValueError: 如果安全设置不符合要求
        """
        errors = []

        # 验证密钥长度
        if len(cls.SECRET_KEY) < cls.MIN_KEY_LENGTH:
            errors.append(f"JWT密钥长度不足，需要至少{cls.MIN_KEY_LENGTH}字符，当前{len(cls.SECRET_KEY)}字符")

        if len(cls.REFRESH_SECRET_KEY) < cls.MIN_KEY_LENGTH:
            errors.append(f"JWT刷新密钥长度不足，需要至少{cls.MIN_KEY_LENGTH}字符，当前{len(cls.REFRESH_SECRET_KEY)}字符")

        # 验证密钥不能相同
        if cls.SECRET_KEY == cls.REFRESH_SECRET_KEY:
            errors.append("访问令牌密钥和刷新令牌密钥不能相同")

        # 验证算法安全性
        if cls.ALGORITHM != cls.REQUIRED_ALGORITHM:
            errors.append(f"不安全的JWT算法：{cls.ALGORITHM}，推荐使用{cls.REQUIRED_ALGORITHM}")

        # 验证令牌过期时间设置合理性
        if cls.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
            errors.append(f"访问令牌过期时间过长：{cls.ACCESS_TOKEN_EXPIRE_MINUTES}分钟，建议不超过60分钟")

        if cls.REFRESH_TOKEN_EXPIRE_DAYS > 30:
            errors.append(f"刷新令牌过期时间过长：{cls.REFRESH_TOKEN_EXPIRE_DAYS}天，建议不超过30天")

        if errors:
            raise ValueError("JWT安全设置验证失败:\n" + "\n".join(f"- {error}" for error in errors))

    @classmethod
    def generate_secure_key(cls, length: int = 32) -> str:
        """
        生成安全的JWT密钥

        Args:
            length: 密钥长度，默认32字符

        Returns:
            安全的随机密钥
        """
        return secrets.token_urlsafe(length)

    # JWT Claims
    USER_ID_CLAIM = "sub"
    SESSION_ID_CLAIM = "session_id"
    USERNAME_CLAIM = "username"
    IS_ADMIN_CLAIM = "is_admin"
    NAME_CLAIM = "name"
    EMAIL_CLAIM = "email"
    ROLES_CLAIM = "roles"
    TOKEN_TYPE_CLAIM = "token_type"
    TOKEN_FAMILY_CLAIM = "family_id"


class JWTUtils:
    """JWT Utilities for token generation and validation"""

    @staticmethod
    def create_access_token(
            user_id: str,
            username: str,
            name: Optional[str] = None,
            email: Optional[str] = None,
            is_admin: bool = False,
            session_id: Optional[str] = None,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token (short-lived)

        Args:
            user_id: User ID
            username: Username
            name: User's full name
            email: User's email
            is_admin: Whether user is admin
            session_id: Session ID
            expires_delta: Token expiration time delta

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Build JWT payload
        payload = {
            JWTConfig.USER_ID_CLAIM: user_id,
            JWTConfig.USERNAME_CLAIM: username,
            JWTConfig.IS_ADMIN_CLAIM: is_admin,
            JWTConfig.TOKEN_TYPE_CLAIM: "access",
            "exp": expire,
            "iat": datetime.now(UTC),
        }

        # Add optional claims
        if name:
            payload[JWTConfig.NAME_CLAIM] = name

        if email:
            payload[JWTConfig.EMAIL_CLAIM] = email

        if session_id:
            payload[JWTConfig.SESSION_ID_CLAIM] = session_id

        # Add roles based on admin status
        if is_admin:
            payload[JWTConfig.ROLES_CLAIM] = ["admin", "user"]
        else:
            payload[JWTConfig.ROLES_CLAIM] = ["user"]

        # Encode JWT token
        token = jwt.encode(payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM)
        return token

    @staticmethod
    def create_refresh_token(
            user_id: str,
            username: str,
            session_id: Optional[str] = None,
            family_id: Optional[str] = None,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT refresh token (long-lived)

        Args:
            user_id: User ID
            username: Username
            session_id: Session ID
            family_id: Token family ID (for rotation detection)
            expires_delta: Token expiration time delta

        Returns:
            JWT refresh token string
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)

        # Generate family_id if not provided (for token rotation)
        if not family_id:
            family_id = secrets.token_urlsafe(32)

        # Build JWT payload (refresh token contains minimal info)
        payload = {
            JWTConfig.USER_ID_CLAIM: user_id,
            JWTConfig.USERNAME_CLAIM: username,
            JWTConfig.TOKEN_TYPE_CLAIM: "refresh",
            JWTConfig.TOKEN_FAMILY_CLAIM: family_id,
            "exp": expire,
            "iat": datetime.now(UTC),
        }

        if session_id:
            payload[JWTConfig.SESSION_ID_CLAIM] = session_id

        # Encode JWT token with refresh secret key
        token = jwt.encode(payload, JWTConfig.REFRESH_SECRET_KEY, algorithm=JWTConfig.ALGORITHM)
        return token

    @staticmethod
    def decode_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string
            token_type: Token type ('access' or 'refresh')

        Returns:
            Decoded payload

        Raises:
            jwt.ExpiredSignatureError: If token is expired
            jwt.InvalidTokenError: If token is invalid
        """
        # 根据token类型选择密钥
        secret_key = JWTConfig.REFRESH_SECRET_KEY if token_type == "refresh" else JWTConfig.SECRET_KEY

        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[JWTConfig.ALGORITHM]
            )

            # 验证token类型是否匹配
            if payload.get(JWTConfig.TOKEN_TYPE_CLAIM) != token_type:
                raise ValueError(
                    f"Token type mismatch: expected {token_type}, got {payload.get(JWTConfig.TOKEN_TYPE_CLAIM)}")

            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    @staticmethod
    def extract_user_id(token: str) -> Optional[str]:
        """
        Extract user ID from token

        Args:
            token: JWT token string

        Returns:
            User ID or None if extraction fails
        """
        try:
            payload = JWTUtils.decode_token(token)
            return payload.get(JWTConfig.USER_ID_CLAIM)
        except Exception:
            return None

    @staticmethod
    def verify_token(token: str) -> bool:
        """
        Verify if token is valid

        Args:
            token: JWT token string

        Returns:
            True if valid, False otherwise
        """
        try:
            JWTUtils.decode_token(token)
            return True
        except Exception:
            return False

    @staticmethod
    def verify_token_type(token: str, expected_type: str) -> bool:
        """
        Verify if token is of expected type ('access' or 'refresh')

        Args:
            token: JWT token string
            expected_type: Expected token type

        Returns:
            True if token type matches, False otherwise
        """
        try:
            payload = JWTUtils.decode_token(token, token_type=expected_type)
            return payload.get(JWTConfig.TOKEN_TYPE_CLAIM) == expected_type
        except Exception:
            return False

    @staticmethod
    def should_refresh_access_token(token: str) -> bool:
        """
        Check if access token should be refreshed

        Args:
            token: JWT access token string

        Returns:
            True if should refresh, False otherwise
        """
        if not JWTConfig.AUTO_REFRESH_ENABLED:
            return False

        try:
            payload = JWTUtils.decode_token(token, token_type="access")
            exp_timestamp = payload.get("exp")

            if not exp_timestamp:
                return False

            # 计算剩余时间
            exp_time = datetime.fromtimestamp(exp_timestamp, UTC)
            remaining_time = exp_time - datetime.now(UTC)

            # 如果剩余时间少于阈值，则应该刷新
            threshold = timedelta(minutes=JWTConfig.REFRESH_THRESHOLD_MINUTES)
            return remaining_time <= threshold

        except Exception:
            return False

    @staticmethod
    def get_token_expiration(token: str) -> Optional[datetime]:
        """
        Get token expiration time

        Args:
            token: JWT token string

        Returns:
            Expiration datetime or None if token is invalid
        """
        try:
            payload = JWTUtils.decode_token(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=UTC)
            return None
        except Exception:
            return None



if __name__ == '__main__':
    test = JWTUtils.extract_user_id('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MTJmZDE5NTRjOGQ0OWYxYTJiYzJiMzIzMzJhYWE3MCIsInVzZXJuYW1lIjoiMTk3Nzg4MjU2MjFAcXEuY29tIiwiaXNfYWRtaW4iOmZhbHNlLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3NjAxMzM4LCJpYXQiOjE3Njc1OTk1MzgsIm5hbWUiOiIxXHU2NzRlXHU4ZDg1Iiwic2Vzc2lvbl9pZCI6InNlc3Npb25fNTk2NDkwMDdjOTQxNDEyNjgxMjU5ZGQ1NGVlNGNmNGMiLCJyb2xlcyI6WyJ1c2VyIl19.ddGGJUZoWVWmAzAO4Bbdwej1GcVe21VoBlPfCj89oKo')
    print(test)
