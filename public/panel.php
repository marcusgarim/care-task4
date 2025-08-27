<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Administrativo - MCI</title>
    <link rel="icon" type="image/x-icon" href="img/favicon.ico">
    <link rel="stylesheet" href="css/panel.css">
</head>
<body>
    <div class="panel-container">
        <!-- Header -->
        <header class="panel-header">
            <div class="header-content">
                <h1>⚙️ Painel Administrativo</h1>
                <button class="back-btn" onclick="window.location.href='chat.php'">← Voltar ao Chat</button>
            </div>
        </header>

        <!-- Tabs Navigation -->
        <nav class="tabs-nav">
            <button class="tab-nav-btn prev" onclick="scrollTabs('prev')" title="Anterior">‹</button>
            <div class="tabs-container">
                <button class="tab-btn active" data-tab="configuracoes">📋 Configurações</button>
                <button class="tab-btn" data-tab="profissionais">👨‍⚕️ Profissionais</button>
                <button class="tab-btn" data-tab="servicos">🩺 Serviços</button>
                <button class="tab-btn" data-tab="convenios">🏥 Convênios</button>
                <button class="tab-btn" data-tab="horarios">🕐 Horários</button>
                <button class="tab-btn" data-tab="agenda">📅 Exceções Agenda</button>
                <button class="tab-btn" data-tab="faq">❓ FAQ</button>
                <button class="tab-btn" data-tab="pagamentos">💳 Pagamentos</button>
                <button class="tab-btn" data-tab="parceiros">🤝 Parceiros</button>
            </div>
            <button class="tab-nav-btn next" onclick="scrollTabs('next')" title="Próximo">›</button>
        </nav>

        <!-- Tab Content -->
        <main class="tab-content">
            <!-- Configurações -->
            <div id="configuracoes" class="tab-panel active">
                <h2>Configurações Gerais</h2>
                <form id="configForm" class="form-grid">
                    <div class="form-group">
                        <label for="nome_assistente">Nome do Assistente Virtual</label>
                        <input type="text" id="nome_assistente" name="nome_assistente">
                    </div>
                    
                    <div class="form-group">
                        <label for="nome_clinica">Nome da Clínica</label>
                        <input type="text" id="nome_clinica" name="nome_clinica">
                    </div>
                    
             
                    
                    <div class="form-group full-width">
                        <label for="endereco">Endereço Completo</label>
                        <input type="text" id="endereco" name="endereco">
                    </div>
                    
                    <div class="form-group">
                        <label for="telefone">Telefone Principal</label>
                        <input type="tel" id="telefone" name="telefone">
                    </div>
                    
                    <div class="form-group">
                        <label for="whatsapp">WhatsApp</label>
                        <input type="tel" id="whatsapp" name="whatsapp">
                    </div>
                    
                   
                    
                    <div class="form-group">
                        <label for="politica_cancelamento">Prazo Cancelamento (horas)</label>
                        <input type="number" id="politica_cancelamento" name="politica_cancelamento">
                    </div>
                    
                    <div class="form-group">
                        <label for="link_google_maps">Link Google Maps</label>
                        <input type="url" id="link_google_maps" name="link_google_maps">
                    </div>
                    
                    <div class="form-group">
                        <label for="link_waze">Link Waze</label>
                        <input type="url" id="link_waze" name="link_waze">
                    </div>
                    
                    <div class="form-group full-width">
                        <label for="referencias">Referências de Localização</label>
                        <input type="text" id="referencias" name="referencias">
                    </div>
                    
                    <div class="form-group full-width">
                        <label for="link_avaliacao_google">Link Avaliação Google</label>
                        <input type="url" id="link_avaliacao_google" name="link_avaliacao_google">
                    </div>
                    
                    <div class="form-group full-width">
                        <label for="mensagem_boas_vindas">Mensagem de Boas-vindas</label>
                        <textarea id="mensagem_boas_vindas" name="mensagem_boas_vindas" rows="3"></textarea>
                    </div>
                    
                    <div class="form-group full-width">
                        <label for="mensagem_pos_consulta">Mensagem Pós-consulta</label>
                        <textarea id="mensagem_pos_consulta" name="mensagem_pos_consulta" rows="3"></textarea>
                    </div>
                    
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Salvar Configurações</button>
                        <button type="button" class="btn-secondary" onclick="loadConfiguracoes()">🔄 Recarregar</button>
                    </div>
                </form>
            </div>

            <!-- Profissionais -->
            <div id="profissionais" class="tab-panel">
                <div class="section-header">
                    <h2>Profissionais</h2>
                    <button class="btn-primary" onclick="showProfissionalModal()">➕ Adicionar Profissional</button>
                </div>
                
                <div class="table-container">
                    <table id="profissionaisTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Especialidade</th>
                                <th>CRM</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="profissionaisTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Serviços -->
            <div id="servicos" class="tab-panel">
                <div class="section-header">
                    <h2>Serviços da Clínica</h2>
                    <button class="btn-primary" onclick="showServicoModal()">➕ Adicionar Serviço</button>
                </div>
                
                <div class="table-container">
                    <table id="servicosTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Descrição</th>
                                <th>Valor</th>
                                <th>Categoria</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="servicosTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Convênios -->
            <div id="convenios" class="tab-panel">
                <div class="section-header">
                    <h2>Convênios Aceitos</h2>
                    <button class="btn-primary" onclick="showConvenioModal()">➕ Adicionar Convênio</button>
                </div>
                
                <div class="table-container">
                    <table id="conveniosTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Registro ANS</th>
                                <th>Observações</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="conveniosTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Horários -->
            <div id="horarios" class="tab-panel">
                <div class="section-header">
                    <h2>Horários de Atendimento</h2>
    
                </div>
                
                <div class="table-container">
                    <table id="horariosTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Dia</th>
                                <th>Manhã</th>
                                <th>Tarde</th>
                                <th>Tempo da consulta</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="horariosTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Agenda -->
            <div id="agenda" class="tab-panel">
                <div class="section-header">
                    <h2>Exceções na Agenda</h2>
                    <button class="btn-primary" onclick="showExcecaoModal()">➕ Adicionar Exceção</button>
                </div>
                
                <div class="table-container">
                    <table id="excecoesTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Tipo</th>
                                <th>Descrição</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="excecoesTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- FAQ -->
            <div id="faq" class="tab-panel">
                <div class="section-header">
                    <h2>Perguntas Frequentes</h2>
                    <button class="btn-primary" onclick="showFaqModal()">➕ Adicionar FAQ</button>
                </div>
                
                <div class="table-container">
                    <table id="faqTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Pergunta</th>
                                <th>Categoria</th>
                                <th>Palavras-chave</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="faqTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Pagamentos -->
            <div id="pagamentos" class="tab-panel">
                <div class="section-header">
                    <h2>Formas de Pagamento</h2>
                    <button class="btn-primary" onclick="showPagamentoModal()">➕ Adicionar Forma</button>
                </div>
                
                <div class="table-container">
                    <table id="pagamentosTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Descrição</th>
                                <th>Parcelas</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="pagamentosTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Parceiros -->
            <div id="parceiros" class="tab-panel">
                <div class="section-header">
                    <h2>Parceiros</h2>
                    <button class="btn-primary" onclick="showParceiroModal()">➕ Adicionar Parceiro</button>
                </div>
                
                <div class="table-container">
                    <table id="parceirosTable" class="data-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Nome</th>
                                <th>Endereço</th>
                                <th>Telefone</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="parceirosTableBody">
                            <!-- Dados carregados via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>

    <!-- Modais serão adicionados aqui -->
    <div id="modalContainer"></div>

    <script src="js/panel.js"></script>
</body>
</html> 