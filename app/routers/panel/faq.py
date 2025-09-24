from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ...core.db import get_db, is_postgres_connection
from ..auth import verify_admin_user
from ...schemas.panel import FAQCreate, FAQUpdate

router = APIRouter(prefix="/panel", tags=["panel-faq"], dependencies=[Depends(verify_admin_user)])

@router.get("/faq")
async def listar_faq():
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM faq ORDER BY categoria, pergunta")
                faqs = cur.fetchall()
                return JSONResponse(content=jsonable_encoder({"success": True, "faqs": faqs}))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": "Erro ao buscar FAQ", "error": str(e)}, status_code=500)


@router.post("/faq")
async def criar_faq(payload: FAQCreate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                if is_postgres_connection(db):
                    cur.execute(
                        """
                        INSERT INTO faq (pergunta, resposta, categoria, palavras_chave, ativo)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                        """,
                        (payload.pergunta, payload.resposta, payload.categoria, payload.palavras_chave, 1 if payload.ativo else 0)
                    )
                    result = cur.fetchone()
                    faq_id = result["id"] if isinstance(result, dict) else result[0]
                else:
                    cur.execute(
                        """
                        INSERT INTO faq (pergunta, resposta, categoria, palavras_chave, ativo)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (payload.pergunta, payload.resposta, payload.categoria, payload.palavras_chave, 1 if payload.ativo else 0)
                    )
                    faq_id = cur.lastrowid
                
                return JSONResponse(content={"success": True, "message": "FAQ criado com sucesso", "id": faq_id})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao criar FAQ: {str(e)}"}, status_code=500)


@router.put("/faq/{faq_id}")
async def atualizar_faq(faq_id: int, payload: FAQUpdate):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            # Montar query dinamicamente baseada nos campos fornecidos
            updates = []
            values = []
            
            if payload.pergunta is not None:
                updates.append("pergunta = %s")
                values.append(payload.pergunta)
            if payload.resposta is not None:
                updates.append("resposta = %s")
                values.append(payload.resposta)
            if payload.categoria is not None:
                updates.append("categoria = %s")
                values.append(payload.categoria)
            if payload.palavras_chave is not None:
                updates.append("palavras_chave = %s")
                values.append(payload.palavras_chave)
            if payload.ativo is not None:
                updates.append("ativo = %s")
                values.append(1 if payload.ativo else 0)
            
            if not updates:
                return JSONResponse(content={"success": False, "message": "Nenhum campo para atualizar"}, status_code=400)
            
            # Adicionar updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(faq_id)
            
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM faq WHERE id = %s", (faq_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "FAQ não encontrado"}, status_code=404)
                
                # Atualizar
                query = f"UPDATE faq SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, values)
                
                return JSONResponse(content={"success": True, "message": "FAQ atualizado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao atualizar FAQ: {str(e)}"}, status_code=500)


@router.delete("/faq/{faq_id}")
async def deletar_faq(faq_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT id FROM faq WHERE id = %s", (faq_id,))
                if not cur.fetchone():
                    return JSONResponse(content={"success": False, "message": "FAQ não encontrado"}, status_code=404)
                
                # Desativar em vez de deletar (soft delete)
                cur.execute("UPDATE faq SET ativo = 0 WHERE id = %s", (faq_id,))
                
                return JSONResponse(content={"success": True, "message": "FAQ desativado com sucesso"})
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao deletar FAQ: {str(e)}"}, status_code=500)


@router.get("/faq/{faq_id}")
async def obter_faq(faq_id: int):
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM faq WHERE id = %s", (faq_id,))
                faq = cur.fetchone()
                if not faq:
                    return JSONResponse(content={"success": False, "message": "FAQ não encontrado"}, status_code=404)
                
                return JSONResponse(content=jsonable_encoder({"success": True, "faq": faq}))
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Erro ao buscar FAQ: {str(e)}"}, status_code=500)


# Endpoints para compatibilidade com o frontend atual
@router.put("/faq")
async def atualizar_faq_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    
    faq_id = payload.pop("id")
    faq_update = FAQUpdate(**payload)
    return await atualizar_faq(faq_id, faq_update)


@router.delete("/faq")
async def deletar_faq_legacy(payload: dict):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID da FAQ é obrigatório")
    
    return await deletar_faq(payload["id"])