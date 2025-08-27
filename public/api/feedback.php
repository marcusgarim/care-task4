<?php
require_once '../../vendor/autoload.php';

use Dotenv\Dotenv;
use App\Services\DatabaseService;
use App\Services\AgentFunctions;

// Carrega variáveis de ambiente
$dotenv = Dotenv::createImmutable(dirname(__DIR__, 2));
$dotenv->load();

// Headers
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Apenas POST é permitido
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Método não permitido']);
    exit;
}

// Recebe dados
$input = json_decode(file_get_contents('php://input'), true);

if (!isset($input['messageId']) || !isset($input['feedbackType']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}

try {
    $db = new DatabaseService();
    $functions = new AgentFunctions();
    
    // Busca a conversa mais recente desta sessão usando a função centralizada
    $conversaId = $functions->buscar_conversa_recente($input['sessionId']);
    
    if ($conversaId) {
        // SALVA APENAS NA TABELA conversas_treinamento
        $sql = "INSERT INTO conversas_treinamento 
                (conversa_id, tipo, resposta_original, contexto_conversa, feedback_tipo) 
                SELECT id, ?, resposta_agente, mensagem_usuario, ? 
                FROM conversas WHERE id = ?";
        
        $tipo = $input['feedbackType'] === 'positivo' ? 'feedback_positivo' : 'feedback_negativo';
        $db->execute($sql, [$tipo, $input['feedbackType'], $conversaId]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Feedback registrado com sucesso'
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Conversa não encontrada'
        ]);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Erro ao registrar feedback'
    ]);
}