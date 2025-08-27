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
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        // Buscar todos os profissionais
        $stmt = $pdo->prepare("SELECT * FROM profissionais ORDER BY nome");
        $stmt->execute();
        $profissionais = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'profissionais' => $profissionais
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Criar novo profissional
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['nome'])) {
            throw new Exception('Nome é obrigatório');
        }
        
        $stmt = $pdo->prepare("INSERT INTO profissionais (nome, especialidade, crm, ativo) VALUES (?, ?, ?, ?)");
        $stmt->execute([
            $input['nome'],
            $input['especialidade'] ?? null,
            $input['crm'] ?? null,
            $input['ativo'] ?? 1
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Profissional criado com sucesso',
            'id' => $pdo->lastInsertId()
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar profissional (suporte a atualizações parciais)
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        // Construir query dinamicamente baseada nos campos fornecidos
        $updateFields = [];
        $params = [];
        
        if (isset($input['nome'])) {
            $updateFields[] = 'nome = ?';
            $params[] = $input['nome'];
        }
        
        if (isset($input['especialidade'])) {
            $updateFields[] = 'especialidade = ?';
            $params[] = $input['especialidade'];
        }
        
        if (isset($input['crm'])) {
            $updateFields[] = 'crm = ?';
            $params[] = $input['crm'];
        }
        
        if (isset($input['ativo'])) {
            $updateFields[] = 'ativo = ?';
            $params[] = $input['ativo'];
        }
        
        if (empty($updateFields)) {
            throw new Exception('Nenhum campo para atualizar foi fornecido');
        }
        
        $params[] = $input['id']; // ID para WHERE
        
        $sql = "UPDATE profissionais SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        
        echo json_encode([
            'success' => true,
            'message' => 'Profissional atualizado com sucesso'
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Excluir profissional
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        $stmt = $pdo->prepare("DELETE FROM profissionais WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Profissional excluído com sucesso'
        ]);
        
    } else {
        throw new Exception('Método não permitido');
    }
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
} 