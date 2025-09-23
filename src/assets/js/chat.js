// Variáveis globais
let sessionId = generateSessionId();
let isFirstMessage = true;
let debugLogs = [];
let totalTokens = 0;
let totalCost = 0;
let messageIdCounter = 0;
let exchangeRate = 5.00; // Taxa de câmbio padrão
let isSending = false; // Evita envios duplicados/concorrentes

// Hidrata token do localStorage em window.CONFIG para uso nas requisições
try {
    if (!window.CONFIG) window.CONFIG = {};
    var existingToken = localStorage.getItem('app_token');
    if (existingToken) window.CONFIG.AUTH_TOKEN = existingToken;
} catch (e) {}

// Utilitário: auto ajusta a altura do textarea (fallback caso ainda não exista)
function autoResize(el) {
    try {
        if (!el || !el.style) return;
        el.style.height = 'auto';
        const min = 72;   // altura mínima em px
        const max = 240;  // altura máxima em px
        const next = Math.max(min, Math.min(max, el.scrollHeight || min));
        el.style.height = next + 'px';
    } catch (e) {
        // não interromper o fluxo do chat
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    bindModernLayout();
    // Sem partículas no novo layout
});

function initializeChat() {
    // Event listeners
    document.getElementById('sendButton').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    document.getElementById('messageInput').addEventListener('input', function(e){ autoResize(e.target); });
    
    // Debug panel
    var tgl = document.getElementById('toggleDebug');
    var clr = document.getElementById('clearLogs');
    var exp = document.getElementById('exportLogs');
    if (tgl) tgl.addEventListener('click', toggleDebugPanel);
    if (clr) clr.addEventListener('click', clearDebugLogs);
    if (exp) exp.addEventListener('click', exportDebugLogs);
    
    // Verificação automática de autenticação
    checkAuthenticationStatus();
    
    // Botoes de nova conversa
    addNewConversationButton();
    
    // Busca taxa de câmbio atual
    fetchExchangeRate();
    
    // Focus no input
    var mi = document.getElementById('messageInput');
    if (mi) mi.focus();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    if (isSending) return;
    isSending = true;
    let requestSucceeded = false; // Se true, não mostrar erro genérico no catch
    
    // Adiciona mensagem do usuário
    addMessage('user', message);
    input.value = '';
    const sendBtn = document.getElementById('sendButton');
    if (sendBtn) sendBtn.disabled = true;
    
    // Mostra indicador de digitação
    showTyping();
    
    // Log debug
    addDebugLog('Enviando mensagem', { message, sessionId });
    
    // Envia para o servidor
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    fetch(`${API_BASE}/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(window.CONFIG && window.CONFIG.AUTH_TOKEN ? { 'Authorization': `Bearer ${window.CONFIG.AUTH_TOKEN}` } : {})
        },
        body: JSON.stringify({
            message: message,
            sessionId: sessionId,
            isFirst: isFirstMessage
        })
    })
    .then(async (response) => {
        let raw = '';
        try {
            raw = await response.text();
            const data = raw ? JSON.parse(raw) : {};
            return { ok: response.ok, status: response.status, data };
        } catch (e) {
            return { ok: false, status: response.status, data: { success: false, message: 'Resposta inválida do servidor', raw } };
        }
    })
    .then(({ ok, data, status }) => {
        hideTyping();
        if (ok && data && data.success) {
            requestSucceeded = true;
            const messageId = addMessage('bot', data.message);
            if (data.tokens) {
                updateStats(data.tokens);
            }
            addDebugLog('Resposta recebida', data);
            isFirstMessage = false;
        } else {
            const fallbackMsg = (data && data.message) ? data.message : 'Desculpe, ocorreu um erro. Por favor, tente novamente.';
            addMessage('bot', fallbackMsg);
            addDebugLog('Erro na resposta', { status, data });
        }
    })
    .catch(error => {
        hideTyping();
        // Não exibir mensagem genérica no UI
        addDebugLog('Erro de rede', String(error));
    })
    .finally(() => {
        isSending = false;
        const sendBtn2 = document.getElementById('sendButton');
        if (sendBtn2) sendBtn2.disabled = false;
    });
}

function addMessage(type, content) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageId = 'msg_' + (++messageIdCounter);
    
    // Layout moderno
    if (document.querySelector('.chat-container')) {
        const wrap = document.createElement('div');
        wrap.className = `message-wrapper ${type === 'user' ? 'user' : 'assistant'}`;
        const inner = document.createElement('div');
        inner.className = 'message';
        const avatar = document.createElement('div');
        avatar.className = `avatar ${type === 'user' ? 'user-avatar' : 'assistant-avatar'}`;
        avatar.textContent = type === 'user' ? 'U' : 'S';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = `<p>${formatMessage(content)}</p>`;
        contentDiv.appendChild(textDiv);
        inner.appendChild(avatar);
        inner.appendChild(contentDiv);
        wrap.appendChild(inner);
        wrap.id = messageId;

        messagesContainer.appendChild(wrap);
    } else {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.id = messageId;
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        const p = document.createElement('p');
        p.innerHTML = formatMessage(content);
        contentDiv.appendChild(p);
        if (type === 'bot') {
            const feedbackDiv = createFeedbackButtons(messageId);
            contentDiv.appendChild(feedbackDiv);
        }
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return messageId;
}

function formatMessage(message) {
    // Converte quebras de linha em <br>
    message = message.replace(/\n/g, '<br>');
    
    // Detecta e formata listas
    message = message.replace(/^- (.+)$/gm, '• $1');
    
    // Removido uso de emojis; manter apenas texto puro
    message = message.replace(/[✅📅⏰👨‍⚕️📍]/g, '');
    
    return message;
}

function createFeedbackButtons(messageId) {
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-buttons';
    
    const likeBtn = document.createElement('button');
    likeBtn.innerHTML = 'Útil';
    likeBtn.onclick = () => handleFeedback(messageId, 'positivo', likeBtn);
    
    const dislikeBtn = document.createElement('button');
    dislikeBtn.innerHTML = 'Não útil';
    dislikeBtn.onclick = () => handleFeedback(messageId, 'negativo', dislikeBtn);
    
    const rewriteBtn = document.createElement('button');
    rewriteBtn.innerHTML = 'Reescrever';
    rewriteBtn.onclick = () => showRewriteModal(messageId);
    
    feedbackDiv.appendChild(likeBtn);
    feedbackDiv.appendChild(dislikeBtn);
    feedbackDiv.appendChild(rewriteBtn);
    
    return feedbackDiv;
}

function handleFeedback(messageId, feedbackType, button) {
    // Visual feedback
    const buttons = button.parentElement.querySelectorAll('button');
    buttons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    
    // Envia feedback para o servidor (FastAPI)
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            messageId: messageId,
            feedbackType: feedbackType,
            sessionId: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        addDebugLog('Feedback enviado', data);
    })
    .catch(error => {
        addDebugLog('Erro ao enviar feedback', error);
    });
}

function showRewriteModal(messageId) {
    const messageElement = document.getElementById(messageId);
    const originalText = messageElement.querySelector('p').innerText;
    
    const modal = document.createElement('div');
    modal.className = 'rewrite-modal';
    
    modal.innerHTML = `
        <div class="rewrite-modal-content">
            <h3>Como você reescreveria esta resposta?</h3>
            <textarea id="rewriteText">${originalText}</textarea>
            <div class="rewrite-modal-actions">
                <button class="save-btn" onclick="saveRewrite('${messageId}')">Salvar</button>
                <button class="cancel-btn" onclick="closeRewriteModal()">Cancelar</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.getElementById('rewriteText').focus();
}

function saveRewrite(messageId) {
    const rewrittenText = document.getElementById('rewriteText').value;
    
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    fetch(`${API_BASE}/rewrite`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            messageId: messageId,
            rewrittenText: rewrittenText,
            sessionId: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        addDebugLog('Reescrita salva', data);
        closeRewriteModal();
        
        // Marca automaticamente o feedback negativo na resposta original
        // pois quando uma resposta é reescrita, significa que a original não foi satisfatória
        const feedbackButtons = document.querySelector(`#${messageId} .feedback-buttons`);
        if (feedbackButtons) {
            const dislikeBtn = feedbackButtons.querySelector('button:nth-child(2)'); // Botão "Não útil" (2º botão)
            if (dislikeBtn && !dislikeBtn.classList.contains('active')) {
                // Simula o clique no botão de feedback negativo
                dislikeBtn.click();
            }
        }
    })
    .catch(error => {
        addDebugLog('Erro ao salvar reescrita', error);
    });
}

function closeRewriteModal() {
    const modal = document.querySelector('.rewrite-modal');
    if (modal) {
        modal.remove();
    }
}

function showTyping() {
    const messagesContainer = document.getElementById('chatMessages');
    if (document.querySelector('.chat-container')) {
        const wrap = document.createElement('div');
        wrap.className = 'message-wrapper assistant';
        wrap.id = 'typingIndicator';
        wrap.innerHTML = `
            <div class="message">
                <div class="avatar assistant-avatar">S</div>
                <div class="message-content">
                    <div class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>
                </div>
            </div>`;
        messagesContainer.appendChild(wrap);
    } else {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot typing-indicator';
        typingDiv.id = 'typingIndicator';
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const content = document.createElement('div');
        content.className = 'content';
        content.innerHTML = '<span></span><span></span><span></span>';
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(content);
        messagesContainer.appendChild(typingDiv);
    }
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTyping() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function updateStats(tokens) {
    if (tokens.prompt_tokens) {
        totalTokens += tokens.prompt_tokens + (tokens.completion_tokens || 0);
        
        const costInDollars = (tokens.prompt_tokens * 0.00025 + (tokens.completion_tokens || 0) * 0.002) / 1000;
        
        // Converte para reais usando a taxa atual
        const costInReais = costInDollars * exchangeRate;
        
        totalCost += costInReais;
        
        const totalTokensEl = document.getElementById('totalTokens');
        const totalCostEl = document.getElementById('totalCost');
        if (totalTokensEl) totalTokensEl.textContent = totalTokens;
        if (totalCostEl) totalCostEl.textContent = 'R$ ' + totalCost.toFixed(4).replace('.', ',');
    }
}

function fetchExchangeRate() {
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    fetch(`${API_BASE}/exchange-rate`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                exchangeRate = data.rate;
                console.log('Taxa de câmbio atualizada:', exchangeRate);
            }
        })
        .catch(error => {
            console.log('Erro ao buscar taxa de câmbio, usando padrão:', error);
        });
}

function toggleDebugPanel() {
    const debugContent = document.getElementById('debugContent');
    const toggleBtn = document.getElementById('toggleDebug');
    
    if (debugContent.classList.contains('hidden')) {
        debugContent.classList.remove('hidden');
        toggleBtn.textContent = '▼';
    } else {
        debugContent.classList.add('hidden');
        toggleBtn.textContent = '▶';
    }
}

function addDebugLog(label, data) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = {
        timestamp: timestamp,
        label: label,
        data: data
    };
    
    debugLogs.push(logEntry);
    
    const logDiv = document.getElementById('debugLogs');
    if (logDiv) {
        const entryDiv = document.createElement('div');
        entryDiv.className = 'debug-log-entry';
        entryDiv.innerHTML = `<strong>[${timestamp}]</strong> ${label}: ${JSON.stringify(data, null, 2)}`;
        logDiv.appendChild(entryDiv);
        logDiv.scrollTop = logDiv.scrollHeight;
    }
}

function clearDebugLogs() {
    debugLogs = [];
    document.getElementById('debugLogs').innerHTML = '';
    addDebugLog('Logs limpos', {});
}

function exportDebugLogs() {
    const dataStr = JSON.stringify(debugLogs, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `chat_logs_${sessionId}_${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    addDebugLog('Logs exportados', { filename: exportFileDefaultName });
}

function createParticles() {
    const particlesContainer = document.getElementById('particles-bg');
    const particleCount = 20;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        const size = Math.random() * 60 + 20;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        
        particle.style.animationDelay = Math.random() * 20 + 's';
        particle.style.animationDuration = (Math.random() * 20 + 20) + 's';
        
        particlesContainer.appendChild(particle);
    }
}

// Função para iniciar nova conversa
function startNewConversation() {
    // Gera novo sessionId
    sessionId = generateSessionId();
    
    // Limpa o localStorage
    localStorage.removeItem('sessionId');
    
    // Limpa as mensagens na tela
    document.getElementById('chatMessages').innerHTML = '';
    
    // Reseta variáveis
    isFirstMessage = true;
    messageIdCounter = 0;
    debugLogs = [];
    totalTokens = 0;
    totalCost = 0;
    
    // Atualiza estatísticas
    document.getElementById('totalTokens').textContent = '0';
    document.getElementById('totalCost').textContent = '$0.0000';
    
    // Limpa logs de debug
    document.getElementById('debugLogs').innerHTML = '';
    
    // Adiciona log de nova conversa
    addDebugLog('Nova conversa iniciada', { sessionId });
    
    // Focus no input
    document.getElementById('messageInput').focus();
}

// Adiciona botão de nova conversa se não existir
function addNewConversationButton() {
    const headerButtons = document.querySelector('.header-buttons');
    if (headerButtons && !document.getElementById('newConversationBtn')) {
        const newBtn = document.createElement('button');
        newBtn.id = 'newConversationBtn';
        newBtn.className = 'new-conversation-btn';
        newBtn.textContent = '🔄 Nova Conversa';
        newBtn.onclick = startNewConversation;
        headerButtons.appendChild(newBtn);
    }
}

// Inicializa com nova conversa (não recupera do localStorage)
// Cada carregamento da página inicia uma nova conversa
localStorage.removeItem('sessionId');

// Função para abrir o painel
function openPanel() {
    addDebugLog('Botão Painel clicado', { timestamp: new Date().toISOString() });
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    fetch(`${API_BASE}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            ...(window.CONFIG && window.CONFIG.AUTH_TOKEN ? { 'Authorization': `Bearer ${window.CONFIG.AUTH_TOKEN}` } : {})
        }
    })
    .then(async function(res){
        if (!res.ok) {
            // Não autenticado: enviar ao login
            window.location.href = 'login.html';
            return;
        }
        try {
            const data = await res.json();
            const isAdmin = !!(data && data.user && (data.user.is_admin === true || data.user.is_admin === 1));
            if (isAdmin) {
                window.location.href = 'panel.html';
            } else {
                addDebugLog('Acesso ao painel negado (não-admin)', data);
                alert('Você não tem permissão de administrador para acessar o painel.');
            }
        } catch(e) {
            window.location.href = 'login.html';
        }
    })
    .catch(function(){ window.location.href = 'login.html'; });
}

function checkAuthenticationStatus() {
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    const authBtn = document.getElementById('authBtn');
    if (!authBtn) return;

    // Estado inicial: Entrar
    authBtn.textContent = 'Entrar';
    authBtn.onclick = function(){ window.location.href = 'login.html'; };

    // Verifica se o usuário está autenticado
    fetch(`${API_BASE}/auth/check-auth`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            ...(window.CONFIG && window.CONFIG.AUTH_TOKEN ? { 'Authorization': `Bearer ${window.CONFIG.AUTH_TOKEN}` } : {})
        }
    })
    .then(async function(res){
        if (!res.ok) return; // Mantém Entrar se não conseguir verificar
        const data = await res.json();
        
        if (data.success && data.authenticated && data.user) {
            // Usuário está logado
            const user = data.user;
            const isAdmin = !!(user.is_admin === true || user.is_admin === 1);
            
            if (isAdmin) {
                // Usuário admin: mostra nome + botão Painel Admin
                authBtn.textContent = `${user.name || user.email} - Painel Admin`;
                authBtn.onclick = function() { window.location.href = 'panel.html'; };
            } else {
                // Usuário comum: mostra apenas nome
                authBtn.textContent = user.name || user.email;
                authBtn.onclick = function() {
                    // Futuramente pode abrir menu de usuário com logout
                    if (confirm('Deseja fazer logout?')) {
                        logout();
                    }
                };
            }
        } else {
            // Usuário não está logado: mantém botão Entrar
            authBtn.textContent = 'Entrar';
            authBtn.onclick = function(){ window.location.href = 'login.html'; };
        }
    })
    .catch(function(){ 
        // Em caso de erro, mantém o botão Entrar
        authBtn.textContent = 'Entrar';
        authBtn.onclick = function(){ window.location.href = 'login.html'; };
    });
}

function logout() {
    const API_BASE = (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
    
    fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            ...(window.CONFIG && window.CONFIG.AUTH_TOKEN ? { 'Authorization': `Bearer ${window.CONFIG.AUTH_TOKEN}` } : {})
        }
    })
    .then(function() {
        // Limpa token local
        try {
            localStorage.removeItem('app_token');
            if (window.CONFIG) window.CONFIG.AUTH_TOKEN = null;
        } catch(e) {}
        
        // Atualiza interface
        checkAuthenticationStatus();
    })
    .catch(function() {
        // Mesmo se falhar a requisição, limpa localmente
        try {
            localStorage.removeItem('app_token');
            if (window.CONFIG) window.CONFIG.AUTH_TOKEN = null;
        } catch(e) {}
        checkAuthenticationStatus();
    });
}

function bindModernLayout() {
    // Eventos do layout
    var menuBtn = document.getElementById('menuBtn');
    if (menuBtn) menuBtn.addEventListener('click', function(){
        var el = document.getElementById('sidebar');
        if (el) el.classList.toggle('hidden');
    });
    var btn1 = document.getElementById('newConversationHeaderBtn');
    var btn2 = document.getElementById('newConversationSidebarBtn');
    if (btn1) btn1.addEventListener('click', startNewConversation);
    if (btn2) btn2.addEventListener('click', startNewConversation);

    // Preenche lista de conversas placeholder
    var list = document.getElementById('conversationList');
    if (list && list.children.length === 0) {
        ['Consulta de rotina','Agendamento exame','Dúvidas sobre preparo','Remarcar consulta'].forEach(function(t){
            var item = document.createElement('div');
            item.className = 'conversation-item';
            item.textContent = t;
            list.appendChild(item);
        });
        if (list.firstChild) list.firstChild.classList.add('active');
    }

    // Sugestões da tela inicial
    document.querySelectorAll('.suggestion-card').forEach(function(el){
        el.addEventListener('click', function(){
            var txt = el.getAttribute('data-suggestion') || el.textContent.trim();
            var mi = document.getElementById('messageInput');
            if (mi) { mi.value = txt; sendMessage(); }
        });
    });
}