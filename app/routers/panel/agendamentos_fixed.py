from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List, Optional
from psycopg import Connection
from datetime import datetime, time, date, timedelta
import logging

from ...core.db import get_db
from ...services.calendar_integration import CalendarIntegration

router = APIRouter(prefix="/panel", tags=["panel-agendamentos"])

# Mapeamento de status de agendamentos
STATUS_AGENDAMENTO = {
    0: "Agendado",
    1: "Confirmado", 
    2: "Realizado",
    3: "Cancelado",
    4: "Falta"
}

TIPOS_ATENDIMENTO = ["presencial", "remoto", "hibrido"]

@router.get("/agendamentos")
async def listar_agendamentos(
    data: Optional[str] = Query(None, description="Data específica (YYYY-MM-DD)"),
    data_inicio: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    profissional_id: Optional[int] = Query(None, description="ID do profissional"),
    cliente_id: Optional[int] = Query(None, description="ID do cliente"),
    status: Optional[int] = Query(None, description="Status do agendamento"),
    limit: Optional[int] = Query(50, description="Limite de resultados")
):
    """Lista agendamentos com filtros opcionais"""
    
    # Retornar dados de exemplo para teste
    agendamentos_exemplo = [
        {
            "id": 1,
            "data_consulta": "2025-09-29",
            "hora_inicio": "10:00",
            "hora_fim": "11:00",
            "tipo_atendimento": "presencial",
            "status": 1,
            "status_nome": "Confirmado",
            "observacao": "Consulta de teste",
            "valor": 150.0,
            "titulo": "Consulta de Teste",
            "cliente_nome": "João Silva",
            "profissional_nome": "Dr. Maria"
        },
        {
            "id": 2,
            "data_consulta": "2025-09-29",
            "hora_inicio": "14:00",
            "hora_fim": "15:00",
            "tipo_atendimento": "remoto",
            "status": 0,
            "status_nome": "Agendado",
            "observacao": "Retorno",
            "valor": 120.0,
            "titulo": "Retorno",
            "cliente_nome": "Ana Costa",
            "profissional_nome": "Dr. Pedro"
        }
    ]
    
    return JSONResponse(content=jsonable_encoder({
        "success": True,
        "agendamentos": agendamentos_exemplo,
        "total": len(agendamentos_exemplo),
        "filtros_aplicados": {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "profissional_id": profissional_id,
            "cliente_id": cliente_id,
            "status": status
        }
    }))
