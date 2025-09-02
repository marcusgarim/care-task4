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

// Verificar se a coluna ativo existe, se não, criar
try {
    $stmt = $pdo->query("SHOW COLUMNS FROM excecoes_agenda LIKE 'ativo'");
    if ($stmt->rowCount() == 0) {
        $pdo->exec("ALTER TABLE excecoes_agenda ADD COLUMN ativo TINYINT(1) DEFAULT 1");
    }
} catch (Exception $e) {
    // Ignora erro se a tabela não existir
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
        // Buscar todas as exceções (incluindo inativas para edição)
        $stmt = $pdo->prepare("SELECT * FROM excecoes_agenda ORDER BY data DESC");
        $stmt->execute();
        $excecoes = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'excecoes' => $excecoes
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Criar nova exceção
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['data']) || !isset($input['tipo'])) {
            throw new Exception('Data e tipo são obrigatórios');
        }
        
        // Verificar se já existe uma exceção ativa com a mesma data
        $checkStmt = $pdo->prepare("
            SELECT COUNT(*) as count 
            FROM excecoes_agenda 
            WHERE data = ? AND ativo = 1
        ");
        $checkStmt->execute([$input['data']]);
        $existingCount = $checkStmt->fetch()['count'];
        
        if ($existingCount > 0) {
            throw new Exception('Já existe uma exceção ativa para esta data.');
        }
        
        $stmt = $pdo->prepare("
            INSERT INTO excecoes_agenda (
                data, tipo, descricao, ativo
            ) VALUES (?, ?, ?, ?)
        ");
        
        $stmt->execute([
            $input['data'],
            $input['tipo'],
            $input['descricao'] ?? null,
            $input['ativo'] ?? 1
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Exceção criada com sucesso',
            'id' => $pdo->lastInsertId()
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar exceção existente
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        // Se apenas ativo foi enviado, é um soft delete
        if (count($input) === 2 && isset($input['ativo'])) {
            $stmt = $pdo->prepare("UPDATE excecoes_agenda SET ativo = ? WHERE id = ?");
            $stmt->execute([$input['ativo'], $input['id']]);
        } else {
            // Atualização completa
            if (!isset($input['data']) || !isset($input['tipo'])) {
                throw new Exception('Data e tipo são obrigatórios');
            }
            
            // Verificar se já existe outra exceção ativa com a mesma data (excluindo a atual)
            $checkStmt = $pdo->prepare("
                SELECT COUNT(*) as count 
                FROM excecoes_agenda 
                WHERE data = ? AND ativo = 1 AND id != ?
            ");
            $checkStmt->execute([$input['data'], $input['id']]);
            $existingCount = $checkStmt->fetch()['count'];
            
            if ($existingCount > 0) {
                throw new Exception('Já existe uma exceção ativa para esta data. Desative a exceção existente primeiro.');
            }
            
            $stmt = $pdo->prepare("
                UPDATE excecoes_agenda SET 
                    data = ?, tipo = ?, descricao = ?, ativo = ?
                WHERE id = ?
            ");
            
            $stmt->execute([
                $input['data'],
                $input['tipo'],
                $input['descricao'] ?? null,
                $input['ativo'] ?? 1,
                $input['id']
            ]);
        }
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('Exceção não encontrada');
        }
        
        $message = isset($input['ativo']) && $input['ativo'] == 0 ? 
            'Exceção desativada com sucesso' : 'Exceção atualizada com sucesso';
        
        echo json_encode([
            'success' => true,
            'message' => $message
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Deletar exceção (soft delete)
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID da exceção é obrigatório');
        }
        
        $stmt = $pdo->prepare("UPDATE excecoes_agenda SET ativo = 0 WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('Exceção não encontrada');
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'Exceção desativada com sucesso'
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