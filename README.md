# Documentação Técnica Completa - Sistema de Assistente Virtual Médico

## Visão Geral do Sistema

O sistema é uma aplicação completa de assistente virtual para clínicas médicas, desenvolvida em PHP com integração à API da OpenAI. O foco principal é automatizar o agendamento de consultas através de conversas naturais, mantendo dados sempre atualizados e fornecendo uma experiência de atendimento personalizada.

## Arquitetura do Sistema

### Estrutura de Diretórios

```
care-task4/
├── public/                     # Arquivos públicos acessíveis via web
│   ├── api/                   # Endpoints da API REST
│   │   ├── chat.php          # Endpoint principal do chat
│   │   ├── feedback.php      # Sistema de feedback das respostas
│   │   ├── rewrite.php       # Sistema de reescrita colaborativa
│   │   └── exchange-rate.php # API de taxa de câmbio
│   ├── css/                  # Estilos da interface
│   ├── js/                   # JavaScript frontend
│   ├── img/                  # Recursos visuais
│   ├── index.php             # Página inicial (redireciona para chat)
│   ├── chat.php              # Interface principal do chat
│   └── panel.php             # Painel administrativo
├── src/                      # Código fonte backend
│   ├── Config/               # Configurações do sistema
│   │   └── Database.php      # Gerenciamento de conexão com banco
│   ├── Controllers/          # Controladores MVC
│   │   └── ChatController.php # Controlador principal do chat
│   └── Services/             # Serviços especializados
│       ├── OpenAIService.php    # Integração com OpenAI
│       ├── AgentFunctions.php   # Funções específicas da clínica
│       ├── DatabaseService.php  # Abstração do banco de dados
│       ├── SessionService.php   # Gerenciamento de sessões
│       ├── LoggerService.php    # Sistema de logging
│       └── CurrencyService.php  # Conversão de moeda
├── database/                 # Scripts e migrações do banco
├── vendor/                   # Dependências Composer
├── .env                      # Variáveis de ambiente
├── composer.json             # Configuração de dependências
└── *.md                      # Documentação específica
```

### Padrão Arquitetural

O sistema utiliza uma arquitetura **Service Layer** com elementos de **MVC**:

- **Controllers**: Orquestram o fluxo de dados entre frontend e services
- **Services**: Encapsulam lógica de negócio específica
- **Config**: Centralizão configurações e conexões
- **API**: Interface REST para comunicação frontend/backend

## Componentes Principais

### 1. ChatController (src/Controllers/ChatController.php)

**Responsabilidade**: Orquestrar todo o fluxo de conversação entre usuário e IA.

#### Métodos Principais:

##### `processMessage($message, $sessionId, $isFirst, $recursionCount)`
- **Entrada**: Mensagem do usuário, ID da sessão, flag primeira mensagem, contador de recursão
- **Saída**: Array com resposta formatada, tokens utilizados e funções chamadas
- **Fluxo**:
  1. Validação de recursão infinita (max 3 tentativas)
  2. Inicialização do SessionService
  3. Verificação de expiração de sessão
  4. Construção do contexto conversacional
  5. Verificação se é primeira pergunta (retorna boas-vindas)
  6. Montagem de mensagens para IA
  7. Chamada da OpenAI com funções disponíveis
  8. Processamento de function calls em loop
  9. Formatação de respostas específicas
  10. Salvamento da conversa no banco

##### `buildContext($sessionId)`
- Busca configurações da clínica
- Recupera histórico de conversas para treinamento
- Obtém dados do paciente da sessão
- Monta contexto temporal (data, hora, dia da semana)
- **Retorna**: Array completo com todo contexto necessário

##### `buildSystemPrompt($contexto)`
- Monta prompt complexo de 800+ linhas
- Inclui regras críticas de comportamento
- Adiciona exemplos de respostas boas/ruins
- Define fluxos obrigatórios de agendamento
- Configura validações de entrada
- **Crítico**: Define que IA NUNCA pode inventar dados

##### `executeFunction($functionName, $args, $sessionId)`
- Executa funções específicas da clínica
- Completa automaticamente dados faltantes da sessão
- Valida dados antes de executar
- Implementa fallbacks inteligentes
- Log detalhado de todas as operações

### 2. OpenAIService (src/Services/OpenAIService.php)

**Responsabilidade**: Comunicação e processamento da API OpenAI.

#### Recursos Implementados:

##### Suporte a Múltiplas APIs
```php
// Detecção automática do modelo
$useResponsesApi = (strpos($normalizedModel, 'gpt-5') !== false || strpos($normalizedModel, 'o-') === 0);

// Chat Completions (GPT-3.5, GPT-4)
POST https://api.openai.com/v1/chat/completions

// Responses API (GPT-5, O-series)
POST https://api.openai.com/v1/responses
```

##### Sistema de Retry com Backoff Exponencial
```php
if ($statusCode === 429 && $attempt < $maxRetries) {
    $waitTime = pow(2, $attempt) * 1000000; // Microsegundos
    usleep($waitTime);
    continue;
}
```

##### Processamento Inteligente de Respostas
- **extractResponseText()**: Extrai texto limpo das respostas complexas
- **handleFunctionCallSummary()**: Gera resumos específicos por função
- **filterInternalNotations()**: Remove anotações técnicas
- **cleanMalformedResponse()**: Detecta e corrige respostas incompletas

##### Mapeamento de Function Calls
- Converte format Responses API para Chat Completions
- Preserva call_ids para continuidade
- Normaliza argumentos JSON

##### Logging Detalhado
- Logs completos de request/response
- Rastreamento de erros e timeouts
- Monitoramento de usage/tokens

### 3. AgentFunctions (src/Services/AgentFunctions.php)

**Responsabilidade**: Implementar todas as funções específicas da clínica.

#### Funções Implementadas:

##### `buscar_profissionais_clinica($params)`
- Busca profissionais ativos por especialidade
- Suporte a busca flexível por nome
- **Regra crítica**: SEMPRE usar antes de mencionar profissionais

##### `buscar_servicos_clinica($params)`
- Lista serviços oferecidos
- Busca por palavras-chave
- Fallback para todos os serviços se busca específica falhar

##### `verificar_convenio($params)`
- Verifica convênios aceitos/inativos
- Retorna observações específicas
- Diferencia status ativo/inativo

##### `verificar_horarios_disponiveis($params)`
- **Algoritmo inteligente**: Busca progressiva em incrementos (10, 20, 30, 40, 50, 60 dias)
- Para quando encontra quantidade desejada de dias com horários
- Filtra horários já passados (margem 30min)
- Valida com exceções de agenda
- **Crítico**: Base para toda validação de agendamentos

```php
// Algoritmo de busca progressiva
$incrementos = [10, 20, 30, 40, 50, 60];
foreach ($incrementos as $incremento) {
    // Verifica período
    if (count($resultado) >= $diasDesejados) {
        break; // Para quando encontra suficientes
    }
}
```

##### `validar_horario_para_agendamento($params)`
- **Validação dupla**: Verifica na lista de disponíveis + banco
- Apenas aceita horários previamente calculados
- Retorna horários alternativos se inválido

##### `criar_agendamento($params)`
- **Validações rigorosas**:
  - Nome completo obrigatório (min 6 chars, 2 palavras)
  - Lista de palavras proibidas (termos médicos/contextuais)
  - Telefone válido (min 10 dígitos)
  - Horário validado previamente
- Busca/cria paciente automaticamente
- Retorna dados formatados para resposta

##### `consultar_agendamento_existente($params)`
- **Prioriza telefone** como identificador principal
- Busca flexível por partes do nome
- Fallback inteligente se nome não bater

##### `reagendar_consulta($params)`
- Cancela agendamento atual + cria novo
- Operação atômica (falha se qualquer etapa falhar)
- Preserva dados do paciente

##### `cancelar_agendamento($params)`
- Validação de existência antes de cancelar
- Horário normalizado para compatibilidade
- Status 'cancelado' (soft delete)

### 4. SessionService (src/Services/SessionService.php)

**Responsabilidade**: Gerenciar estado temporário do usuário.

#### Funcionalidades:

##### Gestão de Dados do Paciente
```php
// Salvar dados
$sessionKey = "paciente_{$this->sessionId}";
$_SESSION[$sessionKey] = [
    'nome' => $nome,
    'telefone' => $telefone,
    'timestamp' => time()
];
```

##### Controle de Expiração
- Timeout: 1 hora (3600 segundos)
- Limpeza automática de dados expirados
- Atualização de timestamp em cada interação

##### Gestão de Etapas de Agendamento
- Rastreamento do progresso do agendamento
- Estados: 'dados_completos', 'horario_escolhido', etc.
- Recuperação de estado em caso de desconexão

### 5. LoggerService (src/Services/LoggerService.php)

**Responsabilidade**: Sistema centralizado de logging.

#### Características:

##### Singleton Pattern
```php
public static function getInstance() {
    if (self::$instance === null) {
        self::$instance = new self();
    }
    return self::$instance;
}
```

##### Níveis de Log
- **DEBUG**: Informações detalhadas de desenvolvimento
- **INFO**: Eventos importantes do sistema
- **WARN**: Situações que podem gerar problemas
- **ERROR**: Erros que precisam atenção

##### Arquivo Centralizado
- Localização: `/openai_debug.log`
- Formato: `[YYYY-MM-DD HH:MM:SS] [LEVEL] message`
- Thread-safe com `LOCK_EX`
- Compatibilidade com `error_log()` existente

### 6. DatabaseService (src/Services/DatabaseService.php)

**Responsabilidade**: Abstração do acesso ao banco de dados.

#### Métodos:

##### `query($sql, $params)`
- Prepared statements para segurança
- Log automático de erros
- Retorno padronizado (array associativo)

##### `execute($sql, $params)`
- Para operações INSERT/UPDATE/DELETE
- Controle de transações
- Contagem de linhas afetadas

##### Tratamento de Erros
- Log em tabela `erros_sistema`
- Falha silenciosa para evitar exposição de dados
- Retry automático em situações específicas

### 7. CurrencyService (src/Services/CurrencyService.php)

**Responsabilidade**: Conversão de custos USD para BRL.

#### Funcionalidades:
- Integração com API do Banco Central
- Cache local da taxa de câmbio
- Fallback para taxa padrão (R$ 5,00)
- Atualização automática diária

## Fluxo de Dados

### 1. Requisição de Chat

```
Frontend (chat.js) 
    ↓ POST /api/chat.php
API Endpoint 
    ↓ new ChatController()
ChatController 
    ↓ processMessage()
    ├── SessionService (recupera dados)
    ├── buildContext() (monta contexto)
    ├── OpenAIService (chama IA)
    └── executeFunction() (executa ações)
        ↓
AgentFunctions 
    ↓ DatabaseService
Banco de Dados
```

### 2. Processamento de Function Calls

```
OpenAI Response com function_call
    ↓
ChatController detecta function_call
    ↓
executeFunction() com argumentos
    ↓
AgentFunctions.{functionName}()
    ↓
DatabaseService query/execute
    ↓
Resultado retornado para IA
    ↓
Nova chamada OpenAI com resultado
    ↓
Resposta final formatada
```

### 3. Gestão de Sessão

```
Usuário fornece dados
    ↓
ChatController.extrairESalvarDados()
    ↓ Análise de contexto
    ↓ Validação estrutural
SessionService.salvarDadosPaciente()
    ↓
$_SESSION["paciente_{sessionId}"]
    ↓
Dados reutilizados em próximas chamadas
```

## Estrutura do Banco de Dados

### Tabelas Principais:

#### `profissionais`
```sql
CREATE TABLE profissionais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    especialidade VARCHAR(255),
    crm VARCHAR(50),
    duracao_consulta INT,
    valor_consulta DECIMAL(10,2),
    ativo TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `agendamentos`
```sql
CREATE TABLE agendamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT,
    data_consulta DATE NOT NULL,
    hora_consulta TIME NOT NULL,
    status ENUM('confirmado', 'pendente', 'cancelado') DEFAULT 'pendente',
    observacoes TEXT,
    procedimento VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
);
```

#### `pacientes`
```sql
CREATE TABLE pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) UNIQUE,
    email VARCHAR(255),
    session_id VARCHAR(255),
    data_nascimento DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `horarios_disponiveis`
```sql
CREATE TABLE horarios_disponiveis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dia_semana ENUM('segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'),
    manha_inicio TIME NOT NULL,
    manha_fim TIME NOT NULL,
    tarde_inicio TIME,
    tarde_fim TIME,
    intervalo_minutos INT,
    ativo INT DEFAULT 1,
    profissional_id INT,
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
);
```

#### `conversas`
```sql
CREATE TABLE conversas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255),
    mensagem_usuario TEXT,
    resposta_agente TEXT,
    funcao_chamada VARCHAR(100),
    tokens_prompt INT DEFAULT 0,
    tokens_resposta INT DEFAULT 0,
    custo_estimado DECIMAL(10,6),
    feedback_tipo ENUM('positivo', 'negativo'),
    resposta_reescrita TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `configuracoes`
```sql
CREATE TABLE configuracoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    descricao VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Relacionamentos:

```
pacientes (1) ←→ (N) agendamentos
profissionais (1) ←→ (N) horarios_disponiveis
conversas → session_id (índice)
```

## Sistema de Prompt Engineering

### Estrutura do System Prompt

O prompt do sistema é construído dinamicamente com mais de 800 linhas, incluindo:

#### 1. Contexto Base
- Data/hora atual
- Especialidades disponíveis
- Dados da clínica (endereço, telefone)
- Dados do paciente (se disponível)

#### 2. Regras Críticas
```
### REGRA CRÍTICA - MÁXIMA PRIORIDADE
**NUNCA USE:** "Vou verificar...", "Posso verificar...", "Deixe-me verificar..."
**SEMPRE:** **CHAME A FUNÇÃO IMEDIATAMENTE** e informe o resultado
```

#### 3. Fluxos Obrigatórios
- **Agendamento**: Coleta dados → Chama verificar_horarios_disponiveis → Valida → Cria
- **Reagendamento**: Consulta existente → Confirma dados → Reagenda
- **Cancelamento**: Consulta existente → Confirma → Cancela

#### 4. Proibições Absolutas
- Nunca inventar nomes de profissionais
- Nunca confirmar horários sem validar
- Nunca mencionar valores sem consultar banco
- Nunca prosseguir sem nome completo + telefone

#### 5. Exemplos de Treinamento
- Respostas bem avaliadas (feedback positivo)
- Respostas reescritas pelos usuários
- Respostas mal avaliadas (para evitar)

### Adaptação por Contexto

O prompt se adapta baseado em:
- **Dados já coletados**: Inclui nome/telefone se disponível
- **Etapa do agendamento**: Ajusta instruções conforme progresso
- **Histórico de conversas**: Inclui padrões de sucesso/falha
- **Configurações da clínica**: Personaliza por especialidade

## Sistema de Validações

### 1. Validação de Entrada (Frontend)

```javascript
// Sanitização básica
message = message.trim();

// Verificação de tamanho
if (message.length > 1000) {
    alert('Mensagem muito longa');
    return;
}
```

### 2. Validação de Dados (Backend)

#### Nome do Paciente
```php
// Lista de palavras proibidas
$palavrasNaoNome = [
    'mas', 'tambem', 'gordurinha', 'procedimento', 
    'cirurgia', 'informações', 'agendamento'
];

// Validações estruturais
- Mínimo 6 caracteres
- Mínimo 2 palavras (nome + sobrenome)
- Máximo 50 caracteres
- Sem palavras contextuais/médicas
```

#### Telefone
```php
// Extração de números
$telefone = preg_replace('/[^0-9]/', '', $telefone);

// Validação de tamanho
if (strlen($telefone) < 10) {
    return ['erro' => 'Telefone deve ter pelo menos 10 dígitos'];
}
```

#### Horários
```php
// Normalização
private function normalizarHorario($hora) {
    $hora = trim(strtolower($hora));
    $hora = preg_replace('/\s*h(r)?\s*$/i', '', $hora); // Remove "h" ou "hr"
    
    if (preg_match('/^\d{1,2}$/', $hora)) {
        return str_pad($hora, 2, '0', STR_PAD_LEFT) . ':00:00';
    }
    // ... outras normalizações
}
```

### 3. Validação de Horários

#### Algoritmo de Verificação
```php
public function validar_horario_para_agendamento($params) {
    // 1. Busca horários disponíveis calculados
    $horariosDisponiveis = $this->verificar_horarios_disponiveis(['data' => $data]);
    
    // 2. Verifica se horário está na lista
    if (!in_array($hora, $dia['horarios'])) {
        return ['valido' => false, 'horarios_disponiveis' => $lista];
    }
    
    // 3. Dupla verificação no banco
    $sql = "SELECT COUNT(*) FROM agendamentos WHERE data_consulta = ? AND hora_consulta = ?";
    
    // 4. Apenas retorna válido se passou todas as verificações
    return ['valido' => true];
}
```

## Sistema de Tratamento de Erros

### 1. Hierarquia de Tratamento

```php
try {
    // Operação principal
} catch (RequestException $e) {
    // Erro de comunicação com OpenAI
    if ($statusCode === 429) {
        // Rate limit - retry com backoff
    }
} catch (\Exception $e) {
    // Erro geral - log e fallback
} finally {
    // Limpeza sempre executada
}
```

### 2. Sistema de Retry

#### Rate Limiting (OpenAI)
```php
if ($statusCode === 429 && $attempt < $maxRetries) {
    $waitTime = pow(2, $attempt) * 1000000; // Backoff exponencial
    usleep($waitTime);
    continue;
}
```

#### Fallbacks Inteligentes
- **IA indisponível**: Mensagem específica para usuário
- **Banco indisponível**: Cache de configurações
- **Função falha**: Resposta genérica + log
- **Sessão expirada**: Limpeza automática + recomeço

### 3. Logging de Erros

#### Tabela `erros_sistema`
```sql
INSERT INTO erros_sistema (tipo_erro, mensagem, created_at) 
VALUES ('openai_error', ?, NOW())
```

#### Arquivo de Log
```
[2024-01-15 10:30:15] [ERROR] OpenAI timeout after 60s
[2024-01-15 10:30:15] [ERROR] Database connection failed: SQLSTATE[HY000]
[2024-01-15 10:30:15] [WARN] Rate limit reached, retrying in 2s
```

## Performance e Otimizações

### 1. Otimizações de Banco

#### Índices Estratégicos
```sql
-- Busca rápida de agendamentos
INDEX idx_data_hora (data_consulta, hora_consulta)
INDEX idx_status (status)

-- Busca por paciente
INDEX idx_telefone (telefone)
INDEX idx_session_id (session_id)

-- Conversas
INDEX idx_session_feedback (session_id, feedback_tipo)
```

#### Queries Otimizadas
```php
// Limite de resultados para evitar sobrecarga
$limit = $limit ?? 3;
$sql = "SELECT * FROM conversas_treinamento ORDER BY created_at DESC LIMIT ?";

// Uso de prepared statements
$stmt = $this->db->prepare($sql);
$stmt->execute($params);
```

### 2. Otimizações de IA

#### Limite de Tokens no Prompt
```php
// Seleção de exemplos prioritários
private function selecionarExemplosPrioritarios($exemplos, $maxTokens = 8000) {
    $tokensAtuais = 0;
    foreach ($exemplos as $exemplo) {
        if ($tokensAtuais + $tokensExemplo > $maxTokens) break;
        // ... adiciona exemplo
    }
}
```

#### Cache de Respostas
- Session data para evitar reprocessamento
- Configurações da clínica em cache
- Horários calculados temporariamente

### 3. Otimizações de Frontend

#### Debouncing
```javascript
// Evita múltiplos envios acidentais
if (isProcessing) return;
isProcessing = true;
```

#### Lazy Loading
- Debug panel carregado sob demanda
- Logs paginados
- Imagens otimizadas

## Sistema de Monitoramento

### 1. Métricas Coletadas

#### Uso da IA
```php
// Salvo em cada conversa
$tokensPrompt = $usage['prompt_tokens'] ?? 0;
$tokensResposta = $usage['completion_tokens'] ?? 0;
$custoEstimado = $this->currencyService->convertDollarToReal($custoDolar);
```

#### Performance
- Tempo de resposta por função
- Taxa de sucesso de agendamentos
- Frequência de errors/retries

### 2. Dashboard de Debug

#### Informações em Tempo Real
```javascript
// Estatísticas acumuladas
document.getElementById('totalTokens').textContent = totalTokens;
document.getElementById('totalCost').textContent = 'R$ ' + totalCost.toFixed(4);

// Log em tempo real
addDebugLog('Função executada', { name: functionName, result: result });
```

### 3. Alertas Automáticos

#### Condições de Alerta
- Erro rate > 10%
- Custo diário > limite
- Tempo resposta > 30s
- Sessões expiradas > threshold

## Segurança

### 1. Validação de Entrada

#### Sanitização
```php
// Limpeza de UTF-8 malformado
private function cleanUtf8($data) {
    return iconv('UTF-8', 'UTF-8//IGNORE', $data);
}

// Validação de tamanho
if (strlen($message) > 1000) {
    return ['error' => 'Mensagem muito longa'];
}
```

#### SQL Injection Protection
```php
// Sempre usar prepared statements
$stmt = $this->db->prepare($sql);
$stmt->execute($params);
```

### 2. Gestão de Sessões

#### Timeout Automático
```php
$tempoLimite = 3600; // 1 hora
if ((time() - $dados['timestamp']) > $tempoLimite) {
    $this->limparDados(); // Limpeza automática
}
```

#### Isolamento de Dados
```php
// Sessões isoladas por sessionId
$sessionKey = "paciente_{$this->sessionId}";
$_SESSION[$sessionKey] = $dados;
```

### 3. Proteção de APIs

#### Rate Limiting
- Headers CORS apropriados
- Validação de métodos HTTP
- Timeout de requisições

#### Validação de Dados
```php
// Verificação de campos obrigatórios
if (!isset($input['message']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}
```

## Configuração e Deploy

### 1. Dependências

#### Composer (composer.json)
```json
{
    "require": {
        "php": ">=8.1",
        "vlucas/phpdotenv": "^5.5",
        "guzzlehttp/guzzle": "^7.5"
    },
    "autoload": {
        "psr-4": { "App\\": "src/" }
    }
}
```

#### Instalação
```bash
composer install
```

### 2. Configuração (.env)
```env
# Banco de Dados
DB_HOST=localhost
DB_NAME=andreia
DB_USER=root
DB_PASS=

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Aplicação
APP_DEBUG=true
TIMEZONE=America/Sao_Paulo
```

### 3. Banco de Dados

#### Criação
```bash
mysql -u root -p andreia < database/schema.sql
```

#### Dados Iniciais
```bash
mysql -u root -p andreia < database/insert_profissionais_example.sql
```

### 4. Servidor Web

#### Apache (.htaccess)
```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^api/(.*)$ api/$1.php [L]
```

#### Nginx
```nginx
location /api/ {
    try_files $uri $uri.php =404;
    fastcgi_pass php-fpm;
    include fastcgi_params;
}
```

## Manutenção e Operação

### 1. Monitoramento de Logs

#### Arquivo Principal
```bash
tail -f openai_debug.log
```

#### Filtragem por Nível
```bash
grep "\[ERROR\]" openai_debug.log
grep "\[WARN\]" openai_debug.log
```

### 2. Limpeza de Dados

#### Sessões Antigas
```sql
DELETE FROM pacientes WHERE session_id IS NOT NULL 
AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR);
```

#### Logs Antigos
```sql
DELETE FROM conversas WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### 3. Backup

#### Banco de Dados
```bash
mysqldump -u root -p andreia > backup_$(date +%Y%m%d).sql
```

#### Logs
```bash
cp openai_debug.log logs/backup_$(date +%Y%m%d).log
```

### 4. Atualizações

#### Código
```bash
git pull origin main
composer update
```

#### Banco
```bash
mysql -u root -p andreia < database/migrations/new_migration.sql
```

## Considerações Finais

### Pontos Fortes
1. **Arquitetura modular** facilita manutenção
2. **Validações rigorosas** garantem qualidade dos dados
3. **Logging extensivo** facilita debugging
4. **Sistema de retry** aumenta confiabilidade
5. **Sessões temporárias** melhoram UX
6. **Prompts dinâmicos** permitem aprendizado contínuo

### Limitações Atuais
1. **Dependência de sessões PHP** (não escala horizontalmente)
2. **Prompts muito longos** podem impactar performance
3. **Cache limitado** (apenas em sessão)
4. **Monitoramento manual** de alertas
5. **Backup manual** de dados críticos

### Roadmap Técnico
1. **Migração para Redis** (sessões distribuídas)
2. **Cache inteligente** de configurações
3. **Métricas automatizadas** (Prometheus/Grafana)
4. **CI/CD pipeline** para deploys
5. **Testes automatizados** (PHPUnit)
6. **API versioning** para compatibilidade

Este sistema representa uma implementação robusta e bem estruturada de um assistente virtual médico, com foco em dados reais, validações rigorosas e experiência de usuário natural.
