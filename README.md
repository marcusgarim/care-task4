# Sistema de Assistente Virtual Médico - Smart Schedule

## Visão Geral do Sistema

O sistema é uma aplicação completa de assistente virtual para clínicas médicas, desenvolvida em **FastAPI** (Python) com frontend estático (HTML/CSS/JavaScript) e integração às APIs da OpenAI / Azure OpenAI. O foco principal é fornecer um painel administrativo completo para gerenciamento de clínicas e um chat de atendimento inteligente.

## Arquitetura do Sistema

### Estrutura de Diretórios

```text
smart-schedule/
├── app/                        # Backend FastAPI
│   ├── main.py                # Arquivo principal da aplicação
│   ├── core/                  # Núcleo da aplicação
│   │   └── db.py             # Gerenciamento de conexões (MySQL/PostgreSQL)
│   ├── routers/              # Endpoints da API REST
│   │   ├── exchange_rate.py  # API de taxa de câmbio
│   │   ├── feedback.py       # Sistema de feedback e chat
│   │   ├── messages.py       # Chat com contexto/sumarização (PostgreSQL)
│   │   ├── auth.py           # Autenticação Google e emissão de JWT
│   │   └── panel/            # Rotas do painel administrativo
│   │       ├── configuracoes.py
│   │       ├── convenios.py
│   │       ├── excecoes.py
│   │       ├── faq.py
│   │       ├── horarios.py
│   │       ├── pagamentos.py
│   │       ├── parceiros.py
│   │       ├── profissionais.py
│   │       └── servicos.py
│   ├── schemas/              # Modelos de dados Pydantic
│   │   └── feedback.py
│   └── services/            # Serviços especializados
│       ├── currency_service.py  # Conversão de moeda
│       └── openai_service.py    # Integração com OpenAI/Azure
├── src/                     # Frontend estático
│   ├── index.html           # Interface principal do chat
│   ├── login.html           # Tela de login (Google OAuth)
│   ├── panel.html           # Painel administrativo
│   └── assets/              # Recursos estáticos
│       ├── css/             # Estilos
│       ├── js/              # JavaScript
│       └── img/             # Imagens e ícones
├── doc/                    # Documentação específica
├── scripts/                # Scripts utilitários
│   └── bootstrap_pg.py     # Bootstrap PostgreSQL
├── requirements.txt        # Dependências Python
└── .env                    # Variáveis de ambiente
```

### Padrão Arquitetural

O sistema utiliza uma arquitetura **REST API** com **FastAPI**:

- **Routers**: Organizam endpoints por funcionalidade (chat, feedback, painel)
- **Services**: Encapsulam lógica de negócio (OpenAI, conversão de moeda)
- **Schemas**: Validação e serialização de dados com Pydantic
- **Core**: Configurações centrais e conexões de banco
- **Frontend**: Interface estática que consome a API REST

## Componentes Principais

### 1. FastAPI Application (app/main.py)

**Responsabilidade**: Coordenar toda a aplicação e configurar middlewares.

#### Funcionalidades Principais:

##### Configuração CORS
```python
# CORS via env: APP_CORS_ORIGINS=dominio1,dominio2 (ou * para liberar)
cors_origins_env = os.getenv("APP_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env != "*" else ["*"]
```

##### Tratamento Global de Erros
- **HTTPException**: Padroniza respostas de erro HTTP com mensagens em português
- **Exception**: Captura erros inesperados e retorna mensagens amigáveis
- **JSON Response**: Mantém formato consistente de resposta

##### Registro de Routers
- **API Principal**: `/api/chat`, `/api/messages`, `/api/feedback`, `/api/exchange-rate`
- **Painel**: `/api/panel/*` para todas as funcionalidades administrativas
- **Importação Segura**: Usa try/except para evitar falhas de inicialização

### 2. OpenAIService (app/services/openai_service.py)

**Responsabilidade**: Comunicação unificada com OpenAI e Azure OpenAI.

#### Recursos Implementados:

##### Suporte a Múltiplos Provedores
```python
# Azure OpenAI (preferencial se configurado)
if self.azure_endpoint and self.azure_api_key and self.azure_deployment:
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_version=self.azure_api_version,
        azure_endpoint=self.azure_endpoint,
        api_key=self.azure_api_key,
    )

# OpenAI padrão (fallback)
from openai import OpenAI
client = OpenAI(api_key=self.api_key)
```

##### Configuração via Variáveis de Ambiente
- **Azure**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- **OpenAI**: `OPENAI_API_KEY`, `OPENAI_MODEL`
- **Fallback**: Sistema funciona sem configuração, retornando respostas mock

##### Processamento de Respostas
- **Extração de conteúdo**: Obtém texto da resposta de forma segura
- **Contagem de tokens**: Monitora usage para controle de custos
- **Temperatura baixa**: Configurada em 0.2 para respostas mais consistentes
- **Prompt do sistema**: Define comportamento básico em português brasileiro

##### Tratamento de Erros
- **Configuração ausente**: Lança RuntimeError com mensagem clara
- **Falhas de API**: Permite que endpoints de nível superior implementem fallbacks
- **Validação**: Verifica configuração antes de tentar conectar

### 3. Database Service (app/core/db.py)

**Responsabilidade**: Gerenciar conexões de banco de dados com suporte a múltiplos SGBDs.

#### Funcionalidades Implementadas:

##### Suporte Dual MySQL/PostgreSQL
```python
# PostgreSQL (preferencial se PGHOST definido)
if pghost and psycopg is not None:
    connection = psycopg.connect(
        host=pghost,
        port=int(os.getenv("PGPORT", "5432")),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        dbname=os.getenv("PGDATABASE"),
        sslmode=os.getenv("PGSSLMODE", "require"),
        row_factory=pg_dict_row,
    )

# MySQL (fallback)
connection = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", ""),
    database=os.getenv("DB_NAME", "andreia"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)
```

##### Características
- **Generator Pattern**: Usa `yield` para gerenciar lifecycle da conexão
- **Autocommit**: Habilitado por padrão em ambos os SGBDs
- **Dict Cursor**: Retorna resultados como dicionários
- **Detecção de Tipo**: Função `is_postgres_connection()` para queries específicas
- **SSL**: Configuração automática para PostgreSQL

### 4. CurrencyService (app/services/currency_service.py)

**Responsabilidade**: Conversão de custos USD para BRL e formatação monetária.

#### Funcionalidades Implementadas:

##### Busca de Taxa de Câmbio
```python
def get_dollar_to_real_rate(self) -> float:
    try:
        rate = self._fetch_from_api()
        if rate and rate > 0:
            return rate
        # fallback conservador
        return 5.00
    except Exception:
        return 5.00
```

##### Integração com API Externa
- **Fonte**: API pública do AwesomeAPI (`economia.awesomeapi.com.br`)
- **Timeout**: 5 segundos para evitar travamentos
- **User-Agent**: Customizado para identificação (`Andreia32/1.0`)
- **Fallback**: Taxa conservadora de R$ 5,00 em caso de erro

##### Conversão e Formatação
```python
def convert_dollar_to_real(self, dollar_amount: float) -> float:
    rate = self.get_dollar_to_real_rate()
    return dollar_amount * rate

def format_real(self, value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
```

##### Características
- **Formato brasileiro**: Vírgula para decimais, ponto para milhares
- **Tolerância a falhas**: Nunca falha, sempre retorna um valor
- **Performance**: Cliente HTTP configurado para reutilização
- **Tratamento de erro silencioso**: Protege a aplicação de falhas externas

## Fluxo de Dados

### 1. Requisição de Chat

```text
Frontend (chat.js) 
    ↓ POST /api/chat
FastAPI Router (feedback.py)
    ↓ @router.post("/chat")
OpenAIService
    ├── Azure OpenAI (preferencial)
    ├── OpenAI (fallback)
    └── Mock Response (sem configuração)
        ↓
Resposta JSON com tokens/custo
    ↓
Frontend atualiza UI e estatísticas
```

### 2. Requisição do Painel Administrativo

```text
Frontend (panel_modern.js)
    ↓ GET/POST/PUT/DELETE /api/panel/{recurso}
FastAPI Router (panel/{recurso}.py)
    ↓ Depends(get_db)
Database Connection (MySQL/PostgreSQL)
    ↓ Cursor operations
    ↓ CRUD operations
Resposta JSON padronizada
    ↓
Frontend atualiza tabelas/formulários
```

### 3. Fluxo de Feedback e Treinamento

```text
Usuário clica thumbs up/down
    ↓ POST /api/feedback
Busca conversa mais recente
    ↓ INSERT conversas_treinamento
Dados salvos para melhoria do modelo
    ↓
Resposta de confirmação

Usuário reescreve resposta
    ↓ POST /api/rewrite
Salva resposta original + reescrita
    ↓ conversas_treinamento
Sistema de aprendizado colaborativo
```

### 4. Taxa de Câmbio

```text
Frontend solicita taxa
    ↓ GET /api/exchange-rate
CurrencyService.get_dollar_to_real_rate()
    ↓ API Externa (awesomeapi.com.br)
    ↓ Fallback (R$ 5,00)
Resposta formatada em BRL
    ↓
Frontend calcula custos em reais
```

## Estrutura do Banco de Dados

### Schema PostgreSQL (Preferencial)

O sistema suporta PostgreSQL como banco principal, com schema definido em `doc/bootstrap_pg.sql`:

#### `configuracoes`
```sql
CREATE TABLE IF NOT EXISTS configuracoes (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  chave VARCHAR(100) UNIQUE,
  valor TEXT,
  updated_at TIMESTAMP NULL
);
```

#### `profissionais`
```sql
CREATE TABLE IF NOT EXISTS profissionais (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    especialidade VARCHAR(255),
    crm VARCHAR(50),
  ativo INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL
);
```

#### `servicos_clinica`
```sql
CREATE TABLE IF NOT EXISTS servicos_clinica (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  descricao TEXT,
  valor NUMERIC(10,2),
  categoria VARCHAR(100),
  palavras_chave TEXT,
    observacoes TEXT,
  preparo_necessario TEXT,
  anestesia_tipo VARCHAR(100),
  local_realizacao VARCHAR(255),
  ativo INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL
);
```

#### `convenios_aceitos`
```sql
CREATE TABLE IF NOT EXISTS convenios_aceitos (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
  registro_ans VARCHAR(50),
  observacoes TEXT,
  ativo INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL
);
```

#### `horarios_disponiveis`
```sql
CREATE TABLE IF NOT EXISTS horarios_disponiveis (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  profissional_id INTEGER,
  dia_semana VARCHAR(20) NOT NULL,
  manha_inicio TIME,
  manha_fim TIME,
    tarde_inicio TIME,
    tarde_fim TIME,
  intervalo_minutos INTEGER,
  ativo INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL
);
```

#### `conversas` e `conversas_treinamento`
```sql
CREATE TABLE IF NOT EXISTS conversas (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  session_id VARCHAR(100) NOT NULL,
    mensagem_usuario TEXT,
    resposta_agente TEXT,
  tokens_prompt INTEGER,
  tokens_completion INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversas_treinamento (
  id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  conversa_id INTEGER NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  resposta_original TEXT,
  resposta_reescrita TEXT,
  contexto_conversa TEXT,
  feedback_tipo VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Outras Tabelas do Sistema

- **`excecoes_agenda`**: Feriados e exceções de horário
- **`faq`**: Perguntas frequentes
- **`formas_pagamento`**: Métodos de pagamento aceitos
- **`parceiros`**: Laboratórios e parceiros da clínica
- **`erros_sistema`**: Log de erros da aplicação

### Compatibilidade MySQL

O sistema mantém compatibilidade com MySQL como fallback, utilizando as mesmas estruturas mas com sintaxe MySQL (AUTO_INCREMENT, etc.).

## Frontend Interface

### Chat Interface (src/index.html)

A interface principal do sistema oferece:

#### Funcionalidades do Chat
- **Interface limpa**: Campo de input com botão de envio
- **Histórico visual**: Mensagens do usuário e assistente
- **Indicador de digitação**: Feedback visual durante processamento
- **Botões de feedback**: Thumbs up/down para avaliar respostas
- **Sistema de reescrita**: Permite melhorar respostas da IA

#### Painel de Debug
```javascript
// Estatísticas em tempo real
document.getElementById('totalTokens').textContent = totalTokens;
document.getElementById('totalCost').textContent = 'R$ ' + totalCost.toFixed(4);

// Logs de debug para desenvolvimento
addDebugLog('Função executada', { name: functionName, result: result });
```

#### Sistema de Sessão
- **Session ID único**: Gerado automaticamente para cada conversa
- **Persistência local**: Mantém contexto durante a sessão
- **Nova conversa**: Botão para reiniciar com novo session ID

### Painel Administrativo (src/panel.html)

Interface completa para gerenciamento da clínica:

#### Abas do Sistema
- **Configurações**: Nome da clínica, assistente virtual
- **Profissionais**: CRUD completo (criar, listar, editar, excluir)
- **Serviços**: Gerenciar procedimentos oferecidos
- **Convênios**: Lista de convênios aceitos
- **Horários**: Configuração de disponibilidade
- **Exceções**: Feriados e bloqueios de agenda
- **FAQ**: Perguntas frequentes
- **Pagamentos**: Formas de pagamento aceitas
- **Parceiros**: Laboratórios e clínicas parceiras

#### Características do Painel
```javascript
// Configuração dinâmica da API
const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? 
    window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';

// Operações CRUD padronizadas
fetch(`${API_BASE}/panel/profissionais`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
});
```

## Configuração e Execução

### 0. Pré‑requisitos

- Python 3.10+ instalado no sistema (recomendado 3.11+)
- Acesso a um banco de dados (PostgreSQL recomendado; MySQL funciona como fallback)
- (Opcional) Chave da OpenAI ou Azure OpenAI para evitar respostas "mock"

### Início Rápido (recomendado para desenvolvimento)

Use o script de desenvolvimento para configurar tudo automaticamente (ambiente virtual, dependências, bootstrap opcional do banco, backend e frontend):

```bash
bash scripts/dev.sh
```

URLs:
- Backend: `http://127.0.0.1:8000`
- Chat: `http://127.0.0.1:5500/index.html`
- Painel: `http://127.0.0.1:5500/panel.html`

Se aparecer "uvicorn: command not found", o `scripts/dev.sh` já resolve isso ao criar/ativar o venv e instalar dependências.

### 1. Dependências do Sistema

#### Python Requirements (requirements.txt)
```text
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.8.2
python-dotenv==1.0.1
pymysql==1.1.0
httpx==0.27.0
openai==1.51.0
psycopg[binary]==3.1.18
PyJWT==2.8.0
```

#### Instalação
```bash
# Criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Banco de Dados PostgreSQL (preferencial)
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=sua_senha
PGDATABASE=andreia
PGSSLMODE=require

# Banco de Dados MySQL (fallback)
DB_HOST=localhost
DB_NAME=andreia
DB_USER=root
DB_PASS=

# Azure OpenAI (preferencial)
AZURE_OPENAI_ENDPOINT=https://seu-recurso.openai.azure.com/
AZURE_OPENAI_API_KEY=sua_chave_azure
AZURE_OPENAI_API_VERSION=2025-05-01-preview
AZURE_OPENAI_DEPLOYMENT=seu_deployment

# OpenAI (alternativo)
OPENAI_API_KEY=sk-sua_chave_openai
OPENAI_MODEL=gpt-4o-mini

# CORS (opcional)
APP_CORS_ORIGINS=*

# Autenticação JWT (opcional, usado por /api/auth/*)
JWT_SECRET=altere-este-segredo
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Google OAuth (opcional, usado por /api/auth/google/*)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/auth/google/callback

# Base do frontend para redireciono pós-login (auth callback)
FRONTEND_BASE_URL=http://127.0.0.1:5500/src/index.html

# Token de proteção simples para /api/messages (opcional)
# Se definido, enviar Authorization: Bearer <APP_AUTH_TOKEN>
APP_AUTH_TOKEN=
```

### 3. Configuração do Banco de Dados

#### PostgreSQL (Recomendado)
```bash
# Executar bootstrap
python scripts/bootstrap_pg.py
```

#### MySQL (Fallback)
```bash
# Executar script SQL
mysql -u root -p andreia < doc/bootstrap.sql
```

### 4. Executando o Sistema

#### Backend (FastAPI)
```bash
# Desenvolvimento
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Produção
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend (Servidor Estático)
```bash
# Editar src/assets/js/config.js com a URL do backend
# window.CONFIG = { API_BASE: 'http://127.0.0.1:8000/api' };

# Servir arquivos estáticos
python3 -m http.server 5500 -d src

# Acessar: http://127.0.0.1:5500/index.html
```

Observação: preferencialmente use `bash scripts/dev.sh` para evitar problemas de ambiente.

## API Endpoints Disponíveis

### Chat e Feedback
- **POST `/api/chat`**: Endpoint principal do chat com IA
- **POST `/api/messages`**: Chat com contexto (histórico, sumarização e snapshot do painel)
  - Requer PostgreSQL para recursos avançados
  - Se `APP_AUTH_TOKEN` estiver definido, enviar header `Authorization: Bearer <token>`
- **POST `/api/feedback`**: Registrar feedback (positivo/negativo)
- **POST `/api/rewrite`**: Salvar reescrita de resposta
- **GET `/api/exchange-rate`**: Obter taxa de câmbio USD→BRL

### Painel Administrativo
- **GET/POST/PUT/DELETE `/api/panel/configuracoes`**: Configurações gerais
- **GET/POST/PUT/DELETE `/api/panel/profissionais`**: Gerenciar profissionais
- **GET/POST/PUT/DELETE `/api/panel/servicos`**: Gerenciar serviços
- **GET/POST/PUT/DELETE `/api/panel/convenios`**: Gerenciar convênios
- **GET/POST/PUT/DELETE `/api/panel/horarios`**: Configurar horários
- **GET/POST/PUT/DELETE `/api/panel/faq`**: Perguntas frequentes
- **GET/POST/PUT/DELETE `/api/panel/pagamentos`**: Formas de pagamento
- **GET/POST/PUT/DELETE `/api/panel/parceiros`**: Laboratórios parceiros
- **GET/POST/PUT/DELETE `/api/panel/excecoes`**: Exceções de agenda

### Autenticação
- **POST `/api/auth/google`**: Recebe `credential` (id_token) ou `access_token` e retorna JWT
- **GET `/api/auth/google/login`**: Inicia login Google (redirect)
- **GET `/api/auth/google/callback`**: Callback do Google; seta cookie `app_token` e redireciona ao frontend

Fluxo de login (Google):
1. Configure no `.env` os campos `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_REDIRECT_URI`.
2. Abra `src/login.html` e clique em "Entrar com Google".
3. Após o callback, um cookie `app_token` é definido e o endpoint `/api/auth/me` passa a retornar seus dados.
4. Regras de admin: o primeiro usuário que fizer login vira admin automaticamente. Usuários inativos não acessam o painel.

### Características das APIs
- **Validação automática**: Schemas Pydantic garantem dados corretos
- **Respostas padronizadas**: JSON consistente em todas as rotas
- **Tratamento de erros**: Mensagens em português brasileiro
- **CORS configurável**: Suporte a diferentes domínios frontend

## Recursos Adicionais

### Scripts de Utilitários

#### Bootstrap PostgreSQL (scripts/bootstrap_pg.py)
- Script para inicialização automática do banco PostgreSQL
- Parse inteligente de statements SQL com suporte a comentários
- Execução transacional com rollback em caso de erro
- Logs detalhados de progresso

#### Documentação Específica (doc/)
- **doc_fastAPI.md**: Guia da aplicação FastAPI
- **doc_cambio.md**: Sistema de conversão monetária
- **doc_logging.md**: Estratégias de logging e monitoramento
- **doc_migração.md**: Migração e considerações
- **doc_assistant_system.md**: Sistema do assistente
- **doc_profissionais.md**: Estrutura de profissionais

### Arquivos de Configuração

#### Frontend Configuration
```javascript
// src/assets/js/config.js
window.CONFIG = {
    API_BASE: 'http://127.0.0.1:8000/api'
};
```

#### CSS Modules
- **chat.css**: Estilos da interface de chat com animações
- **panel.css**: Layout responsivo do painel administrativo

### Compatibilidade e Migrações

#### Sistema Dual de Banco
- **PostgreSQL**: Banco preferencial com recursos modernos
- **MySQL**: Fallback para compatibilidade com sistemas legados
- **Detecção automática**: Sistema escolhe o banco baseado nas variáveis de ambiente

#### APIs Múltiplas de IA
- **Azure OpenAI**: Integração empresarial preferencial
- **OpenAI**: Fallback para desenvolvimento
- **Mock Mode**: Funciona sem configuração de IA para testes

## Considerações Finais

### Pontos Fortes da Arquitetura Atual
1. **API REST moderna** com FastAPI e validação automática
2. **Frontend desacoplado** permite fácil customização
3. **Suporte dual de banco** garante flexibilidade
4. **Sistema de feedback** permite melhoria contínua
5. **Configuração flexível** via variáveis de ambiente
6. **Documentação abrangente** facilita manutenção

### Troubleshooting (erros comuns)

- "O chat responde com (mock) Você disse...":
  - Falta de configuração da IA. Defina `OPENAI_API_KEY` (ou Azure: `AZURE_OPENAI_*`) no `.env` e reinicie o backend.

- "Não consigo acessar o painel":
  - Faça login em `src/login.html` (Google OAuth). O primeiro login vira admin automaticamente.
  - Verifique no banco a tabela `usuarios`. Para promover manualmente: `UPDATE usuarios SET is_admin=TRUE, ativo=TRUE WHERE email='seu_email';`

- "uvicorn: command not found":
  - Use `bash scripts/dev.sh`, que cria o venv e instala `uvicorn` automaticamente.

- "401/403 nas rotas do painel":
  - Verifique se o cookie `app_token` está presente (ou envie o header `Authorization: Bearer <token>`), se o usuário está `ativo` e se possui `is_admin=TRUE`.

### Próximos Passos Recomendados
1. **Sistema de logs centralizados** (ELK Stack ou similar)
2. **Testes automatizados** (pytest para backend, Jest para frontend)
3. **CI/CD pipeline** para deploy automático
4. **Monitoramento de aplicação** (Prometheus + Grafana)
5. **Containerização** com Docker para facilitar deploys

**Tecnologias utilizadas**: FastAPI, Python, PostgreSQL/MySQL, OpenAI/Azure OpenAI, HTML5, CSS3, JavaScript ES6+.
