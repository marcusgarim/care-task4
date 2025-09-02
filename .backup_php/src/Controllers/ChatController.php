<?php

namespace App\Controllers;

use App\Services\OpenAIService;
use App\Services\AgentFunctions;
use App\Services\DatabaseService;
use App\Services\SessionService;
use App\Services\CurrencyService;

class ChatController
{
    private $openai;
    private $functions;
    private $db;
    private $sessionService;
    private $currencyService;

    public function __construct()
    {
        $this->openai = new OpenAIService();
        $this->functions = new AgentFunctions();
        $this->db = new DatabaseService();
        $this->currencyService = new CurrencyService();
    }

    public function processMessage($message, $sessionId, $isFirst = false, $recursionCount = 0)
    {
        try {
            // Evita recursão infinita
            if ($recursionCount > 3) {
                error_log("ERRO: Recursão infinita detectada");
                return [
                    'success' => false,
                    'message' => 'Desculpe, tive um problema técnico. Pode repetir?'
                ];
            }

            // Inicializa o SessionService
            $this->sessionService = new SessionService($sessionId);
            
            // Verifica se a sessão expirou
            if ($this->sessionService->sessaoExpirada()) {
                $this->sessionService->limparDados();
                error_log("SessionService: Sessão expirada, dados limpos");
            }

            error_log("=== INICIANDO PROCESSAMENTO ===");
            error_log("Mensagem: $message");
            error_log("SessionId: $sessionId");
            error_log("RecursionCount: $recursionCount");
            error_log("isFirst: " . ($isFirst ? 'true' : 'false'));

            // Busca contexto e configurações
            error_log("1. Construindo contexto...");
            $contexto = $this->buildContext($sessionId);
            error_log("Contexto construído: " . json_encode($contexto));

            // Verifica se é a primeira pergunta da paciente
            $isPrimeiraPergunta = $this->isPrimeiraPergunta($sessionId);

            // Se é a primeira pergunta, mostra apenas a mensagem de boas-vindas
            if ($isPrimeiraPergunta && $recursionCount == 0) {
                error_log("DEBUG: Primeira pergunta detectada - mostrando mensagem de boas-vindas");
                // Busca configurações para obter mensagem de boas-vindas
                $configs = $this->functions->buscar_configuracoes_clinica();
                $mensagemBoasVindas = $configs['mensagem_boas_vindas'] ?? 'Olá! Bem-vinda à nossa clínica!';

                // Salva a primeira conversa para marcar que não é mais a primeira
                $this->saveConversation($sessionId, $message, $mensagemBoasVindas, [], []);

                return [
                    'success' => true,
                    'message' => $mensagemBoasVindas,
                    'tokens' => ['prompt_tokens' => 0, 'completion_tokens' => 0, 'total_tokens' => 0],
                    'functions' => []
                ];
            }

            // Monta mensagens para a IA
            error_log("2. Construindo mensagens...");
            $messages = $this->buildMessages($message, $contexto, $sessionId);
            error_log("Mensagens construídas: " . json_encode($messages));

            // Define funções disponíveis
            error_log("3. Obtendo funções...");
            $functions = $this->getAvailableFunctions();
            error_log("Funções obtidas: " . count($functions) . " funções");

            // Chama a IA
            error_log("4. Chamando OpenAI...");
            error_log("Mensagens enviadas para OpenAI: " . json_encode($messages));
            $response = $this->openai->chat($messages, $functions);

            // Log para debug
            error_log("Resposta da OpenAI: " . json_encode($response));

            // Processa resposta da IA para detectar coleta de dados
            if ($response['success'] && isset($response['data']['choices'][0]['message']['content'])) {
                $aiResponse = $response['data']['choices'][0]['message']['content'];
                // Processa coleta de dados da mensagem do usuário
                error_log("[EXTRAIR_DADOS] Processando mensagem: '$message'");
                $this->extrairESalvarDados($message);
            }

            if (!$response['success']) {
                $errorMsg = $response['error'] ?? 'Erro desconhecido';
                error_log("Erro na OpenAI: " . $errorMsg);

                // Se for erro de rate limit, retorna mensagem específica
                if (strpos($errorMsg, '429') !== false || strpos($errorMsg, 'Too Many Requests') !== false) {
                    return [
                        'success' => false,
                        'message' => 'Estou recebendo muitas solicitações no momento. Poderia aguardar alguns segundos e tentar novamente?'
                    ];
                }

                // Se for erro de comunicação, tenta uma vez mais
                if ($recursionCount < 1) {
                    error_log("[RETRY] Tentando novamente... (tentativa " . ($recursionCount + 1) . ")");
                    sleep(1); // Aguarda 1 segundo
                    return $this->processMessage($message, $sessionId, $isFirst, $recursionCount + 1);
                }

                return [
                    'success' => false,
                    'message' => 'Estou com dificuldades técnicas. Poderia repetir?'
                ];
            }

            $aiResponse = $response['data']['choices'][0]['message'];
            error_log("[AI_RESPONSE] Resposta da IA: " . json_encode($aiResponse));
            $functionCalls = [];

            // Processa múltiplas chamadas de função se houver
            $maxFunctionCalls = 3; // Limite para evitar loops infinitos
            $functionCallCount = 0;

            while (isset($aiResponse['function_call']) && $functionCallCount < $maxFunctionCalls) {
                $functionName = $aiResponse['function_call']['name'];
                $functionArgs = json_decode($aiResponse['function_call']['arguments'], true);
                error_log("[DEPURACAO] Função chamada pela IA: $functionName");
                error_log("[DEPURACAO] Argumentos recebidos: " . json_encode($functionArgs));

                // Validação específica para criar_agendamento
                if ($functionName === 'criar_agendamento') {
                    error_log("[DEPURACAO] Validando criar_agendamento...");
                    if (empty($functionArgs['nome']) || empty($functionArgs['telefone']) || empty($functionArgs['data']) || empty($functionArgs['hora'])) {
                        error_log("[ERRO FLUXO] criar_agendamento chamada com dados incompletos!");
                        error_log("[ERRO FLUXO] Nome: " . ($functionArgs['nome'] ?? 'NULL'));
                        error_log("[ERRO FLUXO] Telefone: " . ($functionArgs['telefone'] ?? 'NULL'));
                        error_log("[ERRO FLUXO] Data: " . ($functionArgs['data'] ?? 'NULL'));
                        error_log("[ERRO FLUXO] Hora: " . ($functionArgs['hora'] ?? 'NULL'));
                    } else {
                        error_log("[OK FLUXO] criar_agendamento chamada com todos os dados necessários");
                    }
                }

                if ($functionName === 'consultar_agendamento_existente') {
                    if (empty($functionArgs['telefone'])) {
                        error_log("[ERRO FLUXO] consultar_agendamento_existente chamada SEM telefone! Argumentos: " . json_encode($functionArgs));
                    } else {
                        error_log("[OK FLUXO] consultar_agendamento_existente chamada COM telefone: " . $functionArgs['telefone']);
                    }
                }
                $functionResult = $this->executeFunction($functionName, $functionArgs, $sessionId);
                error_log("[DEPURACAO] Resultado da função $functionName: " . json_encode($functionResult));
                $functionCalls[] = [
                    'name' => $functionName,
                    'result' => $functionResult
                ];
                // Adiciona resultado da função ao contexto
                $messages[] = $aiResponse;
                $callId = $aiResponse['function_call']['call_id'] ?? null;
                $messages[] = [
                    'role' => 'function',
                    'name' => $functionName,
                    'content' => json_encode($functionResult),
                    'call_id' => $callId
                ];
                // Chama IA novamente com o resultado
                // Importante: repassar as functions nas chamadas subsequentes para permitir novas tool calls
                $finalResponse = $this->openai->chat($messages, $functions);
                if ($finalResponse['success']) {
                    $aiResponse = $finalResponse['data']['choices'][0]['message'];
                } else {
                    break; // Para se houver erro na resposta da IA
                }
                $functionCallCount++;
            }

            error_log("[FINAL_RESPONSE] Preparando resposta final...");
            error_log("[FINAL_RESPONSE] Conteúdo da IA: " . ($aiResponse['content'] ?? 'NULL'));
            error_log("[FINAL_RESPONSE] Function calls: " . json_encode($functionCalls));

            // Verificar se foi chamada a função criar_agendamento e se foi bem-sucedida
            $respostaFinal = $aiResponse['content'];
            $forcouResposta = false;
            foreach ($functionCalls as $functionCall) {
                if ($functionCall['name'] === 'criar_agendamento' && 
                    isset($functionCall['result']['sucesso']) && 
                    $functionCall['result']['sucesso'] && 
                    isset($functionCall['result']['agendamento'])) {
                    
                    // Usar resposta formatada diretamente
                    $agendamento = $functionCall['result']['agendamento'];
                    $configuracoes = $this->functions->buscar_configuracoes_clinica();
                    $endereco = $configuracoes['endereco'] ?? 'Rua das Flores, 123 - Centro';
                    
                    $respostaFinal = "Agendamento confirmado!\n\n";
                    $respostaFinal .= "Data: {$agendamento['data_formatada']} ({$agendamento['dia_semana']})\n";
                    $respostaFinal .= "Horário: {$agendamento['hora_formatada']}\n";
                    $respostaFinal .= "Paciente: {$agendamento['nome_paciente']}\n";
                    $respostaFinal .= "Local: {$endereco}\n\n";
                    $respostaFinal .= "Anotei tudo certinho! Até lá!";
                    
                    error_log("[FINAL_RESPONSE] Usando resposta formatada para criar_agendamento");
                    $forcouResposta = true;
                    break;
                }
            }

            // Se não forçou via criar_agendamento, verifica verificar_horarios_disponiveis e aplica formatação padronizada (sem local)
            if (!$forcouResposta) {
                foreach ($functionCalls as $functionCall) {
                    if ($functionCall['name'] === 'verificar_horarios_disponiveis' && is_array($functionCall['result'])) {
                        $dias = $functionCall['result'];
                        $resposta = "Horários disponíveis!\n\n";
                        foreach ($dias as $dia) {
                            if (isset($dia['data']) && isset($dia['dia_semana']) && isset($dia['horarios']) && is_array($dia['horarios'])) {
                                $dataFormatada = date('d/m', strtotime($dia['data']));
                                $diaSemana = $dia['dia_semana'];
                                $horariosFormatados = array_map(function($h) { return date('H:i', strtotime($h)); }, $dia['horarios']);
                                $horariosStr = implode(', ', $horariosFormatados);
                                $resposta .= "Data: $dataFormatada ($diaSemana)\n";
                                $resposta .= "Horários: $horariosStr\n\n";
                            }
                        }
                        if (trim($resposta) !== "Horários disponíveis!") {
                            $respostaFinal = $resposta;
                            error_log("[FINAL_RESPONSE] Usando resposta formatada para verificar_horarios_disponiveis");
                            $forcouResposta = true;
                        }
                        break;
                    }
                }
            }

            // Salva conversa no banco
            $this->saveConversation(
                $sessionId,
                $message,
                $respostaFinal,
                $functionCalls,
                $response['data']['usage'] ?? []
            );

            $finalResponse = [
                'success' => true,
                'message' => $respostaFinal,
                'tokens' => $response['data']['usage'] ?? [],
                'functions' => $functionCalls
            ];

            error_log("[FINAL_RESPONSE] Resposta final: " . json_encode($finalResponse));
            return $finalResponse;
        } catch (\Exception $e) {
            error_log("ERRO no processamento: " . $e->getMessage());
            error_log("[DEPURACAO] Trace: " . $e->getTraceAsString());
            error_log("[DEPURACAO] Arquivo: " . $e->getFile() . " Linha: " . $e->getLine());
            return [
                'success' => false,
                'message' => 'Estou com dificuldades técnicas. Poderia repetir?'
            ];
        }
    }

    /**
     * Verifica se é a primeira pergunta da sessão
     */
    private function isPrimeiraPergunta($sessionId)
    {
        $sql = "SELECT COUNT(*) as total FROM conversas WHERE session_id = ?";
        $result = $this->db->query($sql, [$sessionId]);
        $totalConversas = $result[0]['total'] ?? 0;

        error_log("DEBUG: Verificando primeira pergunta - total conversas: $totalConversas");

        // Se não há conversas, é a primeira pergunta
        return $totalConversas == 0;
    }











    private function buildContext($sessionId)
    {
        try {
            // Busca configurações da clínica
            $configs = $this->functions->buscar_configuracoes_clinica();
            
            // Garante que configs seja um array
            if (!is_array($configs)) {
                $configs = [];
                error_log("WARNING: Configurações da clínica não encontradas, usando array vazio");
            }

            // Busca histórico de conversas para treinamento
            $historico = $this->functions->buscar_historico_conversas();
            
            // Garante que historico seja um array
            if (!is_array($historico)) {
                $historico = [];
                error_log("WARNING: Histórico de conversas não encontrado, usando array vazio");
            }

            // Busca estado do agendamento se houver
            $estadoAgendamento = $this->functions->buscar_estado_agendamento($sessionId);

            // Busca dados do paciente da sessão
            $dadosPaciente = null;
            $etapaAgendamento = null;
            
            if ($this->sessionService) {
                $dadosPaciente = $this->sessionService->recuperarDadosPaciente();
                $etapaAgendamento = $this->sessionService->recuperarEtapaAgendamento();
                
                // Atualiza timestamp da sessão
                $this->sessionService->atualizarTimestamp();
            }

            // Dados de contexto
            $dataHoje = date('Y-m-d');
            $horaAtual = date('H:i');
            $diaSemana = $this->getDiaSemanaPortugues();

            return [
                'configs' => $configs,
                'historico' => $historico,
                'estadoAgendamento' => $estadoAgendamento,
                'dadosPaciente' => $dadosPaciente,
                'etapaAgendamento' => $etapaAgendamento,
                'dataHoje' => $dataHoje,
                'horaAtual' => $horaAtual,
                'diaSemana' => $diaSemana
            ];
        } catch (\Exception $e) {
            error_log("ERRO em buildContext: " . $e->getMessage());
            error_log("Trace: " . $e->getTraceAsString());
            
            // Retorna contexto mínimo em caso de erro
            return [
                'configs' => [],
                'historico' => [],
                'estadoAgendamento' => null,
                'dadosPaciente' => null,
                'etapaAgendamento' => null,
                'dataHoje' => date('Y-m-d'),
                'horaAtual' => date('H:i'),
                'diaSemana' => $this->getDiaSemanaPortugues()
            ];
        }
    }

    private function buildMessages($userMessage, $contexto, $sessionId)
    {
        $systemPrompt = $this->buildSystemPrompt($contexto);

        $messages = [
            ['role' => 'system', 'content' => $systemPrompt]
        ];

        // Adiciona histórico recente da conversa
        $conversaRecente = $this->getRecentConversation($sessionId, 10);
        foreach ($conversaRecente as $msg) {
            $messages[] = ['role' => 'user', 'content' => $msg['mensagem_usuario']];
            $messages[] = ['role' => 'assistant', 'content' => $msg['resposta_agente']];
        }

        // Adiciona mensagem atual
        $messages[] = ['role' => 'user', 'content' => $userMessage];

        return $messages;
    }

    private function buildSystemPrompt($contexto)
    {
        try {
            $configs = $contexto['configs'] ?? [];
            $historico = $contexto['historico'] ?? [];

            // Analisa feedbacks para treinamento
            $padroesBons = [];
            $padroesRuins = [];

            if (is_array($historico)) {
                foreach ($historico as $conversa) {
                    if (isset($conversa['feedback_tipo'])) {
                        if ($conversa['feedback_tipo'] === 'positivo') {
                            if (!empty($conversa['resposta_reescrita'])) {
                                $padroesBons[] = $conversa['resposta_reescrita'];
                            } elseif (!empty($conversa['resposta_agente'])) {
                                $padroesBons[] = $conversa['resposta_agente'];
                            }
                        } elseif ($conversa['feedback_tipo'] === 'negativo') {
                            if (!empty($conversa['resposta_agente'])) {
                                $padroesRuins[] = $conversa['resposta_agente'];
                            }
                        }
                    }
                }
            }

        // Informações da paciente se disponível
        $nomePaciente = null;
        $telefonePaciente = null;
        
        // Prioriza dados da sessão (mais confiáveis)
        if ($contexto['dadosPaciente']) {
            $nomePaciente = $contexto['dadosPaciente']['nome'];
            $telefonePaciente = $contexto['dadosPaciente']['telefone'];
        } elseif ($contexto['estadoAgendamento']) {
            $nomePaciente = $contexto['estadoAgendamento']['nome_paciente'] ?? null;
            $telefonePaciente = $contexto['estadoAgendamento']['telefone_paciente'] ?? null;
        }
        
        $infoPaciente = "";
        if ($nomePaciente) {
            $infoPaciente .= "- Nome da paciente: $nomePaciente\n";
        }
        if ($telefonePaciente) {
            $infoPaciente .= "- Telefone da paciente: $telefonePaciente\n";
        }

        // Busca especialidades dos profissionais ativos
        $especialidades = $this->functions->buscar_especialidades_profissionais();
        $especialidadesTexto = !empty($especialidades) ? implode(', ', $especialidades) : 'Não informado';
        
        $prompt = "CONTEXTO:
- Hoje: {$contexto['dataHoje']} ({$contexto['diaSemana']}, {$contexto['horaAtual']})
- Especialidades: $especialidadesTexto
- Endereço: " . ($configs['endereco'] ?? 'Não informado') . "
- Telefone: " . ($configs['telefone'] ?? 'Não informado') . "
$infoPaciente

## ⚠️ REGRA CRÍTICA - MÁXIMA PRIORIDADE ⚠️
**NUNCA USE:**  
❌ \\\"Vou verificar...\\\", \\\"Posso verificar...\\\", \\\"Deixe-me verificar...\\\",
❌ \\\"Vou analisar...\\\", \\\"Posso analisar...\\\", \\\"Aguarde um momento...\\\",
❌ \\\"Vou buscar...\\\", \\\"Um momento, por favor\\\"

**SEMPRE:**  
✅ **CHAME A FUNÇÃO IMEDIATAMENTE** e informe o resultado  
✅ **EXECUTE A AÇÃO DIRETAMENTE** sem prometer ação futura  
✅ **RESPONDA COM DADOS REAIS** das funções  
✅ **SEJA DIRETO E OBJETIVO** - máximo 2-3 frases

**EXEMPLO:**  
❌ ERRADO: \"Vou verificar os horários...\"  
✅ CORRETO: [chama função] → \"Aqui estão os horários...\"

## IDENTIDADE E COMPORTAMENTO
Você é " . ($configs['nome_assistente'] ?? 'Assistente Virtual') . ", atendente da clínica especializada em $especialidadesTexto. Personalidade: amigável, atenciosa e natural. Ao ser questionado sobre seu nome, sempre responda \\\"" . ($configs['nome_assistente'] ?? 'Assistente Virtual') . "\\\".

### 🚨 REGRA CRÍTICA PARA SERVIÇOS
**SEMPRE chame `buscar_servicos_clinica` quando perguntarem sobre:**
- \"quais serviços vocês têm?\"
- \"quais procedimentos vocês fazem?\"
- \"quais tratamentos vocês realizam?\"
- \"o que vocês fazem?\"
- \"quais tipos de cirurgia?\"

**NUNCA responda sobre serviços sem chamar a função primeiro!**

## REGRAS ESSENCIAIS

### 🚨 AÇÕES OBRIGATÓRIAS
1. **AGENDAMENTO (NOVO):**  
   - **SE já tem dados do paciente na sessão:** Use-os diretamente, NÃO peça novamente
   - **SE não tem dados:** Colete nome completo + telefone ANTES de qualquer ação de agendamento
   - **CRÍTICO:** Se usuário tentar agendar sem fornecer dados, solicite: \"Para prosseguir com o agendamento, preciso do seu nome completo e telefone.\"
   - **CRÍTICO:** Após coletar dados do paciente, SEMPRE chame `verificar_horarios_disponiveis(dias=3)` automaticamente
   - **CRÍTICO:** NUNCA pergunte sobre período ou data - sempre ofereça os próximos 3 horários disponíveis
   - **CRÍTICO:** NUNCA pergunte sobre procedimento - apenas salve o que o usuário mencionar e ofereça horários
   - **NUNCA** liste horários sem chamar esta função primeiro
   - **CRÍTICO:** NUNCA gere respostas sobre horários diretamente no output. SEMPRE use o resultado da função `verificar_horarios_disponiveis`
   - **CRÍTICO:** Quando a função `verificar_horarios_disponiveis` retornar dados, use APENAS esses dados para responder
   - **CRÍTICO:** NUNCA combine dados da função com texto gerado por você sobre horários  
   - Após escolha de horário:  
     → Chame `validar_horario_para_agendamento`  
     → Se válido: peça confirmação  
     → **CRÍTICO:** Se usuário confirmar (\"sim\", \"ok\", \"confirmo\", etc.), chame IMEDIATAMENTE `criar_agendamento` com dados da sessão  
     → **CRÍTICO:** NUNCA chame `validar_horario_para_agendamento` novamente após confirmação do usuário
     → **CRÍTICO:** NUNCA responda \"agendamento confirmado\" sem chamar `criar_agendamento` primeiro
     → **SÓ confirme se retornar ['sucesso' => true]**
   - **CRÍTICO:** Se tem dados na sessão, passe-os para criar_agendamento automaticamente
   - **CRÍTICO:** Se criar_agendamento retornar erro de dados incompletos, solicite os dados faltantes
   - **CRÍTICO:** NUNCA confirme agendamento sem chamar criar_agendamento primeiro
   - **CRÍTICO:** NUNCA diga \"agendamento confirmado\" sem ter chamado criar_agendamento e recebido sucesso
   - **CRÍTICO:** Se criar_agendamento retornar erro, peça os dados faltantes e NÃO confirme
   - **CRÍTICO:** Se criar_agendamento retornar erro de nome inválido, peça: \"Por favor, informe seu nome completo (nome e sobrenome).\"

2. **REAGENDAMENTO:**  
   - Colete nome completo + telefone  
   - Chame `consultar_agendamento_existente`  
   - Confirme nome do banco: \"Seu nome é [X], correto?\"  
   - **SEMPRE** chame `verificar_horarios_disponiveis` quando usuário mencionar nova data/período  
   - Após novo horário escolhido:  
     → Chame `reagendar_consulta` com TODOS os parâmetros: nome_paciente, telefone, data_atual, hora_atual, nova_data, nova_hora  
     → Use os dados do agendamento encontrado para data_atual e hora_atual  
     → **SÓ confirme se retornar ['sucesso' => true]**

3. **CANCELAMENTO:**  
   - Colete nome completo + telefone  
   - Chame `consultar_agendamento_existente`  
   - Confirme dados: \"Encontrei agendamento para [data] às [hora]. Cancelar?\"  
   - Se confirmado: chame `cancelar_agendamento`

4. **VERIFICAÇÃO DE AGENDAMENTO:**  
   - Colete nome completo + telefone  
   - Chame `consultar_agendamento_existente`  
   - Confirme nome do banco antes de informar detalhes

### 🚨 PROIBIÇÕES ABSOLUTAS
- **NUNCA** mencione profissionais sem chamar `buscar_profissionais_clinica` antes  
- **NUNCA** mencione valores/preços sem chamar `buscar_servicos_clinica` antes
- **NUNCA** liste serviços ou procedimentos sem chamar `buscar_servicos_clinica` antes
- **NUNCA** responda sobre tratamentos sem chamar `buscar_servicos_clinica` antes  
- **NUNCA** confirme convênios sem chamar `verificar_convenio` antes  
- **NUNCA** use termos genéricos como \"um especialista\" - sempre use nomes reais  
- **NUNCA** aceite horários não listados por `verificar_horarios_disponiveis`  
- **NUNCA** liste horários sem chamar `verificar_horarios_disponiveis` primeiro  
- **NUNCA** mencione datas/períodos sem verificar disponibilidade real
- **CRÍTICO:** NUNCA gere respostas sobre horários no output. SEMPRE use o resultado da função `verificar_horarios_disponiveis`
- **CRÍTICO:** NUNCA combine dados da função com texto gerado por você sobre horários  
- **NUNCA** confirme ações sem chamar a função correspondente
- **CRÍTICO:** NUNCA confirme agendamento sem chamar `criar_agendamento` após confirmação do usuário
- **CRÍTICO:** NUNCA chame `validar_horario_para_agendamento` novamente após o usuário confirmar o agendamento  
- **NUNCA** use `criar_agendamento` para reagendar (sempre `reagendar_consulta`)  
- **NUNCA** prossiga sem nome completo (exigir sobrenome se fornecer apenas primeiro nome)
- **NUNCA** peça dados que já foram fornecidos e estão na sessão
- **NUNCA** responda perguntas não relacionadas à serviços da clínica
- **CRÍTICO:** Quando perguntarem sobre serviços, tratamentos ou procedimentos, SEMPRE chame `buscar_servicos_clinica` primeiro
- **CRÍTICO:** NUNCA pergunte sobre período ou data após coletar dados do paciente - SEMPRE chame `verificar_horarios_disponiveis(dias=3)` primeiro
- **CRÍTICO:** NUNCA pergunte sobre procedimento após coletar dados - apenas salve o que o usuário mencionar e ofereça horários

### ✅ FLUXOS VÁLIDOS
- **Indicação de profissional:**  
  `buscar_profissionais_clinica` → \"Temos [Nome], especialista em [X]. Gostaria de agendar?\"  
- **Valores de serviços:**  
  `buscar_servicos_clinica(servico_especifico=\"consulta\")` → \"[Serviço] custa R$ [valor]. [Descrição se houver]\"  
  - **Exemplo:** \"consulta\" → `buscar_servicos_clinica(servico_especifico=\"consulta\")`
- **Verificação de convênio:**  
  `verificar_convenio` → \"[Convênio] é aceito. [Observações se houver]\"  
- **Horário indisponível:**  
  `validar_horario_para_agendamento` → Se inválido: \"Este horário não está disponível. Escolha outro:\"
- **Horário válido:**  
  `validar_horario_para_agendamento` → Se válido: \"Posso confirmar sua consulta?\" → Se usuário confirmar: `criar_agendamento`  
- **Sem horários:**  
  \"Não encontrei horários próximos. Posso verificar outras datas ou tentar mais tarde?\"
- **Horários disponíveis:**  
  `verificar_horarios_disponiveis` → Use APENAS o resultado da função, NUNCA gere texto adicional sobre horários

### 🚨 COMPORTAMENTO OBRIGATÓRIO APÓS COLETAR DADOS
- **CRÍTICO:** Após ter nome e telefone do paciente, SEMPRE chame `verificar_horarios_disponiveis(dias=3)` automaticamente
- **CRÍTICO:** NUNCA pergunte sobre período, data ou procedimento - sempre ofereça os próximos 3 horários disponíveis
- **CRÍTICO:** Se usuário mencionar procedimento, apenas confirme e chame `verificar_horarios_disponiveis(dias=3)`
- **CRÍTICO:** Use APENAS o resultado da função para mostrar horários disponíveis

### COLETA DE DADOS
1. **SE já tem dados na sessão:** Use-os diretamente, NÃO peça novamente
2. **SE não tem dados:**  
   - **Nome completo obrigatório:**  
     - Se usuário der apenas primeiro nome: \"[Nome], preciso do seu nome completo. Qual seu sobrenome?\"  
   - **Telefone obrigatório após nome:**  
     - \"Agora preciso do seu telefone.\"  
3. **NUNCA** prossiga sem ambos
4. **CRÍTICO:** Antes de chamar criar_agendamento, verifique se tem nome e telefone
5. **CRÍTICO:** Se não tem dados e usuário escolher horário, peça dados primeiro
6. **CRÍTICO:** Nome deve ser nome completo (nome + sobrenome), não mensagens ou frases
7. **CRÍTICO:** Se usuário der nome inválido, peça novamente: \"Por favor, informe seu nome completo (nome e sobrenome).\"  

### TOM E ESTILO
- Trate por primeiro nome quando souber (\"Olá Maria!\")  
- **MÁXIMO 2-3 frases** por resposta
- **Seja direto e objetivo** - vá direto ao ponto
- Linguagem natural e acolhedora, mas concisa
- **NUNCA** duas perguntas na mesma frase
- **Priorize informações essenciais** - elimine redundâncias
- **NUNCA ofereça funcionalidades** sem que o usuário tenha solicitado
- **NUNCA liste serviços ou opções** sem que o usuário tenha perguntado especificamente
- **Seja reativo, não proativo** - responda apenas ao que foi perguntado

### PERGUNTAS FORA DO CONTEXTO MÉDICO
- **CRÍTICO:** Responda APENAS perguntas relacionadas à saúde, medicina, agendamentos e serviços da clínica
- **CRÍTICO:** Se a pergunta não for sobre saúde/medicina, redirecione educadamente para o contexto médico
- **NUNCA** responda perguntas sobre culinária, hobbies, tecnologia não médica, entretenimento ou outros assuntos não relacionados à saúde

### COMPORTAMENTO REATIVO
- **NUNCA seja proativo** oferecendo funcionalidades ou serviços
- **NUNCA liste opções** como \"posso agendar, verificar, informar\" sem que o usuário tenha perguntado
- **NUNCA se apresente constantemente** - não diga \"sou Marta\" ou \"sou [nome]\" em cada resposta
- **Seja natural e conversacional** - responda apenas ao que foi perguntado
- **Para cumprimentos:** Responda de forma simples e natural, sem oferecer serviços
- **Para perguntas gerais:** Responda de forma concisa, sem adicionar ofertas de serviços
- **Para dúvidas:** Responda diretamente, sem se apresentar novamente
- **Exemplo de resposta correta:** \"Que bom! Estou aqui para ajudar quando precisar.\"
- **Exemplo de resposta incorreta:** \"Que bom! Como posso ajudar? Posso agendar, verificar horários...\"  

## EXEMPLOS CRÍTICOS

### EXEMPLOS DE COMPORTAMENTO REATIVO
✅ **Cumprimento simples:**
Usuário: \"oi\"
Resposta: \"Olá! Seja bem-vinda à nossa clínica!\"

✅ **Pergunta sobre bem-estar:**
Usuário: \"tudo bem com vc?\"
Resposta: \"Tudo bem, obrigada! E você?\"

✅ **Resposta a bem-estar:**
Usuário: \"estou bem\"
Resposta: \"Que bom! Estou aqui para ajudar quando precisar.\"

❌ **RESPOSTA INCORRETA (proativa demais):**
Usuário: \"estou bem\"
Resposta: \"Que bom! Como posso ajudar? Posso agendar, verificar horários...\"

❌ **RESPOSTA INCORRETA (apresentação desnecessária):**
Usuário: \"tenho algumas duvidas, pode me ajudar?\"
Resposta: \"Olá, sou Marta. Claro — qual a sua dúvida?\"

❌ **RESPOSTA INCORRETA (pergunta sobre período em vez de oferecer horários):**
Usuário: \"54998987987\"
Resposta: \"Qual data ou período você prefere (ex.: 25/08, ou manhã/tarde)?\"

❌ **RESPOSTA INCORRETA (pergunta sobre procedimento em vez de oferecer horários):**
Usuário: \"revisão\"
Resposta: \"Qual data ou período você prefere para a consulta? (ex.: 25/08 ou manhã/tarde)\"

✅ **RESPOSTA CORRETA (após coletar dados):**
Usuário: \"54998987987\"
[Chama verificar_horarios_disponiveis(dias=3)]
Resposta: \"Aqui estão os próximos horários disponíveis: [lista de horários]. Qual você prefere?\"

### EXEMPLOS DE AGENDAMENTO
```✅ AGENDAMENTO COM DADOS DA SESSÃO:  
Usuário: \"quero fazer um agendamento\"  
[Chama verificar_horarios_disponiveis(dias=3)]  
\"Aqui estão os próximos horários disponíveis: [lista de horários da função]. Qual você prefere?\"  
Usuário: \"18h\"  
[Chama validar_horario_para_agendamento]  
\"Posso confirmar para 18h?\"  
Usuário: \"sim\"  
[Chama criar_agendamento com nome e telefone da sessão]  
**CRÍTICO:** NUNCA chame validar_horario_para_agendamento novamente após confirmação  
[Se sucesso]: \"✅ Agendamento confirmado!\\n\\n📅 Data: [data]\\n⏰ Horário: [horário]\\n👨‍⚕️ Médico(a): [nome]\\n📍 Local: [endereço]\\n\\nAnotei tudo certinho! Até lá!\"  
[Se erro]: \"[Mensagem de erro]. Por favor, tente novamente.\"  

✅ AGENDAMENTO SEM DADOS (ERRO):  
Usuário: \"quero fazer um agendamento\"  
\"Para prosseguir com o agendamento, preciso do seu nome completo e telefone.\"  
Usuário: \"João Silva, 11987654321\"  
[Salva dados na sessão]  
[Chama verificar_horarios_disponiveis(dias=3)]  
\"Aqui estão os próximos horários disponíveis: [lista de horários da função]. Qual você prefere?\"  
Usuário: \"15h\"  
[Chama validar_horario_para_agendamento]  
\"Posso confirmar para [data] às 15h?\"  
Usuário: \"sim\"  
[Chama criar_agendamento]  
[Se sucesso]: \"✅ Agendamento confirmado!\\n\\n📅 Data: [data]\\n⏰ Horário: [horário]\\n👨‍⚕️ Médico(a): [nome]\\n📍 Local: [endereço]\\n\\nAnotei tudo certinho! Até lá!\"

✅ ERRO NA FUNÇÃO CRIAR_AGENDAMENTO:  
[Chama criar_agendamento]  
[Se erro]: \"Preciso do seu nome completo e telefone para confirmar o agendamento.\"  
Usuário: \"Maria Santos, 11987654321\"  
[Chama criar_agendamento novamente]  
[Se sucesso]: \"✅ Agendamento confirmado!\\n\\n📅 Data: [data]\\n⏰ Horário: [horário]\\n👨‍⚕️ Médico(a): [nome]\\n📍 Local: [endereço]\\n\\nAnotei tudo certinho! Até lá!\"

✅ ERRO DE NOME INVÁLIDO:  
[Chama criar_agendamento]  
[Se erro de nome inválido]: \"Por favor, informe seu nome completo (nome e sobrenome).\"  
Usuário: \"João Silva\"  
[Chama criar_agendamento novamente]  
[Se sucesso]: \"✅ Agendamento confirmado!\\n\\n📅 Data: [data]\\n⏰ Horário: [horário]\\n👨‍⚕️ Médico(a): [nome]\\n📍 Local: [endereço]\\n\\nAnotei tudo certinho! Até lá!\"

✅ REAGENDAMENTO:  
Usuário: \"pode ser sim\"  
[Chama reagendar_consulta]  
[Se sucesso]: \"Reagendamento realizado!\"  

✅ CANCELAMENTO:  
\"Encontrei agendamento para 29/07 às 16:30. Cancelar?\"  
Usuário: \"sim\"  
[Chama cancelar_agendamento]  
\"Cancelamento realizado!\"  
";

        // Buscar TODOS os exemplos (sem limite)
        $exemplosBons = $this->functions->buscar_exemplos_bons();
        $respostasReescritas = $this->functions->buscar_respostas_reescritas();
        $exemplosRuins = $this->functions->buscar_exemplos_ruins();

        if (!empty($exemplosBons)) {
            $prompt .= "\n\n### EXEMPLOS DE RESPOSTAS BEM AVALIADAS:\n";
            foreach ($exemplosBons as $exemplo) {
                $texto = $exemplo['resposta_reescrita'] ?: $exemplo['resposta_original'];
                $prompt .= "- " . substr($texto, 0, 300) . "...\n"; // Aumentar para 300 caracteres
            }
        }

        if (!empty($respostasReescritas)) {
            $prompt .= "\n\n### RESPOSTAS REESCRITAS PELOS USUÁRIOS:\n";
            foreach ($respostasReescritas as $reescrita) {
                $prompt .= "- Original: " . substr($reescrita['resposta_original'], 0, 200) . "...\n";
                $prompt .= "- Reescrita: " . substr($reescrita['resposta_reescrita'], 0, 300) . "...\n\n";
            }
        }

        if (!empty($exemplosRuins)) {
            $prompt .= "\n\n### EVITE RESPOSTAS COMO:\n";
            foreach ($exemplosRuins as $exemplo) {
                $prompt .= "- " . substr($exemplo['resposta_original'], 0, 300) . "...\n";
            }
        }

        // Informações sobre dados já coletados
        if ($contexto['dadosPaciente']) {
            $prompt .= "\n\n### DADOS DO PACIENTE JÁ COLETADOS\n";
            $prompt .= "Os seguintes dados já foram fornecidos e estão salvos na sessão:\n";
            $prompt .= "- Nome: {$contexto['dadosPaciente']['nome']}\n";
            $prompt .= "- Telefone: {$contexto['dadosPaciente']['telefone']}\n";
            $prompt .= "\n**CRÍTICO:** Use estes dados automaticamente. NUNCA peça novamente nome ou telefone.\n";
            $prompt .= "Quando chamar criar_agendamento ou reagendar_consulta, use estes dados da sessão.\n";
        } else {
            $prompt .= "\n\n### DADOS DO PACIENTE NÃO COLETADOS\n";
            $prompt .= "**CRÍTICO:** Antes de qualquer agendamento, você DEVE coletar nome completo e telefone do paciente.\n";
            $prompt .= "**IMPORTANTE:** Só peça o nome quando o usuário estiver realmente querendo agendar uma consulta.\n";
            $prompt .= "Não peça nome em conversas gerais ou perguntas sobre saúde.\n";
            $prompt .= "Exemplo de quando NÃO pedir nome: usuário pergunta sobre vitaminas, sintomas, ou informações gerais.\n";
            $prompt .= "Exemplo de quando pedir nome: usuário confirma que quer agendar consulta.\n";
            $prompt .= "**CRÍTICO:** NUNCA confirme agendamento sem ter nome completo e telefone.\n";
            $prompt .= "**CRÍTICO:** Se usuário escolher horário sem ter dados, peça: \"Para confirmar o agendamento, preciso do seu nome completo e telefone.\"\n";
        $prompt .= "**CRÍTICO:** Após coletar dados do paciente, SEMPRE chame `verificar_horarios_disponiveis(dias=3)` automaticamente.\n";
        $prompt .= "**CRÍTICO:** NUNCA pergunte sobre período ou data - sempre ofereça os próximos 3 horários disponíveis.\n";
        $prompt .= "**CRÍTICO:** NUNCA pergunte sobre procedimento após coletar dados - apenas salve o que o usuário mencionar e ofereça horários.\n";
        $prompt .= "**CRÍTICO:** Se o usuário mencionar procedimento (ex: \"revisão\"), apenas confirme e chame `verificar_horarios_disponiveis(dias=3)`.\n";
        $prompt .= "\n**FLUXO CORRETO DE AGENDAMENTO:**\n";
        $prompt .= "1. Usuário diz que quer agendar → Peça nome e telefone\n";
        $prompt .= "2. Usuário fornece nome → Peça telefone\n";
        $prompt .= "3. Usuário fornece telefone → Chame `verificar_horarios_disponiveis(dias=3)` automaticamente\n";
        $prompt .= "4. Mostre os horários disponíveis → \"Aqui estão os próximos horários: [lista]. Qual você prefere?\"\n";
        $prompt .= "5. Se usuário mencionar procedimento → Confirme e chame `verificar_horarios_disponiveis(dias=3)`\n";
        $prompt .= "6. Usuário escolhe horário → Chame `validar_horario_para_agendamento`\n";
        $prompt .= "7. Se válido → Peça confirmação → Se confirmado → Chame `criar_agendamento`\n";
        $prompt .= "\n**CRÍTICO:** NUNCA pergunte sobre período, data ou procedimento após ter nome e telefone - SEMPRE chame `verificar_horarios_disponiveis(dias=3)` primeiro.\n";
        }
        
        // Instruções específicas para reagendamento
        $prompt .= "\n\n### INSTRUÇÕES PARA REAGENDAMENTO\n";
        $prompt .= "Quando o usuário confirmar o reagendamento:\n";
        $prompt .= "1. Use os dados do agendamento encontrado por `consultar_agendamento_existente`\n";
        $prompt .= "2. Chame `reagendar_consulta` com TODOS estes parâmetros:\n";
        $prompt .= "   - nome_paciente: nome do paciente (da sessão ou do agendamento)\n";
        $prompt .= "   - telefone: telefone do paciente (da sessão ou do agendamento)\n";
        $prompt .= "   - data_atual: data do agendamento atual (do resultado de consultar_agendamento_existente)\n";
        $prompt .= "   - hora_atual: hora do agendamento atual (do resultado de consultar_agendamento_existente)\n";
        $prompt .= "   - nova_data: nova data escolhida pelo usuário\n";
        $prompt .= "   - nova_hora: nova hora escolhida pelo usuário\n";
        $prompt .= "3. **EXEMPLO:** Se o agendamento atual é 2025-08-11 às 11:00 e o usuário quer 2025-08-12 às 11:00:\n";
        $prompt .= "   reagendar_consulta(nome_paciente=\\\"samanta silva\\\", telefone=\\\"54991654654\\\", data_atual=\\\"2025-08-11\\\", hora_atual=\\\"11:00:00\\\", nova_data=\\\"2025-08-12\\\", nova_hora=\\\"11:00:00\\\")\n";
        
        if ($contexto['etapaAgendamento']) {
            $prompt .= "\n\n### ETAPA ATUAL DO AGENDAMENTO\n";
            $prompt .= "Etapa: {$contexto['etapaAgendamento']['etapa']}\n";
            if (isset($contexto['etapaAgendamento']['dados'])) {
                $prompt .= "Dados adicionais: " . json_encode($contexto['etapaAgendamento']['dados']) . "\n";
            }
        }
        
        if ($contexto['estadoAgendamento']) {
            $prompt .= "\n\n### AGENDAMENTO EM ANDAMENTO (BANCO)\n";
            $prompt .= "Há um agendamento em processo para esta sessão:\n";
            $prompt .= json_encode($contexto['estadoAgendamento'], JSON_PRETTY_PRINT);
        }

        // Regra solicitada: não assinar respostas com o nome do assistente
        $prompt .= "\n\n### RESTRIÇÃO DE ASSINATURA\n";
        $prompt .= "- Não assine as respostas com seu nome. Nunca termine com '" . ($configs['nome_assistente']) . "'.\n";

        // Adicionando instruções específicas para interpretação inteligente de nomes
        $prompt .= "\n\n### INTERPRETAÇÃO INTELIGENTE DE NOMES\n";
        $prompt .= "**ANÁLISE DE CONTEXTO:** Sempre analise o contexto da conversa antes de interpretar algo como nome.\n";
        $prompt .= "\n**CONTEXTO QUE INDICA NÃO É NOME:**\n";
        $prompt .= "- Perguntas: \"sabe qual é meu nome?\", \"qual meu nome?\", \"como me chamo?\"\n";
        $prompt .= "- Frases incompletas: \"sabe qual meu\", \"meu nome é\", \"eu sou\"\n";
        $prompt .= "- Palavras contextuais: \"meu\", \"minha\", \"qual\", \"como\", \"quem\"\n";
        $prompt .= "- Termos médicos: \"consulta\", \"procedimento\", \"tratamento\"\n";
        $prompt .= "- Expressões temporais: \"hoje\", \"amanhã\", \"segunda-feira\"\n";
        $prompt .= "\n**CONTEXTO QUE INDICA É NOME:**\n";
        $prompt .= "- Resposta direta a pergunta sobre nome: \"João Silva\"\n";
        $prompt .= "- Apresentação formal: \"Meu nome é Maria Santos\"\n";
        $prompt .= "- Dados para agendamento: \"Ana Oliveira, 11987654321\"\n";
        $prompt .= "\n**VALIDAÇÃO ESTRUTURAL:**\n";
        $prompt .= "- Nome deve ter pelo menos 2 palavras (nome + sobrenome)\n";
        $prompt .= "- Cada palavra deve começar com letra\n";
        $prompt .= "- Não pode conter números ou caracteres especiais\n";
        $prompt .= "- Tamanho entre 6 e 50 caracteres\n";
        $prompt .= "\n**EXEMPLOS DE ANÁLISE:**\n";
        $prompt .= "❌ \"sabe qual meu\" → NÃO é nome (frase incompleta)\n";
        $prompt .= "❌ \"qual meu nome?\" → NÃO é nome (pergunta)\n";
        $prompt .= "❌ \"meu nome é\" → NÃO é nome (frase incompleta)\n";
        $prompt .= "✅ \"João Silva\" → É nome (estrutura válida)\n";
        $prompt .= "✅ \"Maria Santos Oliveira\" → É nome (estrutura válida)\n";

        return $prompt;
        } catch (\Exception $e) {
            error_log("ERRO em buildSystemPrompt: " . $e->getMessage());
            error_log("Trace: " . $e->getTraceAsString());
            
            // Retorna prompt mínimo em caso de erro
            return "CONTEXTO:
- Hoje: " . date('Y-m-d') . " (" . $this->getDiaSemanaPortugues() . ", " . date('H:i') . ")
- Especialidades: Não informado
- Endereço: Não informado
- Telefone: Não informado

## IDENTIDADE E COMPORTAMENTO
Você é atendente da clínica. Personalidade: amigável, atenciosa e natural.

## REGRAS ESSENCIAIS
- Colete nome completo + telefone antes de qualquer ação
- Chame as funções disponíveis quando necessário
- Seja direto e objetivo nas respostas";
        }
    }

    private function getAvailableFunctions()
    {
        return [
            [
                'name' => 'buscar_profissionais_clinica',
                'description' => 'OBRIGATÓRIO: Busca profissionais da clínica. Use SEMPRE antes de mencionar qualquer profissional de saúde. NUNCA mencione profissionais sem chamar esta função primeiro.',
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
                'description' => 'OBRIGATÓRIO: Busca serviços e valores da clínica. Use SEMPRE quando perguntarem sobre valores, preços, serviços ou procedimentos. NUNCA mencione valores sem chamar esta função. SEMPRE use servico_especifico para buscar (ex: "consulta", "exame", "procedimento").',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'servico_especifico' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'verificar_convenio',
                'description' => 'OBRIGATÓRIO: Verifica se convênio é aceito. Use SEMPRE quando perguntarem sobre convênios, planos de saúde ou cobertura. NUNCA confirme convênio sem chamar esta função.',
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
                'description' => 'OBRIGATÓRIO: Verifica horários disponíveis para agendamento. Use SEMPRE quando precisar mostrar horários disponíveis. NUNCA liste horários sem chamar esta função. CRÍTICO: Quando esta função retornar dados, use APENAS esses dados para responder. NUNCA gere texto adicional sobre horários no output.',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'data' => ['type' => 'string'],
                        'dias' => ['type' => 'integer'],
                        'periodo' => ['type' => 'string']
                    ]
                ]
            ],
            [
                'name' => 'verificar_horario_disponivel',
                'description' => 'OBRIGATÓRIO: Verifica se um horário específico está disponível. Use SEMPRE antes de criar agendamento para validar se o horário escolhido pelo usuário está realmente disponível.',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'data' => ['type' => 'string'],
                        'hora' => ['type' => 'string']
                    ],
                    'required' => ['data', 'hora']
                ]
            ],
            [
                'name' => 'validar_horario_para_agendamento',
                'description' => 'OBRIGATÓRIO: Valida se um horário específico está disponível para agendamento. Use SEMPRE quando o usuário escolher um horário. APENAS VALIDA - não cria o agendamento automaticamente. CRÍTICO: NUNCA chame esta função novamente após o usuário confirmar o agendamento.',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'data' => ['type' => 'string'],
                        'hora' => ['type' => 'string']
                    ],
                    'required' => ['data', 'hora']
                ]
            ],
            [
                'name' => 'criar_agendamento',
                'description' => 'OBRIGATÓRIO: Cria um novo agendamento. Use SEMPRE quando tiver nome, telefone, data e horário confirmados pelo usuário. NUNCA confirme agendamento sem chamar esta função. CRÍTICO: SEMPRE chame esta função após validar_horario_para_agendamento retornar válido e usuário confirmar (responder "sim", "ok", "confirmo", etc.).',
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
                'description' => 'Consulta agendamentos existentes. Prioriza telefone como principal identificador. Se houver telefone, usa nome apenas para desambiguar. Se não houver telefone, usa apenas o nome.',
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
                'name' => 'reagendar_consulta',
                'description' => 'OBRIGATÓRIO: Reagenda uma consulta existente para nova data/hora. Use SEMPRE quando o usuário escolher um novo horário para reagendamento. NUNCA confirme reagendamento sem chamar esta função.',
                'parameters' => [
                    'type' => 'object',
                    'properties' => [
                        'nome_paciente' => ['type' => 'string'],
                        'telefone' => ['type' => 'string'],
                        'data_atual' => ['type' => 'string'],
                        'hora_atual' => ['type' => 'string'],
                        'nova_data' => ['type' => 'string'],
                        'nova_hora' => ['type' => 'string']
                    ],
                    'required' => ['nome_paciente', 'telefone', 'data_atual', 'hora_atual', 'nova_data', 'nova_hora']
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

    private function executeFunction($functionName, $args, $sessionId = null)
    {
        try {
            error_log("[EXECUTE_FUNCTION] Executando função: $functionName");
            error_log("[EXECUTE_FUNCTION] Argumentos: " . json_encode($args));
            error_log("[EXECUTE_FUNCTION] SessionId: $sessionId");
           // Adiciona session_id para funções que precisam
            if (in_array($functionName, ['criar_agendamento', 'reagendar_consulta']) && $sessionId) {
                $args['session_id'] = $sessionId;
                error_log("[EXECUTE_FUNCTION] SessionId adicionado aos argumentos");
            }

            // Completa dados do paciente com dados da sessão se necessário
            if ($this->sessionService && in_array($functionName, ['criar_agendamento', 'reagendar_consulta', 'consultar_agendamento_existente', 'cancelar_agendamento'])) {
                $dadosSessao = $this->sessionService->recuperarDadosPaciente();
                
                if ($dadosSessao) {
                    // Para criar_agendamento
                    if ($functionName === 'criar_agendamento') {
                        // Se não tem nome nos argumentos, usa da sessão
                        if (empty($args['nome']) && !empty($dadosSessao['nome'])) {
                            $args['nome'] = $dadosSessao['nome'];
                            error_log("[EXECUTE_FUNCTION] Nome da sessão usado: " . $dadosSessao['nome']);
                        }
                        
                        // Se não tem telefone nos argumentos, usa da sessão
                        if (empty($args['telefone']) && !empty($dadosSessao['telefone'])) {
                            $args['telefone'] = $dadosSessao['telefone'];
                            error_log("[EXECUTE_FUNCTION] Telefone da sessão usado: " . $dadosSessao['telefone']);
                        }
                    }
                    
                    // Para reagendar_consulta
                    if ($functionName === 'reagendar_consulta') {
                        // Se não tem nome_paciente nos argumentos, usa da sessão
                        if (empty($args['nome_paciente']) && !empty($dadosSessao['nome'])) {
                            $args['nome_paciente'] = $dadosSessao['nome'];
                            error_log("[EXECUTE_FUNCTION] Nome da sessão usado para reagendamento: " . $dadosSessao['nome']);
                        }
                        
                        // Se não tem telefone nos argumentos, usa da sessão
                        if (empty($args['telefone']) && !empty($dadosSessao['telefone'])) {
                            $args['telefone'] = $dadosSessao['telefone'];
                            error_log("[EXECUTE_FUNCTION] Telefone da sessão usado para reagendamento: " . $dadosSessao['telefone']);
                        }
                        
                        // Se não tem data_atual ou hora_atual, tenta buscar o agendamento atual
                        if ((empty($args['data_atual']) || empty($args['hora_atual'])) && !empty($args['nome_paciente']) && !empty($args['telefone'])) {
                            error_log("[EXECUTE_FUNCTION] Buscando agendamento atual para completar dados do reagendamento");
                            $agendamentoAtual = $this->functions->consultar_agendamento_existente([
                                'nome_paciente' => $args['nome_paciente'],
                                'telefone' => $args['telefone']
                            ]);
                            
                            if (!empty($agendamentoAtual) && is_array($agendamentoAtual)) {
                                $agendamento = $agendamentoAtual[0];
                                if (empty($args['data_atual'])) {
                                    $args['data_atual'] = $agendamento['data_consulta'];
                                    error_log("[EXECUTE_FUNCTION] Data atual obtida do agendamento: " . $agendamento['data_consulta']);
                                }
                                if (empty($args['hora_atual'])) {
                                    $args['hora_atual'] = $agendamento['hora_consulta'];
                                    error_log("[EXECUTE_FUNCTION] Hora atual obtida do agendamento: " . $agendamento['hora_consulta']);
                                }
                            }
                        }
                    }
                    
                    // Para consultar_agendamento_existente
                    if ($functionName === 'consultar_agendamento_existente') {
                        // Se não tem nome_paciente nos argumentos, usa da sessão
                        if (empty($args['nome_paciente']) && !empty($dadosSessao['nome'])) {
                            $args['nome_paciente'] = $dadosSessao['nome'];
                            error_log("[EXECUTE_FUNCTION] Nome da sessão usado para consulta: " . $dadosSessao['nome']);
                        }
                        
                        // Se não tem telefone nos argumentos, usa da sessão
                        if (empty($args['telefone']) && !empty($dadosSessao['telefone'])) {
                            $args['telefone'] = $dadosSessao['telefone'];
                            error_log("[EXECUTE_FUNCTION] Telefone da sessão usado para consulta: " . $dadosSessao['telefone']);
                        }
                    }
                    
                    // Para cancelar_agendamento
                    if ($functionName === 'cancelar_agendamento') {
                        // Se não tem nome_paciente nos argumentos, usa da sessão
                        if (empty($args['nome_paciente']) && !empty($dadosSessao['nome'])) {
                            $args['nome_paciente'] = $dadosSessao['nome'];
                            error_log("[EXECUTE_FUNCTION] Nome da sessão usado para cancelamento: " . $dadosSessao['nome']);
                        }
                        
                        // Se não tem telefone nos argumentos, usa da sessão
                        if (empty($args['telefone']) && !empty($dadosSessao['telefone'])) {
                            $args['telefone'] = $dadosSessao['telefone'];
                            error_log("[EXECUTE_FUNCTION] Telefone da sessão usado para cancelamento: " . $dadosSessao['telefone']);
                        }
                    }
                }
                
                // Validação crítica para criar_agendamento
                if ($functionName === 'criar_agendamento') {
                    if (empty($args['nome']) || empty($args['telefone'])) {
                        error_log("[EXECUTE_FUNCTION] ERRO: Tentativa de criar agendamento sem dados completos");
                        error_log("[EXECUTE_FUNCTION] Nome: " . ($args['nome'] ?? 'VAZIO'));
                        error_log("[EXECUTE_FUNCTION] Telefone: " . ($args['telefone'] ?? 'VAZIO'));
                        return [
                            'erro' => 'Dados incompletos para agendamento. Nome completo e telefone são obrigatórios.',
                            'dados_faltantes' => [
                                'nome' => empty($args['nome']),
                                'telefone' => empty($args['telefone'])
                            ]
                        ];
                    }
                    
                    // Validação adicional do nome
                    $nome = trim($args['nome']);
                    $palavrasNaoNome = [
                        'mas', 'tambem', 'também', 'gordurinha', 'gordurinhas', 'gorda', 'gordura', 'pochete',
                        'flancos', 'corpo', 'abdômen', 'abdomen', 'barriga', 'estômago', 'estomago',
                        'entendi', 'tem', 'solução', 'solucao', 'procedimento', 'cirurgia', 'cirúrgico',
                        'lipoaspiração', 'lipoaspiracao', 'rinoplastia', 'nariz', 'torto', 'calombo',
                        'informações', 'informacoes', 'detalhes', 'valor', 'preço', 'preco', 'custo',
                        'semana', 'próxima', 'proxima', 'disponível', 'disponivel', 'agenda', 'agendamento'
                    ];
                    
                    $nomeLower = strtolower($nome);
                    $palavrasNome = explode(' ', $nomeLower);
                    $nomeInvalido = false;
                    
                    foreach ($palavrasNome as $palavra) {
                        if (in_array($palavra, $palavrasNaoNome)) {
                            $nomeInvalido = true;
                            error_log("[EXECUTE_FUNCTION] Nome inválido detectado: '$nome' contém palavra proibida: '$palavra'");
                            break;
                        }
                    }
                    
                    if ($nomeInvalido || strlen($nome) < 6 || count($palavrasNome) < 2) {
                        error_log("[EXECUTE_FUNCTION] ERRO: Nome inválido para agendamento: '$nome'");
                        return [
                            'erro' => 'Nome inválido. Por favor, informe seu nome completo (nome e sobrenome).',
                            'nome_invalido' => true
                        ];
                    }
                }
                
                // Salva dados do paciente na sessão quando disponíveis
                if ($functionName === 'criar_agendamento' && !empty($args['nome']) && !empty($args['telefone'])) {
                    // Validação adicional: não salva nomes que são claramente inválidos
                    $nome = trim($args['nome']);
                    $palavrasNaoNome = [
                        'oi', 'olá', 'bem', 'estou', 'posso', 'quero', 'gostaria', 'preciso', 'pode', 'agendar',
                        'consulta', 'médico', 'doutor', 'dr', 'dra', 'vitaminas', 'gravida', 'grávida', 'gestante',
                        'sim', 'não', 'nao', 'ok', 'certo', 'claro', 'amanha', 'amanhã', 'hoje', 'ontem'
                    ];
                    
                    $nomeLower = strtolower($nome);
                    $palavrasNome = explode(' ', $nomeLower);
                    $nomeValido = true;
                    
                    foreach ($palavrasNome as $palavra) {
                        if (in_array($palavra, $palavrasNaoNome)) {
                            $nomeValido = false;
                            error_log("[EXECUTE_FUNCTION] Nome inválido detectado: '$nome' contém palavra proibida: '$palavra'");
                            break;
                        }
                    }
                    
                    if ($nomeValido) {
                        $this->sessionService->salvarDadosPaciente($nome, $args['telefone']);
                        error_log("[EXECUTE_FUNCTION] Dados do paciente salvos na sessão - Nome: $nome, Telefone: {$args['telefone']}");
                    } else {
                        error_log("[EXECUTE_FUNCTION] Nome inválido não salvo na sessão: $nome");
                    }
                }
            }

            if (method_exists($this->functions, $functionName)) {
                error_log("[EXECUTE_FUNCTION] Função encontrada, executando...");
                $result = $this->functions->$functionName($args);
                error_log("[EXECUTE_FUNCTION] Resultado: " . json_encode($result));
                return $result;
            }

            error_log("[EXECUTE_FUNCTION] Função não encontrada: $functionName");
            return ['erro' => 'Função não encontrada'];
        } catch (\Exception $e) {
            error_log("[EXECUTE_FUNCTION] ERRO na função $functionName: " . $e->getMessage());
            error_log("[EXECUTE_FUNCTION] Arquivo: " . $e->getFile() . " Linha: " . $e->getLine());
            error_log("[EXECUTE_FUNCTION] Trace: " . $e->getTraceAsString());
            return ['erro' => 'Erro ao executar função: ' . $e->getMessage()];
        }
    }

    private function saveConversation($sessionId, $userMessage, $aiResponse, $functionCalls, $usage)
    {
        try {
            error_log("[SAVE_CONVERSATION] Salvando conversa...");
            error_log("[SAVE_CONVERSATION] SessionId: $sessionId");
            error_log("[SAVE_CONVERSATION] UserMessage: $userMessage");
            error_log("[SAVE_CONVERSATION] AiResponse: $aiResponse");

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
            $custoDolar = ($tokensPrompt * 0.00025 + $tokensResposta * 0.002) / 1000;            // Converte para reais usando taxa de câmbio atual
            $custoEstimado = $this->currencyService->convertDollarToReal($custoDolar);

            $params = [
                $sessionId,
                $userMessage,
                $aiResponse,
                $funcaoChamada,
                $tokensPrompt,
                $tokensResposta,
                $custoEstimado
            ];

            error_log("[SAVE_CONVERSATION] Params: " . json_encode($params));
            $result = $this->db->execute($sql, $params);
            error_log("[SAVE_CONVERSATION] Resultado: " . ($result ? 'true' : 'false'));

            if ($result === false) {
                error_log("[SAVE_CONVERSATION] ERRO: Falha ao salvar conversa no banco");
            }
        } catch (\Exception $e) {
            error_log("[SAVE_CONVERSATION] ERRO: " . $e->getMessage());
            error_log("[SAVE_CONVERSATION] Arquivo: " . $e->getFile() . " Linha: " . $e->getLine());
        }
    }

    private function getRecentConversation($sessionId, $limit = 10)
    {
        $sql = "SELECT mensagem_usuario, resposta_agente 
                FROM conversas 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?";

        $result = $this->db->query($sql, [$sessionId, $limit]);
        return array_reverse($result);
    }



    /**
     * Extrai e salva dados do paciente da mensagem do usuário
     * Versão melhorada com análise de contexto e validação inteligente
     */
    private function extrairESalvarDados($userMessage)
    {
        if (!$this->sessionService) {
            return;
        }

        // Verifica se já tem dados completos
        if ($this->sessionService->temDadosPaciente()) {
            $dadosExistentes = $this->sessionService->recuperarDadosPaciente();
            if (!empty($dadosExistentes['nome']) && !empty($dadosExistentes['telefone'])) {
                return; // Já tem dados completos
            }
        }

        $nome = null;
        $telefone = null;

        // Extrai telefone (padrão brasileiro)
        if (preg_match('/(\d{2}\s?\d{4,5}\s?\d{4})/', $userMessage, $matches)) {
            $telefone = preg_replace('/\s/', '', $matches[1]);
            error_log("SessionService: Telefone extraído: $telefone");
        }

        // ANÁLISE INTELIGENTE DE CONTEXTO
        $contextoConversa = $this->analisarContextoConversa($userMessage);
        
        // Se o contexto indica que não é um nome, não tenta extrair
        if (!$contextoConversa['pareceNome']) {
            error_log("SessionService: Contexto indica que não é nome - Motivo: " . $contextoConversa['motivo']);
            
            // Ainda pode extrair telefone se houver
            if ($telefone) {
                $this->salvarApenasTelefone($telefone);
            }
            return;
        }

        // VALIDAÇÃO ESTRUTURAL INTELIGENTE
        $validacaoEstrutural = $this->validarEstruturaNome($userMessage);
        
        if (!$validacaoEstrutural['valido']) {
            error_log("SessionService: Estrutura inválida para nome - Motivo: " . $validacaoEstrutural['motivo']);
            
            // Ainda pode extrair telefone se houver
            if ($telefone) {
                $this->salvarApenasTelefone($telefone);
            }
            return;
        }

        // Se passou por todas as validações, extrai o nome
        $nome = $validacaoEstrutural['nome'];
        error_log("SessionService: Nome extraído e validado: $nome");

        // Salva os dados
        $this->salvarDadosCompletos($nome, $telefone);
    }

    /**
     * Analisa o contexto da conversa para determinar se a mensagem parece ser um nome
     */
    private function analisarContextoConversa($userMessage)
    {
        $mensagemLower = strtolower(trim($userMessage));
        
        // Padrões que indicam que NÃO é um nome
        $padroesNaoNome = [
            // Perguntas diretas
            '/^(sabe|qual|como|quem|onde|quando|porque|porquê|por que)/i',
            '/\?$/', // Termina com ponto de interrogação
            
            // Frases incompletas ou contextuais
            '/^(meu|minha|seu|sua|qual|como|quem)/i',
            '/^(eu sou|me chamo|meu nome)/i',
            
            // Palavras de contexto que não são nomes
            '/\b(oi|olá|bem|estou|posso|quero|gostaria|preciso|pode|agendar)\b/i',
            '/\b(consulta|médico|doutor|dr|dra|vitaminas|gravida|grávida|gestante)\b/i',
            '/\b(sim|não|nao|ok|certo|claro|amanha|amanhã|hoje|ontem)\b/i',
            '/\b(segunda|terça|quarta|quinta|sexta|sábado|domingo)\b/i',
            '/\b(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b/i',
            '/\b(horário|horario|hora|data|dia|mês|mes|ano)\b/i',
            '/\b(especialista|especialidade|ginecologia|obstetrícia|obstetricia)\b/i',
            '/\b(mas|tambem|também|gordurinha|gordurinhas|gorda|gordura|pochete)\b/i',
            '/\b(flancos|corpo|abdômen|abdomen|barriga|estômago|estomago)\b/i',
            '/\b(entendi|tem|solução|solucao|procedimento|cirurgia|cirúrgico)\b/i',
            '/\b(lipoaspiração|lipoaspiracao|rinoplastia|nariz|torto|calombo)\b/i',
            '/\b(informações|informacoes|detalhes|valor|preço|preco|custo)\b/i',
            '/\b(semana|próxima|proxima|disponível|disponivel|agenda|agendamento)\b/i'
        ];

        // Verifica cada padrão
        foreach ($padroesNaoNome as $padrao) {
            if (preg_match($padrao, $mensagemLower)) {
                return [
                    'pareceNome' => false,
                    'motivo' => "Padrão detectado: " . $padrao
                ];
            }
        }

        // Verifica se é uma frase muito curta ou incompleta
        $palavras = explode(' ', $mensagemLower);
        if (count($palavras) <= 2 && strlen($mensagemLower) < 10) {
            // Verifica se contém palavras que indicam frase incompleta
            $palavrasIncompletas = ['meu', 'minha', 'seu', 'sua', 'qual', 'como', 'quem'];
            foreach ($palavrasIncompletas as $palavra) {
                if (in_array($palavra, $palavras)) {
                    return [
                        'pareceNome' => false,
                        'motivo' => "Frase incompleta com palavra contextual: $palavra"
                    ];
                }
            }
        }

        // Verifica se contém caracteres que não são típicos de nomes
        if (preg_match('/[?!.,;:]/', $userMessage)) {
            return [
                'pareceNome' => false,
                'motivo' => "Contém caracteres de pontuação não típicos de nomes"
            ];
        }

        return [
            'pareceNome' => true,
            'motivo' => "Passou por todas as validações de contexto"
        ];
    }

    /**
     * Valida a estrutura da mensagem como um nome válido
     */
    private function validarEstruturaNome($userMessage)
    {
        $mensagemTrim = trim($userMessage);
        $palavras = explode(' ', $mensagemTrim);
        
        // Remove palavras vazias
        $palavras = array_filter($palavras, function($palavra) {
            return !empty(trim($palavra));
        });
        
        // Validações estruturais
        if (count($palavras) < 2) {
            return [
                'valido' => false,
                'motivo' => "Nome deve ter pelo menos 2 palavras (nome e sobrenome)",
                'nome' => null
            ];
        }
        
        if (strlen($mensagemTrim) < 6) {
            return [
                'valido' => false,
                'motivo' => "Nome muito curto (mínimo 6 caracteres)",
                'nome' => null
            ];
        }
        
        if (strlen($mensagemTrim) > 50) {
            return [
                'valido' => false,
                'motivo' => "Nome muito longo (máximo 50 caracteres)",
                'nome' => null
            ];
        }

        // Verifica se cada palavra parece ser um nome válido
        foreach ($palavras as $palavra) {
            $palavraTrim = trim($palavra);
            
            // Não pode ser número
            if (is_numeric($palavraTrim)) {
                return [
                    'valido' => false,
                    'motivo' => "Palavra numérica encontrada: $palavraTrim",
                    'nome' => null
                ];
            }
            
            // Deve ter pelo menos 2 caracteres
            if (strlen($palavraTrim) < 2) {
                return [
                    'valido' => false,
                    'motivo' => "Palavra muito curta: $palavraTrim",
                    'nome' => null
                ];
            }
            
            // Deve começar com letra
            if (!preg_match('/^[a-zA-ZÀ-ÿ]/', $palavraTrim)) {
                return [
                    'valido' => false,
                    'motivo' => "Palavra não começa com letra: $palavraTrim",
                    'nome' => null
                ];
            }
        }

        // Se passou por todas as validações, retorna o nome
        return [
            'valido' => true,
            'motivo' => "Estrutura válida",
            'nome' => implode(' ', $palavras)
        ];
    }

    /**
     * Salva apenas o telefone quando não há nome válido
     */
    private function salvarApenasTelefone($telefone)
    {
        $dadosExistentes = $this->sessionService->recuperarDadosPaciente();
        $nomeExistente = $dadosExistentes ? $dadosExistentes['nome'] : '';
        
        if ($nomeExistente) {
            $this->sessionService->salvarDadosPaciente($nomeExistente, $telefone);
            error_log("SessionService: Telefone atualizado com nome existente - Nome: $nomeExistente, Telefone: $telefone");
        } else {
            $this->sessionService->salvarDadosPaciente('', $telefone);
            error_log("SessionService: Apenas telefone salvo - Telefone: $telefone");
        }
    }

    /**
     * Salva dados completos (nome e telefone)
     */
    private function salvarDadosCompletos($nome, $telefone)
    {
        // Se já tem dados parciais, completa
        $dadosExistentes = $this->sessionService->recuperarDadosPaciente();
        
        if ($dadosExistentes) {
            $nome = $nome ?: $dadosExistentes['nome'];
            $telefone = $telefone ?: $dadosExistentes['telefone'];
        }

        if ($nome && $telefone) {
            $this->sessionService->salvarDadosPaciente($nome, $telefone);
            $this->sessionService->salvarEtapaAgendamento('dados_completos');
            error_log("SessionService: Dados completos salvos - Nome: $nome, Telefone: $telefone");
        } elseif ($nome || $telefone) {
            // Salva dados parciais
            $nomeParcial = $nome ?: '';
            $telefoneParcial = $telefone ?: '';
            $this->sessionService->salvarDadosPaciente($nomeParcial, $telefoneParcial);
            error_log("SessionService: Dados parciais salvos - Nome: $nomeParcial, Telefone: $telefoneParcial");
        }
    }

    private function getDiaSemanaPortugues()
    {
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

    // Função para verificar tamanho do prompt
    private function calcularTamanhoPrompt($contexto)
    {
        $prompt = $this->buildSystemPrompt($contexto);
        $tokens = $this->contarTokens($prompt);

        // Log para monitoramento
        error_log("Tamanho do prompt: " . strlen($prompt) . " caracteres, ~" . $tokens . " tokens");

        return $tokens;
    }

    private function contarTokens($texto)
    {
        // Estimativa aproximada: 1 token = ~4 caracteres
        return ceil(strlen($texto) / 4);
    }

    // Se o prompt ficar muito grande, usar estratégia de priorização
    private function selecionarExemplosPrioritarios($exemplos, $maxTokens = 8000)
    {
        $exemplosPrioritarios = [];
        $tokensAtuais = 0;

        foreach ($exemplos as $exemplo) {
            $texto = $exemplo['resposta_reescrita'] ?: $exemplo['resposta_original'];
            $tokensExemplo = $this->contarTokens($texto);

            if ($tokensAtuais + $tokensExemplo > $maxTokens) {
                break;
            }

            $exemplosPrioritarios[] = $exemplo;
            $tokensAtuais += $tokensExemplo;
        }

        return $exemplosPrioritarios;
    }

    // Priorizar exemplos mais recentes e reescritas
    private function ordenarExemplosPorPrioridade($exemplos)
    {
        usort($exemplos, function ($a, $b) {
            // Reescritas têm prioridade máxima
            if ($a['tipo'] === 'reescrita' && $b['tipo'] !== 'reescrita') return -1;
            if ($b['tipo'] === 'reescrita' && $a['tipo'] !== 'reescrita') return 1;

            // Depois ordena por data (mais recentes primeiro)
            return strtotime($b['created_at']) - strtotime($a['created_at']);
        });

        return $exemplos;
    }

    // Adicionar função para buscar exemplos ruins
    public function buscar_exemplos_ruins($limit = null)
    {
        $sql = "SELECT * FROM conversas_treinamento 
                WHERE feedback_tipo = 'negativo'
                ORDER BY created_at DESC";

        return $this->db->query($sql);
    }
}
