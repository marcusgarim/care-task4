<?php
namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class OpenAIService {
    private $client;
    private $apiKey;
    private $model;
    private $db;
    private $lastToolCallId = null;
    private $lastToolCallName = null;
    private $lastMessages = [];
    private $logger;
    
    public function __construct() {
        // Configura timeout adequado para evitar respostas incompletas
        $this->client = new Client([
            'timeout' => 60, // 60 segundos para timeout geral
            'connect_timeout' => 10, // 10 segundos para conexão
            'read_timeout' => 60, // 60 segundos para leitura
            'http_errors' => false // Não lança exceções para erros HTTP
        ]);
        
        // Carrega as variáveis de ambiente se não estiverem carregadas
        if (!isset($_ENV['OPENAI_API_KEY'])) {
            $dotenv = \Dotenv\Dotenv::createImmutable(__DIR__ . '/../../');
            $dotenv->load();
        }
        
        $this->apiKey = $_ENV['OPENAI_API_KEY'];
        $this->model = $_ENV['OPENAI_MODEL'];
        $this->db = new DatabaseService();
        $this->logger = LoggerService::getInstance();
    }
    
    public function chat($messages, $functions = null) {
        // Armazena as mensagens para uso posterior
        $this->lastMessages = $messages;
        
        $maxRetries = 3;
        $attempt = 0;

        // Se o modelo é da família gpt-5 (ou outros que exigem Responses API), usa Responses API
        $normalizedModel = trim(strtolower($this->model ?? ''));
        $useResponsesApi = (strpos($normalizedModel, 'gpt-5') !== false || strpos($normalizedModel, 'o-') === 0);

        // DEBUG inicial
        $this->logger->debug("model={$this->model}; normalized={$normalizedModel}; useResponsesApi=" . ($useResponsesApi ? '1' : '0'));
        $this->logger->debug("last user message: " . $this->getLastUserMessage());
        if (!is_array($messages) || empty($messages)) {
            $this->logger->debug('messages vazio ou inválido: ' . json_encode($messages));
        } else {
            // Loga uma versão truncada para evitar excesso
            $messagesPreview = $messages;
            foreach ($messagesPreview as &$m) {
                if (isset($m['content']) && is_string($m['content']) && strlen($m['content']) > 500) {
                    $m['content'] = substr($m['content'], 0, 500) . '...';
                }
            }
            unset($m);
            $this->logger->debug('messages: ' . json_encode($messagesPreview));
        }

        while ($attempt < $maxRetries) {
            try {
                if ($useResponsesApi) {
                    // Constrói input estruturado (role + content) conforme Responses API
                    $structuredInput = $this->buildStructuredInputFromMessages($messages);

                    $payload = [
                        'model' => $this->model,
                        'input' => $structuredInput,
                        'max_output_tokens' => 5000
                    ];

                    // Se funções foram fornecidas, exponha como tools com escolha automática
                    if (is_array($functions) && !empty($functions)) {
                        $payload['tools'] = $this->mapFunctionsToTools($functions);
                        // tool_choice opcional; removido para compatibilidade máxima com Responses API
                    }

                    $cleanPayload = $this->cleanUtf8($payload);
                    $this->logger->debug('REQUEST PAYLOAD: ' . json_encode($cleanPayload));

                    $response = $this->client->post('https://api.openai.com/v1/responses', [
                        'headers' => [
                            'Authorization' => 'Bearer ' . $this->apiKey,
                            'Content-Type' => 'application/json'
                        ],
                        'json' => $cleanPayload
                    ]);

                    $rawBody = $response->getBody()->getContents();
                    $this->logger->debug('RESPONSE BODY: ' . substr($rawBody, 0, 1000));
                    $this->logger->debug('===== RESPOSTA COMPLETA DA IA =====');
                    $this->logger->debug('Raw response body: ' . $rawBody);
                    $result = json_decode($rawBody, true);
                    $this->logger->debug('Decoded result: ' . json_encode($result, JSON_PRETTY_PRINT));

                    // Mapeia para formato compatível com ChatController
                    $usage = $this->extractUsageFromResponse($result);
                    $this->logger->debug('Extracted usage: ' . json_encode($usage));

                    // Preferir mapear tool_calls para function_call (compatível com ChatController)
                    $functionCall = $this->extractFunctionCallFromResponse($result);
                    if ($functionCall) {
                        $this->logger->debug('Function call detected: ' . json_encode($functionCall));
                        $response = [
                            'success' => true,
                            'data' => [
                                'choices' => [
                                    [
                                        'message' => [
                                            'function_call' => $functionCall,
                                            'content' => null
                                        ]
                                    ]
                                ],
                                'usage' => $usage
                            ]
                        ];
                        $this->logger->debug('Returning function call response: ' . json_encode($response, JSON_PRETTY_PRINT));
                        return $response;
                    }

                    // Caso contrário, devolve conteúdo textual legível filtrado
                    $content = $this->extractResponseText($result);
                    $this->logger->debug('Extracted content before filtering: ' . $content);
                    $content = $this->filterInternalNotations($content);
                    $this->logger->debug('Content after filtering: ' . $content);
                    $response = [
                        'success' => true,
                        'data' => [
                            'choices' => [
                                [
                                    'message' => [
                                        'content' => $content
                                    ]
                                ]
                            ],
                            'usage' => $usage
                        ]
                    ];
                    $this->logger->debug('Returning text response: ' . json_encode($response, JSON_PRETTY_PRINT));
                    $this->logger->debug('===== FIM RESPOSTA COMPLETA DA IA =====');
                    return $response;
                } else {
                    // Caminho legado (chat/completions)
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

                    $cleanPayload = $this->cleanUtf8($payload);
                    $this->logger->debug('REQUEST PAYLOAD: ' . json_encode($cleanPayload));

                    $response = $this->client->post('https://api.openai.com/v1/chat/completions', [
                        'headers' => [
                            'Authorization' => 'Bearer ' . $this->apiKey,
                            'Content-Type' => 'application/json'
                        ],
                        'json' => $cleanPayload
                    ]);

                    $rawBody = $response->getBody()->getContents();
                    $this->logger->debug('RESPONSE BODY: ' . substr($rawBody, 0, 1000));
                    $this->logger->debug('===== RESPOSTA COMPLETA DA IA (LEGACY) =====');
                    $this->logger->debug('Raw response body: ' . $rawBody);
                    $result = json_decode($rawBody, true);
                    $this->logger->debug('Decoded result: ' . json_encode($result, JSON_PRETTY_PRINT));

                    $response = [
                        'success' => true,
                        'data' => $result
                    ];
                    $this->logger->debug('Returning legacy response: ' . json_encode($response, JSON_PRETTY_PRINT));
                    $this->logger->debug('===== FIM RESPOSTA COMPLETA DA IA (LEGACY) =====');
                    return $response;
                }
            } catch (RequestException $e) {
                $attempt++;
                $statusCode = $e->hasResponse() ? $e->getResponse()->getStatusCode() : 0;

                // Se for erro 429 (rate limit), tenta novamente com backoff exponencial
                if ($statusCode === 429 && $attempt < $maxRetries) {
                    $waitTime = pow(2, $attempt) * 1000000; // Microssegundos
                    $this->logger->warn("Tentativa $attempt de $maxRetries. Aguardando " . ($waitTime / 1000000) . " segundos...");
                    usleep($waitTime);
                    continue;
                }

                $errorMessage = $e->getMessage();
                if ($e->hasResponse()) {
                    $resp = $e->getResponse();
                    $responseBody = $resp->getBody()->getContents();
                    $errorMessage .= " - Response: " . $responseBody;
                    // Log completo para depuração
                    $this->logger->error("HTTP $statusCode - $responseBody");
                    $this->logger->error("===== ERRO COMPLETO DA IA =====");
                    $this->logger->error("Status Code: $statusCode");
                    $this->logger->error("Error Message: $errorMessage");
                    $this->logger->error("Full Response Body: $responseBody");
                    $this->logger->error("===== FIM ERRO COMPLETO DA IA =====");
                }
                $this->registrarErroNoBanco($errorMessage);

                $errorResponse = [
                    'success' => false,
                    'error' => 'Erro na comunicação com a IA: ' . $e->getMessage()
                ];
                $this->logger->error("Returning error response: " . json_encode($errorResponse, JSON_PRETTY_PRINT));
                return $errorResponse;
            } catch (\Exception $e) {
                $this->logger->error("===== ERRO INESPERADO DA IA =====");
                $this->logger->error("Exception: " . $e->getMessage());
                $this->logger->error("File: " . $e->getFile() . ":" . $e->getLine());
                $this->logger->error("Stack trace: " . $e->getTraceAsString());
                $this->logger->error("===== FIM ERRO INESPERADO DA IA =====");
                
                $this->registrarErroNoBanco($e->getMessage());

                $errorResponse = [
                    'success' => false,
                    'error' => 'Erro inesperado: ' . $e->getMessage()
                ];
                $this->logger->error("Returning unexpected error response: " . json_encode($errorResponse, JSON_PRETTY_PRINT));
                return $errorResponse;
            }
        }

        // Se chegou aqui, todas as tentativas falharam
        $this->logger->error("===== FALHA APÓS MÚLTIPLAS TENTATIVAS =====");
        $this->logger->error("Todas as $maxRetries tentativas falharam");
        $this->logger->error("===== FIM FALHA APÓS MÚLTIPLAS TENTATIVAS =====");
        
        $this->registrarErroNoBanco("Todas as $maxRetries tentativas falharam");
        $failureResponse = [
            'success' => false,
            'error' => 'Erro na comunicação com a IA após múltiplas tentativas'
        ];
        $this->logger->error("Returning failure response: " . json_encode($failureResponse, JSON_PRETTY_PRINT));
        return $failureResponse;
    }
    
    private function registrarErroNoBanco($mensagem) {
        $sql = "INSERT INTO erros_sistema (tipo, mensagem, created_at) 
                VALUES ('openai_error', ?, NOW())";
        $this->db->execute($sql, [$mensagem]);
    }
    
    private function cleanUtf8($data) {
        if (is_string($data)) {
            // Remove caracteres UTF-8 malformados
            return iconv('UTF-8', 'UTF-8//IGNORE', $data);
        } elseif (is_array($data)) {
            $cleaned = [];
            foreach ($data as $key => $value) {
                $cleaned[$key] = $this->cleanUtf8($value);
            }
            return $cleaned;
        }
        return $data;
    }

    private function buildInputBlocksFromMessages(array $messages) {
        // Responses API aceita array de blocos; vamos mapear cada mensagem para um bloco de texto
        $blocks = [];
        foreach ($messages as $msg) {
            $role = $msg['role'] ?? 'user';
            if (!empty($msg['content'])) {
                $blocks[] = [
                    'type' => 'input_text',
                    'text' => '[' . $role . ']: ' . $msg['content']
                ];
            } elseif (!empty($msg['function_call'])) {
                $fn = $msg['function_call'];
                $name = $fn['name'] ?? 'unknown_function';
                $args = $fn['arguments'] ?? '';
                $blocks[] = [
                    'type' => 'input_text',
                    'text' => '[assistant]: <chamada de função> ' . $name . '(' . $args . ')'
                ];
            }
        }
        return $blocks;
    }

    private function buildStructuredInputFromMessages(array $messages) {
        $input = [];
        foreach ($messages as $msg) {
            $role = $msg['role'] ?? 'user';
            if (isset($msg['content'])) {
                // Responses API não aceita role 'function'. Transformar resultados de função em texto do 'assistant'.
                if ($role === 'function') {
                    $functionName = $msg['name'] ?? 'unknown_function';
                    $contentRaw = $msg['content'];
                    $contentText = is_string($contentRaw) ? $contentRaw : json_encode($contentRaw, JSON_UNESCAPED_UNICODE);
                    
                    // Sempre usar fallback: injeta como texto do assistant
                    $input[] = [
                        'role' => 'assistant',
                        'content' => '[resultado_da_funcao ' . $functionName . ']: ' . $this->normalizeFunctionOutput($contentText, $functionName)
                    ];
                } else {
                    $content = $msg['content'];
                    if (!is_string($content)) {
                        $content = json_encode($content, JSON_UNESCAPED_UNICODE);
                    }
                    $input[] = [
                        'role' => $role,
                        'content' => $content
                    ];
                }
            } elseif (!empty($msg['function_call'])) {
                $fn = $msg['function_call'];
                $name = $fn['name'] ?? 'unknown_function';
                $args = $fn['arguments'] ?? '';
                $input[] = [
                    'role' => 'assistant',
                    'content' => '<chamada de função> ' . $name . '(' . (is_string($args) ? $args : json_encode($args)) . ')'
                ];
            }
        }
        return $input;
    }

    private function normalizeFunctionOutput(string $contentText, string $functionName): string {
        // Se output é vazio ou '[]'/'{}', retorna mensagem legível específica por função
        $trim = trim($contentText);
        if ($trim === '' || $trim === '[]' || $trim === '{}' || $trim === 'null') {
            if ($functionName === 'buscar_profissionais_clinica') {
                return 'Nenhum profissional encontrado para os critérios informados.';
            }
            if ($functionName === 'buscar_servicos_clinica') {
                return 'Nenhum serviço encontrado para os critérios informados.';
            }
            if ($functionName === 'verificar_horarios_disponiveis') {
                return 'Não há horários disponíveis nos critérios solicitados.';
            }
            // fallback genérico
            return 'Sem resultados para esta ação.';
        }
        return $contentText;
    }

    private function mapFunctionsToTools(array $functions) {
        // Responses API espera nome no nível superior do tool
        $tools = [];
        foreach ($functions as $fn) {
            $tools[] = [
                'type' => 'function',
                'name' => $fn['name'] ?? 'funcao_sem_nome',
                'description' => $fn['description'] ?? '',
                'parameters' => $fn['parameters'] ?? ['type' => 'object']
            ];
        }
        return $tools;
    }

    private function buildInputTextFromMessages(array $messages) {
        $lines = [];
        foreach ($messages as $msg) {
            $role = $msg['role'] ?? 'user';
            // Ignora blocos que não tenham conteúdo textual simples
            if (!empty($msg['content'])) {
                $prefix = '[' . $role . ']: ';
                $lines[] = $prefix . $msg['content'];
            } elseif (!empty($msg['function_call'])) {
                // Representa function_call de forma textual
                $fn = $msg['function_call'];
                $name = $fn['name'] ?? 'unknown_function';
                $args = $fn['arguments'] ?? '';
                $lines[] = "[assistant]: <chamada de função> $name($args)";
            }
        }
        return implode("\n\n", $lines);
    }

    private function extractResponseText(array $result) {
        $this->logger->debug('===== INÍCIO EXTRACT RESPONSE TEXT =====');
        $this->logger->debug('extractResponseText - chamado com: ' . json_encode($result, JSON_PRETTY_PRINT));
        $this->logger->debug('extractResponseText - input: ' . json_encode($result, JSON_PRETTY_PRINT));
        $this->logger->debug('extractResponseText - functions count: ' . (isset($result['functions']) ? count($result['functions']) : '0'));
        
        // 1. Primeiro verifique se há dados de função válidos que podem ser usados
        if (!empty($result['functions']) && is_array($result['functions'])) {
            $this->logger->debug('Verificando dados de funções...');
            foreach ($result['functions'] as $function) {
                if (isset($function['result'])) {
                    $this->logger->debug('Encontrou função com resultado: ' . $function['name']);
                    
                    // Para funções específicas, SEMPRE use o resultado da função
                    if (in_array($function['name'], ['verificar_horarios_disponiveis', 'buscar_profissionais_clinica', 'buscar_servicos_clinica', 'verificar_convenio'])) {
                        $this->logger->debug('Função crítica encontrada: ' . $function['name'] . ' - usando resultado da função');
                        $response = $this->handleFunctionCallSummary($function['name'], $function['result']);
                        if ($response) {
                            $this->logger->debug('handleFunctionCallSummary retornou: ' . $response);
                            return $response;
                        }
                    } else {
                        // Para outras funções, usa o método handleFunctionCallSummary para gerar respostas estruturadas
                        $this->logger->debug('Chamando handleFunctionCallSummary para: ' . $function['name'] . ' com args: ' . json_encode($function['result']));
                        $response = $this->handleFunctionCallSummary($function['name'], $function['result']);
                        if ($response) {
                            $this->logger->debug('handleFunctionCallSummary retornou: ' . $response);
                            return $response;
                        } else {
                            $this->logger->debug('handleFunctionCallSummary retornou null/vazio para: ' . $function['name']);
                        }
                    }
                } else {
                    $this->logger->debug('Função ' . ($function['name'] ?? 'unknown') . ' não tem resultado');
                }
            }
            $this->logger->debug('Nenhuma função retornou resposta válida, continuando com output...');
        } else {
            $this->logger->debug('Nenhuma função encontrada ou functions não é array');
        }

        // 2. Depois verifique o reasoning (mantendo sua lógica atual)
        if (!empty($result['output']) && is_array($result['output'])) {
            $this->logger->debug('Processing output array with ' . count($result['output']) . ' items');
            
            foreach ($result['output'] as $index => $item) {
                $this->logger->debug('Processing output item ' . $index . ': ' . json_encode($item));
                
                if (!is_array($item)) {
                    // Se o item não é array, pode ser uma string direta
                    if (is_string($item) && trim($item) !== '') {
                        $this->logger->debug('Found direct string item: ' . $item);
                        return $item;
                    }
                    $this->logger->debug('Item ' . $index . ' is not array and not string, skipping');
                    continue;
                }

                // 2a) item com 'content' (lista de partes): procurar textos
                if (!empty($item['content']) && is_array($item['content'])) {
                    $this->logger->debug('Item ' . $index . ' has content array with ' . count($item['content']) . ' parts');
                    foreach ($item['content'] as $partIndex => $part) {
                        $this->logger->debug('Processing content part ' . $partIndex . ': ' . json_encode($part));
                        if (!is_array($part)) {
                            // Se a parte não é array, pode ser uma string direta
                            if (is_string($part) && trim($part) !== '') {
                                $this->logger->debug('Found direct string in content part: ' . $part);
                                return $part;
                            }
                            continue;
                        }
                        if (isset($part['text']) && is_string($part['text']) && trim($part['text']) !== '') {
                            $this->logger->debug('Found text in content part: ' . $part['text']);
                            return $part['text'];
                        }
                        if (isset($part['type']) && $part['type'] === 'message' && isset($part['text']) && is_string($part['text'])) {
                            $this->logger->debug('Found message text: ' . $part['text']);
                            return $part['text'];
                        }
                        // Verificar se há 'content' direto na parte
                        if (isset($part['content']) && is_string($part['content']) && trim($part['content']) !== '') {
                            $this->logger->debug('Found content in part: ' . $part['content']);
                            return $part['content'];
                        }
                    }
                }

                // 2b) Se o item for uma function_call, trate de forma segura
                if (isset($item['type']) && $item['type'] === 'function_call') {
                    $this->logger->debug('Found function_call in output');
                    $name = $item['name'] ?? 'unknown_function';
                    $argsRaw = $item['arguments'] ?? '';
                    $args = null;
                    if (is_string($argsRaw)) {
                        $decoded = json_decode($argsRaw, true);
                        if (json_last_error() === JSON_ERROR_NONE) {
                            $args = $decoded;
                        }
                    } elseif (is_array($argsRaw)) {
                        $args = $argsRaw;
                    }
                    $summary = $this->handleFunctionCallSummary($name, $args);
                    $this->logger->debug('Function call summary: ' . $summary);
                    return $summary;
                }

                // 2c) Se houver 'text' direto no item
                if (isset($item['text']) && is_string($item['text']) && trim($item['text']) !== '') {
                    $this->logger->debug('Found direct text: ' . $item['text']);
                    return $item['text'];
                }
                
                // 2d) Se houver 'message' direto no item
                if (isset($item['message']) && is_string($item['message']) && trim($item['message']) !== '') {
                    $this->logger->debug('Found direct message: ' . $item['message']);
                    return $item['message'];
                }
                
                // 2e) Se houver 'content' direto no item
                if (isset($item['content']) && is_string($item['content']) && trim($item['content']) !== '') {
                    $this->logger->debug('Found direct content: ' . $item['content']);
                    return $item['content'];
                }
                
                // 2f) Se for um item de reasoning, tenta extrair informações úteis
                if (isset($item['type']) && $item['type'] === 'reasoning') {
                    $this->logger->debug('Found reasoning item, checking for useful content');
                    
                    if (!empty($item['summary'])) {
                        if (is_array($item['summary'])) {
                            $summaryText = implode(' ', $item['summary']);
                        } else {
                            $summaryText = $item['summary'];
                        }
                        
                        if (!empty($summaryText)) {
                            $this->logger->debug('Using reasoning summary: ' . $summaryText);
                            return $this->cleanMalformedResponse($summaryText);
                        }
                    }
                    
                    if (!empty($item['text'])) {
                        $this->logger->debug('Using reasoning text: ' . $item['text']);
                        return $this->cleanMalformedResponse($item['text']);
                    }
                }
            }
        }

        // 3. Verificar campos diretos
        if (isset($result['text']) && is_string($result['text']) && trim($result['text']) !== '') {
            $this->logger->debug('Found direct text: ' . $result['text']);
            return $this->cleanMalformedResponse($result['text']);
        }
        
        if (isset($result['content']) && is_string($result['content']) && trim($result['content']) !== '') {
            $this->logger->debug('Found direct content: ' . $result['content']);
            return $this->cleanMalformedResponse($result['content']);
        }

        // 4. Fallback baseado no contexto da conversa
        $this->logger->debug('Usando fallback contextual...');
        $this->logger->debug('===== FIM EXTRACT RESPONSE TEXT - FALLBACK =====');
        return $this->generateContextualFallback($result);
    }

    /**
     * Constrói um resumo legível de uma function_call sem expor JSON bruto.
     * Ponto de extensão: aqui você pode invocar handlers locais e devolver o resultado ao usuário.
     */
    private function handleFunctionCallSummary($functionName, $args = null) {
        $this->logger->debug('===== INÍCIO HANDLE FUNCTION CALL SUMMARY =====');
        $this->logger->debug('handleFunctionCallSummary - function: ' . $functionName . ', args: ' . json_encode($args));
        
        // Fornece respostas mais específicas baseadas na função
        switch ($functionName) {
            case 'validar_horario_para_agendamento':
                $this->logger->debug('Processing validar_horario_para_agendamento');
                if ($args && isset($args['valido']) && $args['valido'] === true) {
                    $response = 'Perfeito! O horário está disponível. Posso confirmar sua consulta?';
                    $this->logger->debug('validar_horario_para_agendamento - horário válido: ' . $response);
                    return $response;
                } else {
                    $horariosDisponiveis = $args['horarios_disponiveis'] ?? [];
                    if (!empty($horariosDisponiveis)) {
                        $horariosStr = implode(', ', $horariosDisponiveis);
                        $response = "Este horário não está disponível. Temos estas opções: $horariosStr";
                        $this->logger->debug('validar_horario_para_agendamento - horários alternativos: ' . $response);
                        return $response;
                    } else {
                        $response = 'Este horário não está disponível. Vou verificar outras opções para você.';
                        $this->logger->debug('validar_horario_para_agendamento - sem alternativas: ' . $response);
                        return $response;
                    }
                }
            case 'criar_agendamento':
                // Verificar se há dados do agendamento criado
                if ($args && isset($args['agendamento'])) {
                    $agendamento = $args['agendamento'];
                } elseif ($args && isset($args['sucesso']) && $args['sucesso'] && isset($args['agendamento'])) {
                    // Se os dados estão no resultado da função
                    $agendamento = $args['agendamento'];
                } else {
                    // Fallback para dados básicos se disponíveis
                    $agendamento = null;
                    if ($args && isset($args['nome_paciente']) && isset($args['data_formatada']) && isset($args['hora_formatada'])) {
                        $agendamento = $args;
                    }
                }
                
                if ($agendamento) {
                    // Buscar endereço da clínica
                    $endereco = 'Rua das Flores, 123 - Centro'; // Endereço padrão
                    try {
                        $result = $this->db->query("SELECT valor FROM configuracoes WHERE chave = 'endereco'");
                        if ($result && !empty($result)) {
                            $endereco = $result[0]['valor'];
                        }
                    } catch (\Exception $e) {
                        $this->logger->debug('Erro ao buscar endereço: ' . $e->getMessage());
                    }
                    
                    $response = "Agendamento confirmado!\n\n";
                    $response .= "Data: {$agendamento['data_formatada']} ({$agendamento['dia_semana']})\n";
                    $response .= "Horário: {$agendamento['hora_formatada']}\n";
                    $response .= "Paciente: {$agendamento['nome_paciente']}\n";
                    $response .= "Local: {$endereco}\n\n";
                    $response .= "Anotei tudo certinho! Até lá!";
                } else {
                    $response = "Agendamento confirmado com sucesso!";
                }
                $this->logger->debug('criar_agendamento: ' . $response);
                $this->logger->debug('criar_agendamento - args recebidos: ' . json_encode($args));
                return $response;
            case 'verificar_horarios_disponiveis':
                $this->logger->debug('Processing verificar_horarios_disponiveis');
                $this->logger->debug('Args recebidos: ' . json_encode($args));
                
                if (empty($args) || !is_array($args)) {
                    $response = 'Não há horários disponíveis nos critérios solicitados.';
                    $this->logger->debug('verificar_horarios_disponiveis - sem dados: ' . $response);
                    return $response;
                }
                
                $this->logger->debug('Args é array com ' . count($args) . ' elementos');
                
                // Formata os horários de forma legível e alinhada à confirmação
                $response = "Horários disponíveis!\n\n";
                
                foreach ($args as $index => $dia) {
                    $this->logger->debug('Processando dia ' . $index . ': ' . json_encode($dia));
                    
                    if (isset($dia['data']) && isset($dia['dia_semana']) && isset($dia['horarios'])) {
                        $dataFormatada = date('d/m', strtotime($dia['data']));
                        $diaSemana = $dia['dia_semana'];
                        
                        // Formata os horários para exibição mais limpa
                        $horariosFormatados = [];
                        foreach ($dia['horarios'] as $horario) {
                            $horariosFormatados[] = date('H:i', strtotime($horario));
                        }
                        
                        $horariosStr = implode(', ', $horariosFormatados);
                        $response .= "Data: $dataFormatada ($diaSemana)\n";
                        $response .= "Horários: $horariosStr\n\n";
                        $this->logger->debug('Adicionado ao response: ' . "Data: $dataFormatada ($diaSemana) - $horariosStr");
                    } else {
                        $this->logger->debug('Dia ' . $index . ' não tem estrutura esperada');
                    }
                }
                
                $this->logger->debug('verificar_horarios_disponiveis - formatado: ' . $response);
                return $response;
            case 'buscar_profissionais_clinica':
                $response = 'Buscando informações dos profissionais da clínica...';
                $this->logger->debug('buscar_profissionais_clinica: ' . $response);
                return $response;
            case 'buscar_servicos_clinica':
                $response = 'Buscando informações sobre os serviços disponíveis...';
                $this->logger->debug('buscar_servicos_clinica: ' . $response);
                return $response;
            case 'consultar_agendamento_existente':
                $this->logger->debug('Processing consultar_agendamento_existente');
                // Se há argumentos e contém erro, retorna mensagem específica
                if ($args && isset($args['erro'])) {
                    if (strpos($args['erro'], 'Telefone é obrigatório') !== false) {
                        $response = 'Para verificar seu agendamento, preciso do seu telefone. Pode me informar?';
                        $this->logger->debug('consultar_agendamento_existente - telefone obrigatório: ' . $response);
                        return $response;
                    }
                    $this->logger->debug('consultar_agendamento_existente - erro: ' . $args['erro']);
                    return $args['erro'];
                }
                $response = 'Verificando se você já possui algum agendamento...';
                $this->logger->debug('consultar_agendamento_existente - verificando: ' . $response);
                return $response;
            case 'reagendar_consulta':
                $response = 'Processando o reagendamento da sua consulta...';
                $this->logger->debug('reagendar_consulta: ' . $response);
                return $response;
            case 'cancelar_agendamento':
                $response = 'Processando o cancelamento do seu agendamento...';
                $this->logger->debug('cancelar_agendamento: ' . $response);
                return $response;
            case 'verificar_convenio':
                $this->logger->debug('Processing verificar_convenio');
                if (empty($args)) {
                    $response = "Não consegui verificar o convênio. Por favor, tente novamente.";
                    $this->logger->debug('verificar_convenio - args vazio: ' . $response);
                    return $response;
                }
                
                // Se for array de resultados, pega o primeiro
                $dados = is_array($args) && isset($args[0]) ? $args[0] : $args;
                $this->logger->debug('verificar_convenio - dados processados: ' . json_encode($dados));
                
                if (isset($dados['status']) && $dados['status'] === 'nao_encontrado') {
                    $response = "Não encontrei o convênio '{$dados['termo_buscado']}' em nossos registros.";
                    $this->logger->debug('verificar_convenio - não encontrado: ' . $response);
                    return $response;
                }
                
                if ($dados['status'] === 'inativo') {
                    $mensagem = "Sobre o convênio {$dados['nome']}:\n";
                    $mensagem .= "🔸 Status: {$dados['mensagem_status']}\n";
                    
                    if (!empty($dados['observacoes'])) {
                        $mensagem .= "\nℹ️ Informações: " . trim($dados['observacoes']);
                    }
                    
                    $this->logger->debug('verificar_convenio - inativo: ' . $mensagem);
                    return $mensagem;
                }
                
                $response = "Sim, aceitamos o convênio {$dados['nome']}! " . 
                      (!empty($dados['observacoes']) ? "\n" . trim($dados['observacoes']) : '');
                $this->logger->debug('verificar_convenio - aceito: ' . $response);
                return $response;
            case 'buscar_configuracoes_clinica':
                $response = 'Buscando informações da clínica...';
                $this->logger->debug('buscar_configuracoes_clinica: ' . $response);
                return $response;
            case 'buscar_historico_conversas':
                $response = 'Analisando o histórico de conversas...';
                $this->logger->debug('buscar_historico_conversas: ' . $response);
                return $response;

            default:
                $response = 'Estou processando sua solicitação. Aguarde um momento...';
                $this->logger->debug('handleFunctionCallSummary - default response: ' . $response);
                $this->logger->debug('===== FIM HANDLE FUNCTION CALL SUMMARY =====');
                return $response;
        }
    }

    private function filterInternalNotations(string $content): string {
        $this->logger->debug('===== INÍCIO FILTER INTERNAL NOTATIONS =====');
        $this->logger->debug('filterInternalNotations - input: ' . $content);
        
        // Remove traços de instrumentação textual como
        // "<chamada de função> ...(...)" e "[resultado_da_funcao ...]: ..."
        $content = preg_replace('/<chamada de função>\s*[^\n]+/u', '', $content);
        $content = preg_replace('/\[resultado_da_funcao\s+[^\]]+\]:\s*[^\n]*/u', '', $content);
        // Limpa espaços/linhas extras
        $content = preg_replace("/\n{2,}/", "\n\n", trim($content));
        
        $this->logger->debug('filterInternalNotations - output: ' . $content);
        $this->logger->debug('===== FIM FILTER INTERNAL NOTATIONS =====');
        return $content;
    }

    private function extractUsageFromResponse(array $result) {
        $usage = ['prompt_tokens' => 0, 'completion_tokens' => 0, 'total_tokens' => 0];
        if (isset($result['usage']) && is_array($result['usage'])) {
            $input = $result['usage']['input_tokens'] ?? 0;
            $output = $result['usage']['output_tokens'] ?? 0;
            $usage['prompt_tokens'] = $input;
            $usage['completion_tokens'] = $output;
            $usage['total_tokens'] = $input + $output;
        }
        return $usage;
    }

    /**
     * Extrai uma chamada de função (Responses API) e mapeia para o formato
     * compatível com Chat Completions: ['name' => string, 'arguments' => json-string]
     */
    private function extractFunctionCallFromResponse(array $result) {
        $this->logger->debug('===== INÍCIO EXTRACT FUNCTION CALL =====');
        $this->logger->debug('extractFunctionCallFromResponse - input: ' . json_encode($result, JSON_PRETTY_PRINT));
        
        if (empty($result['output']) || !is_array($result['output'])) {
            $this->logger->debug('No output found or output is not array');
            $this->logger->debug('===== FIM EXTRACT FUNCTION CALL - SEM OUTPUT =====');
            return null;
        }

        $this->logger->debug('Processing ' . count($result['output']) . ' output items');
        foreach ($result['output'] as $index => $item) {
            $this->logger->debug('Processing output item ' . $index . ': ' . json_encode($item));
            
            if (is_array($item) && isset($item['type']) && $item['type'] === 'function_call') {
                $this->logger->debug('Found function_call item');
                $name = $item['name'] ?? null;
                $argsRaw = $item['arguments'] ?? '';
                $this->logger->debug('Function name: ' . $name);
                $this->logger->debug('Raw arguments: ' . json_encode($argsRaw));
                
                // Garante que arguments seja string JSON
                if (is_array($argsRaw)) {
                    $argsStr = json_encode($argsRaw, JSON_UNESCAPED_UNICODE);
                } elseif (is_string($argsRaw)) {
                    // Se for string, tenta validar; se não for JSON válido, envolve como objeto
                    $decoded = json_decode($argsRaw, true);
                    if (json_last_error() === JSON_ERROR_NONE) {
                        $argsStr = $argsRaw;
                    } else {
                        $argsStr = json_encode(['_raw' => $argsRaw], JSON_UNESCAPED_UNICODE);
                    }
                } else {
                    $argsStr = json_encode(new \stdClass());
                }
                
                $this->logger->debug('Processed arguments: ' . $argsStr);

                if ($name) {
                    // Guarda call_id para enviar tool_result na próxima rodada
                    if (isset($item['call_id'])) {
                        $this->lastToolCallId = $item['call_id'];
                        $this->lastToolCallName = $name;
                        $this->logger->debug('Stored call_id: ' . $item['call_id']);
                    }
                    $fc = [
                        'name' => $name,
                        'arguments' => $argsStr
                    ];
                    if (isset($item['call_id'])) {
                        $fc['call_id'] = $item['call_id'];
                    }
                    $this->logger->debug('Returning function call: ' . json_encode($fc, JSON_PRETTY_PRINT));
                    $this->logger->debug('===== FIM EXTRACT FUNCTION CALL - SUCESSO =====');
                    return $fc;
                }
            }
        }

        $this->logger->debug('No function_call found in output');
        $this->logger->debug('===== FIM EXTRACT FUNCTION CALL - NÃO ENCONTRADO =====');
        return null;
    }

    private function generateIntelligentFallback(array $result) {
        $this->logger->debug('===== INÍCIO GENERATE INTELLIGENT FALLBACK =====');
        $this->logger->debug('generateIntelligentFallback - input: ' . json_encode($result, JSON_PRETTY_PRINT));
        
        // 1. Tente usar dados de funções primeiro
        if (!empty($result['functions']) && is_array($result['functions'])) {
            foreach ($result['functions'] as $function) {
                $response = $this->handleFunctionCallSummary($function['name'], $function['result']);
                if ($response) {
                    return $response;
                }
            }
        }
        
        // 2. Analise o contexto da conversa
        $lastUserMessage = $this->getLastUserMessage();
        if (stripos($lastUserMessage, 'confirmar') !== false) {
            return "Sua consulta foi confirmada com sucesso!";
        }
        
        // 3. Fallback genérico melhorado
        return "Entendi sua solicitação. Estou processando as informações...";
    }

    /**
     * Limpa respostas malformadas da IA
     */
    private function cleanMalformedResponse($content) {
        $this->logger->debug('===== INÍCIO CLEAN MALFORMED RESPONSE =====');
        $this->logger->debug('cleanMalformedResponse - input: ' . $content);
        
        if (empty($content)) {
            $this->logger->debug('cleanMalformedResponse - content is empty');
            $this->logger->debug('===== FIM CLEAN MALFORMED RESPONSE - VAZIO =====');
            return $content;
        }
        
        $content = trim($content);
        
        // Detectar respostas muito curtas que podem estar incompletas
        if (strlen($content) < 20) {
            $this->logger->debug('Response too short: ' . $content);
            $this->logger->debug('===== FIM CLEAN MALFORMED RESPONSE - CURTA =====');
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        // Detectar respostas incompletas (terminam abruptamente)
        $words = explode(' ', trim($content));
        if (count($words) > 0) {
            $lastWord = end($words);
            
            // Se a resposta termina com palavras incompletas ou sem pontuação
            if (!preg_match('/[.!?;:]$/', $lastWord) && strlen($content) > 50) {
                // Verificar se termina com palavras comuns que indicam resposta incompleta
                $incompleteEndings = ['o', 'a', 'e', 'de', 'da', 'do', 'em', 'com', 'para', 'que', 'como', 'quando', 'onde', 'quem', 'qual', 'quais', 'sug', 'pos', 'pre', 'con', 'med', 'exa', 'cons', 'proc', 'trat', 'sint', 'grav', 'test', 'resu', 'conf', 'inic', 'cont', 'agend', 'marc', 'verif', 'busc', 'encontr', 'dispon', 'horar', 'data', 'hora'];
                if (in_array(strtolower($lastWord), $incompleteEndings)) {
                    $this->logger->debug('Detected incomplete response ending with: ' . $lastWord);
                    return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
                }
            }
        }
        
        // Detectar respostas que terminam com palavras cortadas (3 caracteres ou menos)
        if (strlen($lastWord) <= 3 && !preg_match('/[.!?;:]$/', $lastWord)) {
            $this->logger->debug('Detected response ending with short word: ' . $lastWord);
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        // Se a resposta começa com JSON mas não termina corretamente
        if (preg_match('/^["\']?[a-zA-Z_][a-zA-Z0-9_]*["\']?\s*:\s*["\']?[^"\']*$/', $content)) {
            $this->logger->debug('Detected malformed JSON response: ' . $content);
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        // Se a resposta contém apenas JSON parcial
        if (preg_match('/^[{"\']/', $content) && !preg_match('/[}"\']$/', $content)) {
            $this->logger->debug('Detected incomplete JSON response: ' . $content);
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        // Se a resposta contém caracteres estranhos no início
        if (preg_match('/^["\']?[a-zA-Z_][a-zA-Z0-9_]*["\']?\s*:/', $content)) {
            $this->logger->debug('Detected malformed response starting with JSON-like structure: ' . $content);
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        // Detectar respostas que terminam com reticências ou pontos suspensivos
        if (preg_match('/\.{3,}$/', $content)) {
            $this->logger->debug('Detected response ending with ellipsis: ' . $content);
            $this->logger->debug('===== FIM CLEAN MALFORMED RESPONSE - ELLIPSIS =====');
            return 'Desculpe, tive um problema técnico. Vou tentar novamente.';
        }
        
        $this->logger->debug('cleanMalformedResponse - final output: ' . $content);
        $this->logger->debug('===== FIM CLEAN MALFORMED RESPONSE - OK =====');
        return $content;
    }
    

    
    /**
     * Gera fallback contextual baseado no resultado
     */
    private function generateContextualFallback(array $result) {
        $this->logger->debug('===== INÍCIO GENERATE CONTEXTUAL FALLBACK =====');
        
        // 1. Tente usar dados de funções primeiro
        if (!empty($result['functions']) && is_array($result['functions'])) {
            $this->logger->debug('generateContextualFallback - functions count: ' . count($result['functions']));
            foreach ($result['functions'] as $function) {
                $this->logger->debug('generateContextualFallback - processing function: ' . ($function['name'] ?? 'unknown'));
                $response = $this->handleFunctionCallSummary($function['name'], $function['result']);
                if ($response) {
                    $this->logger->debug('generateContextualFallback - found response: ' . $response);
                    return $response;
                }
            }
        }
        
        // 2. Analise o contexto da conversa
        $lastUserMessage = $this->getLastUserMessage();
        if (stripos($lastUserMessage, 'confirmar') !== false) {
            return "Sua consulta foi confirmada com sucesso!";
        }
        
        // 3. Fallback genérico melhorado
        $this->logger->debug('generateContextualFallback - returning generic fallback');
        return "Entendi sua solicitação. Estou processando as informações...";
    }
    
    /**
     * Obtém a última mensagem do usuário (método auxiliar)
     */
    private function getLastUserMessage() {
        $this->logger->debug('===== INÍCIO GET LAST USER MESSAGE =====');
        $this->logger->debug('getLastUserMessage - lastMessages count: ' . count($this->lastMessages));
        
        if (empty($this->lastMessages)) {
            $this->logger->debug('getLastUserMessage - no messages found');
            $this->logger->debug('===== FIM GET LAST USER MESSAGE - VAZIO =====');
            return '';
        }
        
        // Procura pela última mensagem do usuário
        for ($i = count($this->lastMessages) - 1; $i >= 0; $i--) {
            $message = $this->lastMessages[$i];
            if (isset($message['role']) && $message['role'] === 'user' && isset($message['content'])) {
                $this->logger->debug('getLastUserMessage - found user message: ' . $message['content']);
                $this->logger->debug('===== FIM GET LAST USER MESSAGE - ENCONTRADA =====');
                return $message['content'];
            }
        }
        
        $this->logger->debug('getLastUserMessage - no user message found');
        $this->logger->debug('===== FIM GET LAST USER MESSAGE - NÃO ENCONTRADA =====');
        return '';
    }
    
    /**
     * Formata data para exibição
     */
    private function formatarData($data) {
        if (empty($data)) return '';
        $timestamp = strtotime($data);
        return $timestamp ? date('d/m/Y', $timestamp) : $data;
    }
    
    /**
     * Formata hora para exibição
     */
    private function formatarHora($hora) {
        if (empty($hora)) return '';
        $timestamp = strtotime($hora);
        return $timestamp ? date('H:i', $timestamp) : $hora;
    }

}