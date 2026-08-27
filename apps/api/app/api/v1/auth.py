from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.authz.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db import redis_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    BootstrapRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.rate_limit_service import AuthRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPairResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPairResponse:
    """Self-service signup: creates a standalone user account with no
    workspace membership yet. Call `POST /workspaces` next to create
    a tenant and become its Administrator. Distinct from `/bootstrap`,
    which is a one-time, install-wide initialization step.
    """
    service = AuthService(db, settings)
    user = service.register_user(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    access_token, refresh_token = service.issue_token_pair(user)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/bootstrap", response_model=TokenPairResponse)
def bootstrap(
    payload: BootstrapRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPairResponse:
    service = AuthService(db, settings)
    user, _workspace_id = service.bootstrap_owner(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        workspace_name=payload.workspace_name,
    )
    access_token, refresh_token = service.issue_token_pair(user)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPairResponse:
    limiter = AuthRateLimiter(redis_client.get_redis(), settings)
    client_ip = request.client.host if request.client else "unknown"
    limiter.check_and_increment(ip=client_ip, account_key=payload.email.lower())

    service = AuthService(db, settings)
    user = service.authenticate(email=payload.email, password=payload.password)
    access_token, refresh_token = service.issue_token_pair(
        user, user_agent=request.headers.get("user-agent", ""), ip_address=client_ip
    )
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPairResponse:
    service = AuthService(db, settings)
    access_token, refresh_token = service.refresh(raw_refresh_token=payload.refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    service = AuthService(db, settings)
    service.logout(raw_refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
