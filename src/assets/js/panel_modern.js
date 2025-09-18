// Smart Schedule - Painel Administrativo (JS do mock com roteamento por hash)

function apiBase() {
  return (window.CONFIG && window.CONFIG.API_BASE) ? window.CONFIG.API_BASE : 'http://127.0.0.1:8000/api';
}

function authHeaders() {
  var headers = {};
  if (window.CONFIG && window.CONFIG.AUTH_TOKEN) {
    headers['Authorization'] = 'Bearer ' + window.CONFIG.AUTH_TOKEN;
  }
  return headers;
}

async function ensureAuthenticated() {
  try {
    var res = await fetch(apiBase() + '/auth/me', {
      method: 'GET',
      credentials: 'include',
      headers: authHeaders()
    });
    if (!res.ok) throw new Error('unauthorized');
    var data = await res.json();
    var ui = document.querySelector('.user-info span');
    if (ui && data && data.user && (data.user.name || data.user.email)) {
      ui.textContent = data.user.name || data.user.email;
    }
    return true;
  } catch (e) {
    window.location.href = '/login.html';
    return false;
  }
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

function goToChat() { window.location.href = '/index.html'; }
function logout() {
  if (!confirm('Deseja realmente sair?')) return;
  fetch(apiBase() + '/auth/logout', {
    method: 'POST',
    credentials: 'include',
    headers: Object.assign({'Content-Type': 'application/json'}, authHeaders())
  })
  .catch(function(){})
  .finally(function(){
    try { if (window.CONFIG) window.CONFIG.AUTH_TOKEN = null; } catch(e){}
    window.location.href = '/login.html';
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


