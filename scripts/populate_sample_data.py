#!/usr/bin/env python3
"""
Script para popular o banco de dados com dados de exemplo
para demonstrar o funcionamento do painel administrativo.
"""

import sys
from pathlib import Path

# Permite importar app.core.db
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.db import get_db, is_postgres_connection


def populate_sample_data():
    """Popula o banco com dados de exemplo"""
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        with db.cursor() as cur:
            print("Populando dados de exemplo...")
            
            # FAQs
            faqs = [
                ("Como cancelar uma consulta?", "Para cancelar uma consulta, ligue para nossa central com pelo menos 24h de antecedência.", "Agendamento", "cancelar, desmarcar, consulta"),
                ("Quais convênios são aceitos?", "Aceitamos Unimed, Bradesco Saúde, SulAmérica, Amil e outros principais convênios.", "Convênios", "convenio, plano, saude"),
                ("Como chegar na clínica?", "Estamos localizados na Rua das Flores, 123 - Centro. Há estacionamento no local.", "Localização", "endereco, como chegar, estacionamento"),
                ("Qual o horário de funcionamento?", "Funcionamos de segunda a sexta das 7h às 18h, e sábados das 8h às 12h.", "Horários", "funcionamento, horario, atendimento"),
                ("É necessário preparo para exames?", "Alguns exames requerem jejum ou outros preparos. Consulte nossa equipe ao agendar.", "Exames", "preparo, jejum, exames"),
            ]
            
            for pergunta, resposta, categoria, palavras in faqs:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO faq (pergunta, resposta, categoria, palavras_chave, ativo) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (pergunta, resposta, categoria, palavras, 1)
                    )
                else:
                    cur.execute(
                        "INSERT IGNORE INTO faq (pergunta, resposta, categoria, palavras_chave, ativo) VALUES (%s, %s, %s, %s, %s)",
                        (pergunta, resposta, categoria, palavras, 1)
                    )
            
            # Profissionais
            profissionais = [
                ("Dra. Maria Santos", "Clínica Geral", "CRM/SP 98765"),
                ("Dr. Carlos Oliveira", "Dermatologia", "CRM/SP 54321"),
                ("Dra. Ana Costa", "Ginecologia", "CRM/SP 11111"),
                ("Dr. Roberto Lima", "Ortopedia", "CRM/SP 22222"),
                ("Dra. Paula Ferreira", "Pediatria", "CRM/SP 33333"),
            ]
            
            for nome, especialidade, crm in profissionais:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO profissionais (nome, especialidade, crm, ativo) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (nome, especialidade, crm, 1)
                    )
                else:
                    cur.execute(
                        "INSERT IGNORE INTO profissionais (nome, especialidade, crm, ativo) VALUES (%s, %s, %s, %s)",
                        (nome, especialidade, crm, 1)
                    )
            
            # Convênios
            convenios = [
                ("Bradesco Saúde", "78901-2", "Aceito para consultas e exames"),
                ("SulAmérica", "34567-8", "Carência de 30 dias para alguns procedimentos"),
                ("Amil", "90123-4", "Aceito com autorização prévia"),
                ("NotreDame Intermédica", "56789-0", "Aceito para emergências"),
            ]
            
            for nome, registro, obs in convenios:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (nome, registro, obs, 1)
                    )
                else:
                    cur.execute(
                        "INSERT IGNORE INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s)",
                        (nome, registro, obs, 1)
                    )
            
            # Serviços
            servicos = [
                ("Ultrassonografia Abdominal", "Exame de ultrassom da região abdominal", 180.00, "Exames", "ultrassom, abdomen"),
                ("Eletrocardiograma", "Exame do coração para detectar problemas cardíacos", 80.00, "Exames", "ecg, coracao"),
                ("Hemograma Completo", "Análise completa do sangue", 45.00, "Exames", "sangue, hemograma"),
                ("Consulta Dermatológica", "Consulta com especialista em dermatologia", 200.00, "Consultas", "pele, dermatologia"),
                ("Raio-X Tórax", "Radiografia do tórax", 120.00, "Exames", "raio-x, torax, pulmao"),
                ("Consulta Ginecológica", "Consulta com ginecologista", 220.00, "Consultas", "ginecologia, mulher"),
            ]
            
            for nome, desc, valor, cat, palavras in servicos:
                if is_postgres_connection(db):
                    cur.execute(
                        """INSERT INTO servicos_clinica (nome, descricao, valor, categoria, palavras_chave, ativo) 
                           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (nome, desc, valor, cat, palavras, 1)
                    )
                else:
                    cur.execute(
                        """INSERT IGNORE INTO servicos_clinica (nome, descricao, valor, categoria, palavras_chave, ativo) 
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (nome, desc, valor, cat, palavras, 1)
                    )
            
            # Formas de Pagamento
            pagamentos = [
                ("Dinheiro", "Pagamento à vista em dinheiro", 1),
                ("Cartão de Débito", "Pagamento no débito", 1),
                ("Cartão de Crédito", "Parcelamento em até 6x sem juros", 6),
                ("PIX", "Pagamento instantâneo via PIX", 1),
                ("Boleto Bancário", "Pagamento via boleto (à vista)", 1),
            ]
            
            for nome, desc, parcelas in pagamentos:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO formas_pagamento (nome, descricao, max_parcelas, ativo) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (nome, desc, parcelas, 1)
                    )
                else:
                    cur.execute(
                        "INSERT IGNORE INTO formas_pagamento (nome, descricao, max_parcelas, ativo) VALUES (%s, %s, %s, %s)",
                        (nome, desc, parcelas, 1)
                    )
            
            # Parceiros
            parceiros = [
                ("Laboratório", "Lab Central", "Rua da Análise, 456", "(11) 3333-4444"),
                ("Farmácia", "Farmácia Saúde", "Rua dos Remédios, 789", "(11) 5555-6666"),
                ("Hospital", "Hospital Regional", "Av. da Saúde, 100", "(11) 7777-8888"),
            ]
            
            for tipo, nome, endereco, telefone in parceiros:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO parceiros (tipo, nome, endereco, telefone, ativo) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (tipo, nome, endereco, telefone, 1)
                    )
                else:
                    cur.execute(
                        "INSERT IGNORE INTO parceiros (tipo, nome, endereco, telefone, ativo) VALUES (%s, %s, %s, %s, %s)",
                        (tipo, nome, endereco, telefone, 1)
                    )
            
            print("Dados de exemplo inseridos com sucesso!")
            print("- FAQs: 5 + as existentes")
            print("- Profissionais: 5 + os existentes") 
            print("- Convênios: 4 + os existentes")
            print("- Serviços: 6 + os existentes")
            print("- Formas de Pagamento: 5")
            print("- Parceiros: 3")
            
    except Exception as e:
        print(f"Erro ao inserir dados: {e}")
        return 1
    finally:
        try:
            db.close()
        except Exception:
            pass
    
    return 0


if __name__ == "__main__":
    exit_code = populate_sample_data()
    sys.exit(exit_code)
