# Integração Google Calendar - Guia de Configuração

## Visão Geral

A integração com Google Calendar permite sincronizar automaticamente os agendamentos do sistema com os calendários pessoais dos profissionais, criando eventos automaticamente e verificando disponibilidade em tempo real.

## Funcionalidades Implementadas

### 1. **Autenticação OAuth2**
- Conectar profissionais aos seus calendários Google
- Renovação automática de tokens
- Gerenciamento seguro de credenciais

### 2. **Sincronização de Agendamentos**
- Criação automática de eventos no Google Calendar
- Atualização de eventos quando agendamentos são modificados
- Exclusão de eventos quando agendamentos são cancelados

### 3. **Verificação de Disponibilidade**
- Consultar calendário Google para verificar conflitos
- Calcular slots disponíveis considerando eventos existentes
- Integração com sistema de horários dos profissionais

### 4. **Painel Administrativo**
- Interface para conectar/desconectar profissionais
- Status da integração para cada profissional
- Sincronização manual e automática
- Log de sincronização

## Configuração das Credenciais Google

### Passo 1: Criar Projeto no Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Anote o **Project ID**

### Passo 2: Ativar Google Calendar API

1. No menu lateral, vá em **APIs & Services > Library**
2. Busque por "Google Calendar API"
3. Clique em **Enable**

### Passo 3: Configurar OAuth 2.0

1. Vá em **APIs & Services > Credentials**
2. Clique em **Create Credentials > OAuth client ID**
3. Selecione **Application type: Web application**
4. Configure:
   - **Name**: Smart Assistant Calendar Integration
   - **Authorized JavaScript origins**: `http://127.0.0.1:8000`
   - **Authorized redirect URIs**: `http://127.0.0.1:8000/api/google-calendar/callback`

### Passo 4: Baixar Credenciais

1. Após criar o OAuth client, clique em **Download JSON**
2. Salve o arquivo como `credentials/google_calendar_credentials.json`

### Exemplo do arquivo de credenciais:

```json
{
  "web": {
    "client_id": "123456789-abcdefghijk.apps.googleusercontent.com",
    "project_id": "seu-projeto-123456",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz",
    "redirect_uris": [
      "http://127.0.0.1:8000/api/google-calendar/callback"
    ]
  }
}
```

## Configuração do Sistema

### 1. Estrutura de Banco de Dados

O sistema criou automaticamente as seguintes tabelas:

- **`profissional_google_credentials`**: Armazena tokens OAuth de cada profissional
- **`google_calendar_settings`**: Configurações gerais da integração
- **`google_calendar_sync_log`**: Log de operações de sincronização

### 2. Campos Adicionados

- **`agendamentos`**: 
  - `google_event_id`: ID do evento no Google Calendar
  - `google_calendar_id`: ID do calendário
  - `google_event_link`: Link para o evento
  - `sync_status`: Status da sincronização

- **`profissionais`**:
  - `google_calendar_enabled`: Integração habilitada (0/1)
  - `google_calendar_sync_last`: Última sincronização

## Como Usar

### 1. Conectar Profissional

1. Acesse **Painel Admin > Google Calendar**
2. Clique em **Conectar** ao lado do profissional desejado
3. Será aberta janela para autorização Google
4. Faça login e autorize o acesso ao calendário
5. O status mudará para **Ativo**

### 2. Sincronização Automática

- Novos agendamentos são automaticamente criados no Google Calendar
- Modificações são sincronizadas automaticamente
- Cancelamentos removem o evento do calendário

### 3. Sincronização Manual

- Use **Sincronizar** para forçar sincronização de agendamentos pendentes
- Use **Sincronizar Todos** para sincronizar todos os profissionais conectados

### 4. Verificação de Disponibilidade

O sistema considera automaticamente:
- Horários de trabalho do profissional (tabela `disponibilidades_profissional`)
- Agendamentos existentes no sistema
- **Eventos no Google Calendar** (novidade!)
- Exceções e bloqueios de agenda

## API Endpoints

### Autenticação
- `GET /google-calendar/oauth/url?profissional_id={id}` - Gerar URL OAuth
- `GET /google-calendar/callback` - Callback OAuth

### Gerenciamento
- `GET /google-calendar/status/{profissional_id}` - Status da integração
- `POST /google-calendar/sync/{profissional_id}` - Sincronizar calendário
- `DELETE /google-calendar/disconnect/{profissional_id}` - Desconectar

### Listagem
- `GET /google-calendar/professionals` - Listar todos profissionais e status

## Configurações Avançadas

### Parâmetros Configuráveis

1. **Sincronização Automática**: Habilitar/desabilitar sincronização automática
2. **Intervalo de Sincronização**: Frequência de verificação (padrão: 15 minutos)
3. **Duração Padrão**: Duração padrão dos eventos (padrão: 30 minutos)
4. **Timezone**: Fuso horário dos calendários (padrão: America/Sao_Paulo)

### Logs de Sincronização

O sistema mantém log detalhado de todas as operações:
- Criação/atualização/exclusão de eventos
- Sucessos e erros
- Timestamp de cada operação
- Profissional e agendamento relacionados

## Resolução de Problemas

### Token Expirado
- **Sintoma**: Status "Token Expirado"
- **Solução**: Clicar em "Conectar" novamente para renovar

### Erro de Sincronização
- **Sintoma**: Agendamentos não aparecem no Google Calendar
- **Solução**: Verificar permissões do calendário e fazer sincronização manual

### Conflitos de Horário
- **Sintoma**: Sistema mostra slots como disponíveis mas há conflito
- **Solução**: Aguardar próxima sincronização ou forçar sincronização manual

### Calendário Não Encontrado
- **Sintoma**: Erro "calendário não encontrado"
- **Solução**: Reconectar profissional - sistema usará calendário primário

## Segurança

### Dados Protegidos
- Tokens OAuth são criptografados e armazenados com segurança
- Apenas administradores podem gerenciar integrações
- Comunicação via HTTPS com Google APIs

### Permissões Necessárias
- **Google Calendar API**: Leitura e escrita de eventos
- **OAuth Scopes**: `https://www.googleapis.com/auth/calendar`

### Logs de Auditoria
- Todas as operações são registradas
- Histórico de conexões/desconexões
- Rastreamento de sincronizações

## Benefícios da Integração

### Para Profissionais
- Sincronização automática com calendário pessoal
- Visibilidade unificada de todos os compromissos
- Notificações nativas do Google Calendar
- Acesso via dispositivos móveis

### Para Pacientes
- Confirmação automática por email (via Google Calendar)
- Links para videoconferência (se configurado)
- Lembretes automáticos

### Para a Clínica
- Redução de conflitos de agendamento
- Melhor gestão de disponibilidade
- Sincronização em tempo real
- Backup automático dos agendamentos

## Próximos Passos

### Funcionalidades Futuras Planejadas
1. **Webhook Google Calendar**: Sincronização instantânea bidirecional
2. **Múltiplos Calendários**: Suporte a calendários específicos por tipo de serviço
3. **Sala de Reunião**: Integração com Google Meet para teleconsultas
4. **Relatórios Avançados**: Analytics de utilização dos calendários

### Configuração para Produção
1. Configurar domínio próprio para redirect URI
2. Configurar HTTPS
3. Implementar webhook para sincronização em tempo real
4. Configurar backup das credenciais

---

**Nota**: Esta integração foi implementada seguindo as melhores práticas de segurança e utiliza as APIs oficiais do Google. Para suporte, consulte a documentação oficial do Google Calendar API em https://developers.google.com/calendar
