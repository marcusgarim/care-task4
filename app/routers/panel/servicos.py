from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ...core.db import get_db, is_postgres_connection
from ..auth import verify_admin_user
from ...schemas.panel import ServicoCreate, ServicoUpdate

router = APIRouter(prefix="/panel", tags=["panel-servicos"], dependencies=[Depends(verify_admin_user)])

@router.get("/servicos")
async def listar_servicos(request: Request):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            id_str = request.query_params.get("id")
            with db.cursor() as cur:
                if id_str is not None:
                    cur.execute("SELECT * FROM servicos_clinica WHERE id = %s", (id_str,))
                    servico = cur.fetchone()
                    if servico:
                        return JSONResponse(content={"success": True, "servico": servico})
                    return JSONResponse(content={"success": False, "message": "Serviço não encontrado"})
                cur.execute("SELECT * FROM servicos_clinica ORDER BY nome")
                servicos = cur.fetchall()
                return JSONResponse(content=jsonable_encoder({"success": True, "servicos": servicos}))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": "Erro ao buscar serviços", "error": str(e)}, status_code=500)


@router.post("/servicos")
async def criar_servico(payload: ServicoCreate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                if is_postgres_connection(db):
                    cur.execute(
                        """
                        INSERT INTO servicos_clinica (
                            nome, descricao, valor, categoria, palavras_chave, observacoes, 
                            preparo_necessario, anestesia_tipo, local_realizacao, ativo
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """,
                        (
                            payload.nome, payload.descricao, payload.valor, payload.categoria,
                            payload.palavras_chave, payload.observacoes, payload.preparo_necessario,
                            payload.anestesia_tipo, payload.local_realizacao, 1 if payload.ativo else 0
                        )
                    )
                    result = cur.fetchone()
                    servico_id = result["id"] if isinstance(result, dict) else result[0]
                else:
                    cur.execute(
                        """
                        INSERT INTO servicos_clinica (
                            nome, descricao, valor, categoria, palavras_chave, observacoes, 
                            preparo_necessario, anestesia_tipo, local_realizacao, ativo
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload.nome, payload.descricao, payload.valor, payload.categoria,
                            payload.palavras_chave, payload.observacoes, payload.preparo_necessario,
                            payload.anestesia_tipo, payload.local_realizacao, 1 if payload.ativo else 0
                        )
                    )
                    servico_id = cur.lastrowid
                
                return JSONResponse(content={"success": True, "message": "Serviço criado com sucesso", "id": servico_id})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao criar serviço: {str(e)}"}, status_code=500)


@router.put("/servicos/{servico_id}")
async def atualizar_servico(servico_id: int, payload: ServicoUpdate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            # Montar query dinamicamente baseada nos campos fornecidos
            updates = []
            values = []
            
            for field, value in payload.dict(exclude_unset=True).items():
                if value is not None:
                    updates.append(f"{field} = %s")
                    if field == "ativo":
                        values.append(1 if value else 0)
                    else:
                        values.append(value)
            
            if not updates:
                return JSONResponse(content={"success": False, "message": "Nenhum campo para atualizar"}, status_code=400)
            
            # Adicionar updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(servico_id)
            
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM servicos_clinica WHERE id = %s", (servico_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Serviço não encontrado"}, status_code=404)
                
                # Atualizar
                query = f"UPDATE servicos_clinica SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, values)
                
                return JSONResponse(content={"success": True, "message": "Serviço atualizado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao atualizar serviço: {str(e)}"}, status_code=500)


@router.delete("/servicos/{servico_id}")
async def deletar_servico(servico_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM servicos_clinica WHERE id = %s", (servico_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Serviço não encontrado"}, status_code=404)
                
                # Desativar em vez de deletar (soft delete)
                cur.execute("UPDATE servicos_clinica SET ativo = 0 WHERE id = %s", (servico_id,))
                
                return JSONResponse(content={"success": True, "message": "Serviço desativado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao deletar serviço: {str(e)}"}, status_code=500)


@router.get("/servicos/{servico_id}")
async def obter_servico(servico_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM servicos_clinica WHERE id = %s", (servico_id,))
                servico = cur.fetchone()
                if not servico:
                    return JSONResponse(content={"success": False, "message": "Serviço não encontrado"}, status_code=404)
                
                return JSONResponse(content={"success": True, "servico": servico})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao buscar serviço: {str(e)}"}, status_code=500)


# Endpoints para compatibilidade com o frontend atual
@router.put("/servicos")
async def atualizar_servico_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    
    servico_id = payload.pop("id")
    # Converter valores vazios para None
    for key, value in payload.items():
        if value == "":
            payload[key] = None
    
    servico_update = ServicoUpdate(**payload)
    return await atualizar_servico(servico_id, servico_update)


@router.delete("/servicos")
async def deletar_servico_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do serviço é obrigatório")
    
    return await deletar_servico(payload["id"])