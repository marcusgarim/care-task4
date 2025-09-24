from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ...core.db import get_db, is_postgres_connection
from ..auth import verify_admin_user
from ...schemas.panel import ConvenioCreate, ConvenioUpdate

router = APIRouter(prefix="/panel", tags=["panel-convenios"], dependencies=[Depends(verify_admin_user)])

@router.get("/convenios")
async def listar_convenios():
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM convenios_aceitos ORDER BY nome")
                convenios = cur.fetchall()
                return JSONResponse(content=jsonable_encoder({"success": True, "convenios": convenios}))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": "Erro ao buscar convênios", "error": str(e)}, status_code=500)


@router.post("/convenios")
async def criar_convenio(payload: ConvenioCreate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                if is_postgres_connection(db):
                    cur.execute(
                        "INSERT INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s) RETURNING id",
                        (payload.nome, payload.registro_ans, payload.observacoes, 1 if payload.ativo else 0)
                    )
                    result = cur.fetchone()
                    convenio_id = result["id"] if isinstance(result, dict) else result[0]
                else:
                    cur.execute(
                        "INSERT INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s)",
                        (payload.nome, payload.registro_ans, payload.observacoes, 1 if payload.ativo else 0)
                    )
                    convenio_id = cur.lastrowid
                
                return JSONResponse(content={"success": True, "message": "Convênio criado com sucesso", "id": convenio_id})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao criar convênio: {str(e)}"}, status_code=500)


@router.put("/convenios/{convenio_id}")
async def atualizar_convenio(convenio_id: int, payload: ConvenioUpdate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
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
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(convenio_id)
            
            with db.cursor() as cur:
                cur.execute("SELECT id FROM convenios_aceitos WHERE id = %s", (convenio_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Convênio não encontrado"}, status_code=404)
                
                query = f"UPDATE convenios_aceitos SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, values)
                
                return JSONResponse(content={"success": True, "message": "Convênio atualizado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao atualizar convênio: {str(e)}"}, status_code=500)


@router.delete("/convenios/{convenio_id}")
async def deletar_convenio(convenio_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT id FROM convenios_aceitos WHERE id = %s", (convenio_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "Convênio não encontrado"}, status_code=404)
                
                cur.execute("UPDATE convenios_aceitos SET ativo = 0 WHERE id = %s", (convenio_id,))
                return JSONResponse(content={"success": True, "message": "Convênio desativado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao deletar convênio: {str(e)}"}, status_code=500)


@router.get("/convenios/{convenio_id}")
async def obter_convenio(convenio_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM convenios_aceitos WHERE id = %s", (convenio_id,))
                convenio = cur.fetchone()
                if not convenio:
                    return JSONResponse(content={"success": False, "message": "Convênio não encontrado"}, status_code=404)
                
                return JSONResponse(content=jsonable_encoder({"success": True, "convenio": convenio}))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao buscar convênio: {str(e)}"}, status_code=500)


# Endpoints para compatibilidade
@router.put("/convenios")
async def atualizar_convenio_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    
    convenio_id = payload.pop("id")
    convenio_update = ConvenioUpdate(**payload)
    return await atualizar_convenio(convenio_id, convenio_update)


@router.delete("/convenios")
async def deletar_convenio_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do convênio é obrigatório")
    
    return await deletar_convenio(payload["id"])