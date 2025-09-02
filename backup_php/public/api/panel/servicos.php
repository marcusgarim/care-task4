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
        // Se há um ID na query string, buscar serviço específico
        if (isset($_GET['id'])) {
            error_log("Buscando serviço com ID: " . $_GET['id']);
            
            $stmt = $pdo->prepare("SELECT * FROM servicos_clinica WHERE id = ?");
            $stmt->execute([$_GET['id']]);
            $servico = $stmt->fetch(PDO::FETCH_ASSOC);
            
            error_log("Serviço encontrado: " . ($servico ? 'sim' : 'não'));
            if ($servico) {
                error_log("Dados do serviço: " . json_encode($servico));
            }
            
            if ($servico) {
                echo json_encode([
                    'success' => true,
                    'servico' => $servico
                ]);
            } else {
                echo json_encode([
                    'success' => false,
                    'message' => 'Serviço não encontrado'
                ]);
            }
        } else {
            // Buscar todos os serviços
            $stmt = $pdo->prepare("SELECT * FROM servicos_clinica ORDER BY nome");
            $stmt->execute();
            $servicos = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            echo json_encode([
                'success' => true,
                'servicos' => $servicos
            ]);
        }
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Criar novo serviço
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['nome'])) {
            throw new Exception('Nome do serviço é obrigatório');
        }
        
        $stmt = $pdo->prepare("
            INSERT INTO servicos_clinica (
                nome, descricao, valor, ativo, 
                palavras_chave, categoria, observacoes, 
                preparo_necessario, anestesia_tipo, local_realizacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        
        $stmt->execute([
            $input['nome'],
            $input['descricao'] ?? null,
            $input['valor'] === '' ? null : ($input['valor'] ?? null),
            $input['ativo'] ?? 1,
            $input['palavras_chave'] ?? null,
            $input['categoria'] ?? null,
            $input['observacoes'] ?? null,
            $input['preparo_necessario'] ?? null,
            $input['anestesia_tipo'] ?? null,
            $input['local_realizacao'] ?? null
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Serviço criado com sucesso',
            'id' => $pdo->lastInsertId()
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar serviço (suporte a atualizações parciais)
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        // Construir query dinamicamente baseada nos campos fornecidos
        $updateFields = [];
        $params = [];
        
        if (array_key_exists('nome', $input)) {
            $updateFields[] = 'nome = ?';
            $params[] = $input['nome'] === '' ? null : $input['nome'];
        }
        
        if (array_key_exists('descricao', $input)) {
            $updateFields[] = 'descricao = ?';
            $params[] = $input['descricao'] === '' ? null : $input['descricao'];
        }
        
        if (array_key_exists('valor', $input)) {
            $updateFields[] = 'valor = ?';
            $params[] = $input['valor'] === '' ? null : $input['valor'];
        }
        
        if (array_key_exists('ativo', $input)) {
            $updateFields[] = 'ativo = ?';
            $params[] = $input['ativo'] === '' ? null : $input['ativo'];
        }
        
        if (array_key_exists('palavras_chave', $input)) {
            $updateFields[] = 'palavras_chave = ?';
            $params[] = $input['palavras_chave'] === '' ? null : $input['palavras_chave'];
        }
        
        if (array_key_exists('categoria', $input)) {
            $updateFields[] = 'categoria = ?';
            $params[] = $input['categoria'] === '' ? null : $input['categoria'];
        }
        
        if (array_key_exists('observacoes', $input)) {
            $updateFields[] = 'observacoes = ?';
            $params[] = $input['observacoes'] === '' ? null : $input['observacoes'];
        }
        
        if (array_key_exists('preparo_necessario', $input)) {
            $updateFields[] = 'preparo_necessario = ?';
            $params[] = $input['preparo_necessario'] === '' ? null : $input['preparo_necessario'];
        }
        
        if (array_key_exists('anestesia_tipo', $input)) {
            $updateFields[] = 'anestesia_tipo = ?';
            $params[] = $input['anestesia_tipo'] === '' ? null : $input['anestesia_tipo'];
        }
        
        if (array_key_exists('local_realizacao', $input)) {
            $updateFields[] = 'local_realizacao = ?';
            $params[] = $input['local_realizacao'] === '' ? null : $input['local_realizacao'];
        }
        
        if (empty($updateFields)) {
            throw new Exception('Nenhum campo para atualizar foi fornecido');
        }
        
        // Adicionar updated_at e ID para WHERE
        $updateFields[] = 'updated_at = NOW()';
        $params[] = $input['id']; // ID para WHERE
        
        $sql = "UPDATE servicos_clinica SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        
        echo json_encode([
            'success' => true,
            'message' => 'Serviço atualizado com sucesso'
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Deletar serviço
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID do serviço é obrigatório');
        }
        
        $stmt = $pdo->prepare("DELETE FROM servicos_clinica WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('Serviço não encontrado');
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'Serviço deletado com sucesso'
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