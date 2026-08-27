from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.authz.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db import redis_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
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
BROWSER_REFRESH_COOKIE = "csp_refresh"
BROWSER_REFRESH_PATH = "/api/v1/auth/browser"


def _set_browser_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=BROWSER_REFRESH_COOKIE,
        value=token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=BROWSER_REFRESH_PATH,
    )


def _clear_browser_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=BROWSER_REFRESH_COOKIE,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=BROWSER_REFRESH_PATH,
    )


def _authenticate_login(
    payload: LoginRequest,
    request: Request,
    db: Session,
    settings: Settings,
) -> tuple[AuthService, User, str]:
    limiter = AuthRateLimiter(redis_client.get_redis(), settings)
    client_ip = request.client.host if request.client else "unknown"
    limiter.check_and_increment(ip=client_ip, account_key=payload.email.lower())
    service = AuthService(db, settings)
    user = service.authenticate(email=payload.email, password=payload.password)
    return service, user, client_ip


@router.post("/register", response_model=TokenPairResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPairResponse:
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
    service, user, client_ip = _authenticate_login(payload, request, db, settings)
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
    AuthService(db, settings).logout(raw_refresh_token=payload.refresh_token)


@router.post("/browser/login", response_model=AccessTokenResponse)
def browser_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AccessTokenResponse:
    service, user, client_ip = _authenticate_login(payload, request, db, settings)
    access_token, refresh_token = service.issue_token_pair(
        user, user_agent=request.headers.get("user-agent", ""), ip_address=client_ip
    )
    _set_browser_refresh_cookie(response, refresh_token, settings)
    return AccessTokenResponse(access_token=access_token)


@router.post("/browser/refresh", response_model=AccessTokenResponse)
def browser_refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=BROWSER_REFRESH_COOKIE),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AccessTokenResponse:
    if not refresh_token:
        from app.core.exceptions import AuthenticationError

        raise AuthenticationError("Invalid or expired refresh token")
    service = AuthService(db, settings)
    access_token, new_refresh = service.refresh(raw_refresh_token=refresh_token)
    _set_browser_refresh_cookie(response, new_refresh, settings)
    return AccessTokenResponse(access_token=access_token)


@router.post("/browser/logout", status_code=204)
def browser_logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=BROWSER_REFRESH_COOKIE),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    if refresh_token:
        AuthService(db, settings).logout(raw_refresh_token=refresh_token)
    _clear_browser_refresh_cookie(response, settings)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
