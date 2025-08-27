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
            // Remove pontos e normaliza espaços para busca mais flexível
            $termoBusca = preg_replace('/[.\s]+/', ' ', trim($params['profissional_especifico']));
            $sql .= " AND REPLACE(nome, '.', '') LIKE ?";
            $queryParams[] = '%' . str_replace(' ', '%', $termoBusca) . '%';
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
        
        if (!empty($params['servico_especifico'])) {
            $sql .= " AND (nome LIKE ? OR palavras_chave LIKE ?)";
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
            $queryParams[] = '%' . $params['servico_especifico'] . '%';
        }
        
        $resultado = $this->db->query($sql, $queryParams);
        
        // Se não encontrou nada com busca específica, retorna todos os serviços
        if (empty($resultado) && !empty($params['servico_especifico'])) {
            $sqlTodos = "SELECT * FROM servicos_clinica WHERE ativo = 1 ORDER BY nome ASC";
            $resultado = $this->db->query($sqlTodos);
        }
        
        return $resultado;
    }
    
    /**
     * Verifica se convênio é aceito
     */
    public function verificar_convenio($params) {
        if (empty($params['nome_convenio'])) {
            return ['erro' => 'Nome do convênio é obrigatório'];
        }
        
        // Busca convênios tanto ativos quanto inativos para verificar observações
        $sql = "SELECT * FROM convenios_aceitos WHERE nome LIKE ? ORDER BY ativo DESC, nome ASC";
        $resultado = $this->db->query($sql, ['%' . $params['nome_convenio'] . '%']);
        
        // Se encontrou convênios, retorna apenas os ativos, mas inclui informações sobre inativos
        if (!empty($resultado)) {
            $conveniosAtivos = array_filter($resultado, function($convenio) {
                return $convenio['ativo'] == 1;
            });
            
            $conveniosInativos = array_filter($resultado, function($convenio) {
                return $convenio['ativo'] == 0;
            });
            
            // Se há convênios ativos, retorna apenas eles
            if (!empty($conveniosAtivos)) {
                return array_values($conveniosAtivos);
            }
            
            // Se só há convênios inativos, retorna eles com informação sobre o status
            if (!empty($conveniosInativos)) {
                // Adiciona informação sobre o status inativo
                foreach ($conveniosInativos as &$convenio) {
                    $convenio['status_info'] = 'Convênio temporariamente inativo';
                }
                return array_values($conveniosInativos);
            }
        }
        
        return $resultado;
    }
    
    /**
     * Consulta agendamentos por nome ou telefone
     * Prioriza telefone como principal identificador
     */
    public function consultar_agendamento_existente($params = []) {
        // CRÍTICO: Validação obrigatória de telefone
        if (empty($params['telefone'])) {
            error_log('[ERRO FLUXO] consultar_agendamento_existente chamada SEM telefone! Params: ' . json_encode($params));
            return ['erro' => 'Telefone é obrigatório para consultar agendamento. Por favor, informe o telefone do paciente.'];
        }
        
        $sql = "SELECT a.*, p.nome as paciente_nome, p.telefone 
                FROM agendamentos a 
                JOIN pacientes p ON a.paciente_id = p.id 
                WHERE a.status != 'cancelado'";
        $queryParams = [];
        
        // Prioriza telefone como principal identificador
        if (!empty($params['telefone'])) {
            $sql .= " AND p.telefone = ?";
            $queryParams[] = $params['telefone'];
            
            // Se também tem nome, usa como critério adicional para desambiguar
            if (!empty($params['nome_paciente'])) {
                // Busca mais flexível: verifica se o nome fornecido contém partes do nome no banco
                // ou se o nome no banco contém partes do nome fornecido
                $nomeFornecido = trim($params['nome_paciente']);
                $palavrasNome = explode(' ', $nomeFornecido);
                
                $condicoesNome = [];
                foreach ($palavrasNome as $palavra) {
                    if (strlen($palavra) > 2) { // Ignora palavras muito curtas
                        $condicoesNome[] = "p.nome LIKE ?";
                        $queryParams[] = '%' . $palavra . '%';
                    }
                }
                
                if (!empty($condicoesNome)) {
                    $sql .= " AND (" . implode(' OR ', $condicoesNome) . ")";
                }
            }
        } 
        // Se não tem telefone, usa apenas o nome
        elseif (!empty($params['nome_paciente'])) {
            $nomeFornecido = trim($params['nome_paciente']);
            $palavrasNome = explode(' ', $nomeFornecido);
            
            $condicoesNome = [];
            foreach ($palavrasNome as $palavra) {
                if (strlen($palavra) > 2) { // Ignora palavras muito curtas
                    $condicoesNome[] = "p.nome LIKE ?";
                    $queryParams[] = '%' . $palavra . '%';
                }
            }
            
            if (!empty($condicoesNome)) {
                $sql .= " AND (" . implode(' OR ', $condicoesNome) . ")";
            }
        }
        
        $sql .= " ORDER BY a.data_consulta, a.hora_consulta";
        
        $resultado = $this->db->query($sql, $queryParams);
        
        // Se não encontrou com telefone + nome, tenta apenas com telefone
        if (empty($resultado) && !empty($params['telefone']) && !empty($params['nome_paciente'])) {
            $sqlApenasTelefone = "SELECT a.*, p.nome as paciente_nome, p.telefone 
                                 FROM agendamentos a 
                                 JOIN pacientes p ON a.paciente_id = p.id 
                                 WHERE a.status != 'cancelado' AND p.telefone = ?
                                 ORDER BY a.data_consulta, a.hora_consulta";
            
            $resultado = $this->db->query($sqlApenasTelefone, [$params['telefone']]);
        }
        
        return $resultado;
    }
    
    /**
     * Verifica horários disponíveis para agendamento
     */
    public function verificar_horarios_disponiveis($params = []) {
        try {
            $data = $params['data'] ?? date('Y-m-d');
            $diasDesejados = $params['dias'] ?? 3; // Quantidade de dias COM HORÁRIOS DISPONÍVEIS que queremos encontrar
            
            error_log("DEBUG: verificar_horarios_disponiveis - Data inicial: $data, Dias desejados: $diasDesejados");
            
            $resultado = [];
            $diasVerificados = 0;
            $maxDiasVerificacao = 60; // Limite máximo de dias para verificar
            
            // Busca progressiva: primeiro 10 dias, depois 20, depois 30, etc.
            $incrementos = [10, 20, 30, 40, 50, 60];
            
            foreach ($incrementos as $incremento) {
                error_log("DEBUG: Verificando próximos $incremento dias...");
                
                // Verifica do último dia verificado até o incremento atual
                $inicio = $diasVerificados;
                $fim = $incremento;
                
                for ($i = $inicio; $i < $fim && $i < $maxDiasVerificacao; $i++) {
                    $dataVerificar = date('Y-m-d', strtotime($data . " +$i days"));
                    $diaSemana = $this->getDiaSemana($dataVerificar);
                    
                    error_log("DEBUG: Verificando data: $dataVerificar, dia da semana: $diaSemana");
                    
                    // Busca horários de funcionamento
                    $sql = "SELECT * FROM horarios_disponiveis WHERE dia_semana = ? AND ativo = 1";
                    $horarios = $this->db->query($sql, [$diaSemana]);
                    
                    error_log("DEBUG: Horários encontrados para $diaSemana: " . count($horarios));
                    
                    if (empty($horarios)) {
                        error_log("DEBUG: Nenhum horário configurado para $diaSemana");
                        continue; // Pula dias sem horários disponíveis
                    }
                    
                    // Busca agendamentos existentes
                    $sql = "SELECT hora_consulta FROM agendamentos 
                            WHERE data_consulta = ? AND status != 'cancelado'";
                    $agendamentos = $this->db->query($sql, [$dataVerificar]);
                    
                    $horariosOcupados = array_column($agendamentos, 'hora_consulta');
                    error_log("DEBUG: Horários ocupados para $dataVerificar: " . json_encode($horariosOcupados));
                    
                    $horariosDisponiveis = [];
                    
                    foreach ($horarios as $horario) {
                        error_log("DEBUG: Processando horário - manha: {$horario['manha_inicio']}-{$horario['manha_fim']}, tarde: {$horario['tarde_inicio']}-{$horario['tarde_fim']}, intervalo: {$horario['intervalo_minutos']}");
                        
                        // Validação dos dados do horário
                        if (!empty($horario['manha_inicio']) && !empty($horario['manha_fim']) && !empty($horario['intervalo_minutos'])) {
                            $horariosManha = $this->gerarHorarios(
                                $horario['manha_inicio'],
                                $horario['manha_fim'],
                                $horario['intervalo_minutos'],
                                $horariosOcupados,
                                $dataVerificar
                            );
                            $horariosDisponiveis = array_merge($horariosDisponiveis, $horariosManha);
                            error_log("DEBUG: Horários manhã gerados: " . json_encode($horariosManha));
                        }
                        
                        if (!empty($horario['tarde_inicio']) && !empty($horario['tarde_fim']) && !empty($horario['intervalo_minutos'])) {
                            $horariosTarde = $this->gerarHorarios(
                                $horario['tarde_inicio'],
                                $horario['tarde_fim'],
                                $horario['intervalo_minutos'],
                                $horariosOcupados,
                                $dataVerificar
                            );
                            $horariosDisponiveis = array_merge($horariosDisponiveis, $horariosTarde);
                            error_log("DEBUG: Horários tarde gerados: " . json_encode($horariosTarde));
                        }
                    }
                    
                    if (!empty($horariosDisponiveis)) {
                        error_log("DEBUG: Horários disponíveis para $dataVerificar: " . json_encode($horariosDisponiveis));
                        $resultado[] = [
                            'data' => $dataVerificar,
                            'dia_semana' => $this->getDiaSemanaPortugues($dataVerificar),
                            'horarios' => $horariosDisponiveis
                        ];
                        
                        // Se já encontrou o número desejado de dias, para a busca
                        if (count($resultado) >= $diasDesejados) {
                            error_log("DEBUG: Encontrou $diasDesejados dias com horários disponíveis. Parando busca.");
                            break 2; // Sai dos dois loops
                        }
                    } else {
                        error_log("DEBUG: Nenhum horário disponível para $dataVerificar");
                    }
                }
                
                $diasVerificados = $fim;
                
                // Se já encontrou o número desejado de dias, para a busca
                if (count($resultado) >= $diasDesejados) {
                    break;
                }
            }
            
            error_log("DEBUG: Resultado final: " . json_encode($resultado));
            return $resultado;
            
        } catch (\Exception $e) {
            error_log("ERRO em verificar_horarios_disponiveis: " . $e->getMessage());
            throw $e;
        }
    }
    
    /**
     * Verifica se um horário específico está disponível
     */
    public function verificar_horario_disponivel($params = []) {
        if (empty($params['data']) || empty($params['hora'])) {
            return ['erro' => 'Data e hora são obrigatórios'];
        }
        
        $data = $params['data'];
        $hora = $this->normalizarHorario($params['hora']);
        
        // Busca agendamentos existentes para esta data e hora
        $sql = "SELECT COUNT(*) as total FROM agendamentos 
                WHERE data_consulta = ? AND hora_consulta = ? AND status != 'cancelado'";
        $result = $this->db->query($sql, [$data, $hora]);
        
        if (empty($result)) {
            return ['disponivel' => false, 'erro' => 'Erro ao verificar disponibilidade'];
        }
        
        $totalAgendamentos = $result[0]['total'];
        
        // Se não há agendamentos, verifica se o horário está dentro dos horários de funcionamento
        if ($totalAgendamentos == 0) {
            $diaSemana = $this->getDiaSemana($data);
            
            // Busca horários de funcionamento
            $sql = "SELECT * FROM horarios_disponiveis WHERE dia_semana = ? AND ativo = 1";
            $horarios = $this->db->query($sql, [$diaSemana]);
            
            if (empty($horarios)) {
                return ['disponivel' => false, 'erro' => 'Clínica não funciona neste dia'];
            }
            
            // Verifica se o horário está dentro dos horários de funcionamento
            $horarioValido = false;
            foreach ($horarios as $horario) {
                // Verifica manhã
                if ($hora >= $horario['manha_inicio'] && $hora <= $horario['manha_fim']) {
                    $horarioValido = true;
                    break;
                }
                
                // Verifica tarde
                if ($horario['tarde_inicio'] && $horario['tarde_fim'] && 
                    $hora >= $horario['tarde_inicio'] && $hora <= $horario['tarde_fim']) {
                    $horarioValido = true;
                    break;
                }
            }
            
            if (!$horarioValido) {
                return ['disponivel' => false, 'erro' => 'Horário fora do horário de funcionamento'];
            }
            
            // Se for hoje, verifica se o horário não passou
            if ($data === date('Y-m-d')) {
                $horaAtual = date('H:i:s');
                if ($hora <= $horaAtual) {
                    return ['disponivel' => false, 'erro' => 'Horário já passou'];
                }
            }
            
            // VERIFICAÇÃO FINAL: Confirma se o horário está realmente na lista de horários disponíveis
            $horariosDisponiveis = $this->verificar_horarios_disponiveis(['data' => $data, 'dias' => 1]);
            $horarioEncontrado = false;
            
            foreach ($horariosDisponiveis as $dia) {
                if ($dia['data'] === $data) {
                    foreach ($dia['horarios'] as $horario) {
                        if ($horario === $hora) {
                            $horarioEncontrado = true;
                            break 2;
                        }
                    }
                }
            }
            
            if (!$horarioEncontrado) {
                return ['disponivel' => false, 'erro' => 'Horário não está na lista de disponíveis'];
            }
            
            return ['disponivel' => true];
        }
        
        return ['disponivel' => false, 'erro' => 'Horário já está ocupado'];
    }
    
    /**
     * Cria novo agendamento
     */
    public function criar_agendamento($params) {
        error_log("criar_agendamento chamada com params: " . json_encode($params));
        
        // Verifica campos obrigatórios
        $required = ['nome', 'telefone', 'data', 'hora'];
        foreach ($required as $field) {
            if (empty($params[$field])) {
                error_log("Campo obrigatório faltando: $field");
                return ['erro' => "Campo $field é obrigatório"];
            }
        }
        
        // Validação adicional para nome e telefone
        $nome = trim($params['nome']);
        
        // Lista de palavras que não podem estar em um nome
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
        
        // Verifica se contém palavras proibidas
        foreach ($palavrasNome as $palavra) {
            if (in_array($palavra, $palavrasNaoNome)) {
                error_log("Nome contém palavra proibida: '$nome' - palavra: '$palavra'");
                return ['erro' => 'Nome inválido. Por favor, informe seu nome completo (nome e sobrenome).'];
            }
        }
        
        // Validações de tamanho e estrutura
        if (strlen($nome) < 6) {
            error_log("Nome muito curto: " . $nome);
            return ['erro' => 'Nome deve ter pelo menos 6 caracteres'];
        }
        
        if (count($palavrasNome) < 2) {
            error_log("Nome sem sobrenome: " . $nome);
            return ['erro' => 'Nome deve incluir nome e sobrenome'];
        }
        
        if (strlen($nome) > 50) {
            error_log("Nome muito longo: " . $nome);
            return ['erro' => 'Nome muito longo'];
        }
        
        if (strlen(preg_replace('/[^0-9]/', '', $params['telefone'])) < 10) {
            error_log("Telefone inválido: " . $params['telefone']);
            return ['erro' => 'Telefone deve ter pelo menos 10 dígitos'];
        }
        
        try {
            // Normaliza o horário antes de validar
            $horaNormalizada = $this->normalizarHorario($params['hora']);
            
            // CRÍTICO: Valida se o horário foi realmente verificado como disponível
            $validacao = $this->validar_horario_para_agendamento([
                'data' => $params['data'],
                'hora' => $params['hora']
            ]);
            
            if (!$validacao['valido']) {
                error_log("Horário não validado: " . json_encode($validacao));
                return ['erro' => $validacao['erro']];
            }
            
            // Busca ou cria paciente
            error_log("Criando/buscando paciente: " . $params['nome'] . " - " . $params['telefone']);
            $sessionId = $params['session_id'] ?? null;
            $pacienteId = $this->getOrCreatePaciente($params['nome'], $params['telefone'], $sessionId);
            error_log("Paciente ID: $pacienteId");
            
            // Cria agendamento usando o horário normalizado
            $sql = "INSERT INTO agendamentos (paciente_id, data_consulta, hora_consulta, 
                    procedimento, observacoes, status) VALUES (?, ?, ?, ?, ?, 'confirmado')";
            
            $agendamentoParams = [
                $pacienteId,
                $params['data'],
                $horaNormalizada,
                $params['procedimento'] ?? null,
                $params['observacoes'] ?? null
            ];
            error_log("Executando SQL com params: " . json_encode($agendamentoParams));
            
            $result = $this->db->execute($sql, $agendamentoParams);
            error_log("Resultado da inserção: " . ($result ? 'true' : 'false'));
            
            if ($result) {
                error_log("Agendamento criado com sucesso");
                
                // Buscar dados do agendamento criado para retornar na resposta
                $agendamentoId = $this->db->lastInsertId();
                $sql = "SELECT a.*, p.nome as nome_paciente, p.telefone 
                        FROM agendamentos a 
                        JOIN pacientes p ON a.paciente_id = p.id 
                        WHERE a.id = ?";
                $agendamentoResult = $this->db->query($sql, [$agendamentoId]);
                
                if ($agendamentoResult && !empty($agendamentoResult)) {
                    $agendamento = $agendamentoResult[0]; // Pega o primeiro resultado
                    return [
                        'sucesso' => true,
                        'agendamento' => [
                            'id' => $agendamento['id'],
                            'nome_paciente' => $agendamento['nome_paciente'],
                            'telefone' => $agendamento['telefone'],
                            'data_consulta' => $agendamento['data_consulta'],
                            'hora_consulta' => $agendamento['hora_consulta'],
                            'procedimento' => $agendamento['procedimento'],
                            'data_formatada' => date('d/m/Y', strtotime($agendamento['data_consulta'])),
                            'hora_formatada' => date('H:i', strtotime($agendamento['hora_consulta'])),
                            'dia_semana' => $this->getDiaSemana($agendamento['data_consulta'])
                        ]
                    ];
                }
                
                return ['sucesso' => true];
            }
            
            error_log("Falha ao criar agendamento");
            return ['erro' => 'Falha ao criar agendamento'];
        } catch (\Exception $e) {
            error_log("Erro em criar_agendamento: " . $e->getMessage());
            return ['erro' => $e->getMessage()];
        }
    }
    

    
    /**
     * Valida se um horário específico está disponível e pode ser agendado
     * CRÍTICO: Só valida horários que foram calculados por verificar_horarios_disponiveis
     */
    public function validar_horario_para_agendamento($params = []) {
        error_log("validar_horario_para_agendamento chamada com params: " . json_encode($params));
        
        if (empty($params['data']) || empty($params['hora'])) {
            return ['erro' => 'Data e hora são obrigatórios'];
        }
        
        $data = $params['data'];
        $hora = $this->normalizarHorario($params['hora']);
        
        error_log("Horário normalizado: $hora");
        
        // CRÍTICO: Verifica se o horário foi realmente calculado como disponível
        // Busca horários disponíveis para esta data específica
        $horariosDisponiveis = $this->verificar_horarios_disponiveis(['data' => $data, 'dias' => 1]);
        
        if (empty($horariosDisponiveis)) {
            return ['valido' => false, 'erro' => 'Nenhum horário disponível para esta data'];
        }
        
        // Procura pela data específica nos resultados
        $dataEncontrada = false;
        $horarioEncontrado = false;
        $horariosDisponiveisLista = [];
        
        foreach ($horariosDisponiveis as $dia) {
            if ($dia['data'] === $data) {
                $dataEncontrada = true;
                $horariosDisponiveisLista = $dia['horarios'];
                
                error_log("DEBUG: Verificando horário '$hora' na lista: " . json_encode($dia['horarios']));
                
                // Verifica se o horário específico está na lista de horários disponíveis
                if (in_array($hora, $dia['horarios'])) {
                    $horarioEncontrado = true;
                    error_log("DEBUG: Horário '$hora' encontrado na lista!");
                    break;
                } else {
                    error_log("DEBUG: Horário '$hora' NÃO encontrado na lista!");
                }
            }
        }
        
        if (!$dataEncontrada) {
            return ['valido' => false, 'erro' => 'Data não disponível para agendamento'];
        }
        
        if (!$horarioEncontrado) {
            // Formata horários para exibição
            $horariosFormatados = array_map(function($h) {
                return date('H:i', strtotime($h));
            }, $horariosDisponiveisLista);
            
            return [
                'valido' => false, 
                'mensagem' => 'Horário não disponível',
                'horarios_disponiveis' => $horariosFormatados
            ];
        }
        
        // Busca agendamentos existentes para esta data e hora (dupla verificação)
        $sql = "SELECT COUNT(*) as total FROM agendamentos 
                WHERE data_consulta = ? AND hora_consulta = ? AND status != 'cancelado'";
        $result = $this->db->query($sql, [$data, $hora]);
        
        if (empty($result)) {
            return ['valido' => false, 'erro' => 'Erro ao verificar disponibilidade'];
        }
        
        $totalAgendamentos = $result[0]['total'];
        
        if ($totalAgendamentos > 0) {
            return [
                'valido' => false,
                'erro' => 'Horário já está ocupado',
                'data' => $data,
                'hora' => $hora
            ];
        }
        
        return [
            'valido' => true,
            'mensagem' => 'Horário disponível para agendamento',
            'data' => $data,
            'hora' => $hora
        ];
    }
    
    /**
     * Cancela agendamento existente
     */
    public function cancelar_agendamento($params) {
        error_log("cancelar_agendamento chamada com params: " . json_encode($params));
        
        $required = ['nome_paciente', 'telefone', 'data_consulta', 'hora_consulta'];
        foreach ($required as $field) {
            if (empty($params[$field])) {
                error_log("Campo obrigatório faltando: $field");
                return ['erro' => "Campo $field é obrigatório"];
            }
        }
        
        // Normaliza o horário para garantir compatibilidade
        $horaNormalizada = $this->normalizarHorario($params['hora_consulta']);
        error_log("Horário original: " . $params['hora_consulta'] . ", Normalizado: " . $horaNormalizada);
        
        // Primeiro, verifica se o agendamento existe
        $checkSql = "SELECT a.id, a.status, p.nome, p.telefone, a.hora_consulta 
                     FROM agendamentos a 
                     JOIN pacientes p ON a.paciente_id = p.id 
                     WHERE p.nome LIKE ? AND p.telefone = ? 
                     AND a.data_consulta = ? AND a.hora_consulta = ?";
        
        $checkParams = [
            '%' . $params['nome_paciente'] . '%',
            $params['telefone'],
            $params['data_consulta'],
            $horaNormalizada
        ];
        
        error_log("Verificando se agendamento existe com params: " . json_encode($checkParams));
        $existingAppointment = $this->db->query($checkSql, $checkParams);
        
        if (empty($existingAppointment)) {
            error_log("Nenhum agendamento encontrado para os dados fornecidos");
            return ['erro' => 'Nenhum agendamento encontrado com os dados fornecidos'];
        }
        
        $appointment = $existingAppointment[0];
        error_log("Agendamento encontrado: ID=" . $appointment['id'] . ", Status=" . $appointment['status'] . ", Hora=" . $appointment['hora_consulta']);
        
        if ($appointment['status'] === 'cancelado') {
            error_log("Agendamento já está cancelado");
            return ['erro' => 'Agendamento já está cancelado'];
        }
        
        // Cancela o agendamento
        $sql = "UPDATE agendamentos a 
                JOIN pacientes p ON a.paciente_id = p.id 
                SET a.status = 'cancelado' 
                WHERE p.nome LIKE ? AND p.telefone = ? 
                AND a.data_consulta = ? AND a.hora_consulta = ?";
        
        $sqlParams = [
            '%' . $params['nome_paciente'] . '%',
            $params['telefone'],
            $params['data_consulta'],
            $horaNormalizada
        ];
        
        error_log("Executando SQL de cancelamento: $sql");
        error_log("Parâmetros SQL: " . json_encode($sqlParams));
        
        $rowsAffected = $this->db->execute($sql, $sqlParams);
        error_log("Linhas afetadas no cancelamento: $rowsAffected");
        
        if ($rowsAffected > 0) {
            error_log("Cancelamento realizado com sucesso");
            return ['sucesso' => true];
        } else {
            error_log("Falha ao cancelar agendamento - nenhuma linha afetada");
            return ['erro' => 'Falha ao cancelar agendamento'];
        }
    }
    
    /**
     * Reagenda consulta para nova data/hora
     */
    public function reagendar_consulta($params) {
        error_log("reagendar_consulta chamada com params: " . json_encode($params));
        
        // Validação de parâmetros obrigatórios
        $required = ['nome_paciente', 'telefone', 'data_atual', 'hora_atual', 'nova_data', 'nova_hora'];
        foreach ($required as $field) {
            if (empty($params[$field])) {
                error_log("Campo obrigatório faltando em reagendar_consulta: $field");
                return ['erro' => "Campo $field é obrigatório para reagendamento"];
            }
        }
        
        // Normaliza os horários para garantir compatibilidade
        $horaAtualNormalizada = $this->normalizarHorario($params['hora_atual']);
        $novaHoraNormalizada = $this->normalizarHorario($params['nova_hora']);
        
        error_log("Horários normalizados - Atual: " . $params['hora_atual'] . " -> " . $horaAtualNormalizada);
        error_log("Horários normalizados - Nova: " . $params['nova_hora'] . " -> " . $novaHoraNormalizada);
        
        // Cancela agendamento atual
        $cancelParams = [
            'nome_paciente' => $params['nome_paciente'],
            'telefone' => $params['telefone'],
            'data_consulta' => $params['data_atual'],
            'hora_consulta' => $horaAtualNormalizada
        ];
        error_log("Tentando cancelar agendamento com params: " . json_encode($cancelParams));
        
        $cancelResult = $this->cancelar_agendamento($cancelParams);
        error_log("Resultado do cancelamento: " . json_encode($cancelResult));
        
        if (!$cancelResult['sucesso']) {
            error_log("Falha ao cancelar agendamento atual: " . ($cancelResult['erro'] ?? 'Erro desconhecido'));
            return [
                'erro' => 'Falha ao cancelar agendamento atual: ' . ($cancelResult['erro'] ?? 'Erro desconhecido'),
                'detalhes_cancelamento' => $cancelResult
            ];
        }
        
        // Cria novo agendamento
        $novoAgendamentoParams = [
            'nome' => $params['nome_paciente'],
            'telefone' => $params['telefone'],
            'data' => $params['nova_data'],
            'hora' => $novaHoraNormalizada
        ];
        
        // Passa session_id se disponível
        if (isset($params['session_id'])) {
            $novoAgendamentoParams['session_id'] = $params['session_id'];
        }
        
        error_log("Criando novo agendamento com params: " . json_encode($novoAgendamentoParams));
        $result = $this->criar_agendamento($novoAgendamentoParams);
        error_log("Resultado da criação do novo agendamento: " . json_encode($result));
        
        return $result;
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
     * Busca especialidades dos profissionais ativos
     */
    public function buscar_especialidades_profissionais() {
        $sql = "SELECT DISTINCT especialidade FROM profissionais WHERE ativo = 1 AND especialidade IS NOT NULL AND especialidade != '' ORDER BY especialidade";
        $result = $this->db->query($sql);
        
        $especialidades = [];
        foreach ($result as $row) {
            $especialidades[] = $row['especialidade'];
        }
        
        return $especialidades;
    }
    

    
    /**
     * Busca histórico de conversas para treinamento
     */
    public function buscar_historico_conversas($limit = null) {
        // Limita a 3 exemplos para evitar prompt muito grande
        $limit = $limit ?? 3;
        $sql = "SELECT * FROM conversas_treinamento 
                ORDER BY created_at DESC 
                LIMIT ?";
        
        return $this->db->query($sql, [$limit]);
    }

    public function buscar_exemplos_bons($limit = null) {
        // Limita a 3 exemplos positivos
        $limit = $limit ?? 3;
        $sql = "SELECT * FROM conversas_treinamento 
                WHERE feedback_tipo = 'positivo'
                ORDER BY 
                    CASE 
                        WHEN tipo = 'reescrita' THEN 1  -- Prioriza reescritas
                        ELSE 2 
                    END,
                    created_at DESC
                LIMIT ?";
        
        return $this->db->query($sql, [$limit]);
    }

    public function buscar_respostas_reescritas($limit = null) {
        // Limita a 3 reescritas
        $limit = $limit ?? 3;
        $sql = "SELECT * FROM conversas_treinamento 
                WHERE tipo = 'reescrita'
                ORDER BY created_at DESC
                LIMIT ?";
        
        return $this->db->query($sql, [$limit]);
    }

    /**
     * Busca exemplos de respostas com feedback negativo
     */
    public function buscar_exemplos_ruins($limit = null) {
        // Limita a 3 exemplos negativos
        $limit = $limit ?? 3;
        $sql = "SELECT * FROM conversas_treinamento 
                WHERE feedback_tipo = 'negativo'
                ORDER BY created_at DESC
                LIMIT ?";
        
        return $this->db->query($sql, [$limit]);
    }

    /**
     * Busca a conversa mais recente de uma sessão
     */
    public function buscar_conversa_recente($sessionId) {
        $sql = "SELECT id FROM conversas 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1";
        
        $result = $this->db->query($sql, [$sessionId]);
        return $result[0]['id'] ?? null;
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
    
    private function getDiaSemanaPortugues($data) {
        $dias = [
            'Sunday' => 'Domingo',
            'Monday' => 'Segunda-feira',
            'Tuesday' => 'Terça-feira',
            'Wednesday' => 'Quarta-feira',
            'Thursday' => 'Quinta-feira',
            'Friday' => 'Sexta-feira',
            'Saturday' => 'Sábado'
        ];
        
        $diaSemanaIngles = date('l', strtotime($data));
        return $dias[$diaSemanaIngles];
    }
    
    private function gerarHorarios($inicio, $fim, $intervalo, $ocupados, $dataVerificar = null) {
        try {
            // Validação dos parâmetros
            if (empty($inicio) || empty($fim) || empty($intervalo)) {
                error_log("ERRO: Parâmetros inválidos em gerarHorarios - inicio: $inicio, fim: $fim, intervalo: $intervalo");
                return [];
            }
            
            $horarios = [];
            $current = strtotime($inicio);
            $end = strtotime($fim);
            
            // Validação dos timestamps
            if ($current === false || $end === false) {
                error_log("ERRO: Falha ao converter horários para timestamp - inicio: $inicio, fim: $fim");
                return [];
            }
            
            // Se for hoje, filtra horários que já passaram (com margem de 30 minutos)
            $horaAtual = null;
            if ($dataVerificar && $dataVerificar === date('Y-m-d')) {
                $horaAtual = strtotime(date('H:i:s')) + (30 * 60); // 30 minutos de margem
            }
            
            while ($current <= $end) {
                $hora = date('H:i:s', $current);
                
                // Verifica se o horário não está ocupado e não passou (se for hoje)
                if (!in_array($hora, $ocupados)) {
                    if ($horaAtual === null || $current > $horaAtual) {
                        $horarios[] = $hora;
                        error_log("DEBUG: Horário gerado: $hora (inicio: $inicio, fim: $fim, intervalo: $intervalo)");
                    }
                } else {
                    error_log("DEBUG: Horário ocupado: $hora");
                }
                $current += ($intervalo * 60);
            }
            
            return $horarios;
            
        } catch (\Exception $e) {
            error_log("ERRO em gerarHorarios: " . $e->getMessage());
            throw $e;
        }
    }
    
    private function getOrCreatePaciente($nome, $telefone, $sessionId = null) {
        // Validação adicional para garantir que o telefone não seja vazio
        if (empty($telefone) || trim($telefone) === '') {
            throw new \Exception('Telefone é obrigatório para criar paciente');
        }
        
        $sql = "SELECT id FROM pacientes WHERE telefone = ?";
        $result = $this->db->query($sql, [$telefone]);
        
        if (!empty($result)) {
            // Se o paciente existe mas não tem session_id, atualiza
            if ($sessionId) {
                $updateSql = "UPDATE pacientes SET session_id = ? WHERE id = ? AND session_id IS NULL";
                $this->db->execute($updateSql, [$sessionId, $result[0]['id']]);
            }
            
            return $result[0]['id'];
        }
        
        $sql = "INSERT INTO pacientes (nome, telefone, session_id) VALUES (?, ?, ?)";
        $this->db->execute($sql, [$nome, $telefone, $sessionId]);
        
        return $this->db->lastInsertId();
    }
    
    /**
     * Normaliza horário para formato padrão HH:MM:SS
     */
    private function normalizarHorario($hora) {
        // Remove espaços e converte para minúsculas
        $hora = trim(strtolower($hora));
        
        // Remove "h" ou "hr" do final
        $hora = preg_replace('/\s*h(r)?\s*$/i', '', $hora);
        
        // Se já está no formato HH:MM:SS, retorna como está
        if (preg_match('/^\d{2}:\d{2}:\d{2}$/', $hora)) {
            return $hora;
        }
        
        // Se está no formato HH:MM, adiciona :00
        if (preg_match('/^\d{2}:\d{2}$/', $hora)) {
            return $hora . ':00';
        }
        
        // Se está no formato HH, adiciona :00:00
        if (preg_match('/^\d{1,2}$/', $hora)) {
            // Garante que tenha 2 dígitos
            $hora = str_pad($hora, 2, '0', STR_PAD_LEFT);
            return $hora . ':00:00';
        }
        
        // Se não conseguiu normalizar, tenta converter com strtotime
        $timestamp = strtotime($hora);
        if ($timestamp !== false) {
            return date('H:i:s', $timestamp);
        }
        
        // Se tudo falhar, retorna o original
        error_log("ERRO: Não foi possível normalizar o horário: $hora");
        return $hora;
    }
    
    /**
     * Busca estado do agendamento para uma sessão específica
     */
    public function buscar_estado_agendamento($sessionId) {
        try {
            if (empty($sessionId)) {
                return null;
            }
            
            // Busca agendamentos ativos para esta sessão
            $sql = "SELECT a.*, p.nome as nome_paciente, p.telefone as telefone_paciente 
                    FROM agendamentos a 
                    LEFT JOIN pacientes p ON a.paciente_id = p.id 
                    WHERE a.session_id = ? AND a.status = 'ativo' 
                    ORDER BY a.data_consulta ASC, a.hora_consulta ASC 
                    LIMIT 1";
            
            $result = $this->db->query($sql, [$sessionId]);
            
            if (!empty($result)) {
                $agendamento = $result[0];
                return [
                    'id' => $agendamento['id'],
                    'nome_paciente' => $agendamento['nome_paciente'],
                    'telefone_paciente' => $agendamento['telefone_paciente'],
                    'data_consulta' => $agendamento['data_consulta'],
                    'hora_consulta' => $agendamento['hora_consulta'],
                    'status' => $agendamento['status'],
                    'observacoes' => $agendamento['observacoes'] ?? null
                ];
            }
            
            return null;
        } catch (\Exception $e) {
            error_log("ERRO em buscar_estado_agendamento: " . $e->getMessage());
            return null;
        }
    }
}