from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Annotated, List, Optional
from psycopg import Connection
from datetime import datetime, date
import logging

from ..core.db import get_db
router = APIRouter(prefix="/admin", tags=["admin-clientes"])

@router.get("/clientes")
async def listar_clientes(
    busca: Optional[str] = None,
    ativo: Optional[bool] = None
):
    """Lista todos os clientes com filtros opcionais"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Construir query com filtros
                where_conditions = []
                params = []
                
                if busca:
                    where_conditions.append("(nome ILIKE %s OR email ILIKE %s OR telefone ILIKE %s)")
                    busca_param = f"%{busca}%"
                    params.extend([busca_param, busca_param, busca_param])
                
                if ativo is not None:
                    where_conditions.append("ativo = %s")
                    params.append(1 if ativo else 0)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                cur.execute(f"""
                    SELECT 
                        id, nome, email, telefone, data_nascimento,
                        endereco, observacoes, ativo, created_at
                    FROM clientes
                    WHERE {where_clause}
                    ORDER BY nome
                """, params)
                
                clientes_raw = cur.fetchall()
                clientes = []
                
                for c in clientes_raw:
                    clientes.append({
                        "id": c["id"],
                        "nome": c["nome"],
                        "email": c["email"],
                        "telefone": c.get("telefone"),
                        "data_nascimento": c["data_nascimento"].strftime("%Y-%m-%d") if c.get("data_nascimento") else None,
                        "endereco": c.get("endereco"),
                        "observacoes": c.get("observacoes"),
                        "ativo": bool(c["ativo"]),
                        "created_at": c["created_at"].isoformat() if c.get("created_at") else None
                    })
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "clientes": clientes,
                    "total": len(clientes)
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao listar clientes: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar clientes"},
            status_code=500
        )

@router.get("/clientes/{cliente_id}")
async def obter_cliente(
    cliente_id: int
):
    """Obtém detalhes de um cliente específico"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Buscar dados do cliente
                cur.execute("""
                    SELECT 
                        id, nome, email, telefone, data_nascimento,
                        endereco, observacoes, ativo, created_at, updated_at
                    FROM clientes
                    WHERE id = %s
                """, (cliente_id,))
                
                cliente_raw = cur.fetchone()
                
                if not cliente_raw:
                    return JSONResponse(
                        content={"success": False, "message": "Cliente não encontrado"},
                        status_code=404
                    )
                
                # Buscar histórico de agendamentos
                cur.execute("""
                    SELECT 
                        a.id, a.data_consulta, a.hora_inicio, a.hora_fim,
                        a.tipo_atendimento, a.status, a.valor,
                        p.nome as profissional_nome,
                        s.nome as servico_nome
                    FROM agendamentos a
                    JOIN profissionais p ON a.profissional_id = p.id
                    LEFT JOIN servicos_clinica s ON a.servico_id = s.id
                    WHERE a.cliente_id = %s
                    ORDER BY a.data_consulta DESC, a.hora_inicio DESC
                    LIMIT 20
                """, (cliente_id,))
                
                agendamentos_raw = cur.fetchall()
                
                # Formatear dados
                cliente = {
                    "id": cliente_raw[0],
                    "nome": cliente_raw[1],
                    "email": cliente_raw[2],
                    "telefone": cliente_raw[3],
                    "data_nascimento": cliente_raw[4].strftime("%Y-%m-%d") if cliente_raw[4] else None,
                    "endereco": cliente_raw[5],
                    "observacoes": cliente_raw[6],
                    "ativo": bool(cliente_raw[7]),
                    "created_at": cliente_raw[8].isoformat() if cliente_raw[8] else None,
                    "updated_at": cliente_raw[9].isoformat() if cliente_raw[9] else None
                }
                
                agendamentos = []
                status_map = {0: "Agendado", 1: "Confirmado", 2: "Realizado", 3: "Cancelado", 4: "Falta"}
                
                for a in agendamentos_raw:
                    agendamentos.append({
                        "id": a[0],
                        "data_consulta": a[1].strftime("%Y-%m-%d") if a[1] else None,
                        "hora_inicio": a[2].strftime("%H:%M") if a[2] else None,
                        "hora_fim": a[3].strftime("%H:%M") if a[3] else None,
                        "tipo_atendimento": a[4],
                        "status": a[5],
                        "status_nome": status_map.get(a[5], "Desconhecido"),
                        "valor": float(a[6]) if a[6] else None,
                        "profissional_nome": a[7],
                        "servico_nome": a[8]
                    })
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "cliente": cliente,
                    "agendamentos": agendamentos,
                    "total_agendamentos": len(agendamentos)
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao obter cliente {cliente_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar cliente"},
            status_code=500
        )

@router.post("/clientes")
async def criar_cliente(
    request: Request
):
    """Cria um novo cliente"""
    try:
        data = await request.json()
        
        # Validar campos obrigatórios
        nome = data.get("nome")
        email = data.get("email")
        
        if not nome or not email:
            return JSONResponse(
                content={"success": False, "message": "Nome e email são obrigatórios"},
                status_code=400
            )
        
        # Validar formato do email (básico)
        if "@" not in email or "." not in email.split("@")[1]:
            return JSONResponse(
                content={"success": False, "message": "Formato de email inválido"},
                status_code=400
            )
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se email já existe
                cur.execute("SELECT id FROM clientes WHERE email = %s", (email,))
                if cur.fetchone():
                    return JSONResponse(
                        content={"success": False, "message": "Email já cadastrado"},
                        status_code=400
                    )
                
                # Processar data de nascimento
                data_nascimento = None
                if data.get("data_nascimento"):
                    try:
                        data_nascimento = datetime.strptime(data["data_nascimento"], "%Y-%m-%d").date()
                    except ValueError:
                        return JSONResponse(
                            content={"success": False, "message": "Formato de data inválido. Use YYYY-MM-DD"},
                            status_code=400
                        )
                
                # Inserir cliente
                cur.execute("""
                    INSERT INTO clientes (nome, email, telefone, data_nascimento, endereco, observacoes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    nome,
                    email,
                    data.get("telefone"),
                    data_nascimento,
                    data.get("endereco"),
                    data.get("observacoes")
                ))
                
                cliente_id = cur.fetchone()[0]
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Cliente criado com sucesso",
                    "cliente_id": cliente_id
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao criar cliente: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao criar cliente"},
            status_code=500
        )

@router.put("/clientes/{cliente_id}")
async def atualizar_cliente(
    cliente_id: int,
    request: Request
):
    """Atualiza dados de um cliente"""
    try:
        data = await request.json()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se cliente existe
                cur.execute("SELECT id FROM clientes WHERE id = %s", (cliente_id,))
                if not cur.fetchone():
                    return JSONResponse(
                        content={"success": False, "message": "Cliente não encontrado"},
                        status_code=404
                    )
                
                # Verificar email único (se alterado)
                if "email" in data:
                    cur.execute(
                        "SELECT id FROM clientes WHERE email = %s AND id != %s",
                        (data["email"], cliente_id)
                    )
                    if cur.fetchone():
                        return JSONResponse(
                            content={"success": False, "message": "Email já em uso por outro cliente"},
                            status_code=400
                        )
                
                # Preparar campos para atualização
                campos = []
                valores = []
                
                if "nome" in data:
                    campos.append("nome = %s")
                    valores.append(data["nome"])
                
                if "email" in data:
                    campos.append("email = %s")
                    valores.append(data["email"])
                
                if "telefone" in data:
                    campos.append("telefone = %s")
                    valores.append(data["telefone"])
                
                if "data_nascimento" in data:
                    data_nascimento = None
                    if data["data_nascimento"]:
                        try:
                            data_nascimento = datetime.strptime(data["data_nascimento"], "%Y-%m-%d").date()
                        except ValueError:
                            return JSONResponse(
                                content={"success": False, "message": "Formato de data inválido"},
                                status_code=400
                            )
                    campos.append("data_nascimento = %s")
                    valores.append(data_nascimento)
                
                if "endereco" in data:
                    campos.append("endereco = %s")
                    valores.append(data["endereco"])
                
                if "observacoes" in data:
                    campos.append("observacoes = %s")
                    valores.append(data["observacoes"])
                
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
                valores.append(cliente_id)
                
                # Executar atualização
                sql = f"UPDATE clientes SET {', '.join(campos)} WHERE id = %s"
                cur.execute(sql, valores)
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Cliente atualizado com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao atualizar cliente {cliente_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao atualizar cliente"},
            status_code=500
        )

@router.delete("/clientes/{cliente_id}")
async def excluir_cliente(
    cliente_id: int
):
    """Desativa um cliente (soft delete)"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se cliente existe
                cur.execute("SELECT nome FROM clientes WHERE id = %s", (cliente_id,))
                cliente = cur.fetchone()
                
                if not cliente:
                    return JSONResponse(
                        content={"success": False, "message": "Cliente não encontrado"},
                        status_code=404
                    )
                
                # Verificar se há agendamentos ativos
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM agendamentos 
                    WHERE cliente_id = %s AND status IN (0, 1) AND data_consulta >= CURRENT_DATE
                """, (cliente_id,))
                
                agendamentos_ativos = cur.fetchone()[0]
                
                if agendamentos_ativos > 0:
                    return JSONResponse(
                        content={
                            "success": False, 
                            "message": f"Cliente possui {agendamentos_ativos} agendamento(s) ativo(s). Cancele-os primeiro."
                        },
                        status_code=400
                    )
                
                # Desativar cliente
                cur.execute(
                    "UPDATE clientes SET ativo = 0, updated_at = %s WHERE id = %s",
                    (datetime.now(), cliente_id)
                )
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Cliente {cliente[0]} desativado com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao excluir cliente {cliente_id}: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao excluir cliente"},
            status_code=500
        )
