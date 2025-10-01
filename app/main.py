from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from pathlib import Path

app = FastAPI()

# Carrega variáveis de ambiente do .env automaticamente
# 1) Primeiro tenta o .env do diretório atual
# 2) Depois tenta explicitamente o .env na raiz do projeto (um nível acima de app/)
load_dotenv()
project_root_env = Path(__file__).resolve().parents[1] / ".env"
if project_root_env.exists():
    load_dotenv(project_root_env, override=False)

# CORS via env: APP_CORS_ORIGINS=dominio1,dominio2 (ou * para liberar)
cors_origins_env = os.getenv("APP_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tratamento global de exceções para manter formato consistente
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={"error": "Método não permitido"})
    if exc.status_code == 400:
        return JSONResponse(status_code=400, content={"error": "Dados inválidos"})
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "success": False,
        "error": "Erro interno do servidor",
        "message": "Desculpe, ocorreu um erro. Por favor, tente novamente."
    })

# Montagem dos routers
# Essenciais (não engolir erros)
from .routers import exchange_rate, feedback
from .routers import messages as chat_messages

app.include_router(exchange_rate.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")

try:
    from .routers import auth
    app.include_router(auth.router, prefix="/api")
except Exception as e:
    print(f"[WARN] Auth não carregado: {e}")
app.include_router(chat_messages.router, prefix="/api")

# Painel (tolerante a falhas – loga erro e segue)
def _try_include(router_module_path: str, attr: str = "router") -> None:
    try:
        module = __import__(router_module_path, fromlist=[attr])
        r = getattr(module, attr)
        app.include_router(r, prefix="/api")
    except Exception as e:
        print(f"[WARN] Falha ao carregar router {router_module_path}: {e}")

_try_include("app.routers.panel.configuracoes")
_try_include("app.routers.panel.convenios")
# _try_include("app.routers.panel.excecoes")  # Removido - integrado com Google Calendar
_try_include("app.routers.panel.faq")
# _try_include("app.routers.panel.horarios")  # Removido - integrado com Google Calendar
_try_include("app.routers.panel.pagamentos")
_try_include("app.routers.panel.parceiros")
_try_include("app.routers.panel.profissionais")
_try_include("app.routers.panel.servicos")
_try_include("app.routers.panel.agendamentos")
_try_include("app.routers.panel.agenda")

# Agendamento
_try_include("app.routers.agendamento")
_try_include("app.routers.clientes")

# Google Calendar
_try_include("app.routers.google_calendar")
