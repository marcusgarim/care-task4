## Documentação Atual — FastAPI + Frontend Estático

Esta documentação explica, de forma didática, como o projeto está organizado após a migração para FastAPI (backend) e HTML/CSS/JS (frontend). Cada arquivo importante é listado com uma explicação breve.

### Visão geral
- **Backend**: `FastAPI` servindo endpoints REST em `http://127.0.0.1:8000/api`.
- **Frontend**: páginas estáticas em `frontend/` servidas por um servidor HTTP simples (ou qualquer servidor de arquivos estáticos).
- **Banco de dados**: MySQL (acessado via `PyMySQL`) para dados do painel, conversas e configurações.
- **IA**: integração com Azure OpenAI (preferencial) ou OpenAI padrão; se não configurado, retorna resposta “mock” (de teste).
- **Legado PHP**: guardado em `backup_php/` para consulta, não é mais utilizado na execução atual.

---

## Backend (pasta `app/`)

### `app/main.py`
- Cria a aplicação FastAPI.
- Adiciona CORS liberado para o front (permitindo chamadas do navegador).
- Define tratadores globais de erro para respostas JSON amigáveis.
- Conecta os roteadores (rotas HTTP) do projeto com prefixo `/api`.

Você acessará a API sempre por `http://127.0.0.1:8000/api/...`.

### `app/core/db.py`
- Função `get_db()` abre conexão MySQL (via variáveis de ambiente `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`).
- Entrega a conexão para a rota e garante o fechamento ao final.

### `app/services/currency_service.py`
- Busca a taxa USD→BRL em API pública (`awesomeapi`).
- Possui fallback para `5.00` caso a API falhe.
- Converte valores e formata em `pt-BR` (ex.: `R$ 10,00`).

### `app/services/openai_service.py`
- Serviço de IA unificado.
- Usa Azure OpenAI se as variáveis estiverem definidas (`AZURE_OPENAI_*`).
- Caso contrário, tenta OpenAI padrão (`OPENAI_API_KEY`/`OPENAI_MODEL`).
- Se nenhuma opção estiver configurada, a rota de chat usa um “mock” de resposta.
- Principal método: `generate_reply(user_message, session_id, is_first)`, que retorna `{ message, tokens }`.

Variáveis de ambiente relevantes:
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`
- `OPENAI_API_KEY`, `OPENAI_MODEL` (opcional)

### `app/schemas/feedback.py`
- Modelos (esquemas) de entrada para validação automática do FastAPI:
  - `FeedbackIn`: dados para registrar feedback de uma resposta.
  - `RewriteIn`: dados para salvar uma reescrita da resposta.
  - `ChatIn`: dados de entrada do chat (`message`, `sessionId`, `isFirst`).

### Rotas de API (pasta `app/routers/`)

#### `app/routers/exchange_rate.py`
- `GET /api/exchange-rate`: retorna a taxa do dólar e a mesma taxa formatada.

#### `app/routers/feedback.py`
- `POST /api/feedback`: registra feedback (positivo/negativo) da última conversa da sessão.
- `POST /api/rewrite`: salva uma reescrita da última resposta (para treinamento).
- `POST /api/chat`: endpoint principal do chat. Tenta IA (Azure/OpenAI) e, se indisponível, responde com texto “mock”.

Observação: as rotas de `feedback`/`rewrite` requerem MySQL funcionando, pois gravam no banco.

#### Rotas do painel (pasta `app/routers/panel/`)
- `configuracoes.py`
  - `GET /api/panel/configuracoes`: lista chaves/valores de configuração.
  - `POST /api/panel/configuracoes`: atualiza as configurações enviadas.
- `profissionais.py`
  - `GET /api/panel/profissionais`: lista profissionais.
  - `POST /api/panel/profissionais`: cria profissional.
  - `PUT /api/panel/profissionais`: atualiza campos informados.
  - `DELETE /api/panel/profissionais`: exclui (hard delete) por `id`.
- `servicos.py`
  - `GET /api/panel/servicos[?id=N]`: lista todos ou retorna um específico.
  - `POST /api/panel/servicos`: cria serviço.
  - `PUT /api/panel/servicos`: atualiza campos informados.
  - `DELETE /api/panel/servicos`: exclui (hard delete) por `id`.
- `convenios.py`
  - `GET/POST/PUT/DELETE` para convênios aceitos, com campos básicos (nome, registro ANS, observações, ativo).
- `horarios.py`
  - `GET`: lista horários disponíveis (join com profissional).
  - `PUT`: atualiza horas de manhã/tarde, intervalo, ativo e profissional.
  - `DELETE`: exclui horário por `id`.
- `faq.py`
  - `GET`: lista FAQs.
  - `POST`: cria FAQ.
  - `PUT`: atualiza/ativa/desativa.
  - `DELETE`: desativa (soft delete) por `id`.
- `pagamentos.py`, `parceiros.py`, `excecoes.py`
  - Seguem padrão semelhante (listar/criar/atualizar/desativar ou excluir), sempre usando MySQL.

---

## Frontend (pasta `frontend/`)

### `frontend/index.html`
- Estrutura do chat (campo de texto, botão enviar, área de mensagens e painel de debug simples).

### `frontend/assets/js/config.js` e `config.example.js`
- Centraliza a base da API via `window.CONFIG.API_BASE`.
- Copie `config.example.js` para `config.js` e ajuste a URL do backend.

### `frontend/assets/js/chat.js`
- Controla o chat no navegador.
- Usa `window.CONFIG.API_BASE` para chamar `POST /api/chat`.
- Busca taxa de câmbio em `GET /api/exchange-rate` usando `API_BASE`.
- Envia feedback em `POST /api/feedback` e reescritas em `POST /api/rewrite`.
- Atualiza painel de estatísticas (tokens e custos) e registra logs de debug.

### `frontend/panel.html`
- Interface do painel administrativo com abas (configurações, profissionais, serviços, convênios, horários, agenda, FAQ, pagamentos, parceiros).

### `frontend/assets/js/panel.js`
- Usa `window.CONFIG.API_BASE` como base para `/api/panel/...`.
- Carrega dados e faz operações de CRUD chamando as rotas do backend.
- Mostra mensagens de erro/sucesso na interface.
- Requer MySQL ativo e com as tabelas esperadas.

### `frontend/assets/css/*.css`
- Estilos do chat e do painel.

---

## Execução local

### 1) Preparar ambiente Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Variáveis de ambiente
- Banco de dados:
  - `DB_HOST=localhost`
  - `DB_NAME=andreia`
  - `DB_USER=root`
  - `DB_PASS=`
- Azure OpenAI (preferencial):
  - `AZURE_OPENAI_ENDPOINT=...`
  - `AZURE_OPENAI_API_KEY=...`
  - `AZURE_OPENAI_API_VERSION=2025-05-01-preview`
  - `AZURE_OPENAI_DEPLOYMENT=chatbot-care`
- OpenAI padrão (opcional):
  - `OPENAI_API_KEY=...`
  - `OPENAI_MODEL=gpt-4o-mini`

Você pode exportar no shell ou usar um arquivo `.env` na raiz do projeto.

### 3) Rodar o backend (FastAPI)
```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4) Rodar o frontend (estático)
```bash
python3 -m http.server 5500 -d frontend
# Abra http://127.0.0.1:5500/index.html
```

Antes de abrir, copie `frontend/assets/js/config.example.js` para `frontend/assets/js/config.js` e ajuste `API_BASE`.

---

## Dicas e problemas comuns

- Se `POST /api/feedback` ou rotas de painel retornarem 500, provavelmente o MySQL não está rodando ou as tabelas não existem. Solução: subir MySQL e ajustar `DB_*`.
- Se `POST /api/chat` retornar erro 404 “Resource not found” vindo da Azure, revise:
  - Nome do deployment (`AZURE_OPENAI_DEPLOYMENT`) — precisa existir no seu recurso.
  - Endpoint (`AZURE_OPENAI_ENDPOINT`) — use o domínio do seu recurso.
  - Versão de API — `2025-05-01-preview` (ou outra habilitada no recurso).
- CORS configurável via env: defina `APP_CORS_ORIGINS` (ex.: `https://seu-front.com,https://staging.seu-front.com`) no backend.
- Sem chaves de IA, o chat devolve uma resposta “mock” útil para testes de UI.

---

## Legado PHP
- O código anterior (PHP) foi movido para `backup_php/` (inclusive `public/`, `src/`, `vendor/`, `composer.*`).
- O front não chama mais endpoints PHP; toda API agora é servida pelo FastAPI.

---

## Checklist rápido
- [ ] Instalar dependências Python (`requirements.txt`).
- [ ] Configurar variáveis de ambiente (DB e Azure/OpenAI).
- [ ] Subir FastAPI em `127.0.0.1:8000`.
- [ ] Servir frontend e abrir `http://127.0.0.1:5500/index.html`.
- [ ] Enviar mensagem no chat (deverá responder via IA ou mock).
- [ ] Acessar `panel.html` e validar chamadas (requer MySQL).
