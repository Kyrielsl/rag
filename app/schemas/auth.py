from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreateIn(BaseModel):
    name: str
    scope: str = "search"


class ApiKeyOut(BaseModel):
    id: str
    name: str
    scope: str
    key: str


class GrantIn(BaseModel):
    domain: str