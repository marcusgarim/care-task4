// Smart Schedule - Painel Administrativo (JS do mock com roteamento por hash)

function apiBase() {
  return (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
}

function authHeaders() {
  var headers = {};
  try {
    if (!window.CONFIG) window.CONFIG = {};
    if (!window.CONFIG.AUTH_TOKEN) {
      var t = localStorage.getItem('app_token');
      if (t) window.CONFIG.AUTH_TOKEN = t;
    }
    
    // Fallback para desenvolvimento - usar token de teste se não houver autenticação
    if (!window.CONFIG.AUTH_TOKEN) {
      window.CONFIG.AUTH_TOKEN = 'test-token';
      console.log('Usando token de teste para desenvolvimento');
    }
  } catch(e) {}
  
  if (window.CONFIG && window.CONFIG.AUTH_TOKEN) {
    headers['Authorization'] = 'Bearer ' + window.CONFIG.AUTH_TOKEN;
  }
  return headers;
}

async function ensureAuthenticated() {
  try {
    // Primeiro verifica se está autenticado
    var checkAuthRes = await fetch(apiBase() + '/auth/check-auth', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!checkAuthRes.ok) {
      throw new Error('unauthorized');
    }
    
    var authData = await checkAuthRes.json();
    
    if (!authData.success || !authData.authenticated || !authData.user) {
      // Não está logado - redireciona para login
      window.location.href = 'login.html';
      return false;
    }
    
    // Atualiza info do usuário na interface
    var ui = document.querySelector('.user-info span');
    if (ui && authData.user && (authData.user.name || authData.user.email)) {
      ui.textContent = authData.user.name || authData.user.email;
    }
    
    // Verifica se tem permissão de admin
    if (!(authData.user.is_admin === true || authData.user.is_admin === 1)) {
      renderAccessDenied();
      return false;
    }
    
    // Verifica especificamente o endpoint de admin para dupla verificação
    var checkAdminRes = await fetch(apiBase() + '/auth/check-admin', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!checkAdminRes.ok) {
      renderAccessDenied();
      return false;
    }
    
    var adminData = await checkAdminRes.json();
    if (!adminData.success || !adminData.is_admin) {
      renderAccessDenied();
      return false;
    }
    
    return true;
  } catch (e) {
    window.location.href = 'login.html';
    return false;
  }
}

function renderAccessDenied() {
  var content = document.querySelector('.content-area');
  if (!content) return;
  content.innerHTML = '' +
    '<div style="display:flex;align-items:center;justify-content:center;height:calc(100vh - 64px);">' +
    '  <div style="max-width:520px;text-align:center;padding:24px;">' +
    '    <h1 style="margin:0 0 8px 0;">Acesso negado</h1>' +
    '    <p style="color:#666;margin:0 0 16px 0;">Sua conta não possui permissão de administrador para acessar este painel.</p>' +
    '    <div style="display:flex;gap:12px;justify-content:center;">' +
    '      <a href="index.html" class="header-btn">Voltar ao chat</a>' +
    '    </div>' +
    '  </div>' +
    '</div>';
}

function showTab(tabName) {
  document.querySelectorAll('.tab-section').forEach(function(tab){ tab.classList.remove('active'); });
  var selected = document.getElementById(tabName + '-tab');
  if (selected) selected.classList.add('active');
  // Atualiza seleção no menu lateral
  document.querySelectorAll('.nav-item').forEach(function(item){ item.classList.remove('active'); });
  var activeLink = document.querySelector('.nav-item[href="#' + tabName + '"]');
  if (activeLink) activeLink.classList.add('active');
  var ca = document.querySelector('.content-area');
  if (ca) ca.scrollTop = 0;
  
  // Carregar dados específicos da aba
  loadTabData(tabName);
}

async function loadTabData(tabName) {
  switch(tabName) {
    case 'convenios':
      await loadConvenios();
      break;
    case 'profissionais':
      await loadProfissionais();
      break;
    case 'servicos':
      await loadServicos();
      break;
    case 'faq':
      await loadFAQ();
      break;
    case 'pagamentos':
      await loadPagamentos();
      break;
    case 'parceiros':
      await loadParceiros();
      break;
    // case 'horarios': removido - integrado com Google Calendar
    case 'agenda':
      await loadAgenda();
      break;
    case 'agendamentos':
      await loadAgendamentos();
      break;
    
  }
}

async function loadConvenios() {
  try {
    var response = await fetch(apiBase() + '/panel/convenios', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar convênios');
    
    var data = await response.json();
    if (data.success && data.convenios) {
      renderConveniosTable(data.convenios);
    }
  } catch (e) {
    console.error('Erro ao carregar convênios:', e);
    showToast('Erro ao carregar convênios', 'error');
  }
}

function renderConveniosTable(convenios) {
  var tbody = document.querySelector('#convenios-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (convenios.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p class="empty-text">Nenhum convênio cadastrado</p></div></td></tr>';
    return;
  }
  
  convenios.forEach(function(conv) {
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${conv.nome}</td>
      <td>${conv.registro_ans || '-'}</td>
      <td>-</td>
      <td><span class="status-badge ${conv.ativo ? 'active' : 'inactive'}">${conv.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editConvenio(${conv.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deleteConvenio(${conv.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function loadProfissionais() {
  try {
    var response = await fetch(apiBase() + '/panel/profissionais', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar profissionais');
    
    var data = await response.json();
    if (data.success && data.profissionais) {
      renderProfissionaisTable(data.profissionais);
    }
  } catch (e) {
    console.error('Erro ao carregar profissionais:', e);
    showToast('Erro ao carregar profissionais', 'error');
  }
}

function renderProfissionaisTable(profissionais) {
  var tbody = document.querySelector('#profissionais-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (profissionais.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p class="empty-text">Nenhum profissional cadastrado</p></div></td></tr>';
    return;
  }
  
  profissionais.forEach(function(prof) {
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${prof.nome}</td>
      <td>${prof.especialidade || '-'}</td>
      <td>${prof.crm || '-'}</td>
      <td>${prof.telefone || '-'}</td>
      <td><span class="status-badge ${prof.ativo ? 'active' : 'inactive'}">${prof.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editProfissional(${prof.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deleteProfissional(${prof.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function loadServicos() {
  try {
    var response = await fetch(apiBase() + '/panel/servicos', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar serviços');
    
    var data = await response.json();
    if (data.success && data.servicos) {
      renderServicosTable(data.servicos);
    }
  } catch (e) {
    console.error('Erro ao carregar serviços:', e);
    showToast('Erro ao carregar serviços', 'error');
  }
}

function renderServicosTable(servicos) {
  var tbody = document.querySelector('#servicos-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (servicos.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p class="empty-text">Nenhum serviço cadastrado</p></div></td></tr>';
    return;
  }
  
  servicos.forEach(function(servico) {
    var preco = servico.valor ? `R$ ${parseFloat(servico.valor).toFixed(2)}` : '-';
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${servico.nome}</td>
      <td>${servico.categoria || '-'}</td>
      <td>${preco}</td>
      <td>${servico.local_realizacao || '-'}</td>
      <td><span class="status-badge ${servico.ativo ? 'active' : 'inactive'}">${servico.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editServico(${servico.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deleteServico(${servico.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function loadFAQ() {
  try {
    var response = await fetch(apiBase() + '/panel/faq', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar FAQ');
    
    var data = await response.json();
    if (data.success && data.faqs) {
      renderFAQTable(data.faqs);
    }
  } catch (e) {
    console.error('Erro ao carregar FAQ:', e);
    showToast('Erro ao carregar FAQ', 'error');
  }
}

function renderFAQTable(faqs) {
  var tbody = document.querySelector('#faq-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (faqs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p class="empty-text">Nenhuma pergunta cadastrada</p></div></td></tr>';
    return;
  }
  
  faqs.forEach(function(faq) {
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${faq.pergunta}</td>
      <td>${faq.categoria || '-'}</td>
      <td>${faq.palavras_chave || '-'}</td>
      <td><span class="status-badge ${faq.ativo ? 'active' : 'inactive'}">${faq.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editFAQ(${faq.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deleteFAQ(${faq.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function editConvenio(id) {
  showToast('Função de edição será implementada', 'info');
}

function deleteConvenio(id) {
  if (!confirm('Deseja realmente excluir este convênio?')) return;
  
  fetch(apiBase() + '/panel/convenios/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('Convênio excluído com sucesso', 'success');
      loadConvenios(); // Recarregar lista
    } else {
      showToast('Erro ao excluir convênio', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir convênio', 'error');
  });
}

function editFAQ(id) {
  showToast('Função de edição FAQ será implementada', 'info');
}

function deleteFAQ(id) {
  if (!confirm('Deseja realmente excluir esta FAQ?')) return;
  
  fetch(apiBase() + '/panel/faq/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('FAQ excluída com sucesso', 'success');
      loadFAQ(); // Recarregar lista
    } else {
      showToast('Erro ao excluir FAQ', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir FAQ', 'error');
  });
}

function editProfissional(id) {
  showToast('Função de edição profissional será implementada', 'info');
}

function deleteProfissional(id) {
  if (!confirm('Deseja realmente excluir este profissional?')) return;
  
  fetch(apiBase() + '/panel/profissionais/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('Profissional excluído com sucesso', 'success');
      loadProfissionais(); // Recarregar lista
    } else {
      showToast('Erro ao excluir profissional', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir profissional', 'error');
  });
}

function editServico(id) {
  showToast('Função de edição serviço será implementada', 'info');
}

function deleteServico(id) {
  if (!confirm('Deseja realmente excluir este serviço?')) return;
  
  fetch(apiBase() + '/panel/servicos/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('Serviço excluído com sucesso', 'success');
      loadServicos(); // Recarregar lista
    } else {
      showToast('Erro ao excluir serviço', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir serviço', 'error');
  });
}

async function loadPagamentos() {
  try {
    var response = await fetch(apiBase() + '/panel/pagamentos', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar pagamentos');
    
    var data = await response.json();
    if (data.success && data.pagamentos) {
      renderPagamentosTable(data.pagamentos);
    }
  } catch (e) {
    console.error('Erro ao carregar pagamentos:', e);
    showToast('Erro ao carregar pagamentos', 'error');
  }
}

function renderPagamentosTable(pagamentos) {
  var tbody = document.querySelector('#pagamentos-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (pagamentos.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p class="empty-text">Nenhuma forma de pagamento cadastrada</p></div></td></tr>';
    return;
  }
  
  pagamentos.forEach(function(pagamento) {
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${pagamento.nome}</td>
      <td>${pagamento.descricao || '-'}</td>
      <td>${pagamento.max_parcelas || '1'}x</td>
      <td><span class="status-badge ${pagamento.ativo ? 'active' : 'inactive'}">${pagamento.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editPagamento(${pagamento.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deletePagamento(${pagamento.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function loadParceiros() {
  try {
    var response = await fetch(apiBase() + '/panel/parceiros', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar parceiros');
    
    var data = await response.json();
    if (data.success && data.parceiros) {
      renderParceirosTable(data.parceiros);
    }
  } catch (e) {
    console.error('Erro ao carregar parceiros:', e);
    showToast('Erro ao carregar parceiros', 'error');
  }
}

function renderParceirosTable(parceiros) {
  var tbody = document.querySelector('#parceiros-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (parceiros.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p class="empty-text">Nenhum parceiro cadastrado</p></div></td></tr>';
    return;
  }
  
  parceiros.forEach(function(parceiro) {
    var row = document.createElement('tr');
    row.innerHTML = `
      <td>${parceiro.nome}</td>
      <td>${parceiro.tipo || '-'}</td>
      <td>${parceiro.endereco || '-'}</td>
      <td>${parceiro.telefone || '-'}</td>
      <td><span class="status-badge ${parceiro.ativo ? 'active' : 'inactive'}">${parceiro.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editParceiro(${parceiro.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="action-btn delete" onclick="deleteParceiro(${parceiro.id})">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function editPagamento(id) {
  showToast('Função de edição pagamento será implementada', 'info');
}

function deletePagamento(id) {
  if (!confirm('Deseja realmente excluir esta forma de pagamento?')) return;
  
  fetch(apiBase() + '/panel/pagamentos/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('Forma de pagamento excluída com sucesso', 'success');
      loadPagamentos(); // Recarregar lista
    } else {
      showToast('Erro ao excluir forma de pagamento', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir forma de pagamento', 'error');
  });
}

function editParceiro(id) {
  showToast('Função de edição parceiro será implementada', 'info');
}

function deleteParceiro(id) {
  if (!confirm('Deseja realmente excluir este parceiro?')) return;
  
  fetch(apiBase() + '/panel/parceiros/' + id, {
    method: 'DELETE',
    credentials: 'include',
    headers: authHeaders()
  })
  .then(function(response) {
    if (response.ok) {
      showToast('Parceiro excluído com sucesso', 'success');
      loadParceiros(); // Recarregar lista
    } else {
      showToast('Erro ao excluir parceiro', 'error');
    }
  })
  .catch(function() {
    showToast('Erro ao excluir parceiro', 'error');
  });
}

function applyRoute() {
  var hash = (location.hash || '#dashboard');
  var tab = hash.replace('#','');
  showTab(tab);
}

function toggleSidebar() {
  var sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('hidden');
}

// Funções para Horários
async function loadHorarios() {
  try {
    // Carregar profissionais no select primeiro
    await loadProfissionaisHorarios();
    
    var response = await fetch(apiBase() + '/panel/horarios', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar horários');
    
    var data = await response.json();
    if (data.success && data.profissionais) {
      renderHorariosTable(data.profissionais);
    }
  } catch (e) {
    console.error('Erro ao carregar horários:', e);
    showToast('Erro ao carregar horários', 'error');
  }
}

async function loadProfissionaisHorarios() {
  try {
    var response = await fetch(apiBase() + '/panel/profissionais', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar profissionais');
    
    var data = await response.json();
    var select = document.getElementById('hor_profissional');
    
    if (select && data.success && data.profissionais) {
      select.innerHTML = '<option value="">Selecione um profissional</option>';
      data.profissionais.forEach(function(prof) {
        if (prof.ativo) {
          var option = document.createElement('option');
          option.value = prof.id;
          option.textContent = `${prof.nome} - ${prof.especialidade || 'Especialidade não informada'}`;
          select.appendChild(option);
        }
      });
    }
  } catch (e) {
    console.error('Erro ao carregar profissionais para horários:', e);
  }
}

function renderHorariosTable(profissionais) {
  var tbody = document.querySelector('#horarios-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (profissionais.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p class="empty-text">Nenhum horário configurado</p></div></td></tr>';
    return;
  }
  
  profissionais.forEach(function(prof) {
    // Agrupar horários por dia da semana
    var horariosPorDia = {};
    var diasSemana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
    
    prof.horarios.forEach(function(horario) {
      var dia = horario.dia_semana_nome;
      if (!horariosPorDia[dia]) {
        horariosPorDia[dia] = [];
      }
      horariosPorDia[dia].push(horario);
    });
    
    // Criar linha para cada profissional
    var row = document.createElement('tr');
    row.innerHTML = `
      <td rowspan="${Math.max(1, diasSemana.length)}" style="vertical-align: top; border-right: 1px solid #e5e7eb;">
        <strong>${prof.profissional_nome}</strong>
      </td>
    `;
    tbody.appendChild(row);
    
    // Adicionar horários por dia
    diasSemana.forEach(function(dia, index) {
      var diaRow = index === 0 ? row : document.createElement('tr');
      
      if (index > 0) {
        tbody.appendChild(diaRow);
      }
      
      var horariosDoDia = horariosPorDia[dia] || [];
      var horarioInfo = '';
      
      if (horariosDoDia.length === 0) {
        horarioInfo = '<span class="text-gray-400">Não configurado</span>';
      } else {
        horariosDoDia.forEach(function(h) {
          if (h.tipo_atendimento === 'indisponivel') {
            horarioInfo += '<span class="status-badge inactive">Indisponível</span>';
          } else {
            var intervalo = '';
            if (h.intervalo_inicio && h.intervalo_fim) {
              intervalo = ` (Intervalo: ${h.intervalo_inicio} - ${h.intervalo_fim})`;
            }
            horarioInfo += `
              <div class="mb-1">
                <span class="font-medium">${h.hora_inicio} - ${h.hora_fim}</span>
                <span class="text-sm text-gray-600">${intervalo}</span>
                <br><span class="status-badge ${h.tipo_atendimento === 'presencial' ? 'active' : h.tipo_atendimento === 'remoto' ? 'pending' : 'warning'}">${h.tipo_atendimento_nome}</span>
              </div>
            `;
          }
        });
      }
      
      diaRow.innerHTML += `
        <td>${dia}</td>
        <td>${horarioInfo}</td>
        <td>${horariosDoDia.length > 0 ? horariosDoDia[0].duracao_consulta + ' min' : '-'}</td>
        <td><span class="status-badge active">Ativo</span></td>
        <td>
          <div class="action-buttons">
            <button class="action-btn edit" onclick="editarHorariosProfissional(${prof.profissional_id})" title="Editar horários">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button class="action-btn view" onclick="visualizarAgenda(${prof.profissional_id})" title="Ver agenda">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </button>
          </div>
        </td>
      `;
    });
  });
}

function editarHorariosProfissional(profissionalId) {
  showToast('Editor de horários será implementado', 'info');
  // TODO: Implementar modal de edição de horários
}

function visualizarAgenda(profissionalId) {
  showToast('Visualizador de agenda será implementado', 'info');
  // TODO: Implementar visualizador de agenda
}

// Funções para Agenda Integrada - Interface Moderna
async function loadAgenda() {
  try {
    console.log('Carregando nova interface da agenda...');
    
    // Configurar data inicial
    setupDateControls();
    
    // Configurar ações rápidas
    setupQuickActions();
    
    // Verificar status da integração
    await checkCalendarStatus();
    
    // Carregar data de hoje
    const today = new Date().toISOString().split('T')[0];
    await loadScheduleForDate(today);
    
    // Configurar interface
    setupAgendaInterface();
    
    // Carregar próximos horários
    await loadNextAvailableSlots();
    
    console.log('Nova interface da agenda carregada!');
    
  } catch (e) {
    console.error('Erro ao carregar agenda:', e);
    showToast('Erro ao carregar agenda integrada', 'error');
  }
}

async function checkCalendarStatus() {
  try {
    var response = await fetch(apiBase() + '/panel/agenda/status', {
      method: 'GET',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) throw new Error('Erro ao verificar status');
    
    var data = await response.json();
    updateCalendarStatusUI(data.status);
    
    // Forçar atualização do status bar moderno
    setTimeout(() => {
      updateModernStatusBar(data.status);
    }, 100);
    
    return data.status;
  } catch (e) {
    console.error('Erro ao verificar status do calendário:', e);
    showToast('Erro ao verificar Google Calendar', 'error');
    return null;
  }
}

function updateCalendarStatusUI(status) {
  var statusElement = document.querySelector('#calendar-status');
  if (!statusElement) return;
  
  if (status.google_calendar_connected && status.smart_test_calendar_found) {
    statusElement.innerHTML = `
      <div class="status-success">
        <i class="icon">✓</i>
        <span>Google Calendar conectado - Agenda Smart Test encontrada</span>
      </div>
    `;
  } else if (status.google_calendar_connected && !status.smart_test_calendar_found) {
    statusElement.innerHTML = `
      <div class="status-warning">
        <i class="icon">⚠</i>
        <span>Google Calendar conectado - Agenda Smart Test não encontrada</span>
      </div>
    `;
  } else {
    statusElement.innerHTML = `
      <div class="status-error">
        <i class="icon">✗</i>
        <span>Google Calendar não conectado</span>
        <div class="setup-instructions">
          <p>Para configurar:</p>
          <ol>
            <li>Execute a autenticação OAuth</li>
            <li>Compartilhe a agenda Smart Test</li>
            <li>Verifique o token em scripts/token_suporte.json</li>
          </ol>
        </div>
      </div>
    `;
  }
  
  // Atualizar também o status bar moderno
  updateModernStatusBar(status);
}

function updateModernStatusBar(status) {
  const statusBar = document.getElementById('calendar-status-bar');
  const statusDot = statusBar?.querySelector('.status-dot');
  const statusText = statusBar?.querySelector('.status-text');
  const setupBtn = statusBar?.querySelector('#btn-setup-calendar');
  
  if (!statusBar) return;
  
  if (status.google_calendar_connected && status.smart_test_calendar_found) {
    statusDot.className = 'status-dot';
    statusText.textContent = 'Conectado - Smart Test ativa';
    setupBtn.style.display = 'none';
  } else if (status.google_calendar_connected && !status.smart_test_calendar_found) {
    statusDot.className = 'status-dot warning';
    statusText.textContent = 'Conectado - Smart Test não encontrada';
    setupBtn.style.display = 'block';
  } else {
    statusDot.className = 'status-dot error';
    statusText.textContent = 'Desconectado - Modo demo';
    setupBtn.style.display = 'block';
  }
}

async function loadAgendaDisponibilidade() {
  try {
    // Carregar disponibilidade para hoje
    var hoje = new Date().toISOString().split('T')[0];
    
    var response = await fetch(apiBase() + `/panel/agenda/disponibilidade?data=${hoje}`, {
      method: 'GET',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) throw new Error('Erro ao carregar disponibilidade');
    
    var data = await response.json();
    
    if (data.success) {
      renderAgendaDisponibilidade(data);
    } else {
      throw new Error(data.message);
    }
    
  } catch (e) {
    console.error('Erro ao carregar disponibilidade:', e);
    showToast('Erro ao carregar disponibilidade da agenda', 'error');
  }
}

function renderAgendaDisponibilidade(data) {
  var container = document.querySelector('#agenda-disponibilidade');
  if (!container) return;
  
  if (data.available_slots && data.available_slots.length > 0) {
    var slotsHtml = data.available_slots.map(slot => `
      <div class="time-slot available" onclick="agendarHorario('${slot.datetime}')">
        <span class="time">${slot.start} - ${slot.end}</span>
        <span class="status">Disponível</span>
      </div>
    `).join('');
    
    container.innerHTML = `
      <h3>Disponibilidade para ${data.date}</h3>
      <div class="slots-grid">
        ${slotsHtml}
      </div>
      <div class="agenda-stats">
        <span>Horários disponíveis: ${data.total_available}</span>
        <span>Horários ocupados: ${data.total_occupied || 0}</span>
      </div>
    `;
  } else {
    container.innerHTML = `
      <h3>Disponibilidade para ${data.date}</h3>
      <div class="empty-state">
        <p>Nenhum horário disponível hoje</p>
      </div>
    `;
  }
}

function setupAgendaInterface() {
  // Configurar seletor de data
  var dataInput = document.querySelector('#agenda-data-selector');
  if (dataInput) {
    dataInput.addEventListener('change', function() {
      loadAgendaDisponibilidadeData(this.value);
    });
  }
  
  // Configurar botões de ação
  setupAgendaButtons();
}

function setupAgendaButtons() {
  var btnProximosHorarios = document.querySelector('#btn-proximos-horarios');
  if (btnProximosHorarios) {
    btnProximosHorarios.addEventListener('click', loadProximosHorarios);
  }
  
  var btnNovoAgendamento = document.querySelector('#btn-novo-agendamento-calendar');
  if (btnNovoAgendamento) {
    btnNovoAgendamento.addEventListener('click', abrirModalNovoAgendamentoCalendar);
  }
}

async function loadAgendaDisponibilidadeData(data) {
  try {
    var response = await fetch(apiBase() + `/panel/agenda/disponibilidade?data=${data}`, {
      method: 'GET',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) throw new Error('Erro ao carregar disponibilidade');
    
    var result = await response.json();
    
    if (result.success) {
      renderAgendaDisponibilidade(result);
    } else {
      throw new Error(result.message);
    }
    
  } catch (e) {
    console.error('Erro ao carregar disponibilidade:', e);
    showToast('Erro ao carregar disponibilidade', 'error');
  }
}

async function loadProximosHorarios() {
  try {
    var response = await fetch(apiBase() + '/panel/agenda/proximos-horarios?limite=10', {
      method: 'GET',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) throw new Error('Erro ao carregar próximos horários');
    
    var data = await response.json();
    
    if (data.success) {
      renderProximosHorarios(data.proximos_horarios);
    } else {
      throw new Error(data.message);
    }
    
  } catch (e) {
    console.error('Erro ao carregar próximos horários:', e);
    showToast('Erro ao carregar próximos horários', 'error');
  }
}

function renderProximosHorarios(horarios) {
  var container = document.querySelector('#proximos-horarios-list');
  if (!container) return;
  
  if (horarios.length > 0) {
    var horariosHtml = horarios.map(horario => `
      <div class="proximo-horario" onclick="agendarHorario('${horario.datetime_completo}')">
        <div class="data">${horario.data_formatada}</div>
        <div class="horario">${horario.horario_inicio} - ${horario.horario_fim}</div>
        <div class="dia-semana">${horario.dia_semana}</div>
      </div>
    `).join('');
    
    container.innerHTML = `
      <h4>Próximos Horários Disponíveis</h4>
      <div class="horarios-grid">
        ${horariosHtml}
      </div>
    `;
  } else {
    container.innerHTML = `
      <h4>Próximos Horários Disponíveis</h4>
      <div class="empty-state">
        <p>Nenhum horário disponível nos próximos dias</p>
      </div>
    `;
  }
}

function agendarHorario(datetime) {
  // Pré-popular o modal de agendamento com a data/hora selecionada
  var modal = document.querySelector('#modal-agendamento-calendar');
  if (modal) {
    var date = new Date(datetime);
    var dataInput = modal.querySelector('#agendamento-data');
    var horaInput = modal.querySelector('#agendamento-hora');
    
    if (dataInput) dataInput.value = date.toISOString().split('T')[0];
    if (horaInput) horaInput.value = date.toTimeString().substring(0, 5);
    
    modal.style.display = 'block';
  } else {
    abrirModalNovoAgendamentoCalendar(datetime);
  }
}

function abrirModalNovoAgendamentoCalendar(datetime = null) {
  var modal = document.createElement('div');
  modal.className = 'modal';
  modal.id = 'modal-agendamento-calendar';
  
  var defaultDate = '';
  var defaultTime = '';
  
  if (datetime) {
    var date = new Date(datetime);
    defaultDate = date.toISOString().split('T')[0];
    defaultTime = date.toTimeString().substring(0, 5);
  }
  
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>Novo Agendamento - Google Calendar</h3>
        <span class="close" onclick="fecharModal('modal-agendamento-calendar')">&times;</span>
      </div>
      <div class="modal-body">
        <form id="form-agendamento-calendar">
          <div class="form-group">
            <label for="agendamento-titulo">Título do Agendamento:</label>
            <input type="text" id="agendamento-titulo" name="titulo" required>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label for="agendamento-data">Data:</label>
              <input type="date" id="agendamento-data" name="data_consulta" value="${defaultDate}" required>
            </div>
            <div class="form-group">
              <label for="agendamento-hora-inicio">Hora Início:</label>
              <input type="time" id="agendamento-hora-inicio" name="hora_inicio" value="${defaultTime}" required>
            </div>
            <div class="form-group">
              <label for="agendamento-hora-fim">Hora Fim:</label>
              <input type="time" id="agendamento-hora-fim" name="hora_fim" required>
            </div>
          </div>
          
          <div class="form-group">
            <label for="agendamento-descricao">Descrição:</label>
            <textarea id="agendamento-descricao" name="descricao" rows="3"></textarea>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label for="agendamento-cliente-nome">Nome do Cliente:</label>
              <input type="text" id="agendamento-cliente-nome" name="cliente_nome">
            </div>
            <div class="form-group">
              <label for="agendamento-cliente-email">Email do Cliente:</label>
              <input type="email" id="agendamento-cliente-email" name="cliente_email">
            </div>
          </div>
          
          <div class="form-actions">
            <button type="button" onclick="fecharModal('modal-agendamento-calendar')" class="btn-secondary">Cancelar</button>
            <button type="submit" class="btn-primary">Criar Agendamento</button>
          </div>
        </form>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  modal.style.display = 'block';
  
  // Configurar evento de submit
  document.getElementById('form-agendamento-calendar').addEventListener('submit', async function(e) {
    e.preventDefault();
    await criarAgendamentoGoogleCalendar(this);
  });
}

async function criarAgendamentoGoogleCalendar(form) {
  try {
    var formData = new FormData(form);
    var data = {};
    
    // Converter FormData para objeto
    for (var [key, value] of formData.entries()) {
      data[key] = value;
    }
    
    // Validações básicas
    if (!data.titulo || !data.data_consulta || !data.hora_inicio || !data.hora_fim) {
      showToast('Preencha todos os campos obrigatórios', 'error');
      return;
    }
    
    var response = await fetch(apiBase() + '/panel/agendamentos/google-calendar', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    var result = await response.json();
    
    if (result.success) {
      showToast('Agendamento criado com sucesso no Google Calendar!', 'success');
      fecharModal('modal-agendamento-calendar');
      
      // Recarregar a agenda
      await loadAgendaDisponibilidade();
      
      // Se estiver na aba de agendamentos, recarregar também
      if (typeof loadAgendamentosList === 'function') {
        await loadAgendamentosList();
      }
      
    } else {
      showToast(result.message || 'Erro ao criar agendamento', 'error');
    }
    
  } catch (e) {
    console.error('Erro ao criar agendamento:', e);
    showToast('Erro ao criar agendamento', 'error');
  }
}

function fecharModal(modalId) {
  var modal = document.getElementById(modalId);
  if (modal) {
    modal.remove();
  }
}

// Funções para Agendamentos
async function loadAgendamentos() {
  try {
    // Carregar dados para os selects
    await Promise.all([
      loadClientesSelect(),
      loadProfissionaisSelect(),
      loadServicosSelect()
    ]);
    
    // Carregar lista de agendamentos
    await loadAgendamentosList();
  } catch (e) {
    console.error('Erro ao carregar agendamentos:', e);
    showToast('Erro ao carregar agendamentos', 'error');
  }
}

async function loadClientesSelect() {
  try {
    var response = await fetch(apiBase() + '/admin/clientes', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar clientes');
    
    var data = await response.json();
    var select = document.getElementById('agend_cliente');
    
    if (select && data.success && data.clientes) {
      select.innerHTML = '<option value="">Selecione um cliente</option>';
      data.clientes.forEach(function(cliente) {
        if (cliente.ativo) {
          var option = document.createElement('option');
          option.value = cliente.id;
          option.textContent = `${cliente.nome} (${cliente.email})`;
          select.appendChild(option);
        }
      });
    }
  } catch (e) {
    console.error('Erro ao carregar clientes:', e);
  }
}

async function loadProfissionaisSelect() {
  try {
    var response = await fetch(apiBase() + '/panel/profissionais', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar profissionais');
    
    var data = await response.json();
    var select = document.getElementById('agend_profissional');
    
    if (select && data.success && data.profissionais) {
      select.innerHTML = '<option value="">Selecione um profissional</option>';
      data.profissionais.forEach(function(prof) {
        if (prof.ativo) {
          var option = document.createElement('option');
          option.value = prof.id;
          option.textContent = `${prof.nome} - ${prof.especialidade || 'Especialidade não informada'}`;
          select.appendChild(option);
        }
      });
    }
  } catch (e) {
    console.error('Erro ao carregar profissionais:', e);
  }
}

async function loadServicosSelect() {
  try {
    var response = await fetch(apiBase() + '/panel/servicos', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar serviços');
    
    var data = await response.json();
    var select = document.getElementById('agend_servico');
    
    if (select && data.success && data.servicos) {
      select.innerHTML = '<option value="">Selecione um serviço</option>';
      data.servicos.forEach(function(servico) {
        if (servico.ativo) {
          var option = document.createElement('option');
          option.value = servico.id;
          var valorText = servico.valor ? ` - R$ ${parseFloat(servico.valor).toFixed(2)}` : '';
          option.textContent = `${servico.nome}${valorText}`;
          select.appendChild(option);
        }
      });
    }
  } catch (e) {
    console.error('Erro ao carregar serviços:', e);
  }
}

async function loadAgendamentosList(filtros = {}) {
  try {
    // Construir query string com filtros
    var params = new URLSearchParams();
    if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
    if (filtros.status !== undefined && filtros.status !== '') params.append('status', filtros.status);
    if (filtros.profissional_id) params.append('profissional_id', filtros.profissional_id);
    if (filtros.cliente_id) params.append('cliente_id', filtros.cliente_id);
    
    var url = apiBase() + '/panel/agendamentos';
    if (params.toString()) {
      url += '?' + params.toString();
    }
    
    var response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    if (!response.ok) throw new Error('Erro ao carregar agendamentos');
    
    var data = await response.json();
    if (data.success && data.agendamentos) {
      renderAgendamentosTable(data.agendamentos);
    }
  } catch (e) {
    console.error('Erro ao carregar lista de agendamentos:', e);
    showToast('Erro ao carregar agendamentos', 'error');
  }
}

function renderAgendamentosTable(agendamentos) {
  var tbody = document.querySelector('#agendamentos-tab table tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (agendamentos.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p class="empty-text">Nenhum agendamento encontrado</p></div></td></tr>';
    return;
  }
  
  agendamentos.forEach(function(agend) {
    var row = document.createElement('tr');
    
    // Status badge classes
    var statusClass = 'active';
    if (agend.status === 0) statusClass = 'pending';
    else if (agend.status === 1) statusClass = 'active';
    else if (agend.status === 2) statusClass = 'success';
    else if (agend.status === 3) statusClass = 'inactive';
    else if (agend.status === 4) statusClass = 'warning';
    
    var valorText = agend.valor ? `R$ ${parseFloat(agend.valor).toFixed(2)}` : '-';
    var clienteText = agend.cliente_nome || 'Cliente não informado';
    var profissionalText = agend.profissional_nome || 'Profissional não informado';
    
    row.innerHTML = `
      <td>
        <div>${agend.data_consulta}</div>
        <div class="text-sm text-gray-600">${agend.hora_inicio} - ${agend.hora_fim}</div>
      </td>
      <td>${clienteText}</td>
      <td>${profissionalText}</td>
      <td><span class="badge badge-${agend.tipo_atendimento}">${agend.tipo_atendimento}</span></td>
      <td><span class="status-badge ${statusClass}">${agend.status_nome}</span></td>
      <td>${valorText}</td>
      <td>
        <div class="action-buttons">
          <button class="action-btn edit" onclick="editarAgendamento(${agend.id})" title="Editar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          ${agend.status === 0 ? `
            <button class="action-btn success" onclick="confirmarAgendamento(${agend.id})" title="Confirmar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          ` : ''}
          ${agend.status === 1 ? `
            <button class="action-btn success" onclick="realizarAgendamento(${agend.id})" title="Marcar como realizado">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </button>
          ` : ''}
          ${agend.status < 2 ? `
            <button class="action-btn delete" onclick="cancelarAgendamento(${agend.id})" title="Cancelar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          ` : ''}
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function criarAgendamento() {
  try {
    var clienteId = document.getElementById('agend_cliente').value;
    var profissionalId = document.getElementById('agend_profissional').value;
    var data = document.getElementById('agend_data').value;
    var horaInicio = document.getElementById('agend_hora_inicio').value;
    var horaFim = document.getElementById('agend_hora_fim').value;
    var tipo = document.getElementById('agend_tipo').value;
    var servicoId = document.getElementById('agend_servico').value;
    var observacao = document.getElementById('agend_observacao').value;
    
    // Validações básicas
    if (!clienteId || !profissionalId || !data || !horaInicio || !horaFim || !tipo) {
      showToast('Preencha todos os campos obrigatórios', 'error');
      return;
    }
    
    var agendamentoData = {
      cliente_id: parseInt(clienteId),
      profissional_id: parseInt(profissionalId),
      data_consulta: data,
      hora_inicio: horaInicio,
      hora_fim: horaFim,
      tipo_atendimento: tipo,
      observacao: observacao
    };
    
    if (servicoId) {
      agendamentoData.servico_id = parseInt(servicoId);
    }
    
    var response = await fetch(apiBase() + '/panel/agendamentos', {
      method: 'POST',
      credentials: 'include',
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(agendamentoData)
    });
    
    var result = await response.json();
    
    if (result.success) {
      showToast('Agendamento criado com sucesso', 'success');
      // Limpar formulário
      document.getElementById('agend_cliente').value = '';
      document.getElementById('agend_profissional').value = '';
      document.getElementById('agend_data').value = '';
      document.getElementById('agend_hora_inicio').value = '';
      document.getElementById('agend_hora_fim').value = '';
      document.getElementById('agend_tipo').value = 'presencial';
      document.getElementById('agend_servico').value = '';
      document.getElementById('agend_observacao').value = '';
      
      // Recarregar lista
      await loadAgendamentosList();
    } else {
      showToast(result.message || 'Erro ao criar agendamento', 'error');
    }
    
  } catch (e) {
    console.error('Erro ao criar agendamento:', e);
    showToast('Erro ao criar agendamento', 'error');
  }
}

async function verificarSlots() {
  var profissionalId = document.getElementById('agend_profissional').value;
  var data = document.getElementById('agend_data').value;
  var tipo = document.getElementById('agend_tipo').value;
  
  if (!profissionalId || !data) {
    showToast('Selecione profissional e data primeiro', 'warning');
    return;
  }
  
  try {
    var response = await fetch(apiBase() + `/slots-disponiveis?profissional_id=${profissionalId}&data=${data}&tipo_atendimento=${tipo}`, {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    
    var result = await response.json();
    
    if (result.success && result.slots && result.slots.length > 0) {
      var slotsText = result.slots.map(slot => `${slot.inicio} - ${slot.fim}`).join(', ');
      showToast(`Slots disponíveis: ${slotsText}`, 'info');
    } else {
      showToast('Nenhum slot disponível para esta data', 'warning');
    }
    
  } catch (e) {
    console.error('Erro ao verificar slots:', e);
    showToast('Erro ao verificar disponibilidade', 'error');
  }
}

function filtrarAgendamentos() {
  var filtros = {
    data_inicio: document.getElementById('filtro_data_inicio').value,
    data_fim: document.getElementById('filtro_data_fim').value,
    status: document.getElementById('filtro_status').value
  };
  
  loadAgendamentosList(filtros);
}

async function confirmarAgendamento(id) {
  if (!confirm('Confirmar este agendamento?')) return;
  
  await atualizarStatusAgendamento(id, 1, 'Agendamento confirmado');
}

async function realizarAgendamento(id) {
  if (!confirm('Marcar este agendamento como realizado?')) return;
  
  await atualizarStatusAgendamento(id, 2, 'Agendamento realizado');
}

async function cancelarAgendamento(id) {
  var motivo = prompt('Motivo do cancelamento:');
  if (motivo === null) return;
  
  await atualizarStatusAgendamento(id, 3, 'Agendamento cancelado', motivo);
}

async function atualizarStatusAgendamento(id, status, mensagem, motivo = null) {
  try {
    var body = { status: status };
    if (motivo) {
      body.motivo_cancelamento = motivo;
      body.cancelado_por = 'admin';
    }
    
    var response = await fetch(apiBase() + `/panel/agendamentos/${id}/status`, {
      method: 'PUT',
      credentials: 'include',
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    
    var result = await response.json();
    
    if (result.success) {
      showToast(mensagem, 'success');
      await loadAgendamentosList();
    } else {
      showToast(result.message || 'Erro ao atualizar status', 'error');
    }
    
  } catch (e) {
    console.error('Erro ao atualizar status:', e);
    showToast('Erro ao atualizar status', 'error');
  }
}

function editarAgendamento(id) {
  showToast('Editor de agendamento será implementado', 'info');
  // TODO: Implementar modal de edição
}

function addProfissional() {
  var nome = document.getElementById('prof_nome').value;
  var esp = document.getElementById('prof_especialidade').value;
  var crm = document.getElementById('prof_crm').value;
  var tel = document.getElementById('prof_telefone').value;
  if (!nome || !esp) { showToast('Preencha todos os campos obrigatórios', 'error'); return; }
  var tbody = document.getElementById('profissionais-tbody');
  if (tbody.querySelector('.empty-state')) tbody.innerHTML = '';
  var row = document.createElement('tr');
  row.innerHTML = '\n                <td>' + nome + '</td>\n                <td>' + esp + '</td>\n                <td>' + (crm || '-') + '</td>\n                <td><span class="status-badge active">Ativo</span></td>\n                <td>\n                    <div class="action-buttons">\n                        <button class="action-btn edit" onclick="editItem(this)">\n                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">\n                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>\n                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>\n                            </svg>\n                        </button>\n                        <button class="action-btn delete" onclick="deleteItem(this)">\n                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">\n                                <polyline points="3 6 5 6 21 6"/>\n                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>\n                            </svg>\n                        </button>\n                    </div>\n                </td>\n            ';
  tbody.appendChild(row);
  document.getElementById('prof_nome').value = '';
  document.getElementById('prof_especialidade').value = '';
  document.getElementById('prof_crm').value = '';
  document.getElementById('prof_telefone').value = '';
  showToast('Profissional adicionado com sucesso!', 'success');
}

function editItem(button) { showToast('Função de edição será implementada', 'warning'); }
function deleteItem(button) { if (confirm('Deseja realmente excluir este item?')) { button.closest('tr').remove(); showToast('Item excluído com sucesso!', 'success'); } }

function showToast(message, type) {
  var toast = document.getElementById('toast');
  var toastMessage = document.getElementById('toastMessage');
  toast.className = 'toast ' + (type || 'success');
  toastMessage.textContent = message;
  toast.classList.add('show');
  setTimeout(function(){ toast.classList.remove('show'); }, 3000);
}

function goToChat() { window.location.href = 'index.html'; }
function logout() {
  if (!confirm('Deseja realmente sair?')) return;
  fetch(apiBase() + '/auth/logout', {
    method: 'POST',
    credentials: 'include',
    headers: Object.assign({'Content-Type': 'application/json'}, authHeaders())
  })
  .catch(function(){})
  .finally(function(){
    // Limpa token local
    try { 
      localStorage.removeItem('app_token');
      if (window.CONFIG) window.CONFIG.AUTH_TOKEN = null; 
    } catch(e){}
    window.location.href = 'login.html';
  });
}

// Removido: Integração Google Calendar no frontend, a pedido do cliente

document.addEventListener('DOMContentLoaded', function(){
  ensureAuthenticated().then(function(authOk){
    if (!authOk) return;
  // Bind navegação do menu para atualizar o hash
  document.querySelectorAll('.nav-item').forEach(function(link){
    link.addEventListener('click', function(e){
      var href = link.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        if (location.hash !== href) {
          location.hash = href;
        } else {
          applyRoute();
        }
      }
    });
  });
  window.addEventListener('hashchange', applyRoute);
  applyRoute();
  setTimeout(function(){ showToast('Sistema carregado com sucesso!', 'success'); }, 500);
  });
});


