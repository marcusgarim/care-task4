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

if (!isset($input['messageId']) || !isset($input['rewrittenText']) || !isset($input['sessionId'])) {
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
        // Quando uma resposta é reescrita, criamos apenas o registro da reescrita
        // O feedback negativo será criado automaticamente pelo JavaScript (chat.js)
        
        // Registro: Resposta reescrita com feedback positivo
        $sql = "INSERT INTO conversas_treinamento 
                (conversa_id, tipo, resposta_original, resposta_reescrita, contexto_conversa, feedback_tipo) 
                SELECT id, 'reescrita', resposta_agente, ?, mensagem_usuario, 'positivo' 
                FROM conversas WHERE id = ?";
        
        $db->execute($sql, [$input['rewrittenText'], $conversaId]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Resposta reescrita salva com sucesso'
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
        'error' => 'Erro ao salvar resposta reescrita'
    ]);
}