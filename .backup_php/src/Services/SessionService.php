<?php

namespace App\Services;

class SessionService
{
    private $sessionId;
    
    public function __construct($sessionId = null)
    {
        // Inicia a sessão se não estiver ativa
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        
        $this->sessionId = $sessionId;
    }
    
    /**
     * Salva dados do paciente na sessão
     */
    public function salvarDadosPaciente($nome, $telefone)
    {
        $sessionKey = "paciente_{$this->sessionId}";
        $_SESSION[$sessionKey] = [
            'nome' => $nome,
            'telefone' => $telefone,
            'timestamp' => time()
        ];
        
        error_log("SessionService: Dados do paciente salvos - Nome: $nome, Telefone: $telefone");
        return true;
    }
    
    /**
     * Recupera dados do paciente da sessão
     */
    public function recuperarDadosPaciente()
    {
        $sessionKey = "paciente_{$this->sessionId}";
        
        if (isset($_SESSION[$sessionKey])) {
            $dados = $_SESSION[$sessionKey];
            error_log("SessionService: Dados do paciente recuperados - Nome: {$dados['nome']}, Telefone: {$dados['telefone']}");
            return $dados;
        }
        
        error_log("SessionService: Nenhum dado do paciente encontrado para sessionId: {$this->sessionId}");
        return null;
    }
    
    /**
     * Verifica se já tem dados do paciente
     */
    public function temDadosPaciente()
    {
        $sessionKey = "paciente_{$this->sessionId}";
        return isset($_SESSION[$sessionKey]);
    }
    
    /**
     * Salva etapa atual do agendamento
     */
    public function salvarEtapaAgendamento($etapa, $dadosAdicionais = [])
    {
        $sessionKey = "agendamento_{$this->sessionId}";
        $_SESSION[$sessionKey] = array_merge([
            'etapa' => $etapa,
            'timestamp' => time()
        ], $dadosAdicionais);
        
        error_log("SessionService: Etapa do agendamento salva - Etapa: $etapa");
        return true;
    }
    
    /**
     * Recupera etapa atual do agendamento
     */
    public function recuperarEtapaAgendamento()
    {
        $sessionKey = "agendamento_{$this->sessionId}";
        
        if (isset($_SESSION[$sessionKey])) {
            $dados = $_SESSION[$sessionKey];
            error_log("SessionService: Etapa do agendamento recuperada - Etapa: {$dados['etapa']}");
            return $dados;
        }
        
        return null;
    }
    
    /**
     * Limpa dados da sessão
     */
    public function limparDados()
    {
        $pacienteKey = "paciente_{$this->sessionId}";
        $agendamentoKey = "agendamento_{$this->sessionId}";
        
        unset($_SESSION[$pacienteKey]);
        unset($_SESSION[$agendamentoKey]);
        
        error_log("SessionService: Dados da sessão limpos para sessionId: {$this->sessionId}");
        return true;
    }
    
    /**
     * Verifica se a sessão expirou (mais de 1 hora)
     */
    public function sessaoExpirada()
    {
        $pacienteKey = "paciente_{$this->sessionId}";
        $agendamentoKey = "agendamento_{$this->sessionId}";
        
        $tempoLimite = 3600; // 1 hora em segundos
        
        if (isset($_SESSION[$pacienteKey])) {
            $dados = $_SESSION[$pacienteKey];
            if ((time() - $dados['timestamp']) > $tempoLimite) {
                error_log("SessionService: Sessão expirada para sessionId: {$this->sessionId}");
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Atualiza timestamp da sessão
     */
    public function atualizarTimestamp()
    {
        $pacienteKey = "paciente_{$this->sessionId}";
        $agendamentoKey = "agendamento_{$this->sessionId}";
        
        if (isset($_SESSION[$pacienteKey])) {
            $_SESSION[$pacienteKey]['timestamp'] = time();
        }
        
        if (isset($_SESSION[$agendamentoKey])) {
            $_SESSION[$agendamentoKey]['timestamp'] = time();
        }
        
        return true;
    }
} 