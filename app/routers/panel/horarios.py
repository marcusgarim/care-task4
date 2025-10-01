from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List, Optional
from psycopg import Connection
from datetime import datetime, time, date
import logging

from ...core.db import get_db
from ..auth import verify_admin_user

router = APIRouter(prefix="/panel", tags=["panel-horarios"], dependencies=[Depends(verify_admin_user)])

# Mapeamento de dias da semana
DIAS_SEMANA = {
    1: "Segunda-feira",
    2: "Terça-feira", 
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sábado",
    7: "Domingo"
}

TIPOS_ATENDIMENTO = {
    "presencial": "Presencial",
    "remoto": "Remoto",
    "hibrido": "Híbrido",
    "indisponivel": "Indisponível"
}

@router.get("/horarios")
async def listar_horarios():
    """Lista os horários disponíveis organizados por profissional"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Buscar horários com informações do profissional
                cur.execute("""
                    SELECT 
                        dp.id,
                        dp.profissional_id,
                        p.nome as profissional_nome,
                        dp.dia_semana,
                        dp.hora_inicio,
                        dp.hora_fim,
                        dp.intervalo_inicio,
                        dp.intervalo_fim,
                        dp.tipo_atendimento,
                        dp.duracao_consulta,
                        dp.ativo
                    FROM disponibilidades_profissional dp
                    JOIN profissionais p ON dp.profissional_id = p.id
                    WHERE dp.ativo = 1 AND p.ativo = 1
                    ORDER BY p.nome, dp.dia_semana
                """)
                horarios = cur.fetchall()
                
                # Organizar por profissional
                profissionais_horarios = {}
                for horario in horarios:
                    prof_id = horario[1]
                    prof_nome = horario[2]
                    
                    if prof_id not in profissionais_horarios:
                        profissionais_horarios[prof_id] = {
                            "profissional_id": prof_id,
                            "profissional_nome": prof_nome,
                            "horarios": []
                        }
                    
                    profissionais_horarios[prof_id]["horarios"].append({
                        "id": horario[0],
                        "dia_semana": horario[3],
                        "dia_semana_nome": DIAS_SEMANA.get(horario[3], f"Dia {horario[3]}"),
                        "hora_inicio": horario[4].strftime("%H:%M") if horario[4] else None,
                        "hora_fim": horario[5].strftime("%H:%M") if horario[5] else None,
                        "intervalo_inicio": horario[6].strftime("%H:%M") if horario[6] else None,
                        "intervalo_fim": horario[7].strftime("%H:%M") if horario[7] else None,
                        "tipo_atendimento": horario[8],
                        "tipo_atendimento_nome": TIPOS_ATENDIMENTO.get(horario[8], horario[8]),
                        "duracao_consulta": horario[9],
                        "ativo": horario[10]
                    })
                
                # Converter para lista
                resultado = list(profissionais_horarios.values())
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True, 
                    "profissionais": resultado
                }))
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao listar horários: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar horários"}, 
            status_code=500
        )

@router.get("/horarios/profissional/{profissional_id}")
async def obter_horarios_profissional(profissional_id: int):
    """Obtém os horários de um profissional específico"""
    try:
        db_gen = get_db()
        db = next(db_gen)
    try:
        with db.cursor() as cur:
                # Verificar se o profissional existe
                cur.execute("SELECT nome FROM profissionais WHERE id = %s AND ativo = 1", (profissional_id,))
                profissional = cur.fetchone()
                
                if not profissional:
                    return JSONResponse(
                        content={"success": False, "message": "Profissional não encontrado"},
                        status_code=404
                    )
                
                # Buscar horários do profissional
                cur.execute("""
                    SELECT 
                        id, dia_semana, hora_inicio, hora_fim,
                        intervalo_inicio, intervalo_fim, tipo_atendimento,
                        duracao_consulta, ativo
                    FROM disponibilidades_profissional
                    WHERE profissional_id = %s AND ativo = 1
                    ORDER BY dia_semana
                """, (profissional_id,))
                
                horarios_raw = cur.fetchall()
                horarios = []
                
                for h in horarios_raw:
                    horarios.append({
                        "id": h[0],
                        "dia_semana": h[1],
                        "dia_semana_nome": DIAS_SEMANA.get(h[1], f"Dia {h[1]}"),
                        "hora_inicio": h[2].strftime("%H:%M") if h[2] else None,
                        "hora_fim": h[3].strftime("%H:%M") if h[3] else None,
                        "intervalo_inicio": h[4].strftime("%H:%M") if h[4] else None,
                        "intervalo_fim": h[5].strftime("%H:%M") if h[5] else None,
                        "tipo_atendimento": h[6],
                        "tipo_atendimento_nome": TIPOS_ATENDIMENTO.get(h[6], h[6]),
                        "duracao_consulta": h[7],
                        "ativo": h[8]
                    })
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "profissional_id": profissional_id,
                    "profissional_nome": profissional[0],
                    "horarios": horarios
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao obter horários do profissional {profissional_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar horários"},
            status_code=500
        )

@router.post("/horarios/profissional/{profissional_id}/definir")
async def definir_horarios_profissional(
    profissional_id: int,
    request: Request
):
    """Define os horários semanais de um profissional"""
    try:
        data = await request.json()
        horarios = data.get("horarios", [])
        
        if not horarios:
            return JSONResponse(
                content={"success": False, "message": "Lista de horários é obrigatória"},
                status_code=400
            )
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se o profissional existe
                cur.execute("SELECT nome FROM profissionais WHERE id = %s AND ativo = 1", (profissional_id,))
                profissional = cur.fetchone()
                
                if not profissional:
                    return JSONResponse(
                        content={"success": False, "message": "Profissional não encontrado"},
                        status_code=404
                    )
                
                # Remover horários existentes
                cur.execute(
                    "DELETE FROM disponibilidades_profissional WHERE profissional_id = %s",
                    (profissional_id,)
                )
                
                # Inserir novos horários
                for horario in horarios:
                    dia_semana = horario.get("dia_semana")
                    tipo_atendimento = horario.get("tipo_atendimento", "presencial")
                    
                    if not dia_semana or dia_semana < 1 or dia_semana > 7:
                        continue
                    
                    if tipo_atendimento == "indisponivel":
                        # Para dias indisponíveis, inserir só o tipo
                        cur.execute("""
                            INSERT INTO disponibilidades_profissional
                            (profissional_id, dia_semana, tipo_atendimento, ativo)
                            VALUES (%s, %s, %s, 1)
                        """, (profissional_id, dia_semana, tipo_atendimento))
                    else:
                        # Para dias disponíveis, inserir com horários
                        hora_inicio = horario.get("hora_inicio")
                        hora_fim = horario.get("hora_fim")
                        intervalo_inicio = horario.get("intervalo_inicio")
                        intervalo_fim = horario.get("intervalo_fim")
                        duracao_consulta = horario.get("duracao_consulta", 60)
                        
                        # Converter strings de tempo para objetos time
                        try:
                            if hora_inicio:
                                hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
                            if hora_fim:
                                hora_fim = datetime.strptime(hora_fim, "%H:%M").time()
                            if intervalo_inicio:
                                intervalo_inicio = datetime.strptime(intervalo_inicio, "%H:%M").time()
                            if intervalo_fim:
                                intervalo_fim = datetime.strptime(intervalo_fim, "%H:%M").time()
                        except ValueError as ve:
                            return JSONResponse(
                                content={"success": False, "message": f"Formato de horário inválido: {str(ve)}"},
                                status_code=400
                            )
                        
                        cur.execute("""
                            INSERT INTO disponibilidades_profissional
                            (profissional_id, dia_semana, hora_inicio, hora_fim,
                             intervalo_inicio, intervalo_fim, tipo_atendimento, 
                             duracao_consulta, ativo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                        """, (
                            profissional_id, dia_semana, hora_inicio, hora_fim,
                            intervalo_inicio, intervalo_fim, tipo_atendimento,
                            duracao_consulta
                        ))
                
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Horários definidos com sucesso para {profissional[0]}"
                })
                
        finally:
            try:
                db.close()
    except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao definir horários do profissional {profissional_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao salvar horários"},
            status_code=500
        )

@router.put("/horarios/{horario_id}")
async def atualizar_horario(
    horario_id: int,
    request: Request
):
    """Atualiza um horário específico"""
    try:
        data = await request.json()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se o horário existe
                cur.execute(
                    "SELECT profissional_id FROM disponibilidades_profissional WHERE id = %s",
                    (horario_id,)
                )
                horario_existe = cur.fetchone()
                
                if not horario_existe:
                    return JSONResponse(
                        content={"success": False, "message": "Horário não encontrado"},
                        status_code=404
                    )
                
                # Preparar campos para atualização
                campos = []
                valores = []
                
                if "hora_inicio" in data:
                    campos.append("hora_inicio = %s")
                    valores.append(datetime.strptime(data["hora_inicio"], "%H:%M").time() if data["hora_inicio"] else None)
                
                if "hora_fim" in data:
                    campos.append("hora_fim = %s")
                    valores.append(datetime.strptime(data["hora_fim"], "%H:%M").time() if data["hora_fim"] else None)
                
                if "intervalo_inicio" in data:
                    campos.append("intervalo_inicio = %s")
                    valores.append(datetime.strptime(data["intervalo_inicio"], "%H:%M").time() if data["intervalo_inicio"] else None)
                
                if "intervalo_fim" in data:
                    campos.append("intervalo_fim = %s") 
                    valores.append(datetime.strptime(data["intervalo_fim"], "%H:%M").time() if data["intervalo_fim"] else None)
                
                if "tipo_atendimento" in data:
                    campos.append("tipo_atendimento = %s")
                    valores.append(data["tipo_atendimento"])
                
                if "duracao_consulta" in data:
                    campos.append("duracao_consulta = %s")
                    valores.append(data["duracao_consulta"])
                
                if "ativo" in data:
                    campos.append("ativo = %s")
                    valores.append(1 if data["ativo"] else 0)
                
                if not campos:
                    return JSONResponse(
                        content={"success": False, "message": "Nenhum campo para atualizar"},
                        status_code=400
                    )
                
                # Adicionar timestamp de atualização
                campos.append("updated_at = %s")
                valores.append(datetime.now())
                valores.append(horario_id)
                
                # Executar atualização
                sql = f"UPDATE disponibilidades_profissional SET {', '.join(campos)} WHERE id = %s"
                cur.execute(sql, valores)
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Horário atualizado com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except ValueError as ve:
        return JSONResponse(
            content={"success": False, "message": f"Formato de horário inválido: {str(ve)}"},
            status_code=400
        )
    except Exception as e:
        logging.error(f"Erro ao atualizar horário {horario_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao atualizar horário"},
            status_code=500
        )

@router.delete("/horarios/{horario_id}")
async def excluir_horario(
    horario_id: int
):
    """Exclui um horário específico"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute(
                    "SELECT id FROM disponibilidades_profissional WHERE id = %s",
                    (horario_id,)
                )
                if not cur.fetchone():
                    return JSONResponse(
                        content={"success": False, "message": "Horário não encontrado"},
                        status_code=404
                    )
                
                # Excluir
                cur.execute(
                    "DELETE FROM disponibilidades_profissional WHERE id = %s",
                    (horario_id,)
                )
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Horário excluído com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao excluir horário {horario_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao excluir horário"},
            status_code=500
        )