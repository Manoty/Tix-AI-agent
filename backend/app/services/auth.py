from datetime import datetime, timedelta, timezone
from typing import Literal
import uuid

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.schemas.auth import TokenPayload

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    @staticmethod
    def hash_password(plain: str) -> str:
        return pwd_context.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def _create_token(
        user_id: uuid.UUID,
        role: str,
        token_type: Literal["access", "refresh"],
    ) -> str:
        if token_type == "access":
            expire_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        else:
            expire_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

        expire = datetime.now(timezone.utc) + expire_delta

        payload = {
            "sub": str(user_id),
            "role": role,
            "type": token_type,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def create_access_token(user_id: uuid.UUID, role: str) -> str:
        return AuthService._create_token(user_id, role, "access")

    @staticmethod
    def create_refresh_token(user_id: uuid.UUID, role: str) -> str:
        return AuthService._create_token(user_id, role, "refresh")

    @staticmethod
    def create_token_pair(user_id: uuid.UUID, role: str) -> tuple[str, str]:
        access = AuthService.create_access_token(user_id, role)
        refresh = AuthService.create_refresh_token(user_id, role)
        return access, refresh

    @staticmethod
    def verify_token(token: str, expected_type: Literal["access", "refresh"]) -> TokenPayload:
        try:
            raw = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            payload = TokenPayload(**raw)
        except JWTError:
            raise AuthenticationError("Invalid or expired token")

        if payload.type != expected_type:
            raise AuthenticationError(f"Expected {expected_type} token, got {payload.type}")

        return payload