from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List, Optional
from psycopg import Connection
from datetime import datetime, time, date, timedelta
import logging

from ..core.db import get_db
from ..routers.auth import get_current_user

router = APIRouter()

def calcular_slots_disponiveis(
    hora_inicio: time,
    hora_fim: time,
    intervalo_inicio: Optional[time],
    intervalo_fim: Optional[time],
    duracao_consulta: int,
    agendamentos_existentes: List[tuple]
) -> List[dict]:
    """
    Calcula os slots disponíveis baseado nos horários de trabalho e agendamentos existentes
    
    Args:
        hora_inicio: Início do expediente
        hora_fim: Fim do expediente  
        intervalo_inicio: Início do intervalo de descanso (opcional)
        intervalo_fim: Fim do intervalo de descanso (opcional)
        duracao_consulta: Duração da consulta em minutos
        agendamentos_existentes: Lista de tuplas (hora_inicio, hora_fim) dos agendamentos
    
    Returns:
        Lista de slots disponíveis
    """
    slots = []
    
    # Converter time para datetime para facilitar cálculos
    base_date = date.today()
    inicio_trabalho = datetime.combine(base_date, hora_inicio)
    fim_trabalho = datetime.combine(base_date, hora_fim)
    
    inicio_intervalo = datetime.combine(base_date, intervalo_inicio) if intervalo_inicio else None
    fim_intervalo = datetime.combine(base_date, intervalo_fim) if intervalo_fim else None
    
    # Criar lista de períodos ocupados
    periodos_ocupados = []
    
    # Adicionar intervalo de descanso se existir
    if inicio_intervalo and fim_intervalo:
        periodos_ocupados.append((inicio_intervalo, fim_intervalo))
    
    # Adicionar agendamentos existentes
    for agendamento in agendamentos_existentes:
        inicio_agend = datetime.combine(base_date, agendamento[0])
        fim_agend = datetime.combine(base_date, agendamento[1])
        periodos_ocupados.append((inicio_agend, fim_agend))
    
    # Ordenar períodos ocupados
    periodos_ocupados.sort(key=lambda x: x[0])
    
    # Gerar slots disponíveis
    atual = inicio_trabalho
    
    for periodo_ocupado in periodos_ocupados:
        inicio_ocupado, fim_ocupado = periodo_ocupado
        
        # Gerar slots antes do período ocupado
        while atual + timedelta(minutes=duracao_consulta) <= inicio_ocupado:
            slot_fim = atual + timedelta(minutes=duracao_consulta)
            slots.append({
                "inicio": atual.time().strftime("%H:%M"),
                "fim": slot_fim.time().strftime("%H:%M"),
                "disponivel": True
            })
            atual += timedelta(minutes=duracao_consulta)
        
        # Pular o período ocupado
        atual = max(atual, fim_ocupado)
    
    # Gerar slots após o último período ocupado até o fim do expediente
    while atual + timedelta(minutes=duracao_consulta) <= fim_trabalho:
        slot_fim = atual + timedelta(minutes=duracao_consulta)
        slots.append({
            "inicio": atual.time().strftime("%H:%M"),
            "fim": slot_fim.time().strftime("%H:%M"),
            "disponivel": True
        })
        atual += timedelta(minutes=duracao_consulta)
    
    return slots

@router.get("/slots-disponiveis")
async def obter_slots_disponiveis(
    profissional_id: int = Query(..., description="ID do profissional"),
    data: str = Query(..., description="Data da consulta (YYYY-MM-DD)"),
    tipo_atendimento: Optional[str] = Query("presencial", description="Tipo de atendimento")
):
    """
    Obtém os slots disponíveis para um profissional em uma data específica
    """
    try:
        # Validar e converter data
        try:
            data_consulta = datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            return JSONResponse(
                content={"success": False, "message": "Formato de data inválido. Use YYYY-MM-DD"},
                status_code=400
            )
        
        # Não permitir agendamentos no passado
        if data_consulta < date.today():
            return JSONResponse(
                content={"success": False, "message": "Não é possível agendar no passado"},
                status_code=400
            )
        
        # Calcular dia da semana (1=segunda, 7=domingo)
        dia_semana = data_consulta.weekday() + 1
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se o profissional existe
                cur.execute(
                    "SELECT nome FROM profissionais WHERE id = %s AND ativo = 1",
                    (profissional_id,)
                )
                profissional = cur.fetchone()
                
                if not profissional:
                    return JSONResponse(
                        content={"success": False, "message": "Profissional não encontrado"},
                        status_code=404
                    )
                
                # Buscar disponibilidade do profissional para o dia da semana
                cur.execute("""
                    SELECT 
                        hora_inicio, hora_fim, intervalo_inicio, intervalo_fim,
                        tipo_atendimento, duracao_consulta
                    FROM disponibilidades_profissional
                    WHERE profissional_id = %s AND dia_semana = %s AND ativo = 1
                """, (profissional_id, dia_semana))
                
                disponibilidade = cur.fetchone()
                
                if not disponibilidade:
                    return JSONResponse(content=jsonable_encoder({
                        "success": True,
                        "profissional_id": profissional_id,
                        "profissional_nome": profissional[0],
                        "data": data,
                        "dia_semana": dia_semana,
                        "slots": [],
                        "message": "Profissional não tem disponibilidade neste dia"
                    }))
                
                hora_inicio, hora_fim, intervalo_inicio, intervalo_fim, tipo_disp, duracao = disponibilidade
                
                # Verificar se o tipo de atendimento é compatível
                if tipo_disp == "indisponivel":
                    return JSONResponse(content=jsonable_encoder({
                        "success": True,
                        "profissional_id": profissional_id,
                        "profissional_nome": profissional[0],
                        "data": data,
                        "slots": [],
                        "message": "Profissional indisponível neste dia"
                    }))
                
                # Verificar compatibilidade de tipo de atendimento
                tipos_compativeis = {
                    "presencial": ["presencial", "hibrido"],
                    "remoto": ["remoto", "hibrido"],
                    "hibrido": ["presencial", "remoto", "hibrido"]
                }
                
                if tipo_atendimento not in tipos_compativeis.get(tipo_disp, [tipo_disp]):
                    return JSONResponse(content=jsonable_encoder({
                        "success": True,
                        "profissional_id": profissional_id,
                        "profissional_nome": profissional[0],
                        "data": data,
                        "slots": [],
                        "message": f"Tipo de atendimento '{tipo_atendimento}' não disponível para este profissional neste dia"
                    }))
                
                # Buscar agendamentos existentes para a data
                cur.execute("""
                    SELECT hora_inicio, hora_fim
                    FROM agendamentos
                    WHERE profissional_id = %s 
                    AND data_consulta = %s 
                    AND status IN (0, 1)  -- agendado ou confirmado
                    ORDER BY hora_inicio
                """, (profissional_id, data_consulta))
                
                agendamentos_existentes = cur.fetchall()
                
                # Verificar bloqueios de agenda
                cur.execute("""
                    SELECT hora_inicio, hora_fim
                    FROM bloqueios_agenda
                    WHERE (profissional_id = %s OR profissional_id IS NULL)
                    AND data_inicio <= %s AND data_fim >= %s
                    AND ativo = 1
                """, (profissional_id, data_consulta, data_consulta))
                
                bloqueios = cur.fetchall()
                
                # Combinar agendamentos e bloqueios
                todos_ocupados = list(agendamentos_existentes) + [
                    (b[0] or time(0, 0), b[1] or time(23, 59)) for b in bloqueios
                ]
                
                # Calcular slots disponíveis
                slots = calcular_slots_disponiveis(
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    intervalo_inicio=intervalo_inicio,
                    intervalo_fim=intervalo_fim,
                    duracao_consulta=duracao or 60,
                    agendamentos_existentes=todos_ocupados
                )
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "profissional_id": profissional_id,
                    "profissional_nome": profissional[0],
                    "data": data,
                    "dia_semana": dia_semana,
                    "tipo_atendimento": tipo_atendimento,
                    "tipo_disponivel": tipo_disp,
                    "duracao_consulta": duracao or 60,
                    "slots": slots,
                    "total_slots": len(slots)
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao obter slots disponíveis: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao calcular disponibilidade"},
            status_code=500
        )

@router.get("/agenda/profissional/{profissional_id}")
async def obter_agenda_profissional(
    profissional_id: int,
    data_inicio: str = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: str = Query(..., description="Data de fim (YYYY-MM-DD)")
):
    """
    Obtém a agenda de um profissional em um período
    """
    try:
        # Validar datas
        try:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        except ValueError:
            return JSONResponse(
                content={"success": False, "message": "Formato de data inválido. Use YYYY-MM-DD"},
                status_code=400
            )
        
        if dt_fim < dt_inicio:
            return JSONResponse(
                content={"success": False, "message": "Data de fim deve ser posterior à data de início"},
                status_code=400
            )
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se o profissional existe
                cur.execute(
                    "SELECT nome, especialidade FROM profissionais WHERE id = %s AND ativo = 1",
                    (profissional_id,)
                )
                profissional = cur.fetchone()
                
                if not profissional:
                    return JSONResponse(
                        content={"success": False, "message": "Profissional não encontrado"},
                        status_code=404
                    )
                
                # Buscar agendamentos no período
                cur.execute("""
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.status, a.observacao, a.valor,
                        c.nome as cliente_nome, c.email as cliente_email, c.telefone as cliente_telefone,
                        s.nome as servico_nome
                    FROM agendamentos a
                    LEFT JOIN clientes c ON a.cliente_id = c.id
                    LEFT JOIN servicos_clinica s ON a.servico_id = s.id
                    WHERE a.profissional_id = %s
                    AND a.data_consulta BETWEEN %s AND %s
                    ORDER BY a.data_consulta, a.hora_inicio
                """, (profissional_id, dt_inicio, dt_fim))
                
                agendamentos_raw = cur.fetchall()
                
                # Buscar disponibilidades
                cur.execute("""
                    SELECT dia_semana, hora_inicio, hora_fim, intervalo_inicio, 
                           intervalo_fim, tipo_atendimento, duracao_consulta
                    FROM disponibilidades_profissional
                    WHERE profissional_id = %s AND ativo = 1
                    ORDER BY dia_semana
                """, (profissional_id,))
                
                disponibilidades_raw = cur.fetchall()
                
                # Buscar bloqueios no período
                cur.execute("""
                    SELECT data_inicio, data_fim, hora_inicio, hora_fim, tipo, descricao
                    FROM bloqueios_agenda
                    WHERE (profissional_id = %s OR profissional_id IS NULL)
                    AND data_inicio <= %s AND data_fim >= %s
                    AND ativo = 1
                """, (profissional_id, dt_fim, dt_inicio))
                
                bloqueios_raw = cur.fetchall()
                
                # Formatear dados
                agendamentos = []
                for a in agendamentos_raw:
                    status_map = {0: "Agendado", 1: "Confirmado", 2: "Realizado", 3: "Cancelado", 4: "Falta"}
                    agendamentos.append({
                        "id": a[0],
                        "data_consulta": a[1].strftime("%Y-%m-%d") if a[1] else None,
                        "hora_inicio": a[2].strftime("%H:%M") if a[2] else None,
                        "hora_fim": a[3].strftime("%H:%M") if a[3] else None,
                        "tipo_atendimento": a[4],
                        "status": a[5],
                        "status_nome": status_map.get(a[5], "Desconhecido"),
                        "observacao": a[6],
                        "valor": float(a[7]) if a[7] else None,
                        "cliente": {
                            "nome": a[8],
                            "email": a[9],
                            "telefone": a[10]
                        } if a[8] else None,
                        "servico_nome": a[11]
                    })
                
                disponibilidades = []
                for d in disponibilidades_raw:
                    dias_semana = {1: "Segunda", 2: "Terça", 3: "Quarta", 4: "Quinta", 5: "Sexta", 6: "Sábado", 7: "Domingo"}
                    disponibilidades.append({
                        "dia_semana": d[0],
                        "dia_semana_nome": dias_semana.get(d[0], f"Dia {d[0]}"),
                        "hora_inicio": d[1].strftime("%H:%M") if d[1] else None,
                        "hora_fim": d[2].strftime("%H:%M") if d[2] else None,
                        "intervalo_inicio": d[3].strftime("%H:%M") if d[3] else None,
                        "intervalo_fim": d[4].strftime("%H:%M") if d[4] else None,
                        "tipo_atendimento": d[5],
                        "duracao_consulta": d[6]
                    })
                
                bloqueios = []
                for b in bloqueios_raw:
                    bloqueios.append({
                        "data_inicio": b[0].strftime("%Y-%m-%d") if b[0] else None,
                        "data_fim": b[1].strftime("%Y-%m-%d") if b[1] else None,
                        "hora_inicio": b[2].strftime("%H:%M") if b[2] else None,
                        "hora_fim": b[3].strftime("%H:%M") if b[3] else None,
                        "tipo": b[4],
                        "descricao": b[5]
                    })
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "profissional": {
                        "id": profissional_id,
                        "nome": profissional[0],
                        "especialidade": profissional[1]
                    },
                    "periodo": {
                        "data_inicio": data_inicio,
                        "data_fim": data_fim
                    },
                    "agendamentos": agendamentos,
                    "disponibilidades": disponibilidades,
                    "bloqueios": bloqueios,
                    "resumo": {
                        "total_agendamentos": len(agendamentos),
                        "total_bloqueios": len(bloqueios)
                    }
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao obter agenda do profissional {profissional_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar agenda"},
            status_code=500
        )
