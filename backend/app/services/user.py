import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.core.exceptions import ConflictError, AuthenticationError
import structlog

logger = structlog.get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> UserResponse:
        if await self.repo.email_exists(data.email):
            raise ConflictError(f"Email already registered: {data.email}")

        user_create = UserCreate(
            email=data.email,
            full_name=data.full_name,
            password=data.password,
        )
        hashed = AuthService.hash_password(data.password)
        user = await self.repo.create(user_create, hashed)
        return UserResponse.model_validate(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)

        if not user or not AuthService.verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        access, refresh = AuthService.create_token_pair(user.id, user.role.value)
        logger.info("user_login", user_id=str(user.id), email=user.email)

        return TokenResponse(access_token=access, refresh_token=refresh)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = AuthService.verify_token(refresh_token, expected_type="refresh")
        user = await self.repo.get_by_id(uuid.UUID(payload.sub))

        if not user or not user.is_active:
            raise AuthenticationError("User not found or disabled")

        access, refresh = AuthService.create_token_pair(user.id, user.role.value)
        return TokenResponse(access_token=access, refresh_token=refresh)