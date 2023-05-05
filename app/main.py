from datetime import timedelta
from typing import Annotated

import firebase_admin
import uvicorn
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from firebase_admin import credentials, auth
from firebase_admin._auth_utils import InvalidIdTokenError
from fastapi import FastAPI, HTTPException, Depends
from jose import jwt, JWTError
from starlette import status
from starlette.responses import Response

from app.core import BASE_DIR, Settings
from app.schemas import RequestToken, Token
from app.utils.auth import create_access_token

cred = credentials.Certificate(f"{BASE_DIR}/auth-service-poc-firebase-adminsdk-7y3q8-a984a7fd02.json")
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

app = FastAPI()
settings = Settings()


@app.post("/token", response_model=Token)
def get_access_token(request_token: RequestToken):
    try:
        decoded_token = auth.verify_id_token(request_token.id_token)

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"id": decoded_token["user_id"]}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid id token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/validate")
async def validate_access_token(access_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("id")

        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
