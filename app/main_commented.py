"""
ARQUIVO PRINCIPAL DA API - MAIN.PY
==================================

PARA INICIANTES:
Este é o arquivo principal que inicia toda a aplicação FastAPI.
É aqui que configuramos o servidor, definimos regras gerais e 
conectamos todas as rotas (endpoints) da aplicação.

Think of it as the "central hub" that coordinates everything.
"""

# IMPORTAÇÕES: Trazendo as ferramentas necessárias
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

# CRIANDO A APLICAÇÃO FASTAPI
# Isso cria uma instância do servidor web que vai receber requisições
app = FastAPI()

# CONFIGURANDO CORS (Cross-Origin Resource Sharing)
# CORS permite que o frontend (rodando em outro domínio/porta) acesse nossa API
cors_origins_env = os.getenv("APP_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,        # Configure via env APP_CORS_ORIGINS
    allow_credentials=True,             # Permite envio de cookies e credenciais
    allow_methods=["*"]                # Permite todos os métodos HTTP (GET, POST, PUT, DELETE, etc.)
)

# TRATAMENTO GLOBAL DE ERROS HTTP
# Quando algo der erro na API, esta função padroniza como retornar a mensagem
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Captura erros HTTP específicos e retorna mensagens padronizadas em português
    
    Parâmetros:
    - request: A requisição que gerou o erro
    - exc: A exceção HTTP que foi lançada
    """
    # Erro 405: Método não permitido (ex: fazer POST numa rota que só aceita GET)
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={"error": "Método não permitido"})
    
    # Erro 400: Dados enviados estão incorretos
    if exc.status_code == 400:
        return JSONResponse(status_code=400, content={"error": "Dados inválidos"})
    
    # Para outros erros HTTP, retorna a mensagem original
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

# TRATAMENTO GLOBAL DE ERROS INESPERADOS
# Quando algo der muito errado no servidor, esta função cuida do retorno
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Captura qualquer erro não previsto no sistema e retorna uma mensagem amigável
    
    Isso evita que o usuário veja mensagens técnicas assustadoras
    """
    return JSONResponse(status_code=500, content={
        "success": False,
        "error": "Erro interno do servidor",
        "message": "Desculpe, ocorreu um erro. Por favor, tente novamente."
    })

# REGISTRANDO AS ROTAS (ENDPOINTS) DA API
# Aqui importamos e conectamos todos os arquivos que definem as rotas da aplicação
try:
    # Importando os módulos de rotas
    from .routers import exchange_rate, feedback
    
    # Importando rotas do painel administrativo
    from .routers.panel import configuracoes as panel_configuracoes
    from .routers.panel import convenios as panel_convenios
    from .routers.panel import excecoes as panel_excecoes
    from .routers.panel import faq as panel_faq
    from .routers.panel import horarios as panel_horarios
    from .routers.panel import pagamentos as panel_pagamentos
    from .routers.panel import parceiros as panel_parceiros
    from .routers.panel import profissionais as panel_profissionais
    from .routers.panel import servicos as panel_servicos

    # CONECTANDO AS ROTAS PRINCIPAIS
    # prefix="/api" significa que todas essas rotas começarão com /api/
    app.include_router(exchange_rate.router, prefix="/api")     # Rotas de câmbio
    app.include_router(feedback.router, prefix="/api")         # Rotas de feedback

    # CONECTANDO AS ROTAS DO PAINEL ADMINISTRATIVO
    # Todas estas também usam prefix="/api"
    app.include_router(panel_configuracoes.router, prefix="/api")   # /api/configuracoes/*
    app.include_router(panel_convenios.router, prefix="/api")       # /api/convenios/*
    app.include_router(panel_excecoes.router, prefix="/api")        # /api/excecoes/*
    app.include_router(panel_faq.router, prefix="/api")             # /api/faq/*
    app.include_router(panel_horarios.router, prefix="/api")        # /api/horarios/*
    app.include_router(panel_pagamentos.router, prefix="/api")      # /api/pagamentos/*
    app.include_router(panel_parceiros.router, prefix="/api")       # /api/parceiros/*
    app.include_router(panel_profissionais.router, prefix="/api")   # /api/profissionais/*
    app.include_router(panel_servicos.router, prefix="/api")        # /api/servicos/*

except Exception:
    # Se alguma importação falhar, o programa continua funcionando
    # Isso evita que a aplicação inteira pare por causa de um módulo com problema
    pass

"""
RESUMO DO QUE ESTE ARQUIVO FAZ:

1. Cria a aplicação FastAPI
2. Configura CORS para permitir acesso do frontend
3. Define como tratar erros de forma padronizada
4. Importa e registra todas as rotas da aplicação
5. Organiza as rotas com prefixos (/api/)

Quando você roda 'uvicorn app.main:app', este arquivo é executado
e a variável 'app' se torna o servidor web que responde às requisições.
"""
