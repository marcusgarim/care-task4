# Implementação do Sistema de Sessão PHP

## Visão Geral

Esta implementação resolve o problema de repetição de perguntas sobre dados do paciente durante a conversa, utilizando sessões PHP para armazenar temporariamente os dados coletados.

## Arquivos Modificados/Criados

### 1. `src/Services/SessionService.php` (NOVO)
- **Responsabilidade**: Gerenciar sessões PHP para armazenar dados do paciente
- **Funcionalidades**:
  - Salvar/recuperar dados do paciente (nome, telefone)
  - Salvar/recuperar etapa atual do agendamento
  - Verificar expiração de sessão (1 hora)
  - Limpar dados da sessão

### 2. `src/Controllers/ChatController.php` (MODIFICADO)
- **Mudanças**:
  - Integração com SessionService
  - Detecção automática de coleta de dados
  - Inclusão de dados da sessão no contexto da IA
  - Instruções específicas para não repetir perguntas

## Como Funciona

### 1. Inicialização da Sessão
```php
// No ChatController::processMessage()
$this->sessionService = new SessionService($sessionId);
```

### 2. Detecção Automática de Dados
O sistema detecta automaticamente quando:
- A IA está pedindo nome ou telefone
- O usuário fornece dados em suas mensagens

### 3. Armazenamento na Sessão
```php
// Dados são salvos automaticamente
$this->sessionService->salvarDadosPaciente($nome, $telefone);
```

### 4. Recuperação para a IA
```php
// Dados são incluídos no contexto da IA
$dadosPaciente = $this->sessionService->recuperarDadosPaciente();
```

## Fluxo de Funcionamento

1. **Primeira interação**: IA pede nome e telefone
2. **Usuário fornece dados**: Sistema detecta e salva na sessão
3. **Próximas interações**: IA recebe dados da sessão e não pede novamente
4. **Agendamento**: Dados são usados automaticamente

## Vantagens da Implementação

### ✅ Performance
- **Rápido**: Sessões PHP são muito rápidas
- **Sem consultas ao banco**: Dados ficam em memória
- **Automático**: Gerenciamento de sessão nativo do PHP

### ✅ Segurança
- **Dados no servidor**: Não ficam expostos no navegador
- **Expiração automática**: Sessões expiram após 1 hora
- **Isolamento**: Cada sessionId tem seus próprios dados

### ✅ Simplicidade
- **Zero infraestrutura adicional**: Usa recursos nativos do PHP
- **Fácil manutenção**: Código simples e direto
- **Compatibilidade**: Funciona em qualquer servidor PHP

## Configuração

### 1. Verificar Configuração de Sessão PHP
Certifique-se de que o PHP está configurado para usar sessões:

```php
// No php.ini ou via código
session.save_handler = files
session.save_path = /tmp
session.gc_maxlifetime = 3600
```

### 2. Testar Implementação
Execute o arquivo de teste:
```bash
php test_session.php
```

## Monitoramento

### Logs
O sistema gera logs detalhados:
```
SessionService: Dados do paciente salvos - Nome: Silvia Silva, Telefone: 54991223344
SessionService: Dados do paciente recuperados - Nome: Silvia Silva, Telefone: 54991223344
SessionService: Sessão expirada para sessionId: session_123
```

### Debug
Para debug, verifique:
- Logs do PHP (error_log)
- Dados da sessão no contexto da IA
- Etapas do agendamento salvas

## Limitações

1. **Sessões por servidor**: Se usar múltiplos servidores, sessões não são compartilhadas
2. **Memória**: Sessões ocupam memória do servidor
3. **Expiração**: Dados são perdidos após 1 hora de inatividade

## Próximos Passos

1. **Testar em produção**: Verificar se resolve o problema de repetição
2. **Monitorar performance**: Acompanhar uso de memória
3. **Considerar Redis**: Para ambientes com múltiplos servidores

## Exemplo de Uso

```php
// Inicializar
$sessionService = new SessionService($sessionId);

// Salvar dados
$sessionService->salvarDadosPaciente("Maria Silva", "11987654321");

// Recuperar dados
$dados = $sessionService->recuperarDadosPaciente();
if ($dados) {
    echo "Nome: " . $dados['nome'];
    echo "Telefone: " . $dados['telefone'];
}
``` 