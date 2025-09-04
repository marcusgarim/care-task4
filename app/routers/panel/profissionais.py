from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ...core.db import get_db, is_postgres_connection

router = APIRouter(prefix="/panel", tags=["panel-profissionais"])

@router.get("/profissionais")
async def listar_profissionais(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM profissionais ORDER BY nome")
            profissionais = cur.fetchall()
            return JSONResponse(content=jsonable_encoder({"success": True, "profissionais": profissionais}))
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/profissionais")
async def criar_profissional(payload: dict, db = Depends(get_db)):
    if not payload or "nome" not in payload:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    with db.cursor() as cur:
        if is_postgres_connection(db):
            cur.execute(
                "INSERT INTO profissionais (nome, especialidade, crm, ativo) VALUES (%s, %s, %s, %s) RETURNING id",
                (payload.get("nome"), payload.get("especialidade"), payload.get("crm"), payload.get("ativo", 1))
            )
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur.execute(
                "INSERT INTO profissionais (nome, especialidade, crm, ativo) VALUES (%s, %s, %s, %s)",
                (payload.get("nome"), payload.get("especialidade"), payload.get("crm"), payload.get("ativo", 1))
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Profissional criado com sucesso", "id": new_id})

@router.put("/profissionais")
async def atualizar_profissional(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    update_fields = []
    params = []
    for field in ("nome", "especialidade", "crm", "ativo"):
        if field in payload:
            update_fields.append(f"{field} = %s")
            params.append(payload.get(field))
    if not update_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar foi fornecido")
    params.append(payload["id"])
    with db.cursor() as cur:
        cur.execute(f"UPDATE profissionais SET {', '.join(update_fields)} WHERE id = %s", params)
    return JSONResponse(content={"success": True, "message": "Profissional atualizado com sucesso"})

@router.delete("/profissionais")
async def deletar_profissional(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    with db.cursor() as cur:
        cur.execute("DELETE FROM profissionais WHERE id = %s", (payload["id"],))
    return JSONResponse(content={"success": True, "message": "Profissional excluído com sucesso"})

