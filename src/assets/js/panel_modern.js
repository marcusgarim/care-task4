// Smart Schedule - Painel Administrativo (JS do mock extraído)

function showTab(tabName) {
  document.querySelectorAll('.tab-section').forEach(function(tab){ tab.classList.remove('active'); });
  document.querySelectorAll('.tab').forEach(function(tab){ tab.classList.remove('active'); });
  var selected = document.getElementById(tabName + '-tab');
  if (selected) selected.classList.add('active');
  if (event && event.currentTarget) event.currentTarget.classList.add('active');
  var mc = document.querySelector('.main-container');
  if (mc) mc.scrollTop = 0;
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
function logout() { if (confirm('Deseja realmente sair?')) { window.location.href = '/login.html'; } }

document.addEventListener('DOMContentLoaded', function(){ setTimeout(function(){ showToast('Sistema carregado com sucesso!', 'success'); }, 500); });


