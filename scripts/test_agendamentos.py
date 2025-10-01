#!/usr/bin/env python3
"""
Script para testar a API de agendamentos e criar dados de teste
"""

import requests
import json
from datetime import date, timedelta

# Configurações
API_BASE = "http://localhost:8000/api"
TEST_TOKEN = "test-token"

def test_agendamentos_api():
    """Testa a API de agendamentos"""
    
    print("=== TESTE DA API DE AGENDAMENTOS ===")
    
    # Testar endpoint de agendamentos
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Testar com data de hoje
    today = date.today().strftime("%Y-%m-%d")
    print(f"Testando agendamentos para: {today}")
    
    try:
        response = requests.get(
            f"{API_BASE}/panel/agendamentos?data={today}",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            agendamentos = data.get('agendamentos', [])
            print(f"Agendamentos encontrados: {len(agendamentos)}")
            
            if len(agendamentos) == 0:
                print("Nenhum agendamento encontrado para hoje")
                print("Isso explica por que o frontend mostra 'Nenhum evento hoje'")
            else:
                print("Agendamentos encontrados:")
                for ag in agendamentos:
                    print(f"  - {ag.get('hora_inicio')} - {ag.get('hora_fim')}: {ag.get('titulo')}")
                    
        else:
            print(f"Erro: {response.text}")
            
    except Exception as e:
        print(f"Erro na requisição: {e}")
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    test_agendamentos_api()
