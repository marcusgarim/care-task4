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
    $stmt = $pdo->query("SHOW COLUMNS FROM faq LIKE 'ativo'");
    if ($stmt->rowCount() == 0) {
        $pdo->exec("ALTER TABLE faq ADD COLUMN ativo TINYINT(1) DEFAULT 1");
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
        // Buscar todas as FAQs (incluindo inativas para edição)
        $stmt = $pdo->prepare("SELECT * FROM faq ORDER BY categoria, pergunta");
        $stmt->execute();
        $faqs = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'faqs' => $faqs
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Criar nova FAQ
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['pergunta']) || !isset($input['resposta'])) {
            throw new Exception('Pergunta e resposta são obrigatórias');
        }
        
        $stmt = $pdo->prepare("
            INSERT INTO faq (
                pergunta, resposta, categoria, palavras_chave, ativo
            ) VALUES (?, ?, ?, ?, ?)
        ");
        
        $stmt->execute([
            $input['pergunta'],
            $input['resposta'],
            $input['categoria'] ?? null,
            $input['palavras_chave'] ?? null,
            $input['ativo'] ?? 1
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'FAQ criada com sucesso',
            'id' => $pdo->lastInsertId()
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar FAQ existente
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        // Se apenas ativo foi enviado, é um soft delete
        if (count($input) === 2 && isset($input['ativo'])) {
            $stmt = $pdo->prepare("UPDATE faq SET ativo = ? WHERE id = ?");
            $stmt->execute([$input['ativo'], $input['id']]);
        } else {
            // Atualização completa
            if (!isset($input['pergunta']) || !isset($input['resposta'])) {
                throw new Exception('Pergunta e resposta são obrigatórias');
            }
            
            $stmt = $pdo->prepare("
                UPDATE faq SET 
                    pergunta = ?, resposta = ?, categoria = ?, palavras_chave = ?, ativo = ?
                WHERE id = ?
            ");
            
            $stmt->execute([
                $input['pergunta'],
                $input['resposta'],
                $input['categoria'] ?? null,
                $input['palavras_chave'] ?? null,
                $input['ativo'] ?? 1,
                $input['id']
            ]);
        }
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('FAQ não encontrada');
        }
        
        $message = isset($input['ativo']) && $input['ativo'] == 0 ? 
            'FAQ desativada com sucesso' : 'FAQ atualizada com sucesso';
        
        echo json_encode([
            'success' => true,
            'message' => $message
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Deletar FAQ (soft delete)
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID da FAQ é obrigatório');
        }
        
        $stmt = $pdo->prepare("UPDATE faq SET ativo = 0 WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('FAQ não encontrada');
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'FAQ desativada com sucesso'
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