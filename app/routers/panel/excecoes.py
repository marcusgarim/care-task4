from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection
from ..auth import get_current_user

router = APIRouter(prefix="/panel", tags=["panel-excecoes"], dependencies=[Depends(get_current_user)])

@router.get("/excecoes")
async def listar_excecoes(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM excecoes_agenda ORDER BY data DESC")
            excecoes = cur.fetchall()
            return JSONResponse(content={"success": True, "excecoes": excecoes})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/excecoes")
async def criar_excecao(payload: dict, db = Depends(get_db)):
    if not payload or "data" not in payload or "tipo" not in payload:
        raise HTTPException(status_code=400, detail="Data e tipo são obrigatórios")
    with db.cursor() as cur:
        # Verifica duplicidade ativa para a mesma data
        cur.execute("SELECT COUNT(*) as count FROM excecoes_agenda WHERE data = %s AND ativo = 1", (payload["data"],))
        row = cur.fetchone()
        if row and (row.get("count", 0) > 0):
            raise HTTPException(status_code=400, detail="Já existe uma exceção ativa para esta data.")
        if is_postgres_connection(db):
            cur.execute(
                "INSERT INTO excecoes_agenda (data, tipo, descricao, ativo) VALUES (%s, %s, %s, %s) RETURNING id",
                (payload.get("data"), payload.get("tipo"), payload.get("descricao"), payload.get("ativo", 1))
            )
            r = cur.fetchone()
            new_id = r["id"] if r else None
        else:
            cur.execute(
                "INSERT INTO excecoes_agenda (data, tipo, descricao, ativo) VALUES (%s, %s, %s, %s)",
                (payload.get("data"), payload.get("tipo"), payload.get("descricao"), payload.get("ativo", 1))
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Exceção criada com sucesso", "id": new_id})

@router.put("/excecoes")
async def atualizar_excecao(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    with db.cursor() as cur:
        if (len(payload.keys()) == 2) and ("ativo" in payload):
            cur.execute("UPDATE excecoes_agenda SET ativo = %s WHERE id = %s", (payload["ativo"], payload["id"]))
        else:
            if "data" not in payload or "tipo" not in payload:
                raise HTTPException(status_code=400, detail="Data e tipo são obrigatórios")
            cur.execute(
                "SELECT COUNT(*) as count FROM excecoes_agenda WHERE data = %s AND ativo = 1 AND id != %s",
                (payload.get("data"), payload.get("id"))
            )
            row = cur.fetchone()
            if row and (row.get("count", 0) > 0):
                raise HTTPException(status_code=400, detail="Já existe uma exceção ativa para esta data. Desative a exceção existente primeiro.")
            cur.execute(
                "UPDATE excecoes_agenda SET data = %s, tipo = %s, descricao = %s, ativo = %s WHERE id = %s",
                (
                    payload.get("data"), payload.get("tipo"), payload.get("descricao"), payload.get("ativo", 1), payload.get("id")
                )
            )
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Exceção não encontrada")
    return JSONResponse(content={"success": True, "message": "Exceção desativada com sucesso" if payload.get("ativo") == 0 else "Exceção atualizada com sucesso"})

@router.delete("/excecoes")
async def deletar_excecao(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID da exceção é obrigatório")
    with db.cursor() as cur:
        cur.execute("UPDATE excecoes_agenda SET ativo = 0 WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Exceção não encontrada")
    return JSONResponse(content={"success": True, "message": "Exceção desativada com sucesso"})

