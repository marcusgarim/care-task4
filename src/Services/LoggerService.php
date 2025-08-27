<?php
namespace App\Services;

class LoggerService {
    private $logFile;
    private static $instance = null;
    
    private function __construct() {
        $this->logFile = __DIR__ . '/../../openai_debug.log';
    }
    
    public static function getInstance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    public function log($message, $level = 'DEBUG') {
        $timestamp = date('Y-m-d H:i:s');
        $formattedMessage = "[{$timestamp}] [{$level}] {$message}" . PHP_EOL;
        
        // Garante que o diretório existe
        $logDir = dirname($this->logFile);
        if (!is_dir($logDir)) {
            mkdir($logDir, 0755, true);
        }
        
        // Escreve no arquivo de log
        file_put_contents($this->logFile, $formattedMessage, FILE_APPEND | LOCK_EX);
        
        // Também mantém o error_log para compatibilidade
        error_log("[OPENAI DEBUG] {$message}");
    }
    
    public function debug($message) {
        $this->log($message, 'DEBUG');
    }
    
    public function info($message) {
        $this->log($message, 'INFO');
    }
    
    public function warn($message) {
        $this->log($message, 'WARN');
    }
    
    public function error($message) {
        $this->log($message, 'ERROR');
    }
    
    public function getLogFilePath() {
        return $this->logFile;
    }
    
    public function clearLog() {
        if (file_exists($this->logFile)) {
            unlink($this->logFile);
        }
    }
    
    public function getLogSize() {
        if (file_exists($this->logFile)) {
            return filesize($this->logFile);
        }
        return 0;
    }
}
