from pydantic import BaseModel


class RequestToken(BaseModel):
    id_token: str
    email: str
    name: str | None


class Token(BaseModel):
    access_token: str
    token_type: str
