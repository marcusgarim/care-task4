from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection

router = APIRouter(prefix="/panel", tags=["panel-faq"])

@router.get("/faq")
async def listar_faq(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM faq ORDER BY categoria, pergunta")
            faqs = cur.fetchall()
            return JSONResponse(content={"success": True, "faqs": faqs})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/faq")
async def criar_faq(payload: dict, db = Depends(get_db)):
    if not payload or "pergunta" not in payload or "resposta" not in payload:
        raise HTTPException(status_code=400, detail="Pergunta e resposta são obrigatórias")
    with db.cursor() as cur:
        if is_postgres_connection(db):
            cur.execute(
                "INSERT INTO faq (pergunta, resposta, categoria, palavras_chave, ativo) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (
                    payload.get("pergunta"), payload.get("resposta"), payload.get("categoria"),
                    payload.get("palavras_chave"), payload.get("ativo", 1)
                )
            )
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur.execute(
                "INSERT INTO faq (pergunta, resposta, categoria, palavras_chave, ativo) VALUES (%s, %s, %s, %s, %s)",
                (
                    payload.get("pergunta"), payload.get("resposta"), payload.get("categoria"),
                    payload.get("palavras_chave"), payload.get("ativo", 1)
                )
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "FAQ criada com sucesso", "id": new_id})

@router.put("/faq")
async def atualizar_faq(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    with db.cursor() as cur:
        if len(payload.keys()) == 2 and "ativo" in payload:
            cur.execute("UPDATE faq SET ativo = %s WHERE id = %s", (payload["ativo"], payload["id"]))
        else:
            if "pergunta" not in payload or "resposta" not in payload:
                raise HTTPException(status_code=400, detail="Pergunta e resposta são obrigatórias")
            cur.execute(
                "UPDATE faq SET pergunta = %s, resposta = %s, categoria = %s, palavras_chave = %s, ativo = %s WHERE id = %s",
                (
                    payload.get("pergunta"), payload.get("resposta"), payload.get("categoria"),
                    payload.get("palavras_chave"), payload.get("ativo", 1), payload.get("id")
                )
            )
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="FAQ não encontrada")
    return JSONResponse(content={"success": True, "message": "FAQ desativada com sucesso" if payload.get("ativo") == 0 else "FAQ atualizada com sucesso"})

@router.delete("/faq")
async def deletar_faq(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID da FAQ é obrigatório")
    with db.cursor() as cur:
        cur.execute("UPDATE faq SET ativo = 0 WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="FAQ não encontrada")
    return JSONResponse(content={"success": True, "message": "FAQ desativada com sucesso"})

