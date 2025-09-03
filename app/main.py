from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI()

# CORS via env: APP_CORS_ORIGINS=dominio1,dominio2 (ou * para liberar)
cors_origins_env = os.getenv("APP_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
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
try:
    from .routers import exchange_rate, feedback
    from .routers.panel import configuracoes as panel_configuracoes
    from .routers.panel import convenios as panel_convenios
    from .routers.panel import excecoes as panel_excecoes
    from .routers.panel import faq as panel_faq
    from .routers.panel import horarios as panel_horarios
    from .routers.panel import pagamentos as panel_pagamentos
    from .routers.panel import parceiros as panel_parceiros
    from .routers.panel import profissionais as panel_profissionais
    from .routers.panel import servicos as panel_servicos

    app.include_router(exchange_rate.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")

    app.include_router(panel_configuracoes.router, prefix="/api")
    app.include_router(panel_convenios.router, prefix="/api")
    app.include_router(panel_excecoes.router, prefix="/api")
    app.include_router(panel_faq.router, prefix="/api")
    app.include_router(panel_horarios.router, prefix="/api")
    app.include_router(panel_pagamentos.router, prefix="/api")
    app.include_router(panel_parceiros.router, prefix="/api")
    app.include_router(panel_profissionais.router, prefix="/api")
    app.include_router(panel_servicos.router, prefix="/api")
except Exception:
    pass
