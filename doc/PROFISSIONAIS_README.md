# Funcionalidade de Busca de Profissionais

## Visão Geral

O sistema agora possui uma funcionalidade robusta para buscar e indicar profissionais da clínica de forma automática. O assistente virtual **SEMPRE** consulta a tabela `profissionais` antes de mencionar qualquer profissional de saúde.

## Como Funciona

### 1. Regras Implementadas

- **OBRIGATÓRIO**: O assistente sempre chama `buscar_profissionais_clinica` antes de mencionar profissionais
- **PROIBIDO**: Inventar nomes de profissionais sem consultar o banco
- **DADOS REAIS**: Apenas profissionais ativos (ativo = 1) são considerados
- **ESPECIALIDADE**: Busca por especialidade médica específica

### 2. Exemplo de Uso

**Cenário**: Usuária grávida pergunta sobre vitaminas

**Fluxo Correto**:
1. Usuário: "posso tomar vitaminas?"
2. IA: "É importante conversar com um profissional de saúde antes de iniciar qualquer suplementação. Deixe-me verificar nossos especialistas disponíveis."
3. IA: [CHAMA `buscar_profissionais_clinica` com especialidade="ginecologia"]
4. IA: "Temos a Dra. Maria Silva, especialista em Ginecologia e Obstetrícia. Ela pode avaliar suas necessidades específicas e recomendar o melhor plano de suplementação para você e o bebê. Gostaria de agendar uma consulta?"

**Fluxo Incorreto**:
1. Usuário: "posso tomar vitaminas?"
2. IA: "Temos o Dr. João, ginecologista" ← **ERRADO!** Inventou nome sem consultar banco

## Configuração do Banco de Dados

### 1. Estrutura da Tabela

```sql
CREATE TABLE IF NOT EXISTS profissionais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    especialidade VARCHAR(255),
    crm VARCHAR(50),
    duracao_consulta INT,
    valor_consulta DECIMAL(10,2),
    ativo TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Inserir Dados de Exemplo

Execute o script `database/insert_profissionais_example.sql`:

```bash
mysql -u root -p andreia < database/insert_profissionais_example.sql
```

### 3. Dados de Exemplo Inseridos

- **Dra. Maria Silva** - Ginecologia e Obstetrícia
- **Dr. João Santos** - Clínico Geral  
- **Dra. Ana Costa** - Pediatria
- **Dr. Carlos Oliveira** - Cardiologia

## Função `buscar_profissionais_clinica`

### Parâmetros

- `especialidade` (opcional): Busca por especialidade médica
- `profissional_especifico` (opcional): Busca por nome do profissional

### Exemplos de Uso

```php
// Buscar todos os profissionais
$functions->buscar_profissionais_clinica();

// Buscar por especialidade
$functions->buscar_profissionais_clinica(['especialidade' => 'ginecologia']);

// Buscar por nome
$functions->buscar_profissionais_clinica(['profissional_especifico' => 'Maria']);
```

### Retorno

```php
[
    [
        'id' => 1,
        'nome' => 'Dra. Maria Silva',
        'especialidade' => 'Ginecologia e Obstetrícia',
        'crm' => 'CRM-SP 12345',
        'duracao_consulta' => 30,
        'valor_consulta' => '150.00',
        'ativo' => 1
    ]
]
```

## Teste da Funcionalidade

Execute o arquivo de teste:

```bash
php test_profissionais.php
```

Este teste irá:
1. Buscar todos os profissionais
2. Buscar profissionais de ginecologia
3. Buscar profissional específico por nome

## Integração com o Assistente

### Prompt do Sistema

O assistente recebe instruções específicas:

```
### IMPORTANTE SOBRE INDICAÇÃO DE PROFISSIONAIS:
- **SEMPRE use a função buscar_profissionais_clinica** quando precisar indicar um profissional de saúde
- **NUNCA invente nomes de profissionais** - sempre busque na tabela profissionais
- **SEMPRE chame buscar_profissionais_clinica** antes de mencionar qualquer profissional
- **Use apenas profissionais ativos** (ativo = 1) da clínica
```

### Função Disponível

A função `buscar_profissionais_clinica` está disponível no array de funções do assistente:

```php
[
    'name' => 'buscar_profissionais_clinica',
    'description' => 'Lista profissionais da clínica',
    'parameters' => [
        'type' => 'object',
        'properties' => [
            'especialidade' => ['type' => 'string'],
            'profissional_especifico' => ['type' => 'string']
        ]
    ]
]
```

## Casos de Uso Comuns

### 1. Perguntas sobre Gravidez
- **Usuário**: "estou grávida, posso tomar vitaminas?"
- **IA**: Busca ginecologistas e indica a Dra. Maria Silva

### 2. Problemas Cardíacos
- **Usuário**: "tenho pressão alta"
- **IA**: Busca cardiologistas e indica o Dr. Carlos Oliveira

### 3. Consulta Pediátrica
- **Usuário**: "meu filho está doente"
- **IA**: Busca pediatras e indica a Dra. Ana Costa

### 4. Consulta Geral
- **Usuário**: "preciso de um médico"
- **IA**: Lista todos os profissionais disponíveis

## Manutenção

### Adicionar Novos Profissionais

```sql
INSERT INTO profissionais (nome, especialidade, crm, duracao_consulta, valor_consulta, ativo) 
VALUES ('Dr. Nome Novo', 'Especialidade', 'CRM-SP 99999', 30, 150.00, 1);
```

### Desativar Profissional

```sql
UPDATE profissionais SET ativo = 0 WHERE id = 1;
```

### Atualizar Dados

```sql
UPDATE profissionais 
SET especialidade = 'Nova Especialidade', valor_consulta = 180.00 
WHERE id = 1;
```

## Benefícios

1. **Dados Reais**: Sempre usa informações atualizadas do banco
2. **Consistência**: Evita contradições ou informações desatualizadas
3. **Flexibilidade**: Fácil adição/remoção de profissionais
4. **Especialização**: Busca por especialidade médica específica
5. **Confiabilidade**: Apenas profissionais ativos são considerados

## Troubleshooting

### Problema: "Nenhum profissional encontrado"
**Solução**: Verificar se há dados na tabela `profissionais` e se estão ativos

### Problema: "Erro de conexão com banco"
**Solução**: Verificar configurações do banco em `.env`

### Problema: "Função não encontrada"
**Solução**: Verificar se a função está registrada em `getAvailableFunctions()` 