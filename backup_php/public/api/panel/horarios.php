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
        // Buscar todos os horários
        $stmt = $pdo->prepare("
            SELECT h.*, p.nome as profissional_nome 
            FROM horarios_disponiveis h 
            LEFT JOIN profissionais p ON h.profissional_id = p.id 
            ORDER BY h.dia_semana, h.manha_inicio
        ");
        $stmt->execute();
        $horarios = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo json_encode([
            'success' => true,
            'horarios' => $horarios
        ]);
        

    } elseif ($_SERVER['REQUEST_METHOD'] === 'PUT') {
        // Atualizar horário (suporte a atualizações parciais)
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID é obrigatório');
        }
        
        // Função para converter horários vazios ou 00:00 para NULL
        $prepareTime = function($time) {
            return (empty($time) || $time === '00:00' || $time === '00:00:00' ? null : $time);
        };
        
        // Construir query dinamicamente baseada nos campos fornecidos
        $updateFields = [];
        $params = [];
        
        if (isset($input['dia_semana'])) {
            $updateFields[] = 'dia_semana = ?';
            $params[] = $input['dia_semana'];
        }
        
        // Sempre incluir campos de horário, mesmo quando vazios
        $updateFields[] = 'manha_inicio = ?';
        $params[] = $prepareTime($input['manha_inicio'] ?? '');
        
        $updateFields[] = 'manha_fim = ?';
        $params[] = $prepareTime($input['manha_fim'] ?? '');
        
        $updateFields[] = 'tarde_inicio = ?';
        $params[] = $prepareTime($input['tarde_inicio'] ?? '');
        
        $updateFields[] = 'tarde_fim = ?';
        $params[] = $prepareTime($input['tarde_fim'] ?? '');
        
        // Sempre incluir intervalo_minutos, mesmo quando vazio
        $updateFields[] = 'intervalo_minutos = ?';
        $params[] = (empty($input['intervalo_minutos']) || $input['intervalo_minutos'] === '' ? null : $input['intervalo_minutos']);
        
        if (isset($input['ativo'])) {
            $updateFields[] = 'ativo = ?';
            $params[] = $input['ativo'];
        }
        
        if (isset($input['profissional_id'])) {
            $updateFields[] = 'profissional_id = ?';
            $params[] = $input['profissional_id'];
        }
        
        // Sempre teremos pelo menos os campos de horário, então não precisamos verificar se está vazio
        
        // Adicionar ID para WHERE
        $params[] = $input['id']; // ID para WHERE
        
        $sql = "UPDATE horarios_disponiveis SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        
        echo json_encode([
            'success' => true,
            'message' => 'Horário atualizado com sucesso'
        ]);
        
    } elseif ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
        // Deletar horário
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['id'])) {
            throw new Exception('ID do horário é obrigatório');
        }
        
        $stmt = $pdo->prepare("DELETE FROM horarios_disponiveis WHERE id = ?");
        $stmt->execute([$input['id']]);
        
        if ($stmt->rowCount() === 0) {
            throw new Exception('Horário não encontrado');
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'Horário deletado com sucesso'
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