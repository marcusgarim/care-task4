from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import httpx
import jwt

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500/src/index.html")

security = HTTPBearer(auto_error=True)


class GoogleAuthPayload(BaseModel):
    credential: Optional[str] = None  # id_token (JWT do Google)
    access_token: Optional[str] = None  # access_token OAuth2 do Google


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token inválido")
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/google")
async def auth_google(payload: GoogleAuthPayload, request: Request):
    if not payload.credential and not payload.access_token:
        raise HTTPException(status_code=400, detail="Informe credential (id_token) ou access_token")

    user_info: Optional[dict] = None

    async with httpx.AsyncClient(timeout=8.0) as client:
        # Preferir validar id_token quando disponível
        if payload.credential:
            # Validação via tokeninfo do Google
            r = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": payload.credential})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="id_token inválido")
            data = r.json()
            aud = data.get("aud")
            email = data.get("email")
            email_verified = data.get("email_verified") in (True, "true", "1", 1)
            name = data.get("name")
            picture = data.get("picture")

            if GOOGLE_CLIENT_ID and aud != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=401, detail="id_token não corresponde ao client_id")
            if not email or not email_verified:
                raise HTTPException(status_code=401, detail="Email não verificado")

            user_info = {"email": email, "name": name, "picture": picture, "sub": data.get("sub")}

        elif payload.access_token:
            # Obter dados do usuário via userinfo endpoint
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {payload.access_token}"}
            )
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="access_token inválido")
            data = r.json()
            email = data.get("email")
            email_verified = data.get("email_verified") in (True, "true", "1", 1)
            if not email or not email_verified:
                raise HTTPException(status_code=401, detail="Email não verificado")
            user_info = {
                "email": email,
                "name": data.get("name"),
                "picture": data.get("picture"),
                "sub": data.get("sub"),
            }

    # Emite nosso JWT
    claims = {
        "sub": user_info["email"],
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "provider": "google",
    }
    token = create_access_token(claims)

    return JSONResponse(content={
        "success": True,
        "token": token,
        "user": user_info,
    })


@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID não configurado")

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={httpx.QueryParams({'redirect_uri': GOOGLE_REDIRECT_URI})['redirect_uri']}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=online"
        "&prompt=consent"
    )
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/callback")
async def google_callback(code: Optional[str] = None, error: Optional[str] = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Erro no login Google: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização ausente")
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        raise HTTPException(status_code=500, detail="Credenciais do Google ausentes")

    async with httpx.AsyncClient(timeout=8.0) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Falha ao trocar código por token")
        token_json = token_res.json()
        id_token = token_json.get("id_token")
        access_token = token_json.get("access_token")
        if not id_token and not access_token:
            raise HTTPException(status_code=401, detail="Token inválido do Google")

        # Preferir validar id_token
        user_info: Optional[dict] = None
        if id_token:
            r = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="id_token inválido")
            data = r.json()
            if data.get("aud") != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=401, detail="audience inválida")
            if data.get("email_verified") not in (True, "true", "1", 1):
                raise HTTPException(status_code=401, detail="Email não verificado")
            user_info = {
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "sub": data.get("sub"),
            }
        else:
            ui = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if ui.status_code != 200:
                raise HTTPException(status_code=401, detail="Falha ao obter userinfo")
            data = ui.json()
            if data.get("email_verified") not in (True, "true", "1", 1):
                raise HTTPException(status_code=401, detail="Email não verificado")
            user_info = {
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "sub": data.get("sub"),
            }

    claims = {
        "sub": user_info["email"],
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "provider": "google",
    }
    token = create_access_token(claims)

    # Seta cookie HttpOnly com o JWT e redireciona para o frontend
    response = RedirectResponse(url=FRONTEND_BASE_URL, status_code=302)
    # Em dev, secure=False; em prod, ajuste para True
    response.set_cookie(
        key="app_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=JWT_EXPIRE_MINUTES * 60,
        path="/"
    )
    return response


