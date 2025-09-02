// Variáveis globais
let currentTab = 'configuracoes';
let currentEditId = null;
const API_BASE = 'http://127.0.0.1:8000/api';

// Função para aplicar máscara de moeda
function applyCurrencyMask(input) {
    input.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove tudo que não é dígito
        
        // Se não há dígitos, limpa o campo
        if (value === '') {
            e.target.value = '';
            return;
        }
        
        // Converte para centavos e depois para reais
        const numericValue = parseInt(value);
        if (isNaN(numericValue)) {
            e.target.value = '';
            return;
        }
        
        value = (numericValue / 100).toFixed(2);
        value = value.replace('.', ','); // Troca ponto por vírgula
        value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.'); // Adiciona pontos para milhares
        e.target.value = value;
    });

    input.addEventListener('blur', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value === '') {
            e.target.value = '';
            return;
        }
        
        const numericValue = parseInt(value);
        if (isNaN(numericValue)) {
            e.target.value = '';
            return;
        }
        
        value = (numericValue / 100).toFixed(2);
        e.target.value = 'R$ ' + value.replace('.', ',');
    });

    input.addEventListener('focus', function(e) {
        let value = e.target.value.replace('R$ ', '').replace(/\./g, '').replace(',', '.');
        if (value && !isNaN(parseFloat(value))) {
            e.target.value = value;
        } else {
            e.target.value = '';
        }
    });
}

// Função para converter valor formatado para número
function parseCurrencyValue(value) {
    if (!value || value.trim() === '') return null;
    
    // Remove formatação e converte para número
    const cleanValue = value.replace('R$ ', '').replace(/\./g, '').replace(',', '.');
    const numericValue = parseFloat(cleanValue);
    
    // Verifica se é um número válido
    return isNaN(numericValue) ? null : numericValue;
}

// Inicialização
document.addEventListener('DOMContentLoaded', function () {
    initializePanel();
});

function initializePanel() {
    // Event listeners para tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Event listener para formulário de configurações
    document.getElementById('configForm').addEventListener('submit', handleConfigSubmit);
    
    // Inicializar navegação dos tabs
    initializeTabNavigation();
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
        const response = await fetch(`${API_BASE}/panel/configuracoes`, {
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
        const response = await fetch(`${API_BASE}/panel/configuracoes`, {
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
        const response = await fetch(`${API_BASE}/panel/profissionais`);
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
        const response = await fetch(`${API_BASE}/panel/servicos`);
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
            <td>${serv.valor && !isNaN(parseFloat(serv.valor)) ? 'R$ ' + parseFloat(serv.valor).toFixed(2).replace('.', ',') : '-'}</td>
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
        const response = await fetch(`${API_BASE}/panel/convenios`);
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
        const response = await fetch(`${API_BASE}/panel/horarios`);
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
        row.dataset.intervaloMinutos = hor.intervalo_minutos || '';
        row.dataset.ativo = 1; // Apenas horários ativos são exibidos

        // Formatar horários sem segundos
        const formatarHorario = (horario) => {
            if (!horario) return '';
            return horario.substring(0, 5); // Remove segundos (HH:MM:SS -> HH:MM)
        };

        row.innerHTML = `
    <td>${diasSemana[hor.dia_semana] || hor.dia_semana}</td>
    <td>${(!hor.manha_inicio || (hor.manha_inicio === '00:00:00' && hor.manha_fim === '00:00:00'))
                ? 'Fechado'
                : formatarHorario(hor.manha_inicio) + ' - ' + formatarHorario(hor.manha_fim)
            }</td>
    <td>${(!hor.tarde_inicio || (hor.tarde_inicio === '00:00:00' && hor.tarde_fim === '00:00:00'))
                ? 'Fechado'
                : formatarHorario(hor.tarde_inicio) + ' - ' + formatarHorario(hor.tarde_fim)
            }</td>
    <td>${hor.intervalo_minutos ? hor.intervalo_minutos + ' min' : '-'}</td>
    <td>
        <button class="btn-edit" onclick="editHorario(${hor.id})">✏️</button>
    </td>
`;
        tbody.appendChild(row);
    });
}

// ===== EXCEÇÕES DA AGENDA =====
async function loadExcecoes() {
    try {
        const response = await fetch(`${API_BASE}/panel/excecoes`);
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

    // Filtrar apenas exceções ativas
    const excecoesAtivas = excecoes.filter(exc => exc.ativo == 1);

    excecoesAtivas.forEach(exc => {
        const row = document.createElement('tr');
        row.dataset.id = exc.id;
        row.dataset.data = exc.data;
        row.dataset.tipo = exc.tipo;
        row.dataset.descricao = exc.descricao || '';
        row.innerHTML = `
            <td>${formatDate(exc.data)}</td>
            <td>${exc.tipo}</td>
            <td>${exc.descricao || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editExcecao(${exc.id})">✏️</button>
                <button class="btn-delete" onclick="deleteExcecao(${exc.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== FAQ =====
async function loadFaq() {
    try {
        const response = await fetch(`${API_BASE}/panel/faq`);
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

    // Filtrar apenas FAQs ativos
    const faqsAtivos = faq.filter(item => item.ativo == 1);

    faqsAtivos.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${truncateText(item.pergunta, 50)}</td>
            <td>${item.categoria || '-'}</td>
            <td>${truncateText(item.palavras_chave, 30)}</td>
            <td>
                <button class="btn-edit" onclick="editFaq(${item.id})">✏️</button>
                <button class="btn-delete" onclick="deleteFaq(${item.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PAGAMENTOS =====
async function loadPagamentos() {
    try {
        const response = await fetch(`${API_BASE}/panel/pagamentos`);
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

    // Filtrar apenas pagamentos ativos
    const pagamentosAtivos = pagamentos.filter(pag => pag.ativo == 1);

    pagamentosAtivos.forEach(pag => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${pag.nome}</td>
            <td>${truncateText(pag.descricao, 40)}</td>
            <td>${pag.max_parcelas}x</td>
            <td>
                <button class="btn-edit" onclick="editPagamento(${pag.id})">✏️</button>
                <button class="btn-delete" onclick="deletePagamento(${pag.id})">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ===== PARCEIROS =====
async function loadParceiros() {
    try {
        const response = await fetch(`${API_BASE}/panel/parceiros`);
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

    // Filtrar apenas parceiros ativos
    const parceirosAtivos = parceiros.filter(parc => parc.ativo == 1);

    parceirosAtivos.forEach(parc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${parc.tipo || '-'}</td>
            <td>${parc.nome}</td>
            <td>${parc.endereco || '-'}</td>
            <td>${parc.telefone || '-'}</td>
            <td>
                <button class="btn-edit" onclick="editParceiro(${parc.id})">✏️</button>
                <button class="btn-delete" onclick="deleteParceiro(${parc.id})">🗑️</button>
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
    if (!dateString) return '-';
    
    // Para evitar problemas de timezone, vamos tratar a data como local
    // Se a data vier no formato YYYY-MM-DD, vamos criar a data corretamente
    if (dateString.match(/^\d{4}-\d{2}-\d{2}$/)) {
        const [year, month, day] = dateString.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return date.toLocaleDateString('pt-BR');
    }
    
    // Para outros formatos, usar o método original
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function truncateText(text, maxLength) {
    if (!text) return '-';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ===== FUNÇÕES DE MODAL =====
function showModal(title, content, actions = [], onModalReady = null) {
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
                    <button class="${action.class || 'btn-secondary'}" onclick="${action.onclick || action.action}">
                        ${action.text}
                    </button>
                `).join('')}
            </div>
        </div>
    `;

    document.getElementById('modalContainer').appendChild(modal);
    
    // Adicionar evento para fechar modal ao clicar fora
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Executa callback após o modal estar pronto
    if (onModalReady) {
        onModalReady();
    }
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
        const url = `${API_BASE}/panel/profissionais`;
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
        const response = await fetch(`${API_BASE}/panel/profissionais`, {
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
async function showServicoModal(id = null) {
    console.log('showServicoModal chamada com ID:', id);
    
    const title = id ? 'Editar Serviço' : 'Adicionar Serviço';
    const servico = id ? await getServicoById(id) : null;
    
    console.log('Serviço carregado para o modal:', servico);

    // Categorias fixas para o dropdown
    const categorias = [
        'Consultas',
        'Exames',
        'Procedimentos',
        'Tratamentos',
        'Acompanhamento',
        'Outros'
    ];

    const categoriaOptions = categorias.map(cat => 
        `<option value="${cat}" ${servico && servico.categoria === cat ? 'selected' : ''}>${cat}</option>`
    ).join('');

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
                <input type="text" id="valor" name="valor" value="${servico && servico.valor && !isNaN(parseFloat(servico.valor)) ? 'R$ ' + parseFloat(servico.valor).toFixed(2).replace('.', ',') : ''}" placeholder="0,00">
            </div>
            <div class="form-group">
                <label for="categoria">Categoria</label>
                <select id="categoria" name="categoria" onchange="toggleCategoriaOutros()">
                    <option value="">Selecione uma categoria</option>
                    ${categoriaOptions}
                </select>
            </div>
            <div class="form-group" id="categoriaOutrosGroup" style="display: none;">
                <label for="categoriaOutros">Especificar Categoria</label>
                <input type="text" id="categoriaOutros" name="categoriaOutros" placeholder="Digite a categoria personalizada">
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
            text: id ? 'Atualizar' : 'Adicionar',
            class: 'btn-primary',
            onclick: `handleServicoSubmit(${id || 'null'})`
        }
    ];

    showModal(title, content, actions, () => {
        // Aplicar máscara de moeda no campo valor
        const valorInput = document.getElementById('valor');
        if (valorInput) {
            applyCurrencyMask(valorInput);
        }
        
        // Verificar se deve mostrar o campo de categoria personalizada
        toggleCategoriaOutros();
        
        // Se estiver editando e a categoria não estiver na lista, mostrar como "Outros"
        if (servico && servico.categoria && !categorias.includes(servico.categoria)) {
            const categoriaSelect = document.getElementById('categoria');
            const categoriaOutrosInput = document.getElementById('categoriaOutros');
            if (categoriaSelect && categoriaOutrosInput) {
                categoriaSelect.value = 'Outros';
                categoriaOutrosInput.value = servico.categoria;
                toggleCategoriaOutros();
            }
        }
    });
}

// Função para mostrar/ocultar o campo de categoria personalizada
function toggleCategoriaOutros() {
    const categoriaSelect = document.getElementById('categoria');
    const categoriaOutrosGroup = document.getElementById('categoriaOutrosGroup');
    
    if (categoriaSelect && categoriaOutrosGroup) {
        if (categoriaSelect.value === 'Outros') {
            categoriaOutrosGroup.style.display = 'block';
            document.getElementById('categoriaOutros').focus();
        } else {
            categoriaOutrosGroup.style.display = 'none';
            document.getElementById('categoriaOutros').value = '';
        }
    }
}



async function getServicoById(id) {
    try {
        console.log('Buscando serviço com ID:', id);
        // Buscar dados completos do servidor
        const response = await fetch(`${API_BASE}/panel/servicos?id=${id}`);
        console.log('Response status:', response.status);
        
        const data = await response.json();
        console.log('Dados recebidos:', data);
        
        if (data.success && data.servico) {
            console.log('Serviço encontrado:', data.servico);
            return data.servico;
        }
        console.log('Serviço não encontrado ou erro na resposta');
        return null;
    } catch (error) {
        console.error('Erro ao buscar serviço:', error);
        return null;
    }
}

async function handleServicoSubmit(id = null) {
    const form = document.getElementById('servicoForm');
    const formData = new FormData(form);

    // Determinar a categoria final
    let categoria = formData.get('categoria');
    if (categoria === 'Outros') {
        const categoriaOutros = formData.get('categoriaOutros');
        categoria = categoriaOutros && categoriaOutros.trim() !== '' ? categoriaOutros.trim() : '';
    }

    const servicoData = {
        nome: formData.get('nome'),
        descricao: formData.get('descricao'),
        valor: parseCurrencyValue(formData.get('valor')),
        categoria: categoria,
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
        const response = await fetch(`${API_BASE}/panel/servicos`, {
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
    console.log('editServico chamada com ID:', id);
    await showServicoModal(id);
}

async function deleteServico(id) {
    if (!confirm('Tem certeza que deseja excluir este serviço?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/panel/servicos`, {
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
        const response = await fetch(`${API_BASE}/panel/convenios`, {
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
        const response = await fetch(`${API_BASE}/panel/convenios`, {
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
function showHorarioModal(id) {
    const title = 'Editar Horário';
    const horario = getHorarioById(id);

    const content = `
        <form id="horarioForm" class="modal-form">
            <div class="form-group">
                <label for="dia_semana">Dia da Semana</label>
                <input type="text" id="dia_semana" name="dia_semana" value="${horario ? horario.dia_semana : ''}" readonly>
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
                <label for="intervalo_minutos">Tempo da Consulta (minutos)</label>
                <input type="number" id="intervalo_minutos" name="intervalo_minutos" value="${horario ? horario.intervalo_minutos || '' : ''}" min="15" max="120">
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
            text: 'Atualizar',
            class: 'btn-primary',
            onclick: `handleHorarioSubmit(${id})`
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

            return {
                id: id,
                dia_semana: diaMap[diaSemana] || diaSemana.toLowerCase(),
                manha_inicio: row.dataset.manhaInicio || '',
                manha_fim: row.dataset.manhaFim || '',
                tarde_inicio: row.dataset.tardeInicio || '',
                tarde_fim: row.dataset.tardeFim || '',
                intervalo_minutos: row.dataset.intervaloMinutos ? parseInt(row.dataset.intervaloMinutos) : null,
                ativo: 1 // Apenas horários ativos são exibidos
            };
        }
    }
    return null;
}

async function handleHorarioSubmit(id) {
    const form = document.getElementById('horarioForm');
    const formData = new FormData(form);

    // Helper function to check if time is empty or "00:00"
    const isEmptyTime = (time) => !time || time.trim() === '' || time === '00:00';

    // Validação: se um campo da manhã estiver preenchido, o outro também deve estar
    const manhaInicio = formData.get('manha_inicio');
    const manhaFim = formData.get('manha_fim');
    const tardeInicio = formData.get('tarde_inicio');
    const tardeFim = formData.get('tarde_fim');

    const manhaInicioPreenchido = !isEmptyTime(manhaInicio);
    const manhaFimPreenchido = !isEmptyTime(manhaFim);
    const tardeInicioPreenchido = !isEmptyTime(tardeInicio);
    const tardeFimPreenchido = !isEmptyTime(tardeFim);

    // Validação para manhã
    if (manhaInicioPreenchido && !manhaFimPreenchido) {
        alert('Se o horário de início da manhã estiver preenchido, o horário de fim da manhã também deve estar preenchido.');
        return;
    }
    if (!manhaInicioPreenchido && manhaFimPreenchido) {
        alert('Se o horário de fim da manhã estiver preenchido, o horário de início da manhã também deve estar preenchido.');
        return;
    }

    // Validação para tarde
    if (tardeInicioPreenchido && !tardeFimPreenchido) {
        alert('Se o horário de início da tarde estiver preenchido, o horário de fim da tarde também deve estar preenchido.');
        return;
    }
    if (!tardeInicioPreenchido && tardeFimPreenchido) {
        alert('Se o horário de fim da tarde estiver preenchido, o horário de início da tarde também deve estar preenchido.');
        return;
    }

    const horarioData = {
        id: id,
        dia_semana: formData.get('dia_semana'),
        manha_inicio: isEmptyTime(manhaInicio) ? null : manhaInicio,
        manha_fim: isEmptyTime(manhaFim) ? null : manhaFim,
        tarde_inicio: isEmptyTime(tardeInicio) ? null : tardeInicio,
        tarde_fim: isEmptyTime(tardeFim) ? null : tardeFim,
        intervalo_minutos: formData.get('intervalo_minutos') && formData.get('intervalo_minutos').trim() !== '' ? parseInt(formData.get('intervalo_minutos')) : null,
        ativo: 1 // Sempre ativo, já que removemos o checkbox
    };
    
    try {
        const response = await fetch(`${API_BASE}/panel/horarios`, {
            method: 'PUT',
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
        const response = await fetch(`${API_BASE}/panel/horarios`, {
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

// ===== CRUD EXCEÇÕES =====
function showExcecaoModal(id = null) {
    const title = id ? 'Editar Exceção' : 'Adicionar Exceção';
    const excecao = id ? getExcecaoById(id) : null;
    
    const content = `
        <form id="excecaoForm" class="modal-form">
            <div class="form-group">
                <label for="data">Data *</label>
                <input type="date" id="data" name="data" value="${excecao ? excecao.data : ''}" required>
            </div>
            <div class="form-group">
                <label for="tipo">Tipo *</label>
                <select id="tipo" name="tipo" required>
                    <option value="">Selecione o tipo</option>
                    <option value="feriado" ${excecao && excecao.tipo === 'feriado' ? 'selected' : ''}>Feriado</option>
                    <option value="folga" ${excecao && excecao.tipo === 'folga' ? 'selected' : ''}>Folga</option>
                    <option value="fechado" ${excecao && excecao.tipo === 'fechado' ? 'selected' : ''}>Fechado</option>
                    <option value="evento" ${excecao && excecao.tipo === 'evento' ? 'selected' : ''}>Evento</option>
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
            onclick: id ? `handleExcecaoSubmit(${id})` : 'handleExcecaoSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

function getExcecaoById(id) {
    // Buscar a exceção na tabela atual
    const rows = document.querySelectorAll('#excecoesTableBody tr');
    for (let row of rows) {
        if (row.dataset.id === id.toString()) {
            return {
                id: id,
                data: row.dataset.data,
                tipo: row.dataset.tipo,
                descricao: row.dataset.descricao,
                ativo: 1 // Apenas exceções ativas são exibidas
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
        descricao: formData.get('descricao'),
        ativo: 1 // Sempre ativo para novas exceções
    };

    if (id) {
        excecaoData.id = parseInt(id);
    }

    try {
        const response = await fetch(`${API_BASE}/panel/excecoes`, {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(excecaoData)
        });

        const data = await response.json();

        if (data.success) {
            showMessage(data.message, 'success');
            closeModal();
            loadExcecoes(); // Recarregar tabela
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editExcecao(id) {
    showExcecaoModal(id);
}

async function deleteExcecao(id) {
    if (!confirm('Tem certeza que deseja desativar esta exceção?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/panel/excecoes`, {
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
            showMessage('Exceção desativada com sucesso!', 'success');
            loadExcecoes(); // Recarregar tabela
        } else {
            showMessage(data.message || 'Erro ao desativar exceção', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD FAQ =====
function showFaqModal(id = null) {
    const title = id ? 'Editar FAQ' : 'Adicionar FAQ';
    const faq = id ? getFaqById(id) : null;

    // Categorias específicas para FAQ
    const categorias = [
        'Consultas',
        'Exames',
        'Procedimentos',
        'Tratamentos',
        'Acompanhamento',
        'Convenios',
        'Financeiro',
        'Sintomas',
        'Outros'
    ];

    const categoriaOptions = categorias.map(cat => 
        `<option value="${cat}" ${faq && faq.categoria === cat ? 'selected' : ''}>${cat}</option>`
    ).join('');

    const content = `
        <form id="faqForm" class="modal-form">
            <div class="form-group">
                <label for="pergunta">Pergunta *</label>
                <textarea id="pergunta" name="pergunta" rows="3" required>${faq ? faq.pergunta : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="resposta">Resposta *</label>
                <textarea id="resposta" name="resposta" rows="5" required>${faq ? faq.resposta : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="categoria">Categoria</label>
                <select id="categoria" name="categoria" onchange="toggleCategoriaOutros()">
                    <option value="">Selecione uma categoria</option>
                    ${categoriaOptions}
                </select>
            </div>
            <div class="form-group" id="categoriaOutrosGroup" style="display: none;">
                <label for="categoriaOutros">Especificar Categoria</label>
                <input type="text" id="categoriaOutros" name="categoriaOutros" placeholder="Digite a categoria personalizada">
            </div>
            <div class="form-group">
                <label for="palavras_chave">Palavras-chave</label>
                <input type="text" id="palavras_chave" name="palavras_chave" value="${faq ? faq.palavras_chave || '' : ''}" placeholder="Separadas por vírgula">
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
            onclick: id ? `handleFaqSubmit(${id})` : 'handleFaqSubmit()'
        }
    ];
    
    showModal(title, content, actions, () => {
        // Verificar se deve mostrar o campo de categoria personalizada
        toggleCategoriaOutros();
        
        // Se estiver editando e a categoria não estiver na lista, mostrar como "Outros"
        if (faq && faq.categoria && !categorias.includes(faq.categoria)) {
            const categoriaSelect = document.getElementById('categoria');
            const categoriaOutrosInput = document.getElementById('categoriaOutros');
            if (categoriaSelect && categoriaOutrosInput) {
                categoriaSelect.value = 'Outros';
                categoriaOutrosInput.value = faq.categoria;
                toggleCategoriaOutros();
            }
        }
    });
}

function getFaqById(id) {
    // Buscar o FAQ na tabela atual
    const rows = document.querySelectorAll('#faqTableBody tr');
    for (let row of rows) {
        const editButton = row.querySelector('button[onclick*="editFaq"]');
        if (editButton) {
            const rowId = editButton.getAttribute('onclick').match(/\d+/)[0];
            if (rowId == id) {
                return {
                    id: id,
                    pergunta: row.cells[0].textContent,
                    resposta: '', // Será preenchido via API se necessário
                    categoria: row.cells[1].textContent === '-' ? '' : row.cells[1].textContent,
                    palavras_chave: row.cells[2].textContent === '-' ? '' : row.cells[2].textContent,
                    ativo: 1
                };
            }
        }
    }
    return null;
}

async function handleFaqSubmit(id = null) {
    const form = document.getElementById('faqForm');
    const formData = new FormData(form);

    // Determinar a categoria final (mesma lógica dos serviços)
    let categoria = formData.get('categoria');
    if (categoria === 'Outros') {
        const categoriaOutros = formData.get('categoriaOutros');
        categoria = categoriaOutros && categoriaOutros.trim() !== '' ? categoriaOutros.trim() : '';
    }

    const faqData = {
        pergunta: formData.get('pergunta'),
        resposta: formData.get('resposta'),
        categoria: categoria,
        palavras_chave: formData.get('palavras_chave'),
        ativo: 1
    };

    if (id) {
        faqData.id = parseInt(id);
    }

    try {
        const response = await fetch(`${API_BASE}/panel/faq`, {
            method: id ? 'PUT' : 'POST',
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
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editFaq(id) {
    showFaqModal(id);
}

async function deleteFaq(id) {
    if (!confirm('Tem certeza que deseja desativar este FAQ?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/panel/faq`, {
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
            showMessage('FAQ desativado com sucesso!', 'success');
            loadFaq();
        } else {
            showMessage(data.message || 'Erro ao desativar FAQ', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD PAGAMENTOS =====
function showPagamentoModal(id = null) {
    const title = id ? 'Editar Forma de Pagamento' : 'Adicionar Forma de Pagamento';
    const pagamento = id ? getPagamentoById(id) : null;
    
    const content = `
        <form id="pagamentoForm" class="modal-form">
            <div class="form-group">
                <label for="nome">Nome *</label>
                <input type="text" id="nome" name="nome" value="${pagamento ? pagamento.nome : ''}" required>
            </div>
            <div class="form-group">
                <label for="descricao">Descrição</label>
                <textarea id="descricao" name="descricao" rows="3">${pagamento ? pagamento.descricao || '' : ''}</textarea>
            </div>
            <div class="form-group">
                <label for="max_parcelas">Máximo de Parcelas</label>
                <input type="number" id="max_parcelas" name="max_parcelas" value="${pagamento ? pagamento.max_parcelas || 1 : 1}" min="1" max="12">
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
            onclick: id ? `handlePagamentoSubmit(${id})` : 'handlePagamentoSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

function getPagamentoById(id) {
    // Buscar o pagamento na tabela atual
    const rows = document.querySelectorAll('#pagamentosTableBody tr');
    for (let row of rows) {
        const editButton = row.querySelector('button[onclick*="editPagamento"]');
        if (editButton) {
            const rowId = editButton.getAttribute('onclick').match(/\d+/)[0];
            if (rowId == id) {
                return {
                    id: id,
                    nome: row.cells[0].textContent,
                    descricao: row.cells[1].textContent,
                    max_parcelas: parseInt(row.cells[2].textContent.replace('x', '')),
                    ativo: 1
                };
            }
        }
    }
    return null;
}

async function handlePagamentoSubmit(id = null) {
    const form = document.getElementById('pagamentoForm');
    const formData = new FormData(form);

    const pagamentoData = {
        nome: formData.get('nome'),
        descricao: formData.get('descricao'),
        max_parcelas: parseInt(formData.get('max_parcelas')),
        ativo: 1
    };

    if (id) {
        pagamentoData.id = parseInt(id);
    }

    try {
        const response = await fetch(`${API_BASE}/panel/pagamentos`, {
            method: id ? 'PUT' : 'POST',
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
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editPagamento(id) {
    showPagamentoModal(id);
}

async function deletePagamento(id) {
    if (!confirm('Tem certeza que deseja desativar esta forma de pagamento?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/panel/pagamentos`, {
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
            showMessage('Forma de pagamento desativada com sucesso!', 'success');
            loadPagamentos();
        } else {
            showMessage(data.message || 'Erro ao desativar forma de pagamento', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// ===== CRUD PARCEIROS =====
function showParceiroModal(id = null) {
    const title = id ? 'Editar Parceiro' : 'Adicionar Parceiro';
    const parceiro = id ? getParceiroById(id) : null;
    
    const content = `
        <form id="parceiroForm" class="modal-form">
            <div class="form-group">
                <label for="tipo">Tipo *</label>
                <select id="tipo" name="tipo" required>
                    <option value="">Selecione o tipo</option>
                    <option value="laboratorio" ${parceiro && parceiro.tipo === 'laboratorio' ? 'selected' : ''}>Laboratório</option>
                    <option value="farmacia" ${parceiro && parceiro.tipo === 'farmacia' ? 'selected' : ''}>Farmácia</option>
                    <option value="hospital" ${parceiro && parceiro.tipo === 'hospital' ? 'selected' : ''}>Hospital</option>
                    <option value="clinica" ${parceiro && parceiro.tipo === 'clinica' ? 'selected' : ''}>Clínica</option>
                    <option value="outro" ${parceiro && parceiro.tipo === 'outro' ? 'selected' : ''}>Outro</option>
                </select>
            </div>
            <div class="form-group">
                <label for="nome">Nome *</label>
                <input type="text" id="nome" name="nome" value="${parceiro ? parceiro.nome : ''}" required>
            </div>
            <div class="form-group">
                <label for="endereco">Endereço</label>
                <input type="text" id="endereco" name="endereco" value="${parceiro ? parceiro.endereco || '' : ''}">
            </div>
            <div class="form-group">
                <label for="telefone">Telefone</label>
                <input type="tel" id="telefone" name="telefone" value="${parceiro ? parceiro.telefone || '' : ''}">
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
            onclick: id ? `handleParceiroSubmit(${id})` : 'handleParceiroSubmit()'
        }
    ];
    
    showModal(title, content, actions);
}

function getParceiroById(id) {
    // Buscar o parceiro na tabela atual
    const rows = document.querySelectorAll('#parceirosTableBody tr');
    for (let row of rows) {
        const editButton = row.querySelector('button[onclick*="editParceiro"]');
        if (editButton) {
            const rowId = editButton.getAttribute('onclick').match(/\d+/)[0];
            if (rowId == id) {
                return {
                    id: id,
                    tipo: row.cells[0].textContent === '-' ? '' : row.cells[0].textContent,
                    nome: row.cells[1].textContent,
                    endereco: row.cells[2].textContent === '-' ? '' : row.cells[2].textContent,
                    telefone: row.cells[3].textContent === '-' ? '' : row.cells[3].textContent,
                    ativo: 1
                };
            }
        }
    }
    return null;
}

async function handleParceiroSubmit(id = null) {
    const form = document.getElementById('parceiroForm');
    const formData = new FormData(form);

    const parceiroData = {
        tipo: formData.get('tipo'),
        nome: formData.get('nome'),
        endereco: formData.get('endereco'),
        telefone: formData.get('telefone'),
        ativo: 1
    };

    if (id) {
        parceiroData.id = parseInt(id);
    }

    try {
        const response = await fetch(`${API_BASE}/panel/parceiros`, {
            method: id ? 'PUT' : 'POST',
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
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

async function editParceiro(id) {
    showParceiroModal(id);
}

async function deleteParceiro(id) {
    if (!confirm('Tem certeza que deseja desativar este parceiro?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/panel/parceiros`, {
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
            showMessage('Parceiro desativado com sucesso!', 'success');
            loadParceiros();
        } else {
            showMessage(data.message || 'Erro ao desativar parceiro', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão', 'error');
    }
}

// Função para testar conexão
async function testConnection() {
    try {
        const response = await fetch(`${API_BASE}/panel/configuracoes`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || 'Falha no teste');
        }

        return data;
    } catch (error) {
        showMessage('Erro no teste de conexão', 'error');
        throw error;
    }
}

// ===== NAVEGAÇÃO DOS TABS =====
function initializeTabNavigation() {
    const tabsContainer = document.querySelector('.tabs-container');
    const prevBtn = document.querySelector('.tab-nav-btn.prev');
    const nextBtn = document.querySelector('.tab-nav-btn.next');
    
    if (!tabsContainer || !prevBtn || !nextBtn) return;
    
    // Verificar se precisa mostrar os botões
    function checkScrollButtons() {
        const isScrollable = tabsContainer.scrollWidth > tabsContainer.clientWidth;
        const isAtStart = tabsContainer.scrollLeft <= 0;
        const isAtEnd = tabsContainer.scrollLeft >= tabsContainer.scrollWidth - tabsContainer.clientWidth;
        
        prevBtn.classList.toggle('visible', isScrollable && !isAtStart);
        nextBtn.classList.toggle('visible', isScrollable && !isAtEnd);
    }
    
    // Verificar na inicialização
    checkScrollButtons();
    
    // Verificar no resize da janela
    window.addEventListener('resize', checkScrollButtons);
    
    // Verificar no scroll
    tabsContainer.addEventListener('scroll', checkScrollButtons);
}

function scrollTabs(direction) {
    const tabsContainer = document.querySelector('.tabs-container');
    if (!tabsContainer) return;
    
    const scrollAmount = 200; // Quantidade de pixels para scrollar
    const currentScroll = tabsContainer.scrollLeft;
    
    if (direction === 'prev') {
        tabsContainer.scrollTo({
            left: currentScroll - scrollAmount,
            behavior: 'smooth'
        });
    } else if (direction === 'next') {
        tabsContainer.scrollTo({
            left: currentScroll + scrollAmount,
            behavior: 'smooth'
        });
    }
}

// Carregar dados quando a página carregar
document.addEventListener('DOMContentLoaded', function () {
    // Testar conexão primeiro
    testConnection().then(() => {
        loadConfiguracoes();
        loadAllData();
    }).catch(error => {
        showMessage('Erro na conexão com o banco de dados', 'error');
    });
}); 