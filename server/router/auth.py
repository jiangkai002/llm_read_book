import os

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from auth.jwt_handler import create_access_token

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "password123")


@auth_router.post(
    "/login",
    summary="用户登录",
    description="使用用户名和密码登录，成功后返回 JWT access_token。",
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != APP_USERNAME or form_data.password != APP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(form_data.username)
    return {"access_token": access_token, "token_type": "bearer"}
