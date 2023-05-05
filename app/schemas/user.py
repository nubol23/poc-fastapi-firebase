from pydantic import BaseModel


class RequestToken(BaseModel):
    id_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
