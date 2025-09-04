# Sistema de Assistente Virtual Médico — Documentação Geral

Este documento resume a arquitetura atual do projeto, como executar localmente, variáveis de ambiente, endpoints principais e onde encontrar detalhes adicionais.

## Visão Geral

- Backend em Python com FastAPI, servindo APIs REST em `http://127.0.0.1:8000/api`.
- Frontend estático (HTML/CSS/JS) em `frontend/` consumindo as APIs do backend.
- Banco: PostgreSQL (preferencial) via `psycopg` ou MySQL via `PyMySQL` (fallback).
- Integração com Azure OpenAI (preferencial) ou OpenAI padrão. Sem chaves, o chat funciona em modo "mock".

## Estrutura do Projeto

```
care-task4/
├── app/                      # Backend FastAPI
│   ├── core/db.py            # Conexão com banco (PostgreSQL ou MySQL)
│   ├── main.py               # FastAPI app, CORS, routers
│   ├── routers/              # Endpoints (inclui /api/panel/*)
│   ├── schemas/              # Pydantic (validação input)
│   └── services/             # OpenAI/Azure e câmbio
├── frontend/                 # Frontend estático (chat e painel)
│   ├── index.html            # Chat
│   ├── panel.html            # Painel
│   └── assets/               # CSS, JS, imagens
├── doc/                      # Este diretório (docs e SQL)
│   ├── DOCUMENTACAO_ATUAL_FASTAPI.md
│   ├── CAMBIO_MOEDA.md
│   ├── LOGGING_SYSTEM.md
│   ├── REPO_POS_MIGRACAO.md
│   ├── SESSION_IMPLEMENTATION.md
│   └── bootstrap.sql
├── scripts/
│   └── bootstrap_pg.py       # Script para provisionar PostgreSQL a partir do SQL
└── requirements.txt          # Dependências Python
```

## Execução Local (Desenvolvimento)

1) Preparar Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Variáveis de ambiente (`.env` na raiz ou exportadas)
- Banco (usa PostgreSQL se `PGHOST` estiver definido; senão, MySQL):
  - PostgreSQL: `PGHOST`, `PGPORT` (opcional), `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE` (opcional)
  - MySQL: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`
- CORS: `APP_CORS_ORIGINS` (ex.: `https://seu-front.com,https://staging.seu-front.com` ou `*`)
- Azure OpenAI (preferencial): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION` (padrão `2025-05-01-preview`), `AZURE_OPENAI_DEPLOYMENT`
- OpenAI padrão: `OPENAI_API_KEY`, `OPENAI_MODEL` (padrão `gpt-4o-mini`)

3) Subir backend
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

4) Subir frontend (estático)
```bash
python3 -m http.server 5500 -d frontend
# Acesse http://127.0.0.1:5500/index.html
```
Antes, copie `frontend/assets/js/config.example.js` para `frontend/assets/js/config.js` e ajuste `window.CONFIG.API_BASE`.

## Endpoints

Prefixo: `http://127.0.0.1:8000/api`

- `POST /chat`: Chat com IA (ou "mock" sem chaves).
- `POST /feedback`: Registra feedback da última conversa (requer banco).
- `POST /rewrite`: Salva reescrita da última resposta (requer banco).
- `GET /exchange-rate`: Taxa USD→BRL e formato pt-BR.

### Painel Administrativo (`/api/panel/*`)
- Configurações: `GET/POST /panel/configuracoes`
- Profissionais: `GET/POST/PUT/DELETE /panel/profissionais`
- Serviços: `GET/POST/PUT/DELETE /panel/servicos` (suporta `GET /servicos?id=N`)
- Convênios: `GET/POST/PUT/DELETE /panel/convenios`
- Horários: `GET/PUT/DELETE /panel/horarios`
- Exceções: `GET/POST/PUT/DELETE /panel/excecoes`
- FAQ: `GET/POST/PUT/DELETE /panel/faq`
- Pagamentos: `GET/POST/PUT/DELETE /panel/pagamentos`
- Parceiros: `GET/POST/PUT/DELETE /panel/parceiros`

Observações:
- Rotas do painel e feedback requerem banco ativo e tabelas criadas (ver `bootstrap.sql` e `bootstrap_pg.sql`).
- As respostas seguem JSON padronizado para o frontend.

## Banco de Dados

- Suporta PostgreSQL (psycopg) e MySQL (PyMySQL). A detecção é automática conforme variáveis do ambiente.
- Exemplo de schema MySQL: `doc/bootstrap.sql`.

### Bootstrap PostgreSQL

O repositório inclui um SQL de bootstrap para PostgreSQL e um script auxiliar para executá-lo de forma segura:

- SQL: `doc/bootstrap_pg.sql`
- Script: `scripts/bootstrap_pg.py`

Uso (com variáveis PG configuradas):
```bash
# Variáveis esperadas: PGHOST, PGUSER, PGPASSWORD, PGDATABASE (PGPORT/PGSSLMODE opcionais)
python3 scripts/bootstrap_pg.py
```

Esse script carrega o `.env` da raiz (se existir), divide o SQL em instruções e executa sequencialmente.

## Serviços

- `OpenAIService`: usa Azure OpenAI se configurado; caso contrário, OpenAI. Retorna `{ message, tokens }`.
- `CurrencyService`: busca taxa USD→BRL (awesomeapi) com fallback conservador.

## Documentos Relacionados

- Detalhamento do backend e frontend: `DOCUMENTACAO_ATUAL_FASTAPI.md`
- Câmbio e custos: `CAMBIO_MOEDA.md`
- Sessão e fluxo: `SESSION_IMPLEMENTATION.md`
- Logging: `LOGGING_SYSTEM.md`
- Pós-migração: `REPO_POS_MIGRACAO.md`

## Nota sobre o Frontend

A estrutura e decisões do frontend foram preservadas. Para detalhes específicos (CSS/JS/páginas), consulte `frontend/` e configure `frontend/assets/js/config.js` a partir de `config.example.js`.
