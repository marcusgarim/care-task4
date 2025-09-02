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

try {
    $pdo = Database::getConnection();
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Erro na conexão com banco de dados']);
    exit;
}

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        // Buscar todas as configurações
        $stmt = $pdo->prepare("SELECT chave, valor FROM configuracoes ORDER BY id");
        $stmt->execute();
        $configuracoes = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'configuracoes' => $configuracoes
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Atualizar configurações
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input) {
            throw new Exception('Dados inválidos');
        }
        
        $pdo->beginTransaction();
        
        foreach ($input as $chave => $valor) {
            $stmt = $pdo->prepare("UPDATE configuracoes SET valor = ?, updated_at = NOW() WHERE chave = ?");
            $stmt->execute([$valor, $chave]);
        }
        
        $pdo->commit();
        
        echo json_encode([
            'success' => true,
            'message' => 'Configurações atualizadas com sucesso'
        ]);
        
    } else {
        throw new Exception('Método não permitido');
    }
    
} catch (Exception $e) {
    if (isset($pdo)) {
        $pdo->rollBack();
    }
    
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
} 