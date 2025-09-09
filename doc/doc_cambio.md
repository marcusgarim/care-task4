# Conversão de Moeda - Dólar para Real

## Resumo das Alterações

O sistema foi atualizado para calcular e exibir os custos das conversas em **Reais (R$)** em vez de Dólares ($).

## Arquivos Modificados

### 1. Novo Serviço de Moeda
- **`src/Services/CurrencyService.php`**: Serviço responsável por gerenciar conversões de moeda

### 2. Backend (PHP)
- **`src/Controllers/ChatController.php`**: 
  - Adicionado `CurrencyService`
  - Cálculo de custo convertido para reais
  - Taxa de câmbio obtida dinamicamente

### 3. Frontend (JavaScript)
- **`public/js/chat.js`**: 
  - Busca taxa de câmbio da API
  - Cálculo de custo em reais
  - Formatação brasileira (vírgula como separador decimal)

### 4. API
- **`public/api/exchange-rate.php`**: Endpoint para fornecer taxa de câmbio atual

### 5. Interface
- **`public/chat.php`**: Texto inicial atualizado para "R$ 0,00"

## Funcionalidades

### Taxa de Câmbio Automática
- **API Externa**: Usa a API gratuita do Banco Central do Brasil
- **Cache Local**: Salva taxa no banco de dados para uso offline
- **Fallback**: Taxa padrão de R$ 5,00 se API falhar

### Cálculo de Custo
- **Input tokens**: $0.01 por 1.000 tokens
- **Output tokens**: $0.03 por 1.000 tokens
- **Conversão**: Multiplicado pela taxa de câmbio atual

### Formatação Brasileira
- **Símbolo**: R$ (Reais)
- **Separador decimal**: Vírgula (,)
- **Separador de milhares**: Ponto (.)

## Exemplo de Cálculo

```
Tokens de entrada: 1.000
Tokens de saída: 500

Custo em dólares:
- Input: 1.000 × $0.01 ÷ 1.000 = $0.01
- Output: 500 × $0.03 ÷ 1.000 = $0.015
- Total: $0.025

Taxa de câmbio: R$ 5,00
Custo em reais: $0.025 × 5,00 = R$ 0,125
Exibição: R$ 0,1250
```

## Configuração

### Variáveis de Ambiente
O sistema usa as seguintes variáveis (se disponíveis):
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`: Configurações do banco

### Banco de Dados
A taxa de câmbio é salva na tabela `configuracoes`:
- **Chave**: `taxa_cambio_usd_brl`
- **Valor**: Taxa atual (ex: 5.00)
- **Atualização**: Automática via API

## Monitoramento

### Logs
- Taxa obtida da API
- Taxa em cache
- Erros de conexão
- Uso de taxa padrão

### Debug
- Taxa atual exibida no console do navegador
- Logs de erro para troubleshooting

## Manutenção

### Atualização Manual da Taxa
Se necessário, a taxa pode ser atualizada manualmente no banco:
```sql
UPDATE configuracoes 
SET valor = 5.50, updated_at = NOW() 
WHERE chave = 'taxa_cambio_usd_brl';
```

### Fallback
Se a API falhar, o sistema usa:
1. Taxa em cache (última obtida)
2. Taxa padrão (R$ 5,00)

## Compatibilidade

- ✅ Mantém compatibilidade com dados existentes
- ✅ Não afeta funcionalidades existentes
- ✅ Interface atualizada gradualmente
- ✅ Logs para monitoramento
