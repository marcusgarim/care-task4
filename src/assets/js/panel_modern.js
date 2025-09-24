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


