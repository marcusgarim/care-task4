#!/usr/bin/env python3
"""
Script para criar agendamentos de teste
"""

import requests
import json
from datetime import date, timedelta

# Configurações
API_BASE = "http://localhost:8000/api"
TEST_TOKEN = "test-token"

def create_test_agendamentos():
    """Cria agendamentos de teste"""
    
    print("=== CRIANDO AGENDAMENTOS DE TESTE ===")
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Criar agendamento para amanhã (hoje pode estar no passado)
    today = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    agendamento_data = {
        "cliente_id": 1,
        "profissional_id": 1,
        "data_agendamento": today,
        "data_consulta": today,
        "hora_inicio": "10:00",
        "hora_fim": "11:00",
        "titulo": "Consulta de Teste",
        "tipo_atendimento": "presencial",
        "status": 1,  # Confirmado
        "observacao": "Agendamento criado para teste da interface"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/panel/agendamentos/google-calendar",
            headers=headers,
            json=agendamento_data,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Agendamento criado: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {e}")
    
    # Criar outro agendamento para depois de amanhã
    tomorrow = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    agendamento_data2 = {
        "cliente_id": 1,
        "profissional_id": 1,
        "data_agendamento": tomorrow,
        "data_consulta": tomorrow,
        "hora_inicio": "15:00",
        "hora_fim": "16:00",
        "titulo": "Consulta de Teste 2",
        "tipo_atendimento": "remoto",
        "status": 0,  # Agendado
        "observacao": "Segundo agendamento de teste"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/panel/agendamentos/google-calendar",
            headers=headers,
            json=agendamento_data2,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Segundo agendamento criado: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {e}")
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    create_test_agendamentos()
