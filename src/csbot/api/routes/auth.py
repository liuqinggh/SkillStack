from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from csbot.api.deps import AppContext


class LoginBody(BaseModel):
    email: str
    password: str


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    value = authorization.strip()
    if not value.lower().startswith('bearer '):
        return None
    return value[7:].strip()


def _require_user(context: AppContext, authorization: str | None):
    token = _bearer_token(authorization)
    user = context.auth_service.resolve(token)
    if user is None:
        raise HTTPException(status_code=401, detail='Unauthorized')
    return user


def create_auth_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix='/api/auth', tags=['auth'])

    @router.post('/login')
    def login(payload: LoginBody):
        result = context.auth_service.login(payload.email, payload.password)
        if result is None:
            raise HTTPException(status_code=401, detail='Invalid credentials')
        user, token = result
        return {'id': user.id, 'email': user.email, 'name': user.name, 'accessToken': token}

    @router.delete('/logout', status_code=204)
    def logout():
        return Response(status_code=204)

    @router.get('/token')
    def get_me(authorization: str | None = Header(default=None, alias='Authorization')):
        user = _require_user(context, authorization)
        return {'id': user.id, 'email': user.email, 'name': user.name}

    return router
