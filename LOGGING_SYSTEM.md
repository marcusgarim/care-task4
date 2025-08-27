# Sistema de Logging para OpenAI

## Visão Geral

O sistema foi atualizado para usar um sistema de logging personalizado que salva todos os logs da IA em um arquivo específico na raiz do sistema: `openai_debug.log`.

## Arquivos Criados/Modificados

### 1. `src/Services/LoggerService.php` (NOVO)
- Classe singleton para gerenciar logs
- Salva logs em arquivo com timestamp e níveis
- Mantém compatibilidade com `error_log()` existente

### 2. `src/Services/OpenAIService.php` (MODIFICADO)
- Substituído todos os `error_log()` por chamadas ao `LoggerService`
- Adicionado propriedade `$logger` na classe
- Inicializado o logger no construtor

### 3. `openai_debug.log` (NOVO)
- Arquivo de log na raiz do sistema
- Contém todos os logs da IA com timestamps
- Formato estruturado e legível

## Como Funciona

### Estrutura do Log
```
[2024-01-15 10:30:15] [DEBUG] Mensagem do log
[2024-01-15 10:30:15] [INFO] Informação importante
[2024-01-15 10:30:15] [WARN] Aviso
[2024-01-15 10:30:15] [ERROR] Erro crítico
```

### Níveis de Log Disponíveis
- **DEBUG**: Informações detalhadas para depuração
- **INFO**: Informações gerais do sistema
- **WARN**: Avisos que não são erros críticos
- **ERROR**: Erros que precisam de atenção

### Métodos do LoggerService
```php
$logger = LoggerService::getInstance();

$logger->debug('Mensagem de debug');
$logger->info('Informação importante');
$logger->warn('Aviso');
$logger->error('Erro crítico');
$logger->log('Mensagem customizada', 'CUSTOM_LEVEL');
```

## O que é Logado

### 1. Requisições para a IA
- Modelo usado
- Payload enviado
- Configurações da requisição

### 2. Respostas da IA
- Resposta completa (raw)
- Resposta decodificada
- Uso de tokens
- Function calls detectadas

### 3. Processamento de Funções
- Funções chamadas
- Argumentos processados
- Resultados das funções

### 4. Tratamento de Erros
- Erros HTTP
- Exceções inesperadas
- Falhas após múltiplas tentativas

### 5. Filtros e Limpeza
- Conteúdo antes e depois dos filtros
- Respostas malformadas detectadas
- Fallbacks utilizados

## Localização do Arquivo

O arquivo de log está localizado em:
```
/raiz_do_projeto/openai_debug.log
```

## Monitoramento

### Verificar Tamanho do Log
```php
$logger = LoggerService::getInstance();
$size = $logger->getLogSize(); // Retorna tamanho em bytes
```

### Limpar Log
```php
$logger = LoggerService::getInstance();
$logger->clearLog(); // Remove o arquivo de log
```

### Obter Caminho do Log
```php
$logger = LoggerService::getInstance();
$path = $logger->getLogFilePath(); // Retorna caminho completo
```

## Vantagens do Novo Sistema

1. **Centralização**: Todos os logs da IA em um local
2. **Estruturação**: Formato consistente com timestamps
3. **Níveis**: Diferentes níveis para diferentes tipos de informação
4. **Performance**: Escrita otimizada com lock de arquivo
5. **Compatibilidade**: Mantém logs no error_log para compatibilidade
6. **Manutenibilidade**: Fácil de filtrar e analisar

## Exemplo de Uso

```php
// O sistema automaticamente loga tudo
$openaiService = new OpenAIService();
$response = $openaiService->chat($messages, $functions);

// Os logs são salvos automaticamente em openai_debug.log
// Você pode monitorar o arquivo em tempo real:
// tail -f openai_debug.log
```

## Próximos Passos Sugeridos

1. **Rotação de Logs**: Implementar rotação automática para evitar arquivos muito grandes
2. **Níveis Configuráveis**: Permitir configurar quais níveis de log são salvos
3. **Compressão**: Comprimir logs antigos para economizar espaço
4. **Alertas**: Implementar alertas para erros críticos
5. **Dashboard**: Criar interface web para visualizar logs
