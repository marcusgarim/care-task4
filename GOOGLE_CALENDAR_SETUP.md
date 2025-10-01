# Configuração Google Calendar API - Suporte para Smart Test

## Objetivo
Script para autenticar o usuário `suporte@careintelligence.ai` e permitir gerenciamento da agenda `Smart Test` via API do Google Calendar.

## Pré-requisitos

### 1. Google Cloud Console
- Projeto com Google Calendar API ativada
- OAuth Client criado (client_id + client_secret)
- Tela de consentimento OAuth configurada
- Usuários de teste adicionados:
  - `marcus@careintelligence.ai`
  - `suporte@careintelligence.ai`

### 2. Compartilhamento da Agenda
- A agenda `Smart Test` já deve estar compartilhada com `suporte@careintelligence.ai` com permissão de edição

### 3. Arquivo de Credenciais
O arquivo JSON de credenciais deve estar em:
```
credentials/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json
```

## Instalação e Execução

### 1. Instalar Dependências
```bash
pip3 install --upgrade google-auth google-auth-oauthlib google-api-python-client
```

### 2. Configurar Credenciais
Copie o arquivo client_secret JSON do caminho original:
```
/mnt/data/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json
```

Para o diretório do projeto:
```
credentials/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json
```

### 3. Executar Script
```bash
cd scripts
python3 calendar_support_to_marcus.py
```

## Fluxo de Autenticação

### Primeira Execução
1. O script tentará abrir um navegador automaticamente
2. Faça login com **suporte@careintelligence.ai**
3. Aceite as permissões solicitadas
4. O token será salvo em `token_suporte.json`

### Se o Navegador Não Abrir
O script fornecerá instruções alternativas:
1. URL manual para autenticação
2. Comando alternativo para ambientes sem interface gráfica

## Funcionalidades Testadas

O script executa as seguintes ações:
1. **Autenticação**: Login como suporte@careintelligence.ai
2. **Descoberta**: Encontra automaticamente a agenda `Smart Test`
3. **Listagem**: Mostra os próximos 5 eventos da agenda `Smart Test`
4. **Criação**: Cria um evento de teste na agenda `Smart Test`
5. **Token**: Salva token para reutilização

## Troubleshooting

### Erro: redirect_uri_mismatch
**Solução**: Adicione os seguintes URIs na configuração OAuth do Google Cloud:
- `http://localhost`
- `http://127.0.0.1`

### Erro: invalid_grant
**Solução**: Delete o arquivo `token_suporte.json` e execute novamente

### Erro: access_denied
**Solução**: Verifique se:
- O usuário `suporte@careintelligence.ai` está na lista de usuários de teste
- A agenda `Smart Test` está compartilhada com permissão de edição

### Erro: Agenda Smart Test não encontrada
**Solução**: Verifique se:
- A agenda `Smart Test` está compartilhada com `suporte@careintelligence.ai`
- O nome da agenda está exatamente como "Smart Test" (case-sensitive)
- O usuário tem permissão de visualização/edição

## Checklist de Validação

- [ ] `token_suporte.json` foi criado após o login
- [ ] Script encontrou e acessou a agenda `Smart Test`
- [ ] Script listou eventos futuros da agenda `Smart Test`
- [ ] Script criou evento de teste com sucesso
- [ ] Link do evento criado foi exibido
- [ ] Nenhum erro de redirect_uri_mismatch

## Arquivos Gerados

- `scripts/token_suporte.json`: Token de autenticação (NÃO COMMITTAR)
- `scripts/calendar_support_to_marcus.py`: Script principal

## Segurança

**IMPORTANTE**: Nunca commitar os seguintes arquivos:
- `credentials/client_secret_*.json`
- `token_suporte.json`

Adicione ao `.gitignore`:
```
credentials/client_secret_*.json
token_*.json
```
