from datetime import timedelta

import firebase_admin
import uvicorn

from firebase_admin import credentials, auth
from firebase_admin._auth_utils import InvalidIdTokenError
from fastapi import FastAPI, HTTPException
from jose import jwt, JWTError, ExpiredSignatureError
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.core import BASE_DIR, Settings
from app.database import User, init_database
from app.database.models import Role
from app.schemas import RequestToken, Token
from app.utils.auth import create_access_token

cred = credentials.Certificate(f"{BASE_DIR}/auth-service-poc-firebase-adminsdk-7y3q8-a984a7fd02.json")
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

app = FastAPI()
settings = Settings()

# Allow CORS from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_database()


# Create and login
@app.post("/token", response_model=Token)
async def get_access_token(request_token: RequestToken):
    try:
        decoded_token = auth.verify_id_token(request_token.id_token)

        if not decoded_token.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Must verify email",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create user if not exists
        user = await User.objects.filter(firebase_id=decoded_token["user_id"]).first()
        if not user:
            user = await User.objects.create(
                firebase_id=decoded_token.get("user_id"),
                role=Role.MEMBER,
                email=decoded_token.get("email"),
                name=decoded_token.get("name"),
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "id": decoded_token["user_id"],
                "role": user.role.name,
                "email": user.email,
                "name": user.name,
            },
            expires_delta=access_token_expires,
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


@app.get("/user")
async def get_user(access_token: str | None = None, firebase_id: str | None = None):
    if firebase_id is None and access_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not provided",
        )
    if firebase_id is None:
        try:
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Expired token",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token",
            )
        firebase_id = payload.get("id")

    user = await User.objects.filter(firebase_id=firebase_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid user id",
        )

    return {
        "id": user.firebase_id,
        "role": user.role.name,
        "email": user.email,
        "name": user.name,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
