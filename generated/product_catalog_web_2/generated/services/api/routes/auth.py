from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import CurrentUser, create_access_token, get_current_user  # type: ignore

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: str
    roles: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if not body.email or not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and password required",
        )

    claims = {
        "sub": body.email,
        "email": body.email,
        "roles": ["user"],
    }
    token = create_access_token(claims)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, roles=user.roles)
