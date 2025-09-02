<?php
ini_set('display_errors', 0);
error_reporting(0);

// Carrega o autoloader do Composer
require_once __DIR__ . '/../../../vendor/autoload.php';

// Carrega as variáveis de ambiente
$envPath = __DIR__ . '/../../../.env';
if (file_exists($envPath)) {
    $dotenv = Dotenv\Dotenv::createImmutable(__DIR__ . '/../../../');
    $dotenv->load();
}

// Usa a classe Database para conexão
use App\Config\Database;

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    $pdo = Database::getConnection();
    
    // Teste de conexão
    $pdo->query('SELECT 1');
    
    // Verificar se as tabelas existem
    $tables = ['configuracoes', 'profissionais', 'servicos_clinica', 'convenios_aceitos', 
               'horarios_disponiveis', 'excecoes_agenda', 'faq', 'formas_pagamento', 'parceiros'];
    
    $existingTables = [];
    $missingTables = [];
    
    foreach ($tables as $table) {
        try {
            $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
            if ($stmt->rowCount() > 0) {
                $existingTables[] = $table;
            } else {
                $missingTables[] = $table;
            }
        } catch (Exception $e) {
            $missingTables[] = $table;
        }
    }
    
    echo json_encode([
        'success' => true,
        'message' => 'Conexão com banco de dados estabelecida',
        'database' => $dbname,
        'existing_tables' => $existingTables,
        'missing_tables' => $missingTables
    ]);
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'message' => 'Erro na conexão: ' . $e->getMessage(),
        'error_type' => get_class($e)
    ]);
} 