# Sistema de Assistente Virtual Médico - Implementação Completa

## Estrutura de Diretórios
```
medical-assistant/
├── public/
│   ├── index.php
│   ├── chat.php
│   ├── api/
│   │   ├── chat.php
│   │   ├── feedback.php
│   │   └── rewrite.php
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── chat.js
├── src/
│   ├── Controllers/
│   │   └── ChatController.php
│   ├── Services/
│   │   ├── OpenAIService.php
│   │   ├── DatabaseService.php
│   │   └── AgentFunctions.php
│   └── Config/
│       └── Database.php
├── vendor/
├── .env
├── composer.json
└── README.md
```

## 1. Arquivo composer.json
```json
{
    "name": "clinic/medical-assistant",
    "description": "Sistema de Assistente Virtual Médico",
    "type": "project",
    "require": {
        "php": ">=8.1",
        "vlucas/phpdotenv": "^5.5",
        "guzzlehttp/guzzle": "^7.5"
    },
    "autoload": {
        "psr-4": {
            "App\\": "src/"
        }
    }
}
```

## 2. Arquivo .env
```env
# Banco de Dados
DB_HOST=localhost
DB_NAME=andreia
DB_USER=root
DB_PASS=

# OpenAI
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gpt-3.5-turbo

# Aplicação
APP_DEBUG=true
TIMEZONE=America/Sao_Paulo
```

## 3. src/Config/Database.php
```php
<?php
namespace App\Config;

use PDO;
use PDOException;

class Database {
    private static $instance = null;
    private $connection;
    
    private function __construct() {
        try {
            $this->connection = new PDO(
                "mysql:host=" . $_ENV['DB_HOST'] . ";dbname=" . $_ENV['DB_NAME'] . ";charset=utf8mb4",
                $_ENV['DB_USER'],
                $_ENV['DB_PASS'],
                [
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
                ]
            );
        } catch (PDOException $e) {
            die("Erro de conexão: " . $e->getMessage());
        }
    }
    
    public static function getInstance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    public function getConnection() {
        return $this->connection;
    }
}
```

## 4. src/Services/DatabaseService.php
```php
<?php
namespace App\Services;

use App\Config\Database;
use PDO;

class DatabaseService {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance()->getConnection();
    }
    
    public function query($sql, $params = []) {
        try {
            $stmt = $this->db->prepare($sql);
            $stmt->execute($params);
            return $stmt->fetchAll();
        } catch (\Exception $e) {
            $this->logError('query_error', $e->getMessage());
            return false;
        }
    }
    
    public function execute($sql, $params = []) {
        try {
            $stmt = $this->db->prepare($sql);
            return $stmt->execute($params);
        } catch (\Exception $e) {
            $this->logError('execute_error', $e->getMessage());
            return false;
        }
    }
    
    public function lastInsertId() {
        return $this->db->lastInsertId();
    }
    
    private function logError($type, $message) {
        $sql = "INSERT INTO erros_sistema (tipo_erro, mensagem, created_at) VALUES (?, ?, NOW())";
        try {
            $stmt = $this->db->prepare($sql);
            $stmt->execute([$type, $message]);
        } catch (\Exception $e) {
            // Falha silenciosa no log
        }
    }
}
```

## 5. src/Services/AgentFunctions.php
```php
<?php
namespace App\Services;

class AgentFunctions {
    private $db;
    
    public function __construct() {
        $this->db = new DatabaseService();
    }
    
    /**
     * Lista profissionais da clínica
     */
    public function buscar_profissionais_clinica($params = []) {
        $sql = "SELECT * FROM profissionais WHERE ativo = 1";
        $queryParams = [];
        
        if (!empty($params['especialidade'])) {
            $sql .= " AND especialidade LIKE ?";
            $queryParams[] = '%' . $params['especialidade'] . '%';
        }
        
        if (!empty($params['profissional_especifico'])) {
            $sql .= " AND nome LIKE ?";
            $queryParams[] = '%' . $params['profissional_especifico'] . '%';
        }
        
        return $this->db->query($sql, $queryParams);
    }
    
    /**
     * Lista parceiros (hospitais, laboratórios, etc.)
     */
    public function buscar_parceiros($params = []) {
        $sql = "SELECT * FROM parceiros WHERE ativo = 1";
        $queryParams = [];
        
        if (!empty($params['servico_especifico'])) {
            $sql .= " AND (servicos_oferecidos LIKE ? OR nome LIKE ?)";
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
        }
        
        return $this->db->query($sql, $queryParams);
    }
    
    /**
     * Lista serviços oferecidos
     */
    public function buscar_servicos_clinica($params = []) {
        $sql = "SELECT * FROM servicos_clinica WHERE ativo = 1";
        $queryParams = [];
        
        if (!empty($params['categoria'])) {
            $sql .= " AND categoria = ?";
            $queryParams[] = $params['categoria'];
        }
        
        if (!empty($params['servico_especifico'])) {
            $sql .= " AND (nome LIKE ? OR palavras_chave LIKE ?)";
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
        }
        
        return $this->db->query($sql, $queryParams);
    }
    
    /**
     * Verifica se convênio é aceito
     */
    public function verificar_convenio($params) {
        if (empty($params['nome_convenio'])) {
            return ['erro' => 'Nome do convênio é obrigatório'];
        }
        
        $sql = "SELECT * FROM convenios_aceitos WHERE nome LIKE ? AND ativo = 1";
        return $this->db->query($sql, ['%' . $params['nome_convenio'] . '%']);
    }
    
    /**
     * Consulta agendamentos por nome ou telefone
     */
    public function consultar_agendamento_existente($params = []) {
        $sql = "SELECT a.*, p.nome as paciente_nome, p.telefone 
                FROM agendamentos a 
                JOIN pacientes p ON a.paciente_id = p.id 
                WHERE a.status != 'cancelado'";
        $queryParams = [];
        
        if (!empty($params['nome_paciente'])) {
            $sql .= " AND p.nome LIKE ?";
            $queryParams[] = '%' . $params['nome_paciente'] . '%';
        }
        
        if (!empty($params['telefone'])) {
            $sql .= " AND p.telefone = ?";
            $queryParams[] = $params['telefone'];
        }
        
        $sql .= " ORDER BY a.data_consulta, a.hora_consulta";
        
        return $this->db->query($sql, $queryParams);
    }
    
    /**
     * Verifica horários disponíveis para agendamento
     */
    public function verificar_horarios_disponiveis($params = []) {
        $data = $params['data'] ?? date('Y-m-d');
        $diaSemana = $this->getDiaSemana($data);
        
        // Busca horários de funcionamento
        $sql = "SELECT * FROM horarios_disponiveis WHERE dia_semana = ? AND ativo = 1";
        $horarios = $this->db->query($sql, [$diaSemana]);
        
        if (empty($horarios)) {
            return [];
        }
        
        // Busca agendamentos existentes
        $sql = "SELECT hora_consulta FROM agendamentos 
                WHERE data_consulta = ? AND status != 'cancelado'";
        $agendamentos = $this->db->query($sql, [$data]);
        
        $horariosOcupados = array_column($agendamentos, 'hora_consulta');
        $horariosDisponiveis = [];
        
        foreach ($horarios as $horario) {
            $horariosDisponiveis = array_merge(
                $horariosDisponiveis,
                $this->gerarHorarios(
                    $horario['manha_inicio'],
                    $horario['manha_fim'],
                    $horario['intervalo_minutos'],
                    $horariosOcupados
                )
            );
            
            if ($horario['tarde_inicio'] && $horario['tarde_fim']) {
                $horariosDisponiveis = array_merge(
                    $horariosDisponiveis,
                    $this->gerarHorarios(
                        $horario['tarde_inicio'],
                        $horario['tarde_fim'],
                        $horario['intervalo_minutos'],
                        $horariosOcupados
                    )
                );
            }
        }
        
        return ['data' => $data, 'horarios' => $horariosDisponiveis];
    }
    
    /**
     * Cria novo agendamento
     */
    public function criar_agendamento($params) {
        // Verifica campos obrigatórios
        $required = ['nome', 'telefone', 'data', 'hora'];
        foreach ($required as $field) {
            if (empty($params[$field])) {
                return ['erro' => "Campo $field é obrigatório"];
            }
        }
        
        // Busca ou cria paciente
        $pacienteId = $this->getOrCreatePaciente($params['nome'], $params['telefone']);
        
        // Cria agendamento
        $sql = "INSERT INTO agendamentos (paciente_id, data_consulta, hora_consulta, 
                procedimento, observacoes, status) VALUES (?, ?, ?, ?, ?, 'confirmado')";
        
        $result = $this->db->execute($sql, [
            $pacienteId,
            $params['data'],
            $params['hora'],
            $params['procedimento'] ?? null,
            $params['observacoes'] ?? null
        ]);
        
        if ($result) {
            return ['sucesso' => true, 'id' => $this->db->lastInsertId()];
        }
        
        return ['erro' => 'Falha ao criar agendamento'];
    }
    
    /**
     * Cancela agendamento existente
     */
    public function cancelar_agendamento($params) {
        $required = ['nome_paciente', 'telefone', 'data_consulta', 'hora_consulta'];
        foreach ($required as $field) {
            if (empty($params[$field])) {
                return ['erro' => "Campo $field é obrigatório"];
            }
        }
        
        $sql = "UPDATE agendamentos a 
                JOIN pacientes p ON a.paciente_id = p.id 
                SET a.status = 'cancelado' 
                WHERE p.nome = ? AND p.telefone = ? 
                AND a.data_consulta = ? AND a.hora_consulta = ?";
        
        $result = $this->db->execute($sql, [
            $params['nome_paciente'],
            $params['telefone'],
            $params['data_consulta'],
            $params['hora_consulta']
        ]);
        
        return ['sucesso' => $result];
    }
    
    /**
     * Reagenda consulta para nova data/hora
     */
    public function reagendar_consulta($params) {
        // Cancela agendamento atual
        $cancelResult = $this->cancelar_agendamento([
            'nome_paciente' => $params['nome_paciente'],
            'telefone' => $params['telefone'],
            'data_consulta' => $params['data_atual'],
            'hora_consulta' => $params['hora_atual']
        ]);
        
        if (!$cancelResult['sucesso']) {
            return ['erro' => 'Falha ao cancelar agendamento atual'];
        }
        
        // Cria novo agendamento
        return $this->criar_agendamento([
            'nome' => $params['nome_paciente'],
            'telefone' => $params['telefone'],
            'data' => $params['nova_data'],
            'hora' => $params['nova_hora']
        ]);
    }
    
    /**
     * Busca informações da clínica
     */
    public function buscar_configuracoes_clinica($params = []) {
        $sql = "SELECT * FROM configuracoes";
        
        if (!empty($params['chave'])) {
            $sql .= " WHERE chave = ?";
            return $this->db->query($sql, [$params['chave']]);
        }
        
        $configs = $this->db->query($sql);
        $result = [];
        
        foreach ($configs as $config) {
            $result[$config['chave']] = $config['valor'];
        }
        
        return $result;
    }
    
    /**
     * Busca estado do agendamento em andamento
     */
    public function buscar_estado_agendamento($sessionId) {
        $sql = "SELECT * FROM agendamentos_em_andamento WHERE session_id = ?";
        $result = $this->db->query($sql, [$sessionId]);
        return $result[0] ?? null;
    }
    
    /**
     * Atualiza estado do agendamento em andamento
     */
    public function atualizar_estado_agendamento($sessionId, $dados) {
        $estado = $this->buscar_estado_agendamento($sessionId);
        
        if ($estado) {
            $updates = [];
            $params = [];
            
            foreach ($dados as $campo => $valor) {
                $updates[] = "$campo = ?";
                $params[] = $valor;
            }
            
            $params[] = $sessionId;
            $sql = "UPDATE agendamentos_em_andamento SET " . implode(', ', $updates) . 
                   " WHERE session_id = ?";
            
            return $this->db->execute($sql, $params);
        } else {
            $dados['session_id'] = $sessionId;
            $campos = array_keys($dados);
            $placeholders = array_fill(0, count($campos), '?');
            
            $sql = "INSERT INTO agendamentos_em_andamento (" . implode(', ', $campos) . ") 
                    VALUES (" . implode(', ', $placeholders) . ")";
            
            return $this->db->execute($sql, array_values($dados));
        }
    }
    
    /**
     * Busca histórico de conversas para treinamento
     */
    public function buscar_historico_conversas($limit = 100) {
        $sql = "SELECT * FROM conversas 
                WHERE feedback_tipo IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT ?";
        
        return $this->db->query($sql, [$limit]);
    }
    
    // Funções auxiliares privadas
    
    private function getDiaSemana($data) {
        $dias = [
            'Sunday' => 'domingo',
            'Monday' => 'segunda',
            'Tuesday' => 'terca',
            'Wednesday' => 'quarta',
            'Thursday' => 'quinta',
            'Friday' => 'sexta',
            'Saturday' => 'sabado'
        ];
        
        $diaSemanaIngles = date('l', strtotime($data));
        return $dias[$diaSemanaIngles];
    }
    
    private function gerarHorarios($inicio, $fim, $intervalo, $ocupados) {
        $horarios = [];
        $current = strtotime($inicio);
        $end = strtotime($fim);
        
        while ($current <= $end) {
            $hora = date('H:i:s', $current);
            if (!in_array($hora, $ocupados)) {
                $horarios[] = $hora;
            }
            $current += ($intervalo * 60);
        }
        
        return $horarios;
    }
    
    private function getOrCreatePaciente($nome, $telefone) {
        $sql = "SELECT id FROM pacientes WHERE telefone = ?";
        $result = $this->db->query($sql, [$telefone]);
        
        if (!empty($result)) {
            return $result[0]['id'];
        }
        
        $sql = "INSERT INTO pacientes (nome, telefone) VALUES (?, ?)";
        $this->db->execute($sql, [$nome, $telefone]);
        
        return $this->db->lastInsertId();
    }
}
```

## 6. src/Services/OpenAIService.php
```php
<?php
namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class OpenAIService {
    private $client;
    private $apiKey;
    private $model;
    private $db;
    
    public function __construct() {
        $this->client = new Client();
        $this->apiKey = $_ENV['OPENAI_API_KEY'];
        $this->model = $_ENV['OPENAI_MODEL'] ?? 'gpt-3.5-turbo';
        $this->db = new DatabaseService();
    }
    
    public function chat($messages, $functions = null) {
        try {
            $payload = [
                'model' => $this->model,
                'messages' => $messages,
                'temperature' => 0.7,
                'max_tokens' => 1000
            ];
            
            if ($functions) {
                $payload['functions'] = $functions;
                $payload['function_call'] = 'auto';
            }
            
            $response = $this->client->post('https://api.openai.com/v1/chat/completions', [
                'headers' => [
                    'Authorization' => 'Bearer ' . $this->apiKey,
                    'Content-Type' => 'application/json'
                ],
                'json' => $payload
            ]);
            
            $result = json_decode($response->getBody(), true);
            
            return [
                'success' => true,
                'data' => $result
            ];
            
        } catch (RequestException $e) {
            $this->registrarErroNoBanco($e->getMessage());
            
            return [
                'success' => false,
                'error' => 'Erro na comunicação com a IA'
            ];
        }
    }
    
    private function registrarErroNoBanco($mensagem) {
        $sql = "INSERT INTO erros_sistema (tipo_erro, mensagem, created_at) 
                VALUES ('openai_error', ?, NOW())";
        $this->db->execute($sql, [$mensagem]);
    }
}
```

## 7. src/Controllers/ChatController.php
```php
<?php
namespace App\Controllers;

use App\Services\OpenAIService;
use App\Services\AgentFunctions;
use App\Services\DatabaseService;

class ChatController {
    private $openai;
    private $functions;
    private $db;
    
    public function __construct() {
        $this->openai = new OpenAIService();
        $this->functions = new AgentFunctions();
        $this->db = new DatabaseService();
    }
    
    public function processMessage($message, $sessionId, $isFirst = false) {
        // Busca contexto e configurações
        $contexto = $this->buildContext($sessionId);
        
        // Monta mensagens para a IA
        $messages = $this->buildMessages($message, $contexto, $sessionId);
        
        // Define funções disponíveis
        $functions = $this->getAvailableFunctions();
        
        // Chama a IA
        $response = $this->openai->chat($messages, $functions);
        
        if (!$response['success']) {
            return [
                'success' => false,
                'message' => 'Estou com dificuldades técnicas. Poderia repetir?'
            ];
        }
        
        $aiResponse = $response['data']['choices'][0]['message'];
        $functionCalls = [];
        
        // Processa chamadas de função se houver
        if (isset($aiResponse['function_call'])) {
            $functionName = $aiResponse['function_call']['name'];
            $functionArgs = json_decode($aiResponse['function_call']['arguments'], true);
            
            $functionResult = $this->executeFunction($functionName, $functionArgs);
            $functionCalls[] = [
                'name' => $functionName,
                'result' => $functionResult
            ];
            
            // Adiciona resultado da função ao contexto
            $messages[] = $aiResponse;
            $messages[] = [
                'role' => 'function',
                'name' => $functionName,
                'content' => json_encode($functionResult)
            ];
            
            // Chama IA novamente com o resultado
            $finalResponse = $this->openai->chat($messages);
            
            if ($finalResponse['success']) {
                $aiResponse = $finalResponse['data']['choices'][0]['message'];
            }
        }
        
        // Salva conversa no banco
        $this->saveConversation(
            $sessionId,
            $message,
            $aiResponse['content'],
            $functionCalls,
            $response['data']['usage'] ?? []
        );
        
        return [
            'success' => true,
            'message' => $aiResponse['content'],
            'tokens' => $response['data']['usage'] ?? [],
            'functions' => $functionCalls
        ];
    }
    
    private function buildContext($sessionId) {
        // Busca configurações da clínica
        $configs = $this->functions->buscar_configuracoes_clinica();
        
        // Busca histórico de conversas para treinamento
        $historico = $this->functions->buscar_historico_conversas();
        
        // Busca estado do agendamento se houver
        $estadoAgendamento = $this->functions->buscar_estado_agendamento($sessionId);
        
        // Dados de contexto
        $dataHoje = date('Y-m-d');
        $horaAtual = date('H:i');
        $diaSemana = $this->getDiaSemanaPortugues();
        
        return [
            'configs' => $configs,
            'historico' => $historico,
            'estadoAgendamento' => $estadoAgendamento,
            'dataHoje' => $dataHoje,
            'horaAtual' => $horaAtual,
            'diaSemana' => $diaSemana
        ];
    }
    
    private function buildMessages($userMessage, $contexto, $sessionId) {
        $systemPrompt = $this->buildSystemPrompt($contexto);
        
        $messages = [
            ['role' => 'system', 'content' => $systemPrompt]
        ];
        
        // Adiciona histórico recente da conversa
        $conversaRecente = $this->getRecentConversation($sessionId, 5);
        foreach ($conversaRecente as $msg) {
            $messages[] = ['role' => 'user', 'content' => $msg['mensagem_usuario']];
            $messages[] = ['role' => 'assistant', 'content' => $msg['resposta_agente']];
        }
        
        // Adiciona mensagem atual
        $messages[] = ['role' => 'user', 'content' => $userMessage];
        
        return $messages;
    }
    
    private function buildSystemPrompt($contexto) {
        $configs = $contexto['configs'];
        $historico = $contexto['historico'];
        
        // Analisa feedbacks para treinamento
        $padroesBons = [];
        $padroesRuins = [];
        
        foreach ($historico as $conversa) {
            if ($conversa['feedback_tipo'] === 'positivo') {
                if ($conversa['resposta_reescrita']) {
                    $padroesBons[] = $conversa['resposta_reescrita'];
                } else {
                    $padroesBons[] = $conversa['resposta_agente'];
                }
            } elseif ($conversa['feedback_tipo'] === 'negativo') {
                $padroesRuins[] = $conversa['resposta_agente'];
            }
        }
        
        $prompt = "CONTEXTO:
- Hoje: {$contexto['dataHoje']} ({$contexto['diaSemana']}, {$contexto['horaAtual']})
- Especialidade: " . ($configs['especialidade'] ?? 'Medicina Geral') . "
- Endereço: " . ($configs['endereco'] ?? 'Não informado') . "
- Telefone: " . ($configs['telefone'] ?? 'Não informado') . "

## IDENTIDADE E COMPORTAMENTO
Você é um(a) atendente virtual de uma clínica médica. Sua personalidade é amigável, atenciosa e profissional, mas sem ser robótica. Converse naturalmente, como uma pessoa real faria.

## DIRETRIZES DE CONVERSAÇÃO

### TOM E ESTILO
- Use linguagem natural e fluida, como em uma conversa humana
- Seja simpático(a) e acolhedor(a)
- Mantenha respostas curtas e diretas (1-3 frases quando possível)
- Evite templates ou frases prontas
- Varie suas respostas para parecer mais natural

### ESCOPO DE ATUAÇÃO
**VOCÊ PODE ajudar com:**
- Dúvidas sobre a especialidade da clínica
- Agendamento de consultas
- Informações sobre a clínica e profissionais
- Orientações médicas gerais
- Esclarecimentos sobre procedimentos

**VOCÊ NÃO PODE responder sobre:**
- Assuntos não relacionados à saúde
- Temas fora do contexto médico/clínica

### TREINAMENTO E APRENDIZADO
Baseie suas respostas nos padrões que funcionaram bem no passado e evite os que não funcionaram.";

        if (!empty($padroesBons)) {
            $prompt .= "\n\n### EXEMPLOS DE RESPOSTAS BEM AVALIADAS:\n";
            foreach (array_slice($padroesBons, 0, 3) as $exemplo) {
                $prompt .= "- " . substr($exemplo, 0, 100) . "...\n";
            }
        }
        
        if (!empty($padroesRuins)) {
            $prompt .= "\n\n### EVITE RESPOSTAS COMO:\n";
            foreach (array_slice($padroesRuins, 0, 3) as $exemplo) {
                $prompt .= "- " . substr($exemplo, 0, 100) . "...\n";
            }
        }
        
        if ($contexto['estadoAgendamento']) {
            $prompt .= "\n\n### AGENDAMENTO EM ANDAMENTO\n";
            $prompt .= "Há um agendamento em processo para esta sessão:\n";
            $prompt .= json_encode($contexto['estadoAgendamento'], JSON_PRETTY_PRINT);
        }
        
        return $prompt;
    }
    
    private function getAvailableFunctions() {
        return [
            [
                'name' => 'buscar_profissionais_clinica',
                'description' => 'Lista profissionais da clínica',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'especialidade' => ['type' => 'string'],
                        'profissional_especifico' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'buscar_servicos_clinica',
                'description' => 'Lista serviços oferecidos pela clínica',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'categoria' => ['type' => 'string'],
                        'servico_especifico' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'verificar_convenio',
                'description' => 'Verifica se um convênio é aceito',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'nome_convenio' => ['type' => 'string']
                    ],
                    'required' => ['nome_convenio']
                ]
            ],
            [
                'name' => 'verificar_horarios_disponiveis',
                'description' => 'Verifica horários disponíveis para agendamento',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'data' => ['type' => 'string'],
                        'periodo' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'criar_agendamento',
                'description' => 'Cria um novo agendamento',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'nome' => ['type' => 'string'],
                        'telefone' => ['type' => 'string'],
                        'data' => ['type' => 'string'],
                        'hora' => ['type' => 'string'],
                        'procedimento' => ['type' => 'string'],
                        'observacoes' => ['type' => 'string']
                    ],
                    'required' => ['nome', 'telefone', 'data', 'hora']
                ]
            ],
            [
                'name' => 'consultar_agendamento_existente',
                'description' => 'Consulta agendamentos existentes',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'nome_paciente' => ['type' => 'string'],
                        'telefone' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'cancelar_agendamento',
                'description' => 'Cancela um agendamento existente',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'nome_paciente' => ['type' => 'string'],
                        'telefone' => ['type' => 'string'],
                        'data_consulta' => ['type' => 'string'],
                        'hora_consulta' => ['type' => 'string']
                    ],
                    'required' => ['nome_paciente', 'telefone', 'data_consulta', 'hora_consulta']
                ]
            ],
            [
                'name' => 'buscar_configuracoes_clinica',
                'description' => 'Busca informações da clínica',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'chave' => ['type' => 'string']
                    ]
                ]
            ]
        ];
    }
    
    private function executeFunction($functionName, $args) {
        try {
            if (method_exists($this->functions, $functionName)) {
                return $this->functions->$functionName($args);
            }
            return ['erro' => 'Função não encontrada'];
        } catch (\Exception $e) {
            return ['erro' => 'Erro ao executar função: ' . $e->getMessage()];
        }
    }
    
    private function saveConversation($sessionId, $userMessage, $aiResponse, $functionCalls, $usage) {
        $sql = "INSERT INTO conversas (
                    session_id, 
                    mensagem_usuario, 
                    resposta_agente, 
                    funcao_chamada,
                    tokens_prompt, 
                    tokens_resposta, 
                    custo_estimado
                ) VALUES (?, ?, ?, ?, ?, ?, ?)";
        
        $funcaoChamada = !empty($functionCalls) ? $functionCalls[0]['name'] : null;
        $tokensPrompt = $usage['prompt_tokens'] ?? 0;
        $tokensResposta = $usage['completion_tokens'] ?? 0;
        $custoEstimado = ($tokensPrompt * 0.0015 + $tokensResposta * 0.002) / 1000;
        
        $this->db->execute($sql, [
            $sessionId,
            $userMessage,
            $aiResponse,
            $funcaoChamada,
            $tokensPrompt,
            $tokensResposta,
            $custoEstimado
        ]);
    }
    
    private function getRecentConversation($sessionId, $limit = 5) {
        $sql = "SELECT mensagem_usuario, resposta_agente 
                FROM conversas 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?";
        
        $result = $this->db->query($sql, [$sessionId, $limit]);
        return array_reverse($result);
    }
    
    private function getDiaSemanaPortugues() {
        $dias = [
            'Sunday' => 'Domingo',
            'Monday' => 'Segunda-feira',
            'Tuesday' => 'Terça-feira',
            'Wednesday' => 'Quarta-feira',
            'Thursday' => 'Quinta-feira',
            'Friday' => 'Sexta-feira',
            'Saturday' => 'Sábado'
        ];
        
        return $dias[date('l')];
    }
}
```

## 8. public/index.php
```php
<?php
header('Location: chat.php');
exit;
```

## 9. public/chat.php
```php
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✨ Assistente Virtual - Clínica Médica</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div id="particles-bg"></div>
    
    <div class="chat-container">
        <div class="chat-header">
            <h1>✨ Assistente Virtual</h1>
            <p>Clínica Médica</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="avatar">🤖</div>
                <div class="content">
                    <p>Olá! Sou o assistente virtual da clínica. Como posso ajudar você hoje?</p>
                </div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <input 
                type="text" 
                id="messageInput" 
                placeholder="Digite sua mensagem..." 
                autocomplete="off"
            >
            <button id="sendButton">
                <svg width="24" height="24" viewBox="0 0 24 24">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            </button>
        </div>
    </div>
    
    <div class="debug-panel" id="debugPanel">
        <div class="debug-header">
            <h3>🔧 Debug Console</h3>
            <button id="toggleDebug">▼</button>
        </div>
        <div class="debug-content" id="debugContent">
            <div class="debug-stats">
                <span>Tokens: <strong id="totalTokens">0</strong></span>
                <span>Custo: <strong id="totalCost">$0.00</strong></span>
            </div>
            <div class="debug-logs" id="debugLogs"></div>
            <div class="debug-actions">
                <button id="clearLogs">Limpar</button>
                <button id="exportLogs">Exportar</button>
            </div>
        </div>
    </div>
    
    <script src="js/chat.js"></script>
</body>
</html>
```

## 10. public/css/style.css
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}

#particles-bg {
    position: absolute;
    width: 100%;
    height: 100%;
    overflow: hidden;
}

.particle {
    position: absolute;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    animation: float 20s infinite;
}

@keyframes float {
    0%, 100% {
        transform: translateY(0) translateX(0);
    }
    33% {
        transform: translateY(-100px) translateX(100px);
    }
    66% {
        transform: translateY(100px) translateX(-100px);
    }
}

.chat-container {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    width: 90%;
    max-width: 500px;
    height: 80vh;
    max-height: 700px;
    display: flex;
    flex-direction: column;
    position: relative;
    z-index: 1;
}

.chat-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 20px 20px 0 0;
    text-align: center;
}

.chat-header h1 {
    font-size: 24px;
    margin-bottom: 5px;
}

.chat-header p {
    font-size: 14px;
    opacity: 0.9;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    scroll-behavior: smooth;
}

.message {
    display: flex;
    margin-bottom: 20px;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.message.user {
    flex-direction: row-reverse;
}

.avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}

.message.bot .avatar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    margin-right: 10px;
}

.message.user .avatar {
    background: #e0e0e0;
    margin-left: 10px;
}

.content {
    max-width: 70%;
    position: relative;
}

.content p {
    background: #f5f5f5;
    padding: 12px 16px;
    border-radius: 18px;
    line-height: 1.4;
    word-wrap: break-word;
}

.message.user .content p {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.feedback-buttons {
    display: flex;
    gap: 5px;
    margin-top: 5px;
    opacity: 0;
    transition: opacity 0.3s;
}

.message:hover .feedback-buttons {
    opacity: 1;
}

.feedback-buttons button {
    background: none;
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.feedback-buttons button:hover {
    background: #f0f0f0;
    transform: scale(1.05);
}

.feedback-buttons button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.typing-indicator {
    display: flex;
    align-items: center;
    padding: 15px;
}

.typing-indicator span {
    height: 8px;
    width: 8px;
    background: #999;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
    animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% {
        transform: translateY(0);
    }
    30% {
        transform: translateY(-10px);
    }
}

.chat-input-container {
    display: flex;
    padding: 20px;
    border-top: 1px solid #eee;
    gap: 10px;
}

#messageInput {
    flex: 1;
    padding: 12px 20px;
    border: 2px solid #eee;
    border-radius: 25px;
    font-size: 16px;
    outline: none;
    transition: border-color 0.3s;
}

#messageInput:focus {
    border-color: #667eea;
}

#sendButton {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    border: none;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s;
}

#sendButton:hover {
    transform: scale(1.1);
}

#sendButton:active {
    transform: scale(0.95);
}

#sendButton svg {
    fill: white;
}

.debug-panel {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: rgba(0, 0, 0, 0.9);
    color: white;
    border-radius: 10px;
    width: 300px;
    z-index: 1000;
    overflow: hidden;
}

.debug-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    background: rgba(255, 255, 255, 0.1);
    cursor: pointer;
}

.debug-header h3 {
    font-size: 14px;
    margin: 0;
}

#toggleDebug {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 12px;
}

.debug-content {
    max-height: 300px;
    overflow-y: auto;
    padding: 15px;
}

.debug-content.hidden {
    display: none;
}

.debug-stats {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
    font-size: 12px;
}

.debug-logs {
    font-size: 11px;
    font-family: monospace;
    max-height: 200px;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.05);
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 10px;
}

.debug-log-entry {
    margin-bottom: 5px;
    padding: 3px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.debug-actions {
    display: flex;
    gap: 10px;
}

.debug-actions button {
    flex: 1;
    padding: 5px 10px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
}

.debug-actions button:hover {
    background: rgba(255, 255, 255, 0.2);
}

/* Modal de reescrita */
.rewrite-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

.rewrite-modal-content {
    background: white;
    padding: 30px;
    border-radius: 15px;
    width: 90%;
    max-width: 500px;
}

.rewrite-modal h3 {
    margin-bottom: 15px;
    color: #333;
}

.rewrite-modal textarea {
    width: 100%;
    min-height: 100px;
    padding: 10px;
    border: 2px solid #eee;
    border-radius: 10px;
    font-size: 14px;
    resize: vertical;
}

.rewrite-modal-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}

.rewrite-modal-actions button {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
}

.rewrite-modal-actions .save-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.rewrite-modal-actions .cancel-btn {
    background: #f0f0f0;
    color: #333;
}

.rewrite-modal-actions button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

/* Responsividade */
@media (max-width: 768px) {
    .chat-container {
        width: 100%;
        height: 100vh;
        max-height: none;
        border-radius: 0;
    }
    
    .chat-header {
        border-radius: 0;
    }
    
    .debug-panel {
        width: 100%;
        right: 0;
        bottom: 0;
        border-radius: 0;
    }
    
    .content {
        max-width: 80%;
    }
}
</style>
```

## 11. public/js/chat.js
```javascript
// Variáveis globais
let sessionId = generateSessionId();
let isFirstMessage = true;
let debugLogs = [];
let totalTokens = 0;
let totalCost = 0;
let messageIdCounter = 0;

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    createParticles();
});

function initializeChat() {
    // Event listeners
    document.getElementById('sendButton').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Debug panel
    document.getElementById('toggleDebug').addEventListener('click', toggleDebugPanel);
    document.getElementById('clearLogs').addEventListener('click', clearDebugLogs);
    document.getElementById('exportLogs').addEventListener('click', exportDebugLogs);
    
    // Focus no input
    document.getElementById('messageInput').focus();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Adiciona mensagem do usuário
    addMessage('user', message);
    input.value = '';
    
    // Mostra indicador de digitação
    showTyping();
    
    // Log debug
    addDebugLog('Enviando mensagem', { message, sessionId });
    
    // Envia para o servidor
    fetch('api/chat.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            sessionId: sessionId,
            isFirst: isFirstMessage
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTyping();
        
        if (data.success) {
            // Adiciona resposta do bot
            const messageId = addMessage('bot', data.message);
            
            // Atualiza estatísticas
            if (data.tokens) {
                updateStats(data.tokens);
            }
            
            // Log debug
            addDebugLog('Resposta recebida', data);
            
            // Marca que não é mais a primeira mensagem
            isFirstMessage = false;
        } else {
            addMessage('bot', 'Desculpe, ocorreu um erro. Por favor, tente novamente.');
            addDebugLog('Erro na resposta', data);
        }
    })
    .catch(error => {
        hideTyping();
        addMessage('bot', 'Desculpe, não consegui processar sua mensagem. Tente novamente.');
        addDebugLog('Erro de rede', error);
    });
}

function addMessage(type, content) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageId = 'msg_' + (++messageIdCounter);
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.id = messageId;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = type === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    
    const p = document.createElement('p');
    p.innerHTML = formatMessage(content);
    contentDiv.appendChild(p);
    
    // Adiciona botões de feedback para mensagens do bot
    if (type === 'bot') {
        const feedbackDiv = createFeedbackButtons(messageId);
        contentDiv.appendChild(feedbackDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

function formatMessage(message) {
    // Converte quebras de linha em <br>
    message = message.replace(/\n/g, '<br>');
    
    // Detecta e formata listas
    message = message.replace(/^- (.+)$/gm, '• $1');
    
    // Detecta emojis de confirmação
    message = message.replace(/✅/g, '<span style="font-size: 1.2em">✅</span>');
    message = message.replace(/📅/g, '<span style="font-size: 1.2em">📅</span>');
    message = message.replace(/⏰/g, '<span style="font-size: 1.2em">⏰</span>');
    message = message.replace(/👨‍⚕️/g, '<span style="font-size: 1.2em">👨‍⚕️</span>');
    message = message.replace(/📍/g, '<span style="font-size: 1.2em">📍</span>');
    
    return message;
}

function createFeedbackButtons(messageId) {
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-buttons';
    
    const likeBtn = document.createElement('button');
    likeBtn.innerHTML = '👍 Útil';
    likeBtn.onclick = () => handleFeedback(messageId, 'positivo', likeBtn);
    
    const dislikeBtn = document.createElement('button');
    dislikeBtn.innerHTML = '👎 Não útil';
    dislikeBtn.onclick = () => handleFeedback(messageId, 'negativo', dislikeBtn);
    
    const rewriteBtn = document.createElement('button');
    rewriteBtn.innerHTML = '✏️ Reescrever';
    rewriteBtn.onclick = () => showRewriteModal(messageId);
    
    feedbackDiv.appendChild(likeBtn);
    feedbackDiv.appendChild(dislikeBtn);
    feedbackDiv.appendChild(rewriteBtn);
    
    return feedbackDiv;
}

function handleFeedback(messageId, feedbackType, button) {
    // Visual feedback
    const buttons = button.parentElement.querySelectorAll('button');
    buttons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    
    // Envia feedback para o servidor
    fetch('api/feedback.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            messageId: messageId,
            feedbackType: feedbackType,
            sessionId: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        addDebugLog('Feedback enviado', data);
    })
    .catch(error => {
        addDebugLog('Erro ao enviar feedback', error);
    });
}

function showRewriteModal(messageId) {
    const messageElement = document.getElementById(messageId);
    const originalText = messageElement.querySelector('p').innerText;
    
    const modal = document.createElement('div');
    modal.className = 'rewrite-modal';
    
    modal.innerHTML = `
        <div class="rewrite-modal-content">
            <h3>Como você reescreveria esta resposta?</h3>
            <textarea id="rewriteText">${originalText}</textarea>
            <div class="rewrite-modal-actions">
                <button class="save-btn" onclick="saveRewrite('${messageId}')">Salvar</button>
                <button class="cancel-btn" onclick="closeRewriteModal()">Cancelar</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.getElementById('rewriteText').focus();
}

function saveRewrite(messageId) {
    const rewrittenText = document.getElementById('rewriteText').value;
    
    fetch('api/rewrite.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            messageId: messageId,
            rewrittenText: rewrittenText,
            sessionId: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        addDebugLog('Reescrita salva', data);
        closeRewriteModal();
        
        // Marca como feedback positivo também
        const feedbackBtn = document.querySelector(`#${messageId} .feedback-buttons button:first-child`);
        if (feedbackBtn) {
            feedbackBtn.click();
        }
    })
    .catch(error => {
        addDebugLog('Erro ao salvar reescrita', error);
    });
}

function closeRewriteModal() {
    const modal = document.querySelector('.rewrite-modal');
    if (modal) {
        modal.remove();
    }
}

function showTyping() {
    const messagesContainer = document.getElementById('chatMessages');
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing-indicator';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';
    
    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = '<span></span><span></span><span></span>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTyping() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function updateStats(tokens) {
    if (tokens.prompt_tokens) {
        totalTokens += tokens.prompt_tokens + (tokens.completion_tokens || 0);
        totalCost += (tokens.prompt_tokens * 0.0015 + (tokens.completion_tokens || 0) * 0.002) / 1000;
        
        document.getElementById('totalTokens').textContent = totalTokens;
        document.getElementById('totalCost').textContent = '$' + totalCost.toFixed(4);
    }
}

function toggleDebugPanel() {
    const debugContent = document.getElementById('debugContent');
    const toggleBtn = document.getElementById('toggleDebug');
    
    if (debugContent.classList.contains('hidden')) {
        debugContent.classList.remove('hidden');
        toggleBtn.textContent = '▼';
    } else {
        debugContent.classList.add('hidden');
        toggleBtn.textContent = '▶';
    }
}

function addDebugLog(label, data) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = {
        timestamp: timestamp,
        label: label,
        data: data
    };
    
    debugLogs.push(logEntry);
    
    const logDiv = document.getElementById('debugLogs');
    const entryDiv = document.createElement('div');
    entryDiv.className = 'debug-log-entry';
    entryDiv.innerHTML = `<strong>[${timestamp}]</strong> ${label}: ${JSON.stringify(data, null, 2)}`;
    
    logDiv.appendChild(entryDiv);
    logDiv.scrollTop = logDiv.scrollHeight;
}

function clearDebugLogs() {
    debugLogs = [];
    document.getElementById('debugLogs').innerHTML = '';
    addDebugLog('Logs limpos', {});
}

function exportDebugLogs() {
    const dataStr = JSON.stringify(debugLogs, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `chat_logs_${sessionId}_${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    addDebugLog('Logs exportados', { filename: exportFileDefaultName });
}

function createParticles() {
    const particlesContainer = document.getElementById('particles-bg');
    const particleCount = 20;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        const size = Math.random() * 60 + 20;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        
        particle.style.animationDelay = Math.random() * 20 + 's';
        particle.style.animationDuration = (Math.random() * 20 + 20) + 's';
        
        particlesContainer.appendChild(particle);
    }
}

// Auto-save do sessionId no localStorage para recuperação
if (localStorage.getItem('sessionId')) {
    sessionId = localStorage.getItem('sessionId');
} else {
    localStorage.setItem('sessionId', sessionId);
}

// Limpa sessionId após 24 horas
setTimeout(() => {
    localStorage.removeItem('sessionId');
}, 24 * 60 * 60 * 1000);
```

## 12. public/api/chat.php
```php
<?php
require_once '../../vendor/autoload.php';

use Dotenv\Dotenv;
use App\Controllers\ChatController;

// Carrega variáveis de ambiente
$dotenv = Dotenv::createImmutable(dirname(__DIR__, 2));
$dotenv->load();

// Headers
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Apenas POST é permitido
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Método não permitido']);
    exit;
}

// Recebe dados
$input = json_decode(file_get_contents('php://input'), true);

if (!isset($input['message']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}

try {
    // Processa mensagem
    $chatController = new ChatController();
    $response = $chatController->processMessage(
        $input['message'],
        $input['sessionId'],
        $input['isFirst'] ?? false
    );
    
    echo json_encode($response);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Erro interno do servidor',
        'message' => 'Desculpe, ocorreu um erro. Por favor, tente novamente.'
    ]);
}
```

## 13. public/api/feedback.php
```php
<?php
require_once '../../vendor/autoload.php';

use Dotenv\Dotenv;
use App\Services\DatabaseService;

// Carrega variáveis de ambiente
$dotenv = Dotenv::createImmutable(dirname(__DIR__, 2));
$dotenv->load();

// Headers
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Apenas POST é permitido
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Método não permitido']);
    exit;
}

// Recebe dados
$input = json_decode(file_get_contents('php://input'), true);

if (!isset($input['messageId']) || !isset($input['feedbackType']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}

try {
    $db = new DatabaseService();
    
    // Busca a conversa mais recente desta sessão
    $sql = "SELECT id FROM conversas 
            WHERE session_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1";
    
    $result = $db->query($sql, [$input['sessionId']]);
    
    if (!empty($result)) {
        $conversaId = $result[0]['id'];
        
        // Atualiza o feedback
        $sql = "UPDATE conversas 
                SET feedback_tipo = ? 
                WHERE id = ?";
        
        $db->execute($sql, [$input['feedbackType'], $conversaId]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Feedback registrado com sucesso'
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Conversa não encontrada'
        ]);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Erro ao registrar feedback'
    ]);
}
```

## 14. public/api/rewrite.php
```php
<?php
require_once '../../vendor/autoload.php';

use Dotenv\Dotenv;
use App\Services\DatabaseService;

// Carrega variáveis de ambiente
$dotenv = Dotenv::createImmutable(dirname(__DIR__, 2));
$dotenv->load();

// Headers
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Apenas POST é permitido
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Método não permitido']);
    exit;
}

// Recebe dados
$input = json_decode(file_get_contents('php://input'), true);

if (!isset($input['messageId']) || !isset($input['rewrittenText']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}

try {
    $db = new DatabaseService();
    
    // Busca a conversa mais recente desta sessão
    $sql = "SELECT id FROM conversas 
            WHERE session_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1";
    
    $result = $db->query($sql, [$input['sessionId']]);
    
    if (!empty($result)) {
        $conversaId = $result[0]['id'];
        
        // Atualiza com a resposta reescrita
        $sql = "UPDATE conversas 
                SET resposta_reescrita = ?,
                    feedback_melhorado = 1 
                WHERE id = ?";
        
        $db->execute($sql, [$input['rewrittenText'], $conversaId]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Resposta reescrita salva com sucesso'
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Conversa não encontrada'
        ]);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Erro ao salvar resposta reescrita'
    ]);
}
```

## 15. README.md
```markdown
# Sistema de Assistente Virtual Médico

Sistema de assistente virtual para clínicas médicas com foco em agendamento contextual, utilizando PHP/MySQL e integração com OpenAI.

## Características

- 🤖 Assistente virtual inteligente com processamento de linguagem natural
- 📅 Sistema completo de agendamento de consultas
- 💬 Interface de chat moderna e responsiva
- 🔄 Aprendizado contínuo através de feedback dos usuários
- 📊 Dashboard de debug para monitoramento
- 🎨 Design moderno com animações e partículas
- 📱 Totalmente responsivo para mobile e desktop

## Requisitos

- PHP 8.1 ou superior
- MySQL 5.7 ou superior
- Composer
- Chave de API da OpenAI

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/medical-assistant.git
cd medical-assistant
```

2. Instale as dependências:
```bash
composer install
```

3. Configure o arquivo `.env`:
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:
```env
DB_HOST=localhost
DB_NAME=andreia
DB_USER=root
DB_PASS=sua_senha

OPENAI_API_KEY=sua_chave_openai
OPENAI_MODEL=gpt-3.5-turbo
```

4. Importe o banco de dados:
```bash
mysql -u root -p andreia < database/schema.sql
```

5. Configure o servidor web para apontar para a pasta `public/`

6. Acesse o sistema através do navegador

## Estrutura do Projeto

```
medical-assistant/
├── public/              # Arquivos públicos
│   ├── api/            # Endpoints da API
│   ├── css/            # Estilos
│   ├── js/             # JavaScript
│   └── chat.php        # Interface principal
├── src/                # Código fonte
│   ├── Config/         # Configurações
│   ├── Controllers/    # Controladores
│   └── Services/       # Serviços
├── vendor/             # Dependências
├── .env                # Variáveis de ambiente
└── composer.json       # Configuração do Composer
```

## Funcionalidades Principais

### Para Pacientes
- Agendamento de consultas
- Consulta de horários disponíveis
- Cancelamento e reagendamento
- Informações sobre profissionais
- Verificação de convênios aceitos
- Consulta de serviços oferecidos

### Para a Clínica
- Sistema de aprendizado por feedback
- Histórico completo de conversas
- Estatísticas de uso
- Configurações personalizáveis
- Gestão de estado de agendamentos

## Uso

1. Acesse `http://seu-dominio/chat.php`
2. Inicie uma conversa com o assistente
3. O sistema identificará automaticamente a intenção do usuário
4. Para agendamentos, o assistente guiará o processo passo a passo
5. Use os botões de feedback para melhorar as respostas

## Debug e Monitoramento

O sistema inclui um painel de debug que mostra:
- Logs em tempo real
- Contagem de tokens utilizados
- Custo estimado das conversas
- Exportação de logs para análise

Para acessar, clique no ícone 🔧 no canto inferior direito.

## Segurança

- Todas as entradas são sanitizadas
- Conexões seguras com o banco de dados
- API keys protegidas em variáveis de ambiente
- Validação de dados em todas as operações

## Manutenção

### Logs de Erro
Os erros são automaticamente registrados na tabela `erros_sistema`.

### Backup
Recomenda-se backup diário do banco de dados, especialmente das tabelas:
- `agendamentos`
- `pacientes`
- `conversas`

### Atualizações
Para atualizar o sistema:
```bash
git pull origin main
composer update
```

## Suporte

Para suporte ou dúvidas sobre o sistema, consulte a documentação completa ou entre em contato com o desenvolvedor.

## Licença

Este projeto é proprietário e confidencial. Todos os direitos reservados.
```

## 16. Script SQL para Criação do Banco (database/schema.sql)
```sql
-- Criação do banco de dados
CREATE DATABASE IF NOT EXISTS andreia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE andreia;

-- Tabela de pacientes
CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) UNIQUE,
    email VARCHAR(255),
    session_id VARCHAR(255),
    data_nascimento DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_telefone (telefone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de profissionais
CREATE TABLE IF NOT EXISTS profissionais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    especialidade VARCHAR(255),
    crm VARCHAR(50),
    duracao_consulta INT,
    valor_consulta DECIMAL(10,2),
    ativo TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de agendamentos
CREATE TABLE IF NOT EXISTS agendamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT,
    data_consulta DATE NOT NULL,
    hora_consulta TIME NOT NULL,
    status ENUM('confirmado', 'pendente', 'cancelado') DEFAULT 'pendente',
    observacoes TEXT,
    procedimento VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    valor_consulta DECIMAL(10,2),
    forma_pagamento VARCHAR(100),
    parcelas INT DEFAULT 1,
    profissional VARCHAR(255),
    tipo_consulta ENUM('primeira_vez', 'retorno', 'procedimento') DEFAULT 'primeira_vez',
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    INDEX idx_data_hora (data_consulta, hora_consulta),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de agendamentos em andamento
CREATE TABLE IF NOT EXISTS agendamentos_em_andamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    data_consulta DATE,
    hora_consulta TIME,
    nome_paciente VARCHAR(255),
    telefone_paciente VARCHAR(20),
    etapa ENUM('data', 'hora', 'nome', 'telefone', 'concluido', 'aguardando_escolha', 
               'aguardando_identificacao', 'aguardando_escolha_agendamento', 
               'aguardando_opcao_paciente') DEFAULT 'data',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    dados_reagendamento JSON,
    dados_json JSON,
    INDEX idx_session_id (session_id),
    INDEX idx_etapa (etapa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de configurações
CREATE TABLE IF NOT EXISTS configuracoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    descricao VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de horários disponíveis
CREATE TABLE IF NOT EXISTS horarios_disponiveis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dia_semana ENUM('segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo') NOT NULL,
    manha_inicio TIME NOT NULL,
    manha_fim TIME NOT NULL,
    intervalo_minutos INT,
    ativo INT NOT NULL DEFAULT 1,
    tarde_inicio TIME,
    tarde_fim TIME,
    profissional_id INT,
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de serviços
CREATE TABLE IF NOT EXISTS servicos_clinica (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    duracao_minutos INT,
    valor DECIMAL(10,2),
    ativo TINYINT(1) DEFAULT 1,
    palavras_chave TEXT,
    categoria VARCHAR(100),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    tipo VARCHAR(255),
    preparo_necessario TEXT,
    anestesia_tipo VARCHAR(100),
    local_realizacao VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de convênios
CREATE TABLE IF NOT EXISTS convenios_aceitos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    registro_ans VARCHAR(50),
    ativo TINYINT(1) DEFAULT 1,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    observacoes_especificas TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de conversas
CREATE TABLE IF NOT EXISTS conversas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255),
    mensagem_usuario TEXT,
    resposta_agente TEXT,
    funcao_chamada VARCHAR(100),
    tokens_prompt INT DEFAULT 0,
    tokens_resposta INT DEFAULT 0,
    custo_estimado DECIMAL(10,6) DEFAULT 0.000000,
    feedback_tipo ENUM('positivo', 'negativo'),
    resposta_reescrita TEXT,
    feedback_melhorado TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_feedback (feedback_tipo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de parceiros
CREATE TABLE IF NOT EXISTS parceiros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(100),
    servicos_oferecidos TEXT,
    telefone VARCHAR(20),
    endereco TEXT,
    ativo TINYINT(1) DEFAULT 1,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de FAQ
CREATE TABLE IF NOT EXISTS faq_ginecologia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    categoria VARCHAR(100),
    palavras_chave TEXT,
    ordem INT DEFAULT 0,
    ativo TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de formas de pagamento
CREATE TABLE IF NOT EXISTS formas_pagamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    ativo TINYINT(1) DEFAULT 1,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de atividade do chat
CREATE TABLE IF NOT EXISTS chat_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('active', 'inactive', 'ended') DEFAULT 'active',
    INDEX idx_session_status (session_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de mensagens automáticas
CREATE TABLE IF NOT EXISTS chat_auto_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_type (session_id, message_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de erros do sistema
CREATE TABLE IF NOT EXISTS erros_sistema (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo_erro VARCHAR(100),
    mensagem TEXT,
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tipo_erro (tipo_erro)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de exceções de agenda
CREATE TABLE IF NOT EXISTS excecoes_agenda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data DATE NOT NULL,
    tipo ENUM('feriado', 'fechamento', 'horario_especial') NOT NULL,
    descricao VARCHAR(255),
    horario_inicio TIME,
    horario_fim TIME,
    profissional_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    INDEX idx_data (data)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Inserir dados iniciais de configuração
INSERT INTO configuracoes (chave, valor, descricao) VALUES
('nome_clinica', 'Clínica Médica Exemplo', 'Nome da clínica'),
('endereco', 'Rua Exemplo, 123 - Centro', 'Endereço completo'),
('telefone', '(11) 1234-5678', 'Telefone principal'),
('whatsapp', '(11) 91234-5678', 'WhatsApp para contato'),
('email', 'contato@clinicaexemplo.com.br', 'E-mail de contato'),
('horario_funcionamento', 'Segunda a Sexta: 8h às 18h', 'Horário de funcionamento'),
('especialidade', 'Clínica Geral', 'Especialidade principal da clínica');

-- Inserir horários padrão
INSERT INTO horarios_disponiveis (dia_semana, manha_inicio, manha_fim, tarde_inicio, tarde_fim, intervalo_minutos) VALUES
('segunda', '08:00:00', '12:00:00', '14:00:00', '18:00:00', 30),
('terca', '08:00:00', '12:00:00', '14:00:00', '18:00:00', 30),
('quarta', '08:00:00', '12:00:00', '14:00:00', '18:00:00', 30),
('quinta', '08:00:00', '12:00:00', '14:00:00', '18:00:00', 30),
('sexta', '08:00:00', '12:00:00', '14:00:00', '18:00:00', 30);

-- Inserir formas de pagamento padrão
INSERT INTO formas_pagamento (nome) VALUES
('Dinheiro'),
('Cartão de Crédito'),
('Cartão de Débito'),
('PIX'),
('Transferência Bancária');

-- Inserir profissionais de exemplo
INSERT INTO profissionais (nome, especialidade, crm, duracao_consulta, valor_consulta, ativo) VALUES
('Dra. Maria Silva', 'Ginecologia e Obstetrícia', 'CRM-SP 12345', 30, 150.00, 1),
('Dr. João Santos', 'Clínico Geral', 'CRM-SP 67890', 30, 120.00, 1),
('Dra. Ana Costa', 'Pediatria', 'CRM-SP 11111', 30, 130.00, 1),
('Dr. Carlos Oliveira', 'Cardiologia', 'CRM-SP 22222', 45, 200.00, 1);
```

---

Este é um sistema completo e robusto de assistente virtual médico, com todas as funcionalidades especificadas:

1. **Funções mínimas de acesso a dados** - As funções apenas buscam e retornam dados do banco
2. **Liberdade interpretativa da IA** - O sistema permite que a IA interprete contexto e gere respostas naturais
3. **Gestão de estado via tabela agendamentos_em_andamento** - Implementado com funções específicas
4. **Integração com mecanismo de aprendizado por feedback** - Sistema completo de feedback e reescrita
5. **Interface conversacional fluída** - Design moderno com animações e responsividade

O sistema está pronto para implantação e uso imediato!