// === FUNÇÕES PARA INTERFACE MODERNA DA AGENDA ===

// Configurar controles de data modernos
function setupDateControls() {
  const dateInput = document.getElementById('agenda-data-selector');
  const prevBtn = document.getElementById('btn-prev-day');
  const nextBtn = document.getElementById('btn-next-day');
  const quickDateBtns = document.querySelectorAll('.quick-date-btn');
  
  if (!dateInput) return;
  
  // Definir data de hoje
  const today = new Date().toISOString().split('T')[0];
  dateInput.value = today;
  
  // Navegação de data
  prevBtn?.addEventListener('click', () => {
    const currentDate = new Date(dateInput.value);
    currentDate.setDate(currentDate.getDate() - 1);
    dateInput.value = currentDate.toISOString().split('T')[0];
    loadScheduleForDate(dateInput.value);
  });
  
  nextBtn?.addEventListener('click', () => {
    const currentDate = new Date(dateInput.value);
    currentDate.setDate(currentDate.getDate() + 1);
    dateInput.value = currentDate.toISOString().split('T')[0];
    loadScheduleForDate(dateInput.value);
  });
  
  // Mudança manual de data
  dateInput?.addEventListener('change', () => {
    loadScheduleForDate(dateInput.value);
    updateQuickDateButtons();
  });
  
  // Botões de data rápida
  quickDateBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const offset = parseInt(btn.dataset.offset);
      const targetDate = new Date();
      targetDate.setDate(targetDate.getDate() + offset);
      
      dateInput.value = targetDate.toISOString().split('T')[0];
      loadScheduleForDate(dateInput.value);
      updateQuickDateButtons();
    });
  });
}

function updateQuickDateButtons() {
  const selectedDate = document.getElementById('agenda-data-selector')?.value;
  if (!selectedDate) return;
  
  const today = new Date().toISOString().split('T')[0];
  const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];
  const dayAfter = new Date(Date.now() + 172800000).toISOString().split('T')[0];
  
  document.querySelectorAll('.quick-date-btn').forEach(btn => {
    btn.classList.remove('active');
    const offset = parseInt(btn.dataset.offset);
    
    if ((offset === 0 && selectedDate === today) ||
        (offset === 1 && selectedDate === tomorrow) ||
        (offset === 2 && selectedDate === dayAfter)) {
      btn.classList.add('active');
    }
  });
}

// Carregar cronograma para uma data específica
async function loadScheduleForDate(date) {
  try {
    console.log('Carregando cronograma para:', date);
    
    // Atualizar título
    updateScheduleTitle(date);
    
    // Mostrar loading
    showTimelineLoading();
    
    // Buscar disponibilidade
    const response = await fetch(`${apiBase()}/panel/agenda/disponibilidade?data=${date}`, {
      method: 'GET',
      headers: authHeaders()
    });
    
    if (response.ok) {
      const data = await response.json();
      renderTimelineSchedule(data, date);
      updateDaySummary(data);
      
      // Carregar eventos agendados para o dia
      await loadScheduledEvents(date);
    } else {
      throw new Error('Erro ao carregar cronograma');
    }
    
  } catch (e) {
    console.error('Erro ao carregar cronograma:', e);
    showTimelineError();
  }
}

function updateScheduleTitle(date) {
  const titleEl = document.getElementById('selected-date-title');
  const subtitleEl = document.getElementById('selected-date-subtitle');
  
  if (!titleEl || !subtitleEl) return;
  
  const dateObj = new Date(date + 'T00:00:00');
  const today = new Date().toISOString().split('T')[0];
  
  let dayLabel = '';
  if (date === today) {
    dayLabel = 'Hoje';
  } else {
    const diffTime = dateObj.getTime() - new Date(today + 'T00:00:00').getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays === 1) dayLabel = 'Amanhã';
    else if (diffDays === -1) dayLabel = 'Ontem';
    else dayLabel = `${diffDays > 0 ? '+' : ''}${diffDays} dias`;
  }
  
  titleEl.textContent = `Agenda - ${dayLabel}`;
  subtitleEl.textContent = dateObj.toLocaleDateString('pt-BR', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
}

function showTimelineLoading() {
  const timeline = document.getElementById('schedule-timeline');
  if (timeline) {
    timeline.innerHTML = `
      <div class="timeline-loading">
        <div class="loading-spinner"></div>
        <p>Carregando horários...</p>
      </div>
    `;
  }
}

function showTimelineError() {
  const timeline = document.getElementById('schedule-timeline');
  if (timeline) {
    timeline.innerHTML = `
      <div class="timeline-loading">
        <p style="color: #ef4444;">Erro ao carregar horários</p>
        <button class="btn btn-secondary" onclick="location.reload()">Tentar Novamente</button>
      </div>
    `;
  }
}

function renderTimelineSchedule(data, date) {
  const timeline = document.getElementById('schedule-timeline');
  if (!timeline) return;
  
  if (!data.success) {
    showTimelineError();
    return;
  }
  
  const availableSlots = data.available_slots || [];
  const occupiedSlots = data.occupied_slots || [];
  
  // Criar lista de todos os slots (disponíveis + ocupados)
  const allSlots = [...availableSlots, ...occupiedSlots];
  
  // Ordenar por horário de início
  allSlots.sort((a, b) => a.start.localeCompare(b.start));
  
  let timelineHTML = '';
  
  allSlots.forEach(slot => {
    const hourStr = slot.start.substring(0, 2);
    const hour = parseInt(hourStr);
    const isCurrentHour = isCurrentTime(date, hour);
    const isOccupied = occupiedSlots.some(occ => occ.start === slot.start);
    
    timelineHTML += `
      <div class="timeline-hour">
        <div class="timeline-time">${hourStr}:00</div>
        <div class="timeline-content">
          ${isOccupied ? `
            <div class="timeline-slot occupied">
              <div class="timeline-slot-title">${slot.title || 'Ocupado'}</div>
              <div class="timeline-slot-info">${slot.start} - ${slot.end}</div>
            </div>
          ` : `
            <div class="timeline-slot available ${isCurrentHour ? 'current' : ''}" 
                 data-start="${slot.start}" data-end="${slot.end}"
                 onclick="selectTimeSlot('${slot.start}', '${slot.end}', '${date}')">
              <div class="timeline-slot-title">Disponível: ${slot.start} - ${slot.end}</div>
              <div class="timeline-slot-info">Clique para agendar</div>
            </div>
          `}
        </div>
      </div>
    `;
  });
  
  timeline.innerHTML = timelineHTML;
}

function isCurrentTime(date, hour) {
  const now = new Date();
  const today = new Date().toISOString().split('T')[0];
  
  return date === today && now.getHours() === hour;
}

function updateDaySummary(data) {
  const summaryEl = document.getElementById('day-summary');
  if (!summaryEl) return;
  
  const available = data.total_available || 0;
  const occupied = data.total_occupied || 0;
  const total = available + occupied;
  
  // Atualizar contadores com dados reais
  summaryEl.innerHTML = `
    <div class="stat">
      <span class="stat-number">${available}</span>
      <span class="stat-label">Disponíveis</span>
    </div>
    <div class="stat">
      <span class="stat-number">${occupied}</span>
      <span class="stat-label">Ocupados</span>
    </div>
    <div class="stat">
      <span class="stat-number">${total}</span>
      <span class="stat-label">Total</span>
    </div>
  `;
}

function selectTimeSlot(startTime, endTime, date) {
  console.log('Slot selecionado:', {startTime, endTime, date});
  
  // Destacar slot selecionado
  document.querySelectorAll('.timeline-slot').forEach(slot => {
    slot.classList.remove('selected');
  });
  
  event.target.closest('.timeline-slot').classList.add('selected');
  
  // Abrir modal de agendamento com dados pré-preenchidos
  abrirModalNovoAgendamentoCalendar({
    data: date,
    hora_inicio: startTime,
    hora_fim: endTime
  });
}

async function loadNextAvailableSlots() {
  try {
    const response = await fetch(`${apiBase()}/panel/agenda/proximos-horarios?limite=5`, {
      method: 'GET',
      headers: authHeaders()
    });
    
    if (response.ok) {
      const data = await response.json();
      renderNextAvailableSlots(data.proximos_horarios || []);
    }
  } catch (e) {
    console.error('Erro ao carregar próximos horários:', e);
  }
}

function renderNextAvailableSlots(slots) {
  const container = document.getElementById('proximos-horarios-list');
  if (!container) return;
  
  if (slots.length === 0) {
    container.innerHTML = `
      <div class="empty-events">
        Nenhum horário disponível encontrado
      </div>
    `;
    return;
  }
  
  const slotsHTML = slots.map(slot => `
    <div class="suggestion-item" onclick="selectSuggestion('${slot.datetime_completo}')">
      <div>
        <div class="suggestion-time">${slot.horario_inicio} - ${slot.horario_fim}</div>
        <div class="suggestion-date">${slot.data_formatada} - ${slot.dia_semana}</div>
      </div>
      <div style="font-size: 18px; color: #10b981;">&rarr;</div>
    </div>
  `).join('');
  
  container.innerHTML = slotsHTML;
}

function selectSuggestion(datetime) {
  const date = new Date(datetime);
  const dateStr = date.toISOString().split('T')[0];
  const timeStr = date.toTimeString().slice(0, 5);
  
  // Navegar para a data
  document.getElementById('agenda-data-selector').value = dateStr;
  loadScheduleForDate(dateStr);
  
  // Destacar horário
  setTimeout(() => {
    const timeSlots = document.querySelectorAll('.timeline-slot');
    timeSlots.forEach(slot => {
      if (slot.dataset.start === timeStr) {
        slot.scrollIntoView({ behavior: 'smooth', block: 'center' });
        slot.classList.add('highlighted');
        setTimeout(() => slot.classList.remove('highlighted'), 2000);
      }
    });
  }, 500);
}

// === FUNCIONALIDADES DOS BOTÕES DE AÇÕES RÁPIDAS ===

// Carregar eventos agendados para o dia
async function loadScheduledEvents(date) {
  try {
    console.log('Carregando eventos agendados para:', date);
    
    // Buscar dados de disponibilidade que incluem occupied_slots
    const response = await fetch(`${apiBase()}/panel/agenda/disponibilidade?data=${date}`, {
      method: 'GET',
      headers: authHeaders()
    });
    
    console.log('Status da resposta:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Dados completos recebidos:', data);
      console.log('Slots ocupados encontrados:', data.occupied_slots?.length || 0);
      
      // Converter occupied_slots para formato de eventos
      const events = (data.occupied_slots || []).map(slot => ({
        hora_inicio: slot.start,
        hora_fim: slot.end,
        titulo: slot.title || 'Evento',
        cliente_nome: 'Cliente',
        profissional_nome: 'Profissional'
      }));
      
      renderScheduledEvents(events);
    } else {
      console.error('Erro na resposta:', response.status, response.statusText);
      const errorText = await response.text();
      console.error('Erro detalhado:', errorText);
      renderScheduledEvents([]);
    }
  } catch (e) {
    console.error('Erro ao carregar eventos agendados:', e);
    renderScheduledEvents([]);
  }
}

function renderScheduledEvents(events) {
  const container = document.getElementById('eventos-agendados');
  if (!container) {
    console.error('Container eventos-agendados não encontrado');
    return;
  }
  
  console.log('Renderizando eventos:', events);
  
  if (events.length === 0) {
    container.innerHTML = `
      <div class="empty-events">
        Nenhum evento hoje
      </div>
    `;
    return;
  }
  
  const eventsHTML = events.map(event => `
    <div class="event-item">
      <div class="event-time">${event.hora_inicio} - ${event.hora_fim}</div>
      <div class="event-title">${event.titulo || 'Agendamento'}</div>
      ${event.cliente_nome ? `<div class="event-client">Cliente: ${event.cliente_nome}</div>` : ''}
      ${event.profissional_nome ? `<div class="event-professional">Profissional: ${event.profissional_nome}</div>` : ''}
    </div>
  `).join('');
  
  container.innerHTML = eventsHTML;
  console.log('Eventos renderizados com sucesso');
}

// Configurar eventos dos botões de ações rápidas
function setupQuickActions() {
  // Botão Novo Agendamento
  const btnNovoAgendamento = document.getElementById('btn-novo-agendamento-calendar');
  if (btnNovoAgendamento) {
    btnNovoAgendamento.addEventListener('click', () => {
      abrirModalNovoAgendamentoCalendar();
    });
  }
  
  // Botão Próximos Horários
  const btnProximosHorarios = document.getElementById('btn-proximos-horarios');
  if (btnProximosHorarios) {
    btnProximosHorarios.addEventListener('click', () => {
      loadNextAvailableSlots();
      showToast('Próximos horários atualizados', 'success');
    });
  }
  
  // Botão Sincronizar
  const btnSync = document.getElementById('btn-sync-calendar');
  if (btnSync) {
    btnSync.addEventListener('click', async () => {
      btnSync.disabled = true;
      btnSync.innerHTML = '<span class="btn-icon">⟳</span> Sincronizando...';
      
      try {
        // Recarregar status da conexão
        await checkCalendarStatus();
        
        // Recarregar dados da agenda
        const currentDate = document.getElementById('agenda-data-selector')?.value;
        if (currentDate) {
          await loadScheduleForDate(currentDate);
        }
        
        // Recarregar próximos horários
        await loadNextAvailableSlots();
        
        showToast('Agenda sincronizada com sucesso', 'success');
      } catch (e) {
        console.error('Erro na sincronização:', e);
        showToast('Erro na sincronização', 'error');
      } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = '<span class="btn-icon">⟳</span> Sincronizar';
      }
    });
  }
}
