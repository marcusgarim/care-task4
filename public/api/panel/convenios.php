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
        // Buscar todos os convênios
        $stmt = $pdo->prepare("SELECT * FROM convenios_aceitos ORDER BY nome");
        $stmt->execute();
        $convenios = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'convenios' => $convenios
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Criar novo convênio
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['nome'])) {
            throw new Exception('Nome do convênio é obrigatório');
        }
        
        $stmt = $pdo->prepare("
            INSERT INTO convenios_aceitos (
                nome, registro_ans, observacoes, ativo
            ) VALUES (?, ?, ?, ?)
        ");
        
        $stmt->execute([
            $input['nome'],
            $input['registro_ans'] ?? null,
            $input['observacoes'] ?? null,
            1 // Sempre ativo ao criar
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Convênio criado com sucesso',
            'id' => $pdo->lastInsertId()
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar convênio (suporte a atualizações parciais)
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
        
        if (isset($input['registro_ans'])) {
            $updateFields[] = 'registro_ans = ?';
            $params[] = $input['registro_ans'];
        }
        
        if (isset($input['observacoes'])) {
            $updateFields[] = 'observacoes = ?';
            $params[] = $input['observacoes'];
        }
        
        if (isset($input['ativo'])) {
            $updateFields[] = 'ativo = ?';
            $params[] = $input['ativo'];
        }
        
        if (empty($updateFields)) {
            throw new Exception('Nenhum campo para atualizar foi fornecido');
        }
        
        // Adicionar updated_at e ID para WHERE
        $updateFields[] = 'updated_at = NOW()';
        $params[] = $input['id']; // ID para WHERE
        
        $sql = "UPDATE convenios_aceitos SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        
        echo json_encode([
            'success' => true,
            'message' => 'Convênio atualizado com sucesso'
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Deletar convênio
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID do convênio é obrigatório');
        }
        
        $stmt = $pdo->prepare("DELETE FROM convenios_aceitos WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('Convênio não encontrado');
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'Convênio deletado com sucesso'
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