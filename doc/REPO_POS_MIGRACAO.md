### Guia do Repositório (depois da migração) — explicado como se você tivesse 16 anos

Este projeto é um assistente virtual para uma clínica. Pense assim:
- **Frontend** = a "cara" com quem você conversa (a página de chat).
- **Backend** = o "cérebro" que pensa e fala com a IA (OpenAI) e com o banco.
- **Banco de dados** = a "memória" onde guardamos conversas, custos e configurações.

### O que mudou com a migração

- A branch `dev` agora está igual à `front` (o conteúdo da `front` foi levado para a `dev`).
- Isso significa que o que você vê em `frontend/` é o que a `dev` entrega agora.

### Como tudo se conecta (visão geral)

1) Você digita uma mensagem na página `frontend/index.html`.
2) O arquivo `frontend/assets/js/chat.js` envia sua mensagem para o servidor (endpoint `public/api/chat.php`).
3) No servidor, o `ChatController` junta contexto, chama a IA (`OpenAIService`) e executa funções de negócio (`AgentFunctions`).
4) A resposta volta para a página do chat e aparece bonitinha na tela.
5) A conversa e alguns números (tokens, custo estimado) são salvos no banco.

### Onde ficam as coisas

- `frontend/`
  - `index.html`: a página do chat.
  - `assets/js/chat.js`: manda mensagem para o backend e mostra as respostas.
  - `assets/css/chat.css`: estilos do chat.
  - `assets/img/`: imagens (ex.: avatar).

- `public/`
  - `api/chat.php`: endpoint principal do chat (recebe `message`, `sessionId`).
  - `api/exchange-rate.php`: fornece a taxa de câmbio (dólar→real) para calcular custos.
  - `api/feedback.php` e `api/rewrite.php`: salvam feedback e reescritas das respostas.
  - `panel/`: páginas do painel administrativo (configurações, serviços, etc.).

- `src/`
  - `Controllers/ChatController.php`: orquestra tudo (sessão, contexto, IA, funções e salvamento da conversa).
  - `Services/OpenAIService.php`: fala com a OpenAI (suporta a API nova de Responses e a antiga de Chat).
  - `Services/AgentFunctions.php`: onde ficam as funções de negócio (buscar horários, criar agendamento, etc.).
  - `Services/SessionService.php`: cuida dos dados do paciente na sessão (nome, telefone, etapa do agendamento).
  - `Services/DatabaseService.php` + `Config/Database.php`: conexão e consultas no MySQL.
  - `Services/LoggerService.php`: logs detalhados da IA em `openai_debug.log`.
  - `Services/CurrencyService.php`: pega/cached a taxa de câmbio para calcular custo em reais.

### Fluxo de uma mensagem (passo a passo)

1. Front manda POST para `public/api/chat.php` com `{ message, sessionId, isFirst }`.
2. `ChatController->processMessage(...)`:
   - Verifica/atualiza sessão (`SessionService`).
   - Monta contexto (configs da clínica, histórico, dados do paciente, data/hora).
   - Cria um "prompt" com regras claras do que a IA deve fazer.
   - Define a lista de funções que a IA pode chamar (ex.: `verificar_horarios_disponiveis`, `criar_agendamento`).
   - Chama a IA via `OpenAIService->chat(...)`.
   - Se a IA pedir para chamar uma função, executa em `AgentFunctions` e devolve o resultado para a IA finalizar a resposta.
   - Formata uma resposta curta e direta para a paciente.
   - Salva a conversa no banco em `conversas`, junto com tokens e custo estimado (convertido em reais com `CurrencyService`).

### Regras importantes que o sistema segue

- Sobre horários: NUNCA inventa. Sempre chama `verificar_horarios_disponiveis` e usa só o que a função retornar.
- Para confirmar agendamento: só depois que `validar_horario_para_agendamento` disser que dá e a paciente confirmar, aí chama `criar_agendamento`.
- Sobre serviços, preços e convênios: só responde depois de chamar as funções `buscar_servicos_clinica` ou `verificar_convenio`.
- Nome e telefone: se não tiver na sessão, pede antes de avançar no agendamento. Se já tiver, não pede de novo.

### Sessão (como o sistema "lembra" de você durante a conversa)

- `SessionService` guarda na sessão PHP (via `sessionId`):
  - `nome` e `telefone` da paciente.
  - etapa do agendamento (para saber em que parte do fluxo está).
  - expira depois de ~1 hora parada.

### Banco de dados (o que é salvo)

- Conversas: mensagem do usuário, resposta da IA, função chamada (se teve), e custo estimado.
- Configurações: dados da clínica (endereço, telefone, etc.) e também a taxa de câmbio cacheada.
- Erros: logs de erros (ex.: falha na IA) em `erros_sistema`.

Obs.: As tabelas exatas podem variar, mas o código usa nomes como `conversas`, `configuracoes` e `erros_sistema`.

### Custos e câmbio (por que aparece um valor em R$)

- A IA cobra por tokens. O front mostra tokens e custo estimado.
- `CurrencyService` busca a taxa USD→BRL e salva no banco para reusar.
- O cálculo (simplificado) acontece no servidor e o front exibe em reais.

### Arquivos e pontos que valem atenção

- `frontend_oficial/frontend`: isso é um repositório Git dentro do seu repo. Se for intencional, transforme em submódulo. Se não for, remova do index com `git rm --cached -r frontend_oficial/frontend` e adicione ao `.gitignore`.
- Imagem `Andréia`: houve normalização de nome/acentos. No `frontend/` é `assets/img/andreia.png`.

### Variáveis de ambiente (crie um `.env`)

Coloque na raiz do projeto (mesmo nível de `composer.json`):
- `OPENAI_API_KEY` e `OPENAI_MODEL` (ex.: `gpt-5.1-mini` ou similar).
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` (acesso ao MySQL).

### Como rodar local (simples)

1) Instale dependências PHP: `composer install`.
2) Crie o `.env` com as chaves acima.
3) Suba um servidor PHP apontando para `public/` (document root):
   - `php -S 127.0.0.1:8000 -t public`
4) Abra `http://127.0.0.1:8000/` no navegador.

Se quiser abrir o HTML puro em `frontend/index.html`, os endpoints `api/*` podem não funcionar por causa de caminho/origem. Prefira rodar via `public/`.

### Branches (depois da migração)

- `front`: continua sendo onde você pode trabalhar no front.
- `dev`: agora tem o mesmo conteúdo que `front` (no momento da migração).
- Dica: quando quiser atualizar `dev` com o que ficou commitado em `front`, repita o merge preferindo `front` (o time já documentou em `doc/FRONT_MIGRATION.md`).

### TL;DR (resumo)

- Você conversa na página do chat → o backend fala com a OpenAI e com o banco → a resposta volta para a tela → tudo importante fica salvo. `dev` agora reflete o front que você vê em `frontend/`.


