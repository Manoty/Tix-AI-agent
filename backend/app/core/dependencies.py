import uuid
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.services.auth import AuthService
from app.repositories.user import UserRepository
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = AuthService.verify_token(
        credentials.credentials,
        expected_type="access",
    )
    user = await UserRepository(db).get_by_id(uuid.UUID(payload.sub))

    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    return user


def require_role(*roles: UserRole):
    """
    Returns a FastAPI dependency that enforces the caller has one of the given roles.
    Usage: Depends(require_role(UserRole.admin, UserRole.agent))
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError(
                f"Role '{current_user.role.value}' is not permitted. "
                f"Required: {[r.value for r in roles]}"
            )
        return current_user
    return _check