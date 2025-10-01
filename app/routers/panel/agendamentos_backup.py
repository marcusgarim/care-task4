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
                base_query = """
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.status, a.observacao, a.valor,
                        a.data_agendamento, a.data_confirmacao, a.data_realizacao,
                        a.cancelado_por, a.motivo_cancelamento,
                        c.id as cliente_id, c.nome as cliente_nome, c.email as cliente_email,
                        c.telefone as cliente_telefone,
                        p.id as profissional_id, p.nome as profissional_nome, 
                        p.especialidade as profissional_especialidade,
                        s.nome as servico_nome, s.valor as servico_valor,
                        fp.nome as forma_pagamento_nome
                    FROM agendamentos a
                    LEFT JOIN clientes c ON a.cliente_id = c.id
                    JOIN profissionais p ON a.profissional_id = p.id
                    LEFT JOIN servicos_clinica s ON a.servico_id = s.id
                    LEFT JOIN formas_pagamento fp ON a.forma_pagamento_id = fp.id
                    WHERE 1=1
                """
                
                params = []
                conditions = []
                
                # Aplicar filtros
                if data:
                    # Se data específica for fornecida, usar ela
                    try:
                        dt_especifica = datetime.strptime(data, "%Y-%m-%d").date()
                        conditions.append("a.data_consulta = %s")
                        params.append(dt_especifica)
                    except ValueError:
                        return JSONResponse(
                            content={"success": False, "message": "Formato de data inválido"},
                            status_code=400
                        )
                else:
                    # Caso contrário, usar data_inicio e data_fim
                    if data_inicio:
                        try:
                            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                            conditions.append("a.data_consulta >= %s")
                            params.append(dt_inicio)
                        except ValueError:
                            return JSONResponse(
                                content={"success": False, "message": "Formato de data início inválido"},
                                status_code=400
                            )
                    
                    if data_fim:
                        try:
                            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                            conditions.append("a.data_consulta <= %s")
                            params.append(dt_fim)
                        except ValueError:
                            return JSONResponse(
                                content={"success": False, "message": "Formato de data fim inválido"},
                                status_code=400
                            )
                
                if profissional_id:
                    conditions.append("a.profissional_id = %s")
                    params.append(profissional_id)
                
                if cliente_id:
                    conditions.append("a.cliente_id = %s")
                    params.append(cliente_id)
                
                if status is not None:
                    conditions.append("a.status = %s")
                    params.append(status)
                
                # Adicionar condições à query
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                # Ordenar e limitar
                base_query += " ORDER BY a.data_consulta DESC, a.hora_inicio DESC"
                if limit:
                    base_query += f" LIMIT {limit}"
                
                cur.execute(base_query, params)
                agendamentos_raw = cur.fetchall()
                
                # Formatar dados
                agendamentos = []
                for a in agendamentos_raw:
                    agendamento = {
                        "id": a[0],
                        "data_consulta": a[1].strftime("%Y-%m-%d") if a[1] else None,
                        "hora_inicio": a[2].strftime("%H:%M") if a[2] else None,
                        "hora_fim": a[3].strftime("%H:%M") if a[3] else None,
                        "tipo_atendimento": a[4],
                        "status": a[5],
                        "status_nome": STATUS_AGENDAMENTO.get(a[5], "Desconhecido"),
                        "observacao": a[6],
                        "valor": float(a[7]) if a[7] else None,
                        "data_agendamento": a[8].isoformat() if a[8] else None,
                        "data_confirmacao": a[9].isoformat() if a[9] else None,
                        "data_realizacao": a[10].isoformat() if a[10] else None,
                        "cancelado_por": a[11],
                        "motivo_cancelamento": a[12],
                        "cliente": {
                            "id": a[13],
                            "nome": a[14],
                            "email": a[15],
                            "telefone": a[16]
                        } if a[13] else None,
                        "profissional": {
                            "id": a[17],
                            "nome": a[18],
                            "especialidade": a[19]
                        },
                        "servico": {
                            "nome": a[20],
                            "valor": float(a[21]) if a[21] else None
                        } if a[20] else None,
                        "forma_pagamento": a[22]
                    }
                    agendamentos.append(agendamento)
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "agendamentos": agendamentos,
                    "total": len(agendamentos),
                    "filtros_aplicados": {
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "profissional_id": profissional_id,
                        "cliente_id": cliente_id,
                        "status": status
                    }
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao listar agendamentos: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar agendamentos"},
            status_code=500
        )

@router.get("/agendamentos/{agendamento_id}")
async def obter_agendamento(agendamento_id: int):
    """Obtém detalhes de um agendamento específico"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("""
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.status, a.observacao, a.valor,
                        a.data_agendamento, a.data_confirmacao, a.data_realizacao,
                        a.cancelado_por, a.motivo_cancelamento,
                        c.id as cliente_id, c.nome as cliente_nome, c.email as cliente_email,
                        c.telefone as cliente_telefone, c.data_nascimento as cliente_nascimento,
                        p.id as profissional_id, p.nome as profissional_nome, 
                        p.especialidade as profissional_especialidade, p.email as profissional_email,
                        s.id as servico_id, s.nome as servico_nome, s.valor as servico_valor,
                        fp.id as forma_pagamento_id, fp.nome as forma_pagamento_nome
                    FROM agendamentos a
                    LEFT JOIN clientes c ON a.cliente_id = c.id
                    JOIN profissionais p ON a.profissional_id = p.id
                    LEFT JOIN servicos_clinica s ON a.servico_id = s.id
                    LEFT JOIN formas_pagamento fp ON a.forma_pagamento_id = fp.id
                    WHERE a.id = %s
                """, (agendamento_id,))
                
                agendamento_raw = cur.fetchone()
                
                if not agendamento_raw:
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento não encontrado"},
                        status_code=404
                    )
                
                a = agendamento_raw
                agendamento = {
                    "id": a[0],
                    "data_consulta": a[1].strftime("%Y-%m-%d") if a[1] else None,
                    "hora_inicio": a[2].strftime("%H:%M") if a[2] else None,
                    "hora_fim": a[3].strftime("%H:%M") if a[3] else None,
                    "tipo_atendimento": a[4],
                    "status": a[5],
                    "status_nome": STATUS_AGENDAMENTO.get(a[5], "Desconhecido"),
                    "observacao": a[6],
                    "valor": float(a[7]) if a[7] else None,
                    "data_agendamento": a[8].isoformat() if a[8] else None,
                    "data_confirmacao": a[9].isoformat() if a[9] else None,
                    "data_realizacao": a[10].isoformat() if a[10] else None,
                    "cancelado_por": a[11],
                    "motivo_cancelamento": a[12],
                    "cliente": {
                        "id": a[13],
                        "nome": a[14],
                        "email": a[15],
                        "telefone": a[16],
                        "data_nascimento": a[17].strftime("%Y-%m-%d") if a[17] else None
                    } if a[13] else None,
                    "profissional": {
                        "id": a[18],
                        "nome": a[19],
                        "especialidade": a[20],
                        "email": a[21]
                    },
                    "servico": {
                        "id": a[22],
                        "nome": a[23],
                        "valor": float(a[24]) if a[24] else None
                    } if a[22] else None,
                    "forma_pagamento": {
                        "id": a[25],
                        "nome": a[26]
                    } if a[25] else None
                }
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "agendamento": agendamento
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao obter agendamento {agendamento_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar agendamento"},
            status_code=500
        )

@router.post("/agendamentos")
async def criar_agendamento(request: Request):
    """Cria um novo agendamento"""
    try:
        data = await request.json()
        
        # Validar campos obrigatórios
        required_fields = ["profissional_id", "data_consulta", "hora_inicio", "hora_fim", "tipo_atendimento"]
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(
                    content={"success": False, "message": f"Campo '{field}' é obrigatório"},
                    status_code=400
                )
        
        # Validar tipo de atendimento
        if data["tipo_atendimento"] not in TIPOS_ATENDIMENTO:
            return JSONResponse(
                content={"success": False, "message": "Tipo de atendimento inválido"},
                status_code=400
            )
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Validar se profissional existe
                cur.execute("SELECT id, nome FROM profissionais WHERE id = %s AND ativo = 1", (data["profissional_id"],))
                profissional = cur.fetchone()
                if not profissional:
                    return JSONResponse(
                        content={"success": False, "message": "Profissional não encontrado"},
                        status_code=404
                    )
                
                # Processar dados do cliente
                cliente_id = data.get("cliente_id")
                cliente_email = data.get("cliente_email")
                cliente_nome = data.get("cliente_nome")
                
                if not cliente_id and not cliente_email:
                    return JSONResponse(
                        content={"success": False, "message": "ID ou email do cliente é obrigatório"},
                        status_code=400
                    )
                
                # Buscar ou criar cliente
                if cliente_id:
                    cur.execute("SELECT id, nome, email FROM clientes WHERE id = %s", (cliente_id,))
                    cliente = cur.fetchone()
                    if not cliente:
                        return JSONResponse(
                            content={"success": False, "message": "Cliente não encontrado"},
                            status_code=404
                        )
                elif cliente_email:
                    cur.execute("SELECT id, nome, email FROM clientes WHERE email = %s", (cliente_email,))
                    cliente = cur.fetchone()
                    
                    if not cliente:
                        # Criar novo cliente
                        if not cliente_nome:
                            return JSONResponse(
                                content={"success": False, "message": "Nome do cliente é obrigatório para novos clientes"},
                                status_code=400
                            )
                        
                        cur.execute("""
                            INSERT INTO clientes (nome, email, telefone)
                            VALUES (%s, %s, %s)
                            RETURNING id, nome, email
                        """, (cliente_nome, cliente_email, data.get("cliente_telefone")))
                        cliente = cur.fetchone()
                        cliente_id = cliente[0]
                    else:
                        cliente_id = cliente[0]
                
                # Validar data e horários
                try:
                    data_consulta = datetime.strptime(data["data_consulta"], "%Y-%m-%d").date()
                    hora_inicio = datetime.strptime(data["hora_inicio"], "%H:%M").time()
                    hora_fim = datetime.strptime(data["hora_fim"], "%H:%M").time()
                except ValueError:
                    return JSONResponse(
                        content={"success": False, "message": "Formato de data/hora inválido"},
                        status_code=400
                    )
                
                # Verificar se não é no passado
                if data_consulta < date.today():
                    return JSONResponse(
                        content={"success": False, "message": "Não é possível agendar no passado"},
                        status_code=400
                    )
                
                # Verificar conflitos de horário
                cur.execute("""
                    SELECT id FROM agendamentos
                    WHERE profissional_id = %s 
                    AND data_consulta = %s
                    AND status IN (0, 1)
                    AND (
                        (hora_inicio <= %s AND hora_fim > %s) OR
                        (hora_inicio < %s AND hora_fim >= %s) OR
                        (hora_inicio >= %s AND hora_fim <= %s)
                    )
                """, (
                    data["profissional_id"], data_consulta,
                    hora_inicio, hora_inicio,
                    hora_fim, hora_fim,
                    hora_inicio, hora_fim
                ))
                
                conflito = cur.fetchone()
                if conflito:
                    return JSONResponse(
                        content={"success": False, "message": "Horário já ocupado"},
                        status_code=400
                    )
                
                # Criar agendamento
                cur.execute("""
                    INSERT INTO agendamentos (
                        cliente_id, profissional_id, servico_id, data_consulta,
                        hora_inicio, hora_fim, tipo_atendimento, status,
                        observacao, valor, forma_pagamento_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    cliente_id,
                    data["profissional_id"],
                    data.get("servico_id"),
                    data_consulta,
                    hora_inicio,
                    hora_fim,
                    data["tipo_atendimento"],
                    0,  # Status: agendado
                    data.get("observacao"),
                    data.get("valor"),
                    data.get("forma_pagamento_id")
                ))
                
                agendamento_id = cur.fetchone()[0]
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Agendamento criado com sucesso",
                    "agendamento_id": agendamento_id
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao criar agendamento: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao criar agendamento"},
            status_code=500
        )

@router.put("/agendamentos/{agendamento_id}")
async def atualizar_agendamento(agendamento_id: int, request: Request):
    """Atualiza um agendamento existente"""
    try:
        data = await request.json()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se agendamento existe
                cur.execute("SELECT id, status FROM agendamentos WHERE id = %s", (agendamento_id,))
                agendamento = cur.fetchone()
                
                if not agendamento:
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento não encontrado"},
                        status_code=404
                    )
                
                # Não permitir edição de agendamentos realizados ou cancelados
                if agendamento[1] in [2, 3]:  # realizado ou cancelado
                    return JSONResponse(
                        content={"success": False, "message": "Não é possível editar agendamentos realizados ou cancelados"},
                        status_code=400
                    )
                
                # Preparar campos para atualização
                campos = []
                valores = []
                
                if "data_consulta" in data:
                    try:
                        data_consulta = datetime.strptime(data["data_consulta"], "%Y-%m-%d").date()
                        if data_consulta < date.today():
                            return JSONResponse(
                                content={"success": False, "message": "Não é possível agendar no passado"},
                                status_code=400
                            )
                        campos.append("data_consulta = %s")
                        valores.append(data_consulta)
                    except ValueError:
                        return JSONResponse(
                            content={"success": False, "message": "Formato de data inválido"},
                            status_code=400
                        )
                
                if "hora_inicio" in data:
                    try:
                        hora_inicio = datetime.strptime(data["hora_inicio"], "%H:%M").time()
                        campos.append("hora_inicio = %s")
                        valores.append(hora_inicio)
                    except ValueError:
                        return JSONResponse(
                            content={"success": False, "message": "Formato de hora início inválido"},
                            status_code=400
                        )
                
                if "hora_fim" in data:
                    try:
                        hora_fim = datetime.strptime(data["hora_fim"], "%H:%M").time()
                        campos.append("hora_fim = %s")
                        valores.append(hora_fim)
                    except ValueError:
                        return JSONResponse(
                            content={"success": False, "message": "Formato de hora fim inválido"},
                            status_code=400
                        )
                
                if "tipo_atendimento" in data:
                    if data["tipo_atendimento"] not in TIPOS_ATENDIMENTO:
                        return JSONResponse(
                            content={"success": False, "message": "Tipo de atendimento inválido"},
                            status_code=400
                        )
                    campos.append("tipo_atendimento = %s")
                    valores.append(data["tipo_atendimento"])
                
                if "observacao" in data:
                    campos.append("observacao = %s")
                    valores.append(data["observacao"])
                
                if "valor" in data:
                    campos.append("valor = %s")
                    valores.append(data["valor"])
                
                if "servico_id" in data:
                    campos.append("servico_id = %s")
                    valores.append(data["servico_id"])
                
                if "forma_pagamento_id" in data:
                    campos.append("forma_pagamento_id = %s")
                    valores.append(data["forma_pagamento_id"])
                
                if not campos:
                    return JSONResponse(
                        content={"success": False, "message": "Nenhum campo para atualizar"},
                        status_code=400
                    )
                
                # Adicionar timestamp de atualização
                campos.append("updated_at = %s")
                valores.append(datetime.now())
                valores.append(agendamento_id)
                
                # Executar atualização
                sql = f"UPDATE agendamentos SET {', '.join(campos)} WHERE id = %s"
                cur.execute(sql, valores)
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Agendamento atualizado com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao atualizar agendamento {agendamento_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao atualizar agendamento"},
            status_code=500
        )

@router.put("/agendamentos/{agendamento_id}/status")
async def atualizar_status_agendamento(agendamento_id: int, request: Request):
    """Atualiza o status de um agendamento (confirmar, realizar, cancelar, etc.)"""
    try:
        data = await request.json()
        
        novo_status = data.get("status")
        if novo_status is None or novo_status not in [0, 1, 2, 3, 4]:
            return JSONResponse(
                content={"success": False, "message": "Status inválido. Use: 0=Agendado, 1=Confirmado, 2=Realizado, 3=Cancelado, 4=Falta"},
                status_code=400
            )
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se agendamento existe
                cur.execute("SELECT id, status FROM agendamentos WHERE id = %s", (agendamento_id,))
                agendamento = cur.fetchone()
                
                if not agendamento:
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento não encontrado"},
                        status_code=404
                    )
                
                status_atual = agendamento[1]
                
                # Validações de transição de status
                if status_atual == 2:  # realizado
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento já foi realizado"},
                        status_code=400
                    )
                
                if status_atual == 3 and novo_status != 0:  # cancelado só pode voltar para agendado
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento cancelado só pode ser reagendado"},
                        status_code=400
                    )
                
                # Preparar campos para atualização
                campos = ["status = %s"]
                valores = [novo_status]
                
                current_time = datetime.now()
                
                # Definir timestamps específicos por status
                if novo_status == 1:  # confirmado
                    campos.append("data_confirmacao = %s")
                    valores.append(current_time)
                elif novo_status == 2:  # realizado
                    campos.append("data_realizacao = %s")
                    valores.append(current_time)
                    if not agendamento[1] == 1:  # se não estava confirmado, confirmar também
                        campos.append("data_confirmacao = %s")
                        valores.append(current_time)
                elif novo_status == 3:  # cancelado
                    campos.append("cancelado_por = %s")
                    valores.append(data.get("cancelado_por", "admin"))
                    if data.get("motivo_cancelamento"):
                        campos.append("motivo_cancelamento = %s")
                        valores.append(data["motivo_cancelamento"])
                
                campos.append("updated_at = %s")
                valores.append(current_time)
                valores.append(agendamento_id)
                
                # Executar atualização
                sql = f"UPDATE agendamentos SET {', '.join(campos)} WHERE id = %s"
                cur.execute(sql, valores)
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Status atualizado para: {STATUS_AGENDAMENTO.get(novo_status)}"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao atualizar status do agendamento {agendamento_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao atualizar status"},
            status_code=500
        )

@router.delete("/agendamentos/{agendamento_id}")
async def cancelar_agendamento(agendamento_id: int, request: Request):
    """Cancela um agendamento (soft delete)"""
    try:
        data = await request.json()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se agendamento existe
                cur.execute("SELECT id, status, data_consulta FROM agendamentos WHERE id = %s", (agendamento_id,))
                agendamento = cur.fetchone()
                
                if not agendamento:
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento não encontrado"},
                        status_code=404
                    )
                
                if agendamento[1] == 3:  # já cancelado
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento já está cancelado"},
                        status_code=400
                    )
                
                if agendamento[1] == 2:  # realizado
                    return JSONResponse(
                        content={"success": False, "message": "Não é possível cancelar agendamento já realizado"},
                        status_code=400
                    )
                
                # Cancelar agendamento
                cur.execute("""
                    UPDATE agendamentos 
                    SET status = 3, 
                        cancelado_por = %s,
                        motivo_cancelamento = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    data.get("cancelado_por", "admin"),
                    data.get("motivo_cancelamento", "Cancelado via painel admin"),
                    datetime.now(),
                    agendamento_id
                ))
                
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Agendamento cancelado com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao cancelar agendamento {agendamento_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao cancelar agendamento"},
            status_code=500
        )

@router.get("/agendamentos/pendentes-confirmacao")
async def listar_pendentes_confirmacao(
    dias_antecedencia: int = Query(2, description="Dias de antecedência para buscar confirmações")
):
    """Lista agendamentos que precisam de confirmação"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Calcular data alvo
                data_alvo = date.today() + timedelta(days=dias_antecedencia)
                
                cur.execute("""
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.data_agendamento,
                        c.nome as cliente_nome, c.email as cliente_email, c.telefone as cliente_telefone,
                        p.nome as profissional_nome, p.email as profissional_email
                    FROM agendamentos a
                    JOIN clientes c ON a.cliente_id = c.id
                    JOIN profissionais p ON a.profissional_id = p.id
                    WHERE a.status = 0 
                    AND a.data_consulta = %s
                    ORDER BY a.hora_inicio
                """, (data_alvo,))
                
                pendentes_raw = cur.fetchall()
                
                pendentes = []
                for p in pendentes_raw:
                    pendente = {
                        "id": p[0],
                        "data_consulta": p[1].strftime("%Y-%m-%d") if p[1] else None,
                        "hora_inicio": p[2].strftime("%H:%M") if p[2] else None,
                        "hora_fim": p[3].strftime("%H:%M") if p[3] else None,
                        "tipo_atendimento": p[4],
                        "data_agendamento": p[5].isoformat() if p[5] else None,
                        "cliente": {
                            "nome": p[6],
                            "email": p[7],
                            "telefone": p[8]
                        },
                        "profissional": {
                            "nome": p[9],
                            "email": p[10]
                        }
                    }
                    pendentes.append(pendente)
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "agendamentos_pendentes": pendentes,
                    "total": len(pendentes),
                    "data_alvo": data_alvo.strftime("%Y-%m-%d"),
                    "dias_antecedencia": dias_antecedencia
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao listar agendamentos pendentes: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar agendamentos pendentes"},
            status_code=500
        )

@router.post("/agendamentos/google-calendar")
async def criar_agendamento_google_calendar(request: Request):
    """
    Cria agendamento sincronizado com Google Calendar Smart Test
    Combina agendamento no banco + evento no Google Calendar
    """
    try:
        data = await request.json()
        
        # Validar campos obrigatórios
        required_fields = ["data_consulta", "hora_inicio", "hora_fim", "titulo"]
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(
                    content={"success": False, "message": f"Campo '{field}' é obrigatório"},
                    status_code=400
                )
        
        # Validar e processar data/hora
        try:
            data_consulta = datetime.strptime(data["data_consulta"], "%Y-%m-%d").date()
            hora_inicio = datetime.strptime(data["hora_inicio"], "%H:%M").time()
            hora_fim = datetime.strptime(data["hora_fim"], "%H:%M").time()
            
            # Combinar data e hora
            start_datetime = datetime.combine(data_consulta, hora_inicio)
            end_datetime = datetime.combine(data_consulta, hora_fim)
            
        except ValueError:
            return JSONResponse(
                content={"success": False, "message": "Formato de data/hora inválido"},
                status_code=400
            )
        
        # Verificar se não é no passado
        if start_datetime < datetime.now():
            return JSONResponse(
                content={"success": False, "message": "Não é possível agendar no passado"},
                status_code=400
            )
        
        # Inicializar serviço de calendário
        calendar_service = CalendarIntegration()
        calendar_initialized = await calendar_service.initialize()
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            with db.cursor() as cur:
                # Verificar conflitos no banco de dados (se ainda usando)
                if data.get("profissional_id"):
                    cur.execute("""
                        SELECT id FROM agendamentos
                        WHERE profissional_id = %s 
                        AND data_consulta = %s
                        AND status IN (0, 1)
                        AND (
                            (hora_inicio <= %s AND hora_fim > %s) OR
                            (hora_inicio < %s AND hora_fim >= %s) OR
                            (hora_inicio >= %s AND hora_fim <= %s)
                        )
                    """, (
                        data["profissional_id"], data_consulta,
                        hora_inicio, hora_inicio,
                        hora_fim, hora_fim,
                        hora_inicio, hora_fim
                    ))
                    
                    conflito = cur.fetchone()
                    if conflito:
                        return JSONResponse(
                            content={"success": False, "message": "Horário já ocupado no banco de dados"},
                            status_code=400
                        )
                
                # Verificar disponibilidade no Google Calendar
                if calendar_initialized:
                    availability = await calendar_service.get_availability(data_consulta)
                    if availability["success"]:
                        # Verificar se horário está disponível
                        available_slots = availability.get("available_slots", [])
                        slot_disponivel = False
                        
                        for slot in available_slots:
                            slot_start = datetime.strptime(slot["start"], "%H:%M").time()
                            slot_end = datetime.strptime(slot["end"], "%H:%M").time()
                            
                            if slot_start <= hora_inicio and slot_end >= hora_fim:
                                slot_disponivel = True
                                break
                        
                        if not slot_disponivel:
                            return JSONResponse(
                                content={
                                    "success": False, 
                                    "message": "Horário não disponível na agenda Smart Test",
                                    "horarios_disponiveis": available_slots
                                },
                                status_code=400
                            )
                
                # Criar evento no Google Calendar primeiro
                event_id = None
                event_link = None
                
                if calendar_initialized:
                    attendees = []
                    if data.get("cliente_email"):
                        attendees.append(data["cliente_email"])
                    
                    calendar_result = await calendar_service.create_event(
                        title=data["titulo"],
                        start_dt=start_datetime,
                        end_dt=end_datetime,
                        description=data.get("descricao", ""),
                        attendees=attendees
                    )
                    
                    if calendar_result["success"]:
                        event_id = calendar_result["event_id"]
                        event_link = calendar_result["html_link"]
                        logging.info(f"Evento criado no Google Calendar: {event_id}")
                    else:
                        return JSONResponse(
                            content={
                                "success": False, 
                                "message": f"Erro ao criar evento no Google Calendar: {calendar_result.get('error')}"
                            },
                            status_code=500
                        )
                
                # Processar cliente (se fornecido)
                cliente_id = data.get("cliente_id")
                if not cliente_id and data.get("cliente_email"):
                    cliente_email = data["cliente_email"]
                    cliente_nome = data.get("cliente_nome", "Cliente")
                    
                    # Buscar ou criar cliente
                    cur.execute("SELECT id FROM clientes WHERE email = %s", (cliente_email,))
                    cliente = cur.fetchone()
                    
                    if not cliente:
                        cur.execute("""
                            INSERT INTO clientes (nome, email, telefone)
                            VALUES (%s, %s, %s)
                            RETURNING id
                        """, (cliente_nome, cliente_email, data.get("cliente_telefone")))
                        cliente = cur.fetchone()
                    
                    cliente_id = cliente[0] if cliente else None
                
                # Criar agendamento no banco de dados
                agendamento_id = None
                if cliente_id and data.get("profissional_id"):
                    cur.execute("""
                        INSERT INTO agendamentos (
                            cliente_id, profissional_id, data_consulta,
                            hora_inicio, hora_fim, tipo_atendimento, status,
                            observacao, event_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        cliente_id,
                        data["profissional_id"],
                        data_consulta,
                        hora_inicio,
                        hora_fim,
                        data.get("tipo_atendimento", "presencial"),
                        0,  # Status: agendado
                        data.get("descricao", ""),
                        event_id
                    ))
                    
                    result = cur.fetchone()
                    agendamento_id = result[0] if result else None
                    
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Agendamento criado com sucesso",
                    "agendamento_id": agendamento_id,
                    "google_calendar": {
                        "event_id": event_id,
                        "event_link": event_link,
                        "calendar_integration": calendar_initialized
                    },
                    "detalhes": {
                        "data": data_consulta.strftime("%Y-%m-%d"),
                        "hora_inicio": hora_inicio.strftime("%H:%M"),
                        "hora_fim": hora_fim.strftime("%H:%M"),
                        "titulo": data["titulo"]
                    }
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao criar agendamento Google Calendar: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro interno do servidor"},
            status_code=500
        )

@router.put("/agendamentos/{agendamento_id}/sync-google-calendar")
async def sincronizar_agendamento_google_calendar(agendamento_id: int, request: Request):
    """
    Sincroniza um agendamento existente com Google Calendar
    Cria evento no Google Calendar para agendamento que não tem
    """
    try:
        data = await request.json()
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            with db.cursor() as cur:
                # Buscar agendamento
                cur.execute("""
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.observacao, a.event_id,
                        c.nome as cliente_nome, c.email as cliente_email,
                        p.nome as profissional_nome
                    FROM agendamentos a
                    LEFT JOIN clientes c ON a.cliente_id = c.id
                    LEFT JOIN profissionais p ON a.profissional_id = p.id
                    WHERE a.id = %s
                """, (agendamento_id,))
                
                agendamento = cur.fetchone()
                
                if not agendamento:
                    return JSONResponse(
                        content={"success": False, "message": "Agendamento não encontrado"},
                        status_code=404
                    )
                
                # Verificar se já tem event_id
                if agendamento[6]:  # event_id
                    return JSONResponse(
                        content={
                            "success": False, 
                            "message": "Agendamento já está sincronizado com Google Calendar",
                            "event_id": agendamento[6]
                        },
                        status_code=400
                    )
                
                # Inicializar calendário
                calendar_service = CalendarIntegration()
                calendar_initialized = await calendar_service.initialize()
                
                if not calendar_initialized:
                    return JSONResponse(
                        content={"success": False, "message": "Google Calendar não disponível"},
                        status_code=503
                    )
                
                # Preparar dados do evento
                data_consulta = agendamento[1]
                hora_inicio = agendamento[2]
                hora_fim = agendamento[3]
                
                start_datetime = datetime.combine(data_consulta, hora_inicio)
                end_datetime = datetime.combine(data_consulta, hora_fim)
                
                titulo = data.get("titulo", f"Consulta - {agendamento[7] or 'Cliente'}")
                descricao = agendamento[5] or data.get("descricao", "")
                
                attendees = []
                if agendamento[8]:  # cliente_email
                    attendees.append(agendamento[8])
                
                # Criar evento
                calendar_result = await calendar_service.create_event(
                    title=titulo,
                    start_dt=start_datetime,
                    end_dt=end_datetime,
                    description=descricao,
                    attendees=attendees
                )
                
                if not calendar_result["success"]:
                    return JSONResponse(
                        content={
                            "success": False,
                            "message": f"Erro ao criar evento: {calendar_result.get('error')}"
                        },
                        status_code=500
                    )
                
                # Atualizar agendamento com event_id
                cur.execute("""
                    UPDATE agendamentos 
                    SET event_id = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    calendar_result["event_id"],
                    datetime.now(),
                    agendamento_id
                ))
                
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Agendamento sincronizado com Google Calendar",
                    "event_id": calendar_result["event_id"],
                    "event_link": calendar_result["html_link"]
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao sincronizar agendamento: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro interno do servidor"},
            status_code=500
        )
