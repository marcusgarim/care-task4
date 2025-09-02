// Variáveis globais
let currentTab = 'configuracoes';
let currentEditId = null;

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializePanel();
});

function initializePanel() {
    // Event listeners para tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Event listener para formulário de configurações
    document.getElementById('configForm').addEventListener('submit', handleConfigSubmit);
}

// Função para alternar entre abas
function switchTab(tabName) {
    // Remove active de todas as abas
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

    // Adiciona active na aba selecionada
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');

    currentTab = tabName;
}

// ===== CONFIGURAÇÕES =====
async function loadConfiguracoes() {
    try {
        const response = await fetch('api/panel/configuracoes.php', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                populateConfigForm(data.configuracoes);
            } else {
                showMessage('Erro ao carregar configurações', 'error');
            }
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

function populateConfigForm(configuracoes) {
    configuracoes.forEach(config => {
        const element = document.getElementById(config.chave);
        if (element) {
            element.value = config.valor;
        }
    });
}

async function handleConfigSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const configData = {};
    
    for (let [key, value] of formData.entries()) {
        configData[key] = value;
    }

    try {
        const response = await fetch('api/panel/configuracoes.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        const data = await response.json();
        
        if (data.success) {
            showMessage('Configurações salvas com sucesso!', 'success');
        } else {
            showMessage(data.message || 'Erro ao salvar configurações', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CARREGAMENTO DE DADOS =====
async function loadAllData() {
    await Promise.all([
        loadProfissionais(),
        loadServicos(),
        loadConvenios(),
        loadHorarios(),
        loadExcecoes(),
        loadFaq(),
        loadPagamentos(),
        loadParceiros()
    ]);
}

// ===== PROFISSIONAIS =====
async function loadProfissionais() {
    try {
        const response = await fetch('api/panel/profissionais.php');
        const data = await response.json();
        
        if (data.success) {
            renderProfissionaisTable(data.profissionais);
        }
    } catch (error) {
        showMessage('Erro ao carregar profissionais', 'error');
    }
}

function renderProfissionaisTable(profissionais) {
    const tbody = document.getElementById('profissionaisTableBody');
    tbody.innerHTML = '';

    // Filtrar apenas profissionais ativos
    const profissionaisAtivos = profissionais.filter(prof => prof.ativo == 1);

    profissionaisAtivos.forEach(prof => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${prof.nome}</td>
            <td>${prof.especialidade || '-'}</td>
            <td>${prof.crm || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editProfissional(${prof.id})">✏️</button>
                <button class="btn-delete" onclick="deleteProfissional(${prof.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== SERVIÇOS =====
async function loadServicos() {
    try {
        const response = await fetch('api/panel/servicos.php');
        const data = await response.json();
        
        if (data.success) {
            renderServicosTable(data.servicos);
        }
    } catch (error) {
        showMessage('Erro ao carregar serviços', 'error');
    }
}

function renderServicosTable(servicos) {
    const tbody = document.getElementById('servicosTableBody');
    tbody.innerHTML = '';

    // Filtrar apenas serviços ativos
    const servicosAtivos = servicos.filter(serv => serv.ativo == 1);

    servicosAtivos.forEach(serv => {
        const row = document.createElement('tr');
        row.dataset.id = serv.id;
        row.dataset.tipo = serv.tipo || '';
        row.dataset.palavrasChave = serv.palavras_chave || '';
        row.dataset.preparo = serv.preparo_necessario || '';
        row.dataset.anestesia = serv.anestesia_tipo || '';
        row.dataset.local = serv.local_realizacao || '';
        row.dataset.observacoes = serv.observacoes || '';
        row.dataset.duracaoMinutos = serv.duracao_minutos || '';
        
        row.innerHTML = `
            <td>${serv.nome}</td>
            <td>${truncateText(serv.descricao || '', 50)}</td>
            <td>${serv.valor ? 'R$ ' + parseFloat(serv.valor).toFixed(2) : '-'}</td>
            <td>${serv.categoria || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editServico(${serv.id})">✏️</button>
                <button class="btn-delete" onclick="deleteServico(${serv.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== CONVÊNIOS =====
async function loadConvenios() {
    try {
        const response = await fetch('api/panel/convenios.php');
        const data = await response.json();
        
        if (data.success) {
            renderConveniosTable(data.convenios);
        }
    } catch (error) {
        showMessage('Erro ao carregar convênios', 'error');
    }
}

function renderConveniosTable(convenios) {
    const tbody = document.getElementById('conveniosTableBody');
    tbody.innerHTML = '';

    // Filtrar apenas convênios ativos
    const conveniosAtivos = convenios.filter(conv => conv.ativo == 1);

    conveniosAtivos.forEach(conv => {
        const row = document.createElement('tr');
        row.dataset.id = conv.id;
        row.dataset.observacoes = conv.observacoes || '';
        row.innerHTML = `
            <td>${conv.nome}</td>
            <td>${conv.registro_ans || '-'}</td>
            <td>${truncateText(conv.observacoes || '', 50)}</td>
            <td>
                <button class="btn-edit" onclick="editConvenio(${conv.id})">✏️</button>
                <button class="btn-delete" onclick="deleteConvenio(${conv.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== HORÁRIOS =====
async function loadHorarios() {
    try {
        const response = await fetch('api/panel/horarios.php');
        const data = await response.json();
        
        if (data.success) {
            renderHorariosTable(data.horarios);
        }
    } catch (error) {
        showMessage('Erro ao carregar horários', 'error');
    }
}

function renderHorariosTable(horarios) {
    const tbody = document.getElementById('horariosTableBody');
    tbody.innerHTML = '';

    const diasSemana = {
        'segunda': 'Segunda-feira',
        'terca': 'Terça-feira',
        'quarta': 'Quarta-feira',
        'quinta': 'Quinta-feira',
        'sexta': 'Sexta-feira',
        'sabado': 'Sábado',
        'domingo': 'Domingo'
    };

    // Filtrar apenas horários ativos
    const horariosAtivos = horarios.filter(hor => hor.ativo == 1);

    horariosAtivos.forEach(hor => {
        const row = document.createElement('tr');
        row.dataset.id = hor.id;
        row.dataset.manhaInicio = hor.manha_inicio || '';
        row.dataset.manhaFim = hor.manha_fim || '';
        row.dataset.tardeInicio = hor.tarde_inicio || '';
        row.dataset.tardeFim = hor.tarde_fim || '';
        row.dataset.intervaloMinutos = hor.intervalo_minutos || 30;

                    // Formatar horários sem segundos
            const formatarHorario = (horario) => {
                if (!horario || horario === '00:00:00' || horario === '00:00') return '';
                return horario.substring(0, 5); // Remove os segundos (HH:MM:SS -> HH:MM)
            };

                        // Verificar se há horários válidos
                const manhaInicio = formatarHorario(hor.manha_inicio);
                const manhaFim = formatarHorario(hor.manha_fim);
                const tardeInicio = formatarHorario(hor.tarde_inicio);
                const tardeFim = formatarHorario(hor.tarde_fim);
                
                const manhaTexto = (manhaInicio && manhaFim) ? `${manhaInicio} - ${manhaFim}` : 'Fechado';
                const tardeTexto = (tardeInicio && tardeFim) ? `${tardeInicio} - ${tardeFim}` : 'Fechado';
                
                row.innerHTML = `
                    <td>${diasSemana[hor.dia_semana] || hor.dia_semana}</td>
                    <td>${manhaTexto}</td>
                    <td>${tardeTexto}</td>
                    <td>${hor.intervalo_minutos || '-'} min</td>
                    <td>
                        <button class="btn-edit" onclick="editHorario(${hor.id})">✏️</button>
                        <button class="btn-delete" onclick="deleteHorario(${hor.id})">🗑️</button>
                    </td>
                `;
        tbody.appendChild(row);
    });
}

// ===== EXCEÇÕES DA AGENDA =====
async function loadExcecoes() {
    try {
        const response = await fetch('api/panel/excecoes.php');
        const data = await response.json();
        
        if (data.success) {
            renderExcecoesTable(data.excecoes);
        }
    } catch (error) {
        showMessage('Erro ao carregar exceções', 'error');
    }
}

function renderExcecoesTable(excecoes) {
    const tbody = document.getElementById('excecoesTableBody');
    tbody.innerHTML = '';

    excecoes.forEach(exc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(exc.data)}</td>
            <td>${exc.tipo}</td>
            <td>${exc.descricao || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editExcecao(${exc.id})">✏️</button>
                <button class="btn-danger" onclick="deleteExcecao(${exc.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== FAQ =====
async function loadFaq() {
    try {
        const response = await fetch('api/panel/faq.php');
        const data = await response.json();
        
        if (data.success) {
            renderFaqTable(data.faqs);
        }
    } catch (error) {
        showMessage('Erro ao carregar FAQ', 'error');
    }
}

function renderFaqTable(faq) {
    const tbody = document.getElementById('faqTableBody');
    tbody.innerHTML = '';

    faq.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${truncateText(item.pergunta, 50)}</td>
            <td>${item.categoria || '-'}</td>
            <td>${truncateText(item.palavras_chave, 30)}</td>
            <td>
                <button class="btn-edit" onclick="editFaq(${item.id})">✏️</button>
                <button class="btn-danger" onclick="deleteFaq(${item.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PAGAMENTOS =====
async function loadPagamentos() {
    try {
        const response = await fetch('api/panel/pagamentos.php');
        const data = await response.json();
        
        if (data.success) {
            renderPagamentosTable(data.pagamentos);
        }
    } catch (error) {
        showMessage('Erro ao carregar pagamentos', 'error');
    }
}

function renderPagamentosTable(pagamentos) {
    const tbody = document.getElementById('pagamentosTableBody');
    tbody.innerHTML = '';

    pagamentos.forEach(pag => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${pag.nome}</td>
            <td>${truncateText(pag.descricao, 40)}</td>
            <td>${pag.max_parcelas}x</td>
            <td><span class="status-${pag.ativo ? 'active' : 'inactive'}">${pag.ativo ? 'Ativo' : 'Inativo'}</span></td>
            <td>
                <button class="btn-edit" onclick="editPagamento(${pag.id})">✏️</button>
                <button class="btn-danger" onclick="deletePagamento(${pag.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PARCEIROS =====
async function loadParceiros() {
    try {
        const response = await fetch('api/panel/parceiros.php');
        const data = await response.json();
        
        if (data.success) {
            renderParceirosTable(data.parceiros);
        }
    } catch (error) {
        showMessage('Erro ao carregar parceiros', 'error');
    }
}

function renderParceirosTable(parceiros) {
    const tbody = document.getElementById('parceirosTableBody');
    tbody.innerHTML = '';

    parceiros.forEach(parc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${parc.tipo || '-'}</td>
            <td>${parc.nome}</td>
            <td>${parc.endereco || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editParceiro(${parc.id})">✏️</button>
                <button class="btn-danger" onclick="deleteParceiro(${parc.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== FUNÇÕES AUXILIARES =====
function showMessage(message, type = 'info') {
    // Remove mensagens existentes
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());

    // Cria nova mensagem
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;

    // Insere no topo do conteúdo da aba atual
    const currentPanel = document.querySelector('.tab-panel.active');
    currentPanel.insertBefore(messageDiv, currentPanel.firstChild);

    // Remove após 5 segundos
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function truncateText(text, maxLength) {
    if (!text) return '-';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ===== FUNÇÕES DE MODAL =====
function showModal(title, content, actions = []) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
            <div class="modal-actions">
                ${actions.map(action => `
                    <button class="btn-${action.class || 'secondary'}" onclick="${action.onclick || action.action}">
                        ${action.text}
                    </button>
                `).join('')}
            </div>
        </div>
    `;

    document.getElementById('modalContainer').appendChild(modal);
}

function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
    currentEditId = null;
}

// ===== FUNÇÕES DE CRUD (serão implementadas conforme necessário) =====

// Profissionais
function showProfissionalModal(id = null) {
    const title = id ? 'Editar Profissional' : 'Adicionar Profissional';
    const profissional = id ? getProfissionalById(id) : null;
    
    const content = `
        <form id="profissionalForm" class="modal-form">
            <div class="form-group">
                <label for="nome">Nome *</label>
                <input type="text" id="nome" name="nome" value="${profissional ? profissional.nome : ''}" required>
            </div>
            <div class="form-group">
                <label for="especialidade">Especialidade</label>
                <input type="text" id="especialidade" name="especialidade" value="${profissional ? profissional.especialidade || '' : ''}">
            </div>
            <div class="form-group">
                <label for="crm">CRM</label>
                <input type="text" id="crm" name="crm" value="${profissional ? profissional.crm || '' : ''}">
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: id ? `handleProfissionalSubmit(${id})` : 'handleProfissionalSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

// ===== CRUD PROFISSIONAIS =====
function getProfissionalById(id) {
    // Buscar o profissional na tabela atual
    const rows = document.querySelectorAll('#profissionaisTableBody tr');
    for (let row of rows) {
        const editButton = row.querySelector('button[onclick*="editProfissional"]');
        if (editButton) {
            const rowId = editButton.getAttribute('onclick').match(/\d+/)[0];
            if (rowId == id) {
                return {
                    id: id,
                    nome: row.cells[0].textContent,
                    especialidade: row.cells[1].textContent === '-' ? '' : row.cells[1].textContent,
                    crm: row.cells[2].textContent === '-' ? '' : row.cells[2].textContent,
                    ativo: 1 // Como só exibimos profissionais ativos, sempre será 1
                };
            }
        }
    }
    return null;
}

async function handleProfissionalSubmit(id = null) {
    
    const form = document.getElementById('profissionalForm');
    if (!form) {
        console.error('Formulário não encontrado');
        showMessage('Erro: formulário não encontrado', 'error');
        return;
    }
    
    const formData = new FormData(form);
    
    const profissionalData = {
        nome: formData.get('nome'),
        especialidade: formData.get('especialidade'),
        crm: formData.get('crm'),
        ativo: 1 // Sempre ativo, já que removemos o checkbox
    };



    try {
        const url = 'api/panel/profissionais.php';
        const method = id ? 'PUT' : 'POST';
        
        if (id) {
            profissionalData.id = parseInt(id);
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profissionalData)
        });

        const data = await response.json();
        
        if (data.success) {
            showMessage(id ? 'Profissional atualizado com sucesso!' : 'Profissional criado com sucesso!', 'success');
            closeModal();
            loadProfissionais(); // Recarregar a tabela
        } else {
            showMessage(data.message || 'Erro ao salvar profissional', 'error');
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showMessage('Erro de conexão', 'error');
    }
}

async function editProfissional(id) {
    const profissional = getProfissionalById(id);
    showProfissionalModal(id);
}

async function deleteProfissional(id) {
    if (!confirm('Tem certeza que deseja desativar este profissional?')) {
        return;
    }

    try {
        const response = await fetch('api/panel/profissionais.php', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                id: parseInt(id),
                ativo: 0
            })
        });

        const data = await response.json();
        
        if (data.success) {
            showMessage('Profissional desativado com sucesso!', 'success');
            loadProfissionais(); // Recarregar a tabela
        } else {
            showMessage(data.message || 'Erro ao desativar profissional', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD SERVIÇOS =====
function showServicoModal(id = null) {
    const title = id ? 'Editar Serviço' : 'Adicionar Serviço';
    const servico = id ? getServicoById(id) : null;
    
    const content = `
        <form id="servicoForm" class="modal-form">
            <div class="form-group">
                <label for="nome">Nome do Serviço *</label>
                <input type="text" id="nome" name="nome" value="${servico ? servico.nome : ''}" required>
            </div>
            <div class="form-group">
                <label for="descricao">Descrição</label>
                <textarea id="descricao" name="descricao" rows="3">${servico ? servico.descricao || '' : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="valor">Valor (R$)</label>
                <input type="number" id="valor" name="valor" step="0.01" value="${servico ? servico.valor || '' : ''}">
            </div>
            <div class="form-group">
                <label for="categoria">Categoria</label>
                <input type="text" id="categoria" name="categoria" value="${servico ? servico.categoria || '' : ''}">
            </div>
            <div class="form-group">
                <label for="palavras_chave">Palavras-chave</label>
                <input type="text" id="palavras_chave" name="palavras_chave" value="${servico ? servico.palavras_chave || '' : ''}">
            </div>
            <div class="form-group">
                <label for="preparo_necessario">Preparo Necessário</label>
                <textarea id="preparo_necessario" name="preparo_necessario" rows="3">${servico ? servico.preparo_necessario || '' : ''}</textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="anestesia_tipo">Tipo de Anestesia</label>
                    <input type="text" id="anestesia_tipo" name="anestesia_tipo" value="${servico ? servico.anestesia_tipo || '' : ''}">
                </div>
                <div class="form-group">
                    <label for="local_realizacao">Local de Realização</label>
                    <input type="text" id="local_realizacao" name="local_realizacao" value="${servico ? servico.local_realizacao || '' : ''}">
                </div>
            </div>
            <div class="form-group">
                <label for="observacoes">Observações</label>
                <textarea id="observacoes" name="observacoes" rows="3">${servico ? servico.observacoes || '' : ''}</textarea>
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: id ? `handleServicoSubmit(${id})` : 'handleServicoSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

function getServicoById(id) {
    // Buscar o serviço na tabela atual
    const rows = document.querySelectorAll('#servicosTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                nome: row.cells[0].textContent,
                descricao: row.cells[1].textContent,
                valor: row.cells[2].textContent.replace('R$ ', ''),
                categoria: row.cells[3].textContent,
                palavras_chave: row.dataset.palavrasChave || '',
                preparo_necessario: row.dataset.preparo || '',
                anestesia_tipo: row.dataset.anestesia || '',
                local_realizacao: row.dataset.local || '',
                observacoes: row.dataset.observacoes || '',
                ativo: 1 // Apenas serviços ativos são exibidos
            };
        }
    }
    return null;
}

async function handleServicoSubmit(id = null) {
    const form = document.getElementById('servicoForm');
    const formData = new FormData(form);
    
    const servicoData = {
        nome: formData.get('nome'),
        descricao: formData.get('descricao'),
        valor: formData.get('valor') ? parseFloat(formData.get('valor')) : null,
        categoria: formData.get('categoria'),
        palavras_chave: formData.get('palavras_chave'),
        preparo_necessario: formData.get('preparo_necessario'),
        anestesia_tipo: formData.get('anestesia_tipo'),
        local_realizacao: formData.get('local_realizacao'),
        observacoes: formData.get('observacoes'),
        ativo: 1 // Sempre ativo para novos serviços
    };
    
    if (id) {
        servicoData.id = id;
    }
    
    try {
        const response = await fetch('api/panel/servicos.php', {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(servicoData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadServicos(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editServico(id) {
    showServicoModal(id);
}

async function deleteServico(id) {
    if (!confirm('Tem certeza que deseja excluir este serviço?')) {
        return;
    }
    
    try {
        const response = await fetch('api/panel/servicos.php', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: parseInt(id), ativo: 0 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('Serviço excluído com sucesso', 'success');
            loadServicos(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD CONVÊNIOS =====
function showConvenioModal(id = null) {
    const title = id ? 'Editar Convênio' : 'Adicionar Convênio';
    const convenio = id ? getConvenioById(id) : null;
    
    const content = `
        <form id="convenioForm" class="modal-form">
            <div class="form-group">
                <label for="nome">Nome do Convênio *</label>
                <input type="text" id="nome" name="nome" value="${convenio ? convenio.nome : ''}" required>
            </div>
            <div class="form-group">
                <label for="registro_ans">Registro ANS</label>
                <input type="text" id="registro_ans" name="registro_ans" value="${convenio ? convenio.registro_ans || '' : ''}">
            </div>
            <div class="form-group">
                <label for="observacoes">Observações</label>
                <textarea id="observacoes" name="observacoes" rows="3">${convenio ? convenio.observacoes || '' : ''}</textarea>
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: id ? `handleConvenioSubmit(${id})` : 'handleConvenioSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

function getConvenioById(id) {
    // Buscar o convênio na tabela atual
    const rows = document.querySelectorAll('#conveniosTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                nome: row.cells[0].textContent,
                registro_ans: row.cells[1].textContent !== '-' ? row.cells[1].textContent : '',
                observacoes: row.dataset.observacoes || '',
                ativo: 1 // Apenas convênios ativos são exibidos
            };
        }
    }
    return null;
}

async function handleConvenioSubmit(id = null) {
    const form = document.getElementById('convenioForm');
    const formData = new FormData(form);
    
    const convenioData = {
        nome: formData.get('nome'),
        registro_ans: formData.get('registro_ans'),
        observacoes: formData.get('observacoes')
    };
    
    if (id) {
        convenioData.id = id;
    }
    
    try {
        const response = await fetch('api/panel/convenios.php', {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(convenioData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadConvenios(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editConvenio(id) {
    showConvenioModal(id);
}

async function deleteConvenio(id) {
    if (!confirm('Tem certeza que deseja excluir este convênio?')) {
        return;
    }
    
    try {
        const response = await fetch('api/panel/convenios.php', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: parseInt(id), ativo: 0 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('Convênio excluído com sucesso', 'success');
            loadConvenios(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD HORÁRIOS =====
function showHorarioModal(id = null) {
    const title = id ? 'Editar Horário' : 'Adicionar Horário';
    const horario = id ? getHorarioById(id) : null;
    
    const content = `
        <form id="horarioForm" class="modal-form">
            <div class="form-group">
                <label for="dia_semana">Dia da Semana *</label>
                <select id="dia_semana" name="dia_semana" required>
                    <option value="">Selecione...</option>
                    <option value="segunda" ${horario && horario.dia_semana === 'segunda' ? 'selected' : ''}>Segunda-feira</option>
                    <option value="terca" ${horario && horario.dia_semana === 'terca' ? 'selected' : ''}>Terça-feira</option>
                    <option value="quarta" ${horario && horario.dia_semana === 'quarta' ? 'selected' : ''}>Quarta-feira</option>
                    <option value="quinta" ${horario && horario.dia_semana === 'quinta' ? 'selected' : ''}>Quinta-feira</option>
                    <option value="sexta" ${horario && horario.dia_semana === 'sexta' ? 'selected' : ''}>Sexta-feira</option>
                    <option value="sabado" ${horario && horario.dia_semana === 'sabado' ? 'selected' : ''}>Sábado</option>
                    <option value="domingo" ${horario && horario.dia_semana === 'domingo' ? 'selected' : ''}>Domingo</option>
                </select>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="manha_inicio">Início Manhã</label>
                    <input type="time" id="manha_inicio" name="manha_inicio" value="${horario ? horario.manha_inicio || '' : ''}">
                </div>
                <div class="form-group">
                    <label for="manha_fim">Fim Manhã</label>
                    <input type="time" id="manha_fim" name="manha_fim" value="${horario ? horario.manha_fim || '' : ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="tarde_inicio">Início Tarde</label>
                    <input type="time" id="tarde_inicio" name="tarde_inicio" value="${horario ? horario.tarde_inicio || '' : ''}">
                </div>
                <div class="form-group">
                    <label for="tarde_fim">Fim Tarde</label>
                    <input type="time" id="tarde_fim" name="tarde_fim" value="${horario ? horario.tarde_fim || '' : ''}">
                </div>
            </div>
                                <div class="form-group">
                        <label for="intervalo_minutos">Intervalo entre Consultas (minutos)</label>
                        <input type="number" id="intervalo_minutos" name="intervalo_minutos" value="${horario && horario.intervalo_minutos !== null ? horario.intervalo_minutos : ''}" min="15" max="120" placeholder="Deixe em branco para usar padrão">
                    </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: `handleHorarioSubmit(${id || 'null'})`
        }
    ];
    
    showModal(title, content, actions);
}

function getHorarioById(id) {
    // Buscar o horário na tabela atual
    const rows = document.querySelectorAll('#horariosTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            const diaSemana = row.cells[0].textContent;
            const diaMap = {
                'Segunda-feira': 'segunda',
                'Terça-feira': 'terca',
                'Quarta-feira': 'quarta',
                'Quinta-feira': 'quinta',
                'Sexta-feira': 'sexta',
                'Sábado': 'sabado',
                'Domingo': 'domingo'
            };
            
                                // Processar intervalo - se for '-', usar null
                    const intervaloText = row.cells[3].textContent.replace(' min', '');
                    const intervalo = intervaloText === '-' ? null : parseInt(intervaloText) || 30;
                    
                    return {
                        id: id,
                        dia_semana: diaMap[diaSemana] || diaSemana.toLowerCase(),
                        manha_inicio: row.dataset.manhaInicio || '',
                        manha_fim: row.dataset.manhaFim || '',
                        tarde_inicio: row.dataset.tardeInicio || '',
                        tarde_fim: row.dataset.tardeFim || '',
                        intervalo_minutos: intervalo,
                        ativo: 1 // Apenas horários ativos são exibidos
                    };
        }
    }
    return null;
}

        async function handleHorarioSubmit(id = null) {
            const form = document.getElementById('horarioForm');
            const formData = new FormData(form);
            
            // Processar horários - se estiver vazio, salvar como null
            const manhaInicio = formData.get('manha_inicio') || null;
            const manhaFim = formData.get('manha_fim') || null;
            const tardeInicio = formData.get('tarde_inicio') || null;
            const tardeFim = formData.get('tarde_fim') || null;
            
            // Processar intervalo - só incluir se for preenchido
            const intervaloMinutos = formData.get('intervalo_minutos');
            const intervalo = intervaloMinutos && intervaloMinutos.trim() !== '' ? parseInt(intervaloMinutos) : null;
            
            const horarioData = {
                dia_semana: formData.get('dia_semana'),
                manha_inicio: manhaInicio,
                manha_fim: manhaFim,
                tarde_inicio: tardeInicio,
                tarde_fim: tardeFim,
                ativo: 1 // Sempre ativo ao criar/editar
            };
            
            // Só incluir intervalo se foi preenchido
            if (intervalo !== null) {
                horarioData.intervalo_minutos = intervalo;
            }
    
    if (id) {
        horarioData.id = id;
    }
    
    try {
        const response = await fetch('api/panel/horarios.php', {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(horarioData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadHorarios(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editHorario(id) {
    showHorarioModal(id);
}

async function deleteHorario(id) {
    if (!confirm('Tem certeza que deseja excluir este horário?')) {
        return;
    }
    
    try {
        const response = await fetch('api/panel/horarios.php', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: parseInt(id), ativo: 0 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('Horário excluído com sucesso', 'success');
            loadHorarios(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== EXCEÇÕES DA AGENDA =====
async function loadExcecoes() {
    try {
        const response = await fetch('api/panel/excecoes.php');
        const data = await response.json();
        
        if (data.success) {
            renderExcecoesTable(data.excecoes);
        }
    } catch (error) {
        showMessage('Erro ao carregar exceções', 'error');
    }
}

function renderExcecoesTable(excecoes) {
    const tbody = document.getElementById('excecoesTableBody');
    tbody.innerHTML = '';

    excecoes.forEach(exc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(exc.data)}</td>
            <td>${exc.tipo}</td>
            <td>${exc.descricao || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editExcecao(${exc.id})">✏️</button>
                <button class="btn-danger" onclick="deleteExcecao(${exc.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== FAQ =====
async function loadFaq() {
    try {
        const response = await fetch('api/panel/faq.php');
        const data = await response.json();
        
        if (data.success) {
            renderFaqTable(data.faqs);
        }
    } catch (error) {
        showMessage('Erro ao carregar FAQ', 'error');
    }
}

function renderFaqTable(faq) {
    const tbody = document.getElementById('faqTableBody');
    tbody.innerHTML = '';

    faq.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${truncateText(item.pergunta, 50)}</td>
            <td>${item.categoria || '-'}</td>
            <td>${truncateText(item.palavras_chave, 30)}</td>
            <td>
                <button class="btn-edit" onclick="editFaq(${item.id})">✏️</button>
                <button class="btn-danger" onclick="deleteFaq(${item.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PAGAMENTOS =====
async function loadPagamentos() {
    try {
        const response = await fetch('api/panel/pagamentos.php');
        const data = await response.json();
        
        if (data.success) {
            renderPagamentosTable(data.pagamentos);
        }
    } catch (error) {
        showMessage('Erro ao carregar pagamentos', 'error');
    }
}

function renderPagamentosTable(pagamentos) {
    const tbody = document.getElementById('pagamentosTableBody');
    tbody.innerHTML = '';

    pagamentos.forEach(pag => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${pag.nome}</td>
            <td>${truncateText(pag.descricao, 40)}</td>
            <td>${pag.max_parcelas}x</td>
            <td><span class="status-${pag.ativo ? 'active' : 'inactive'}">${pag.ativo ? 'Ativo' : 'Inativo'}</span></td>
            <td>
                <button class="btn-edit" onclick="editPagamento(${pag.id})">✏️</button>
                <button class="btn-danger" onclick="deletePagamento(${pag.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PARCEIROS =====
async function loadParceiros() {
    try {
        const response = await fetch('api/panel/parceiros.php');
        const data = await response.json();
        
        if (data.success) {
            renderParceirosTable(data.parceiros);
        }
    } catch (error) {
        showMessage('Erro ao carregar parceiros', 'error');
    }
}

function renderParceirosTable(parceiros) {
    const tbody = document.getElementById('parceirosTableBody');
    tbody.innerHTML = '';

    parceiros.forEach(parc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${parc.tipo || '-'}</td>
            <td>${parc.nome}</td>
            <td>${parc.endereco || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editParceiro(${parc.id})">✏️</button>
                <button class="btn-danger" onclick="deleteParceiro(${parc.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== EXCEÇÕES NA AGENDA =====
function showExcecaoModal(id = null) {
    const title = id ? 'Editar Exceção' : 'Adicionar Exceção';
    const excecao = id ? getExcecaoById(id) : null;
    
    const content = `
        <form id="excecaoForm" class="modal-form">
            <div class="form-group">
                <label for="data">Data</label>
                <input type="date" id="data" name="data" value="${excecao ? excecao.data : ''}" required>
            </div>
            <div class="form-group">
                <label for="tipo">Tipo</label>
                <select id="tipo" name="tipo" required>
                    <option value="">Selecione o tipo</option>
                    <option value="feriado" ${excecao && excecao.tipo === 'feriado' ? 'selected' : ''}>Feriado</option>
                    <option value="folga" ${excecao && excecao.tipo === 'folga' ? 'selected' : ''}>Folga</option>
                    <option value="fechado" ${excecao && excecao.tipo === 'fechado' ? 'selected' : ''}>Fechado</option>
                </select>
            </div>
            <div class="form-group">
                <label for="descricao">Descrição</label>
                <textarea id="descricao" name="descricao" rows="3" placeholder="Descrição da exceção">${excecao ? excecao.descricao || '' : ''}</textarea>
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: `handleExcecaoSubmit(${id || 'null'})`
        }
    ];
    
    showModal(title, content, actions);
}

function getExcecaoById(id) {
    const rows = document.querySelectorAll('#excecoesTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                data: row.cells[0].textContent,
                tipo: row.cells[1].textContent.toLowerCase(),
                descricao: row.cells[2].textContent
            };
        }
    }
    return null;
}

async function handleExcecaoSubmit(id = null) {
    const form = document.getElementById('excecaoForm');
    const formData = new FormData(form);
    
    const excecaoData = {
        data: formData.get('data'),
        tipo: formData.get('tipo'),
        descricao: formData.get('descricao') || null
    };
    
    try {
        const url = 'api/panel/excecoes.php';
        const method = id ? 'PUT' : 'POST';
        
        if (id) {
            excecaoData.id = parseInt(id);
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(excecaoData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadExcecoes();
        } else {
            showMessage(data.message || 'Erro ao salvar exceção', 'error');
        }
    } catch (error) {
        showMessage('Erro ao salvar exceção', 'error');
    }
}

async function editExcecao(id) {
    showExcecaoModal(id);
}

async function deleteExcecao(id) {
    if (confirm('Tem certeza que deseja excluir esta exceção?')) {
        try {
            const response = await fetch('api/panel/excecoes.php', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: parseInt(id) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('Exceção excluída com sucesso', 'success');
                loadExcecoes();
            } else {
                showMessage(data.message || 'Erro ao excluir exceção', 'error');
            }
        } catch (error) {
            showMessage('Erro ao excluir exceção', 'error');
        }
    }
}

// ===== FAQ =====
function showFaqModal(id = null) {
    const title = id ? 'Editar FAQ' : 'Adicionar FAQ';
    const faq = id ? getFaqById(id) : null;
    
    const content = `
        <form id="faqForm" class="modal-form">
            <div class="form-group">
                <label for="pergunta">Pergunta</label>
                <textarea id="pergunta" name="pergunta" rows="3" required placeholder="Digite a pergunta">${faq ? faq.pergunta : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="resposta">Resposta</label>
                <textarea id="resposta" name="resposta" rows="5" required placeholder="Digite a resposta">${faq ? faq.resposta : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="categoria">Categoria</label>
                <input type="text" id="categoria" name="categoria" value="${faq ? faq.categoria || '' : ''}" placeholder="Categoria (opcional)">
            </div>
            <div class="form-group">
                <label for="palavras_chave">Palavras-chave</label>
                <textarea id="palavras_chave" name="palavras_chave" rows="2" placeholder="Palavras-chave separadas por vírgula (opcional)">${faq ? faq.palavras_chave || '' : ''}</textarea>
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: `handleFaqSubmit(${id || 'null'})`
        }
    ];
    
    showModal(title, content, actions);
}

function getFaqById(id) {
    const rows = document.querySelectorAll('#faqTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                pergunta: row.cells[0].textContent,
                categoria: row.cells[1].textContent,
                palavras_chave: row.cells[2].textContent
            };
        }
    }
    return null;
}

async function handleFaqSubmit(id = null) {
    const form = document.getElementById('faqForm');
    const formData = new FormData(form);
    
    const faqData = {
        pergunta: formData.get('pergunta'),
        resposta: formData.get('resposta'),
        categoria: formData.get('categoria') || null,
        palavras_chave: formData.get('palavras_chave') || null
    };
    
    try {
        const url = 'api/panel/faq.php';
        const method = id ? 'PUT' : 'POST';
        
        if (id) {
            faqData.id = parseInt(id);
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(faqData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadFaq();
        } else {
            showMessage(data.message || 'Erro ao salvar FAQ', 'error');
        }
    } catch (error) {
        showMessage('Erro ao salvar FAQ', 'error');
    }
}

async function editFaq(id) {
    showFaqModal(id);
}

async function deleteFaq(id) {
    if (confirm('Tem certeza que deseja excluir este FAQ?')) {
        try {
            const response = await fetch('api/panel/faq.php', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: parseInt(id) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('FAQ excluído com sucesso', 'success');
                loadFaq();
            } else {
                showMessage(data.message || 'Erro ao excluir FAQ', 'error');
            }
        } catch (error) {
            showMessage('Erro ao excluir FAQ', 'error');
        }
    }
}

// ===== FORMAS DE PAGAMENTO =====
function showPagamentoModal(id = null) {
    const title = id ? 'Editar Forma de Pagamento' : 'Adicionar Forma de Pagamento';
    const pagamento = id ? getPagamentoById(id) : null;
    
    const content = `
        <form id="pagamentoForm" class="modal-form">
            <div class="form-group">
                <label for="nome">Nome</label>
                <input type="text" id="nome" name="nome" value="${pagamento ? pagamento.nome : ''}" required placeholder="Nome da forma de pagamento">
            </div>
            <div class="form-group">
                <label for="descricao">Descrição</label>
                <textarea id="descricao" name="descricao" rows="3" placeholder="Descrição da forma de pagamento">${pagamento ? pagamento.descricao || '' : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="max_parcelas">Máximo de Parcelas</label>
                <input type="number" id="max_parcelas" name="max_parcelas" value="${pagamento ? pagamento.max_parcelas : '1'}" min="1" max="12" required>
            </div>
            <div class="form-group">
                <label for="ativo">Ativo</label>
                <select id="ativo" name="ativo" required>
                    <option value="1" ${pagamento && pagamento.ativo == 1 ? 'selected' : ''}>Ativo</option>
                    <option value="0" ${pagamento && pagamento.ativo == 0 ? 'selected' : ''}>Inativo</option>
                </select>
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: `handlePagamentoSubmit(${id || 'null'})`
        }
    ];
    
    showModal(title, content, actions);
}

function getPagamentoById(id) {
    const rows = document.querySelectorAll('#pagamentosTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                nome: row.cells[0].textContent,
                descricao: row.cells[1].textContent,
                max_parcelas: parseInt(row.cells[2].textContent.replace('x', '')),
                ativo: row.cells[3].textContent.includes('Ativo') ? 1 : 0
            };
        }
    }
    return null;
}

async function handlePagamentoSubmit(id = null) {
    const form = document.getElementById('pagamentoForm');
    const formData = new FormData(form);
    
    const pagamentoData = {
        nome: formData.get('nome'),
        descricao: formData.get('descricao') || null,
        max_parcelas: parseInt(formData.get('max_parcelas')),
        ativo: parseInt(formData.get('ativo'))
    };
    
    try {
        const url = 'api/panel/pagamentos.php';
        const method = id ? 'PUT' : 'POST';
        
        if (id) {
            pagamentoData.id = parseInt(id);
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pagamentoData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadPagamentos();
        } else {
            showMessage(data.message || 'Erro ao salvar forma de pagamento', 'error');
        }
    } catch (error) {
        showMessage('Erro ao salvar forma de pagamento', 'error');
    }
}

async function editPagamento(id) {
    showPagamentoModal(id);
}

async function deletePagamento(id) {
    if (confirm('Tem certeza que deseja excluir esta forma de pagamento?')) {
        try {
            const response = await fetch('api/panel/pagamentos.php', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: parseInt(id) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('Forma de pagamento excluída com sucesso', 'success');
                loadPagamentos();
            } else {
                showMessage(data.message || 'Erro ao excluir forma de pagamento', 'error');
            }
        } catch (error) {
            showMessage('Erro ao excluir forma de pagamento', 'error');
        }
    }
}

// ===== PARCEIROS =====
function showParceiroModal(id = null) {
    const title = id ? 'Editar Parceiro' : 'Adicionar Parceiro';
    const parceiro = id ? getParceiroById(id) : null;
    
    const content = `
        <form id="parceiroForm" class="modal-form">
            <div class="form-group">
                <label for="tipo">Tipo</label>
                <input type="text" id="tipo" name="tipo" value="${parceiro ? parceiro.tipo || '' : ''}" placeholder="Tipo de parceiro (opcional)">
            </div>
            <div class="form-group">
                <label for="nome">Nome</label>
                <input type="text" id="nome" name="nome" value="${parceiro ? parceiro.nome : ''}" required placeholder="Nome do parceiro">
            </div>
            <div class="form-group">
                <label for="endereco">Endereço</label>
                <input type="text" id="endereco" name="endereco" value="${parceiro ? parceiro.endereco || '' : ''}" placeholder="Endereço (opcional)">
            </div>
        </form>
    `;
    
    const actions = [
        {
            text: 'Cancelar',
            class: 'btn-secondary',
            onclick: 'closeModal()'
        },
        {
            text: id ? 'Atualizar' : 'Criar',
            class: 'btn-primary',
            onclick: `handleParceiroSubmit(${id || 'null'})`
        }
    ];
    
    showModal(title, content, actions);
}

function getParceiroById(id) {
    const rows = document.querySelectorAll('#parceirosTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                tipo: row.cells[0].textContent === '-' ? null : row.cells[0].textContent,
                nome: row.cells[1].textContent,
                endereco: row.cells[2].textContent === '-' ? null : row.cells[2].textContent
            };
        }
    }
    return null;
}

async function handleParceiroSubmit(id = null) {
    const form = document.getElementById('parceiroForm');
    const formData = new FormData(form);
    
    const parceiroData = {
        tipo: formData.get('tipo') || null,
        nome: formData.get('nome'),
        endereco: formData.get('endereco') || null
    };
    
    try {
        const url = 'api/panel/parceiros.php';
        const method = id ? 'PUT' : 'POST';
        
        if (id) {
            parceiroData.id = parseInt(id);
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(parceiroData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadParceiros();
        } else {
            showMessage(data.message || 'Erro ao salvar parceiro', 'error');
        }
    } catch (error) {
        showMessage('Erro ao salvar parceiro', 'error');
    }
}

async function editParceiro(id) {
    showParceiroModal(id);
}

async function deleteParceiro(id) {
    if (confirm('Tem certeza que deseja excluir este parceiro?')) {
        try {
            const response = await fetch('api/panel/parceiros.php', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: parseInt(id) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('Parceiro excluído com sucesso', 'success');
                loadParceiros();
            } else {
                showMessage(data.message || 'Erro ao excluir parceiro', 'error');
            }
        } catch (error) {
            showMessage('Erro ao excluir parceiro', 'error');
        }
    }
}

// Função para testar conexão
async function testConnection() {
    try {
        const response = await fetch('api/panel/test.php');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message);
        }
        
        return data;
    } catch (error) {
        showMessage('Erro no teste de conexão', 'error');
        throw error;
    }
}

// Carregar dados quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    // Testar conexão primeiro
    testConnection().then(() => {
        loadConfiguracoes();
        loadAllData();
    }).catch(error => {
        showMessage('Erro na conexão com o banco de dados', 'error');
    });
}); 