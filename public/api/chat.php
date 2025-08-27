<?php
require_once '../../vendor/autoload.php';

use Dotenv\Dotenv;
use App\Controllers\ChatController;

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

if (!isset($input['message']) || !isset($input['sessionId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Dados inválidos']);
    exit;
}

try {
    // Processa mensagem
    $chatController = new ChatController();
    $response = $chatController->processMessage(
        $input['message'],
        $input['sessionId'],
        $input['isFirst'] ?? false
    );
    
    echo json_encode($response);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Erro interno do servidor',
        'message' => 'Desculpe, ocorreu um erro. Por favor, tente novamente.'
    ]);
}