<?php
namespace App\Services;

use App\Config\Database;
use PDO;

class DatabaseService {
    private $db;
    
    public function __construct() {
        $this->db = Database::getConnection();
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
            $stmt->execute($params);
            return $stmt->rowCount();
        } catch (\Exception $e) {
            $this->logError('execute_error', $e->getMessage());
            return 0;
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