// Variáveis globais
let sessionId = generateSessionId();
let isFirstMessage = true;
let debugLogs = [];
let totalTokens = 0;
let totalCost = 0;
let messageIdCounter = 0;
let exchangeRate = 5.00; // Taxa de câmbio padrão

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    createParticles();
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
    
    // Debug panel
    document.getElementById('toggleDebug').addEventListener('click', toggleDebugPanel);
    document.getElementById('clearLogs').addEventListener('click', clearDebugLogs);
    document.getElementById('exportLogs').addEventListener('click', exportDebugLogs);
    
    // Panel button
    document.getElementById('panelBtn').addEventListener('click', openPanel);
    
    // Adiciona botão de nova conversa
    addNewConversationButton();
    
    // Busca taxa de câmbio atual
    fetchExchangeRate();
    
    // Focus no input
    document.getElementById('messageInput').focus();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Adiciona mensagem do usuário
    addMessage('user', message);
    input.value = '';
    
    // Mostra indicador de digitação
    showTyping();
    
    // Log debug
    addDebugLog('Enviando mensagem', { message, sessionId });
    
    // Envia para o servidor
    fetch('api/chat.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            sessionId: sessionId,
            isFirst: isFirstMessage
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTyping();
        
        if (data.success) {
            // Adiciona resposta do bot
            const messageId = addMessage('bot', data.message);
            
            // Atualiza estatísticas
            if (data.tokens) {
                updateStats(data.tokens);
            }
            
            // Log debug
            addDebugLog('Resposta recebida', data);
            
            // Marca que não é mais a primeira mensagem
            isFirstMessage = false;
        } else {
            addMessage('bot', 'Desculpe, ocorreu um erro. Por favor, tente novamente.');
            addDebugLog('Erro na resposta', data);
        }
    })
    .catch(error => {
        hideTyping();
        addMessage('bot', 'Desculpe, não consegui processar sua mensagem. Tente novamente.');
        addDebugLog('Erro de rede', error);
    });
}

function addMessage(type, content) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageId = 'msg_' + (++messageIdCounter);
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.id = messageId;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    // Removido textContent pois agora usamos imagens de fundo
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    
    const p = document.createElement('p');
    p.innerHTML = formatMessage(content);
    contentDiv.appendChild(p);
    
    // Adiciona botões de feedback para mensagens do bot
    if (type === 'bot') {
        const feedbackDiv = createFeedbackButtons(messageId);
        contentDiv.appendChild(feedbackDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    messagesContainer.appendChild(messageDiv);
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
    
    // Envia feedback para o servidor
    fetch('api/feedback.php', {
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
    
    fetch('api/rewrite.php', {
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
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing-indicator';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    // Usa a mesma imagem da Andréia para o indicador de digitação
    
    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = '<span></span><span></span><span></span>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    
    messagesContainer.appendChild(typingDiv);
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
        
        document.getElementById('totalTokens').textContent = totalTokens;
        document.getElementById('totalCost').textContent = 'R$ ' + totalCost.toFixed(4).replace('.', ',');
    }
}

function fetchExchangeRate() {
    fetch('api/exchange-rate.php')
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
    const entryDiv = document.createElement('div');
    entryDiv.className = 'debug-log-entry';
    entryDiv.innerHTML = `<strong>[${timestamp}]</strong> ${label}: ${JSON.stringify(data, null, 2)}`;
    
    logDiv.appendChild(entryDiv);
    logDiv.scrollTop = logDiv.scrollHeight;
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
    // Log para debug
    addDebugLog('Botão Painel clicado', { timestamp: new Date().toISOString() });
    
    // Redireciona para o painel administrativo
    window.location.href = 'panel.html';
}