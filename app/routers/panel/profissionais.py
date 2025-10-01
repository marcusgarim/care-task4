from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ...core.db import get_db, is_postgres_connection
from ...schemas.panel import ProfissionalCreate, ProfissionalUpdate
from ...services.calendar_integration import CalendarIntegration
import logging

router = APIRouter(prefix="/panel", tags=["panel-profissionais"])

@router.get("/profissionais")
async def listar_profissionais():
    """Lista profissionais com informações para integração Google Calendar"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Buscar profissionais com informações extras para Google Calendar
                cur.execute("""
                    SELECT 
                        id, nome, especialidade, crm, ativo, email,
                        horas_trabalho_semana, created_at, updated_at
                    FROM profissionais 
                    ORDER BY nome
                """)
                profissionais_raw = cur.fetchall()
                
                # Formatear dados para incluir status de integração
                profissionais = []
                for p in profissionais_raw:
                    profissional = {
                        "id": p["id"],
                        "nome": p["nome"],
                        "especialidade": p["especialidade"],
                        "crm": p["crm"],
                        "ativo": bool(p["ativo"]),
                        "email": p.get("email"),
                        "horas_trabalho_semana": p.get("horas_trabalho_semana"),
                        "created_at": p["created_at"].isoformat() if p.get("created_at") else None,
                        "updated_at": p["updated_at"].isoformat() if p.get("updated_at") else None,
                        "google_calendar_integrated": p.get("email") is not None
                    }
                    profissionais.append(profissional)
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True, 
                    "profissionais": profissionais,
                    "total": len(profissionais)
                }))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Erro ao buscar profissionais: {str(e)}")
        return JSONResponse(content={"success": False, "message": "Erro ao buscar profissionais", "error": str(e)}, status_code=500)


@router.post("/profissionais")
async def criar_profissional(payload: ProfissionalCreate):
    """Cria profissional com integração Google Calendar"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se email já existe (se fornecido)
                if payload.email:
                    cur.execute("SELECT id FROM profissionais WHERE email = %s", (payload.email,))
                    if cur.fetchone():
                        return JSONResponse(
                            content={"success": False, "message": "Email já está em uso"},
                            status_code=400
                        )
                
                if is_postgres_connection(db):
                    cur.execute(
                        """
                        INSERT INTO profissionais 
                        (nome, especialidade, crm, email, horas_trabalho_semana, ativo)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """,
                        (payload.nome, payload.especialidade, payload.crm, 
                         payload.email, payload.horas_trabalho_semana, 1 if payload.ativo else 0)
                    )
                    result = cur.fetchone()
                    prof_id = result["id"] if isinstance(result, dict) else result[0]
                else:
                    cur.execute(
                        """
                        INSERT INTO profissionais 
                        (nome, especialidade, crm, email, horas_trabalho_semana, ativo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (payload.nome, payload.especialidade, payload.crm,
                         payload.email, payload.horas_trabalho_semana, 1 if payload.ativo else 0)
                    )
                    prof_id = cur.lastrowid
                
                return JSONResponse(content={
                    "success": True, 
                    "message": "Profissional criado com sucesso", 
                    "id": prof_id,
                    "google_calendar_ready": payload.email is not None
                })
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Erro ao criar profissional: {str(e)}")
        return JSONResponse(content={"success": False, "message": f"Erro ao criar profissional: {str(e)}"}, status_code=500)


@router.put("/profissionais/{prof_id}")
async def atualizar_profissional(prof_id: int, payload: ProfissionalUpdate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            # Montar query dinamicamente baseada nos campos fornecidos
            updates = []
            values = []
            
            if payload.nome is not None:
                updates.append("nome = %s")
                values.append(payload.nome)
            if payload.especialidade is not None:
                updates.append("especialidade = %s")
                values.append(payload.especialidade)
            if payload.crm is not None:
                updates.append("crm = %s")
                values.append(payload.crm)
            if payload.email is not None:
                updates.append("email = %s")
                values.append(payload.email)
            if payload.horas_trabalho_semana is not None:
                updates.append("horas_trabalho_semana = %s")
                values.append(payload.horas_trabalho_semana)
            if payload.ativo is not None:
                updates.append("ativo = %s")
                values.append(1 if payload.ativo else 0)
            
            if not updates:
                return JSONResponse(content={"success": False, "message": "Nenhum campo para atualizar"}, status_code=400)
            
            # Adicionar updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(prof_id)
            
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM profissionais WHERE id = %s", (prof_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Profissional não encontrado"}, status_code=404)
                
                # Atualizar
                query = f"UPDATE profissionais SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, values)
                
                return JSONResponse(content={"success": True, "message": "Profissional atualizado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao atualizar profissional: {str(e)}"}, status_code=500)


@router.delete("/profissionais/{prof_id}")
async def deletar_profissional(prof_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM profissionais WHERE id = %s", (prof_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Profissional não encontrado"}, status_code=404)
                
                # Verificar se há horários vinculados
                cur.execute("SELECT id FROM horarios_disponiveis WHERE profissional_id = %s LIMIT 1", (prof_id,))
                if cur.fetchone():
                    # Se há horários vinculados, apenas desativar
                    cur.execute("UPDATE profissionais SET ativo = 0 WHERE id = %s", (prof_id,))
                    return JSONResponse(content={"success": True, "message": "Profissional desativado com sucesso (possui horários vinculados)"})
                else:
                    # Se não há vinculações, pode deletar
                    cur.execute("DELETE FROM profissionais WHERE id = %s", (prof_id,))
                    return JSONResponse(content={"success": True, "message": "Profissional excluído com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao deletar profissional: {str(e)}"}, status_code=500)


@router.get("/profissionais/{prof_id}")
async def obter_profissional(prof_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM profissionais WHERE id = %s", (prof_id,))
                profissional = cur.fetchone()
                if not profissional:
                    return JSONResponse(content={"success": False, "message": "Profissional não encontrado"}, status_code=404)
                
                return JSONResponse(content={"success": True, "profissional": profissional})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao buscar profissional: {str(e)}"}, status_code=500)


# Endpoints para compatibilidade com o frontend atual
@router.put("/profissionais")
async def atualizar_profissional_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    
    prof_id = payload.pop("id")
    prof_update = ProfissionalUpdate(**payload)
    return await atualizar_profissional(prof_id, prof_update)


@router.delete("/profissionais")
async def deletar_profissional_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    
    return await deletar_profissional(payload["id"])