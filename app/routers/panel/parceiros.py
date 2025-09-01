from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db

router = APIRouter(prefix="/panel", tags=["panel-parceiros"])

@router.get("/parceiros")
async def listar_parceiros(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM parceiros ORDER BY nome")
            parceiros = cur.fetchall()
            return JSONResponse(content={"success": True, "parceiros": parceiros})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/parceiros")
async def criar_parceiro(payload: dict, db = Depends(get_db)):
    if not payload or "nome" not in payload:
        raise HTTPException(status_code=400, detail="Nome do parceiro é obrigatório")
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO parceiros (tipo, nome, endereco, telefone, ativo) VALUES (%s, %s, %s, %s, %s)",
            (
                payload.get("tipo"), payload.get("nome"), payload.get("endereco"),
                payload.get("telefone"), payload.get("ativo", 1)
            )
        )
        new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Parceiro criado com sucesso", "id": new_id})

@router.put("/parceiros")
async def atualizar_parceiro(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    with db.cursor() as cur:
        if len(payload.keys()) == 2 and "ativo" in payload:
            cur.execute("UPDATE parceiros SET ativo = %s WHERE id = %s", (payload["ativo"], payload["id"]))
        else:
            if "nome" not in payload:
                raise HTTPException(status_code=400, detail="Nome é obrigatório")
            cur.execute(
                "UPDATE parceiros SET tipo = %s, nome = %s, endereco = %s, telefone = %s, ativo = %s, updated_at = NOW() WHERE id = %s",
                (
                    payload.get("tipo"), payload.get("nome"), payload.get("endereco"),
                    payload.get("telefone"), payload.get("ativo", 1), payload.get("id")
                )
            )
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Parceiro não encontrado")
    return JSONResponse(content={"success": True, "message": "Parceiro desativado com sucesso" if payload.get("ativo") == 0 else "Parceiro atualizado com sucesso"})

@router.delete("/parceiros")
async def deletar_parceiro(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do parceiro é obrigatório")
    with db.cursor() as cur:
        cur.execute("UPDATE parceiros SET ativo = 0 WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Parceiro não encontrado")
    return JSONResponse(content={"success": True, "message": "Parceiro desativado com sucesso"})

