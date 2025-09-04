from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection

router = APIRouter(prefix="/panel", tags=["panel-pagamentos"])

@router.get("/pagamentos")
async def listar_pagamentos(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM formas_pagamento ORDER BY nome")
            pagamentos = cur.fetchall()
            return JSONResponse(content={"success": True, "pagamentos": pagamentos})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/pagamentos")
async def criar_pagamento(payload: dict, db = Depends(get_db)):
    if not payload or "nome" not in payload:
        raise HTTPException(status_code=400, detail="Nome da forma de pagamento é obrigatório")
    with db.cursor() as cur:
        if is_postgres_connection(db):
            cur.execute(
                "INSERT INTO formas_pagamento (nome, descricao, max_parcelas, ativo) VALUES (%s, %s, %s, %s) RETURNING id",
                (
                    payload.get("nome"), payload.get("descricao"), payload.get("max_parcelas", 1), payload.get("ativo", 1)
                )
            )
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur.execute(
                "INSERT INTO formas_pagamento (nome, descricao, max_parcelas, ativo) VALUES (%s, %s, %s, %s)",
                (
                    payload.get("nome"), payload.get("descricao"), payload.get("max_parcelas", 1), payload.get("ativo", 1)
                )
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Forma de pagamento criada com sucesso", "id": new_id})

@router.put("/pagamentos")
async def atualizar_pagamento(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    with db.cursor() as cur:
        if len(payload.keys()) == 2 and "ativo" in payload:
            cur.execute("UPDATE formas_pagamento SET ativo = %s WHERE id = %s", (payload["ativo"], payload["id"]))
        else:
            if "nome" not in payload:
                raise HTTPException(status_code=400, detail="Nome é obrigatório")
            cur.execute(
                "UPDATE formas_pagamento SET nome = %s, descricao = %s, max_parcelas = %s, ativo = %s WHERE id = %s",
                (
                    payload.get("nome"), payload.get("descricao"), payload.get("max_parcelas", 1), payload.get("ativo", 1), payload.get("id")
                )
            )
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Forma de pagamento não encontrada")
    return JSONResponse(content={"success": True, "message": "Forma de pagamento desativada com sucesso" if payload.get("ativo") == 0 else "Forma de pagamento atualizada com sucesso"})

@router.delete("/pagamentos")
async def deletar_pagamento(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID da forma de pagamento é obrigatório")
    with db.cursor() as cur:
        cur.execute("UPDATE formas_pagamento SET ativo = 0 WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Forma de pagamento não encontrada")
    return JSONResponse(content={"success": True, "message": "Forma de pagamento desativada com sucesso"})

