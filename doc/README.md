# Frontend - Sistema de Assistente Virtual Médico

Esta pasta contém o frontend migrado do sistema PHP para HTML/CSS puro, mantendo fielmente o layout e funcionalidades da interface original.

## Estrutura dos Arquivos

```
frontend/
├── index.html              # Página principal do chat (equivale a chat.php)
├── panel.html              # Painel administrativo (equivale a panel.php)
├── assets/
│   ├── css/
│   │   ├── chat.css        # Estilos específicos da página de chat
│   │   └── panel.css       # Estilos específicos do painel administrativo
│   ├── js/
│   │   ├── chat.js         # JavaScript do chat (copiado do original)
│   │   ├── panel.js        # JavaScript do painel (copiado do original)
│   │   └── panel_backup.js # Backup do painel
│   └── img/
│       ├── Andréia.png     # Avatar do assistente
│       ├── blank.png       # Avatar do usuário
│       └── favicon.ico     # Ícone do site
└── README.md               # Este arquivo
```

## Decisões de Arquitetura

### CSS Separado por Página
Optei por manter os arquivos CSS separados (chat.css e panel.css) pelas seguintes razões:
- **Modularidade**: Cada página tem suas próprias regras de estilo
- **Performance**: Carrega apenas os estilos necessários para cada página
- **Manutenção**: Facilita a manutenção e modificação de estilos específicos
- **Organização**: Evita conflitos entre estilos de diferentes páginas

### Estrutura de Assets
- **Pasta centralizada**: Todos os recursos (CSS, JS, imagens) em `/assets/`
- **Organização por tipo**: Subpastas para cada tipo de recurso
- **Compatibilidade**: Mantém compatibilidade com o JavaScript existente

## Páginas Disponíveis

### 1. Chat (index.html)
- Interface principal do assistente virtual
- Chat em tempo real com debug panel
- Design responsivo para mobile e desktop
- Animações de partículas de fundo
- Sistema de feedback integrado

### 2. Painel Administrativo (panel.html)
- Configurações gerais da clínica
- Gestão de profissionais, serviços, convênios
- Horários de atendimento e exceções
- FAQ e formas de pagamento
- Interface com abas navegáveis

## Compatibilidade com Backend

### APIs Necessárias
O frontend espera que o backend Python implemente as seguintes APIs:

#### Chat
- `POST /api/chat` - Processar mensagens do chat
- `POST /api/feedback` - Sistema de feedback
- `POST /api/rewrite` - Reescrita colaborativa
- `GET /api/exchange-rate` - Taxa de câmbio

#### Painel Administrativo
- `GET/POST /api/panel/configuracoes` - Configurações gerais
- `GET/POST /api/panel/profissionais` - Gestão de profissionais
- `GET/POST /api/panel/servicos` - Gestão de serviços
- `GET/POST /api/panel/convenios` - Gestão de convênios
- `GET/POST /api/panel/horarios` - Horários de atendimento
- `GET/POST /api/panel/excecoes` - Exceções de agenda
- `GET/POST /api/panel/faq` - Perguntas frequentes
- `GET/POST /api/panel/pagamentos` - Formas de pagamento
- `GET/POST /api/panel/parceiros` - Parceiros

### Formato de Dados
O JavaScript espera receber dados no mesmo formato JSON utilizado pelo sistema PHP original.

## Como Servir o Frontend

### Servidor de Desenvolvimento
```bash
# Usando Python
cd frontend
python -m http.server 8000

# Usando Node.js
npx serve .

# Usando PHP (se ainda estiver disponível)
php -S localhost:8000
```

### Produção
- Configure um servidor web (nginx, Apache) para servir os arquivos estáticos
- Configure proxy reverso para as APIs do backend Python
- Certifique-se de que os caminhos dos assets estão corretos

## Modificações Realizadas

### Alterações nos Caminhos
- **CSS**: Movido de `css/` para `assets/css/`
- **JavaScript**: Movido de `js/` para `assets/js/`
- **Imagens**: Movido de `img/` para `assets/img/`

### Alterações nos Links
- **Panel button**: Agora aponta para `panel.html` em vez de `panel.php`
- **Back button**: No painel aponta para `index.html` em vez de `chat.php`
- **Assets**: Todos os links atualizados para a nova estrutura

### CSS
- **chat.css**: Replica fielmente todos os estilos da página de chat
- **panel.css**: Replica fielmente todos os estilos do painel administrativo
- **Responsividade**: Mantém todas as breakpoints e ajustes mobile

## Próximos Passos

### Para o Backend Python
1. Implementar as APIs listadas acima
2. Manter compatibilidade com formato JSON existente
3. Configurar CORS para permitir requisições do frontend
4. Implementar autenticação/autorização se necessário

### Para Deploy
1. Configurar servidor web para servir arquivos estáticos
2. Configurar proxy para APIs do backend
3. Otimizar assets (minificação, compressão)
4. Configurar cache adequado

## Notas Técnicas

- **Compatibilidade**: HTML5, CSS3, ES6+
- **Dependências**: Nenhuma dependência externa (Vanilla JavaScript)
- **Tamanho**: Assets otimizados para carregamento rápido
- **Acessibilidade**: Mantém estrutura semântica do HTML
- **SEO**: Meta tags apropriadas configuradas

O frontend está pronto para ser integrado com o backend Python, mantendo total fidelidade ao design e funcionalidades originais.
