from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection
from ..auth import verify_admin_user

router = APIRouter(prefix="/panel", tags=["panel-convenios"], dependencies=[Depends(verify_admin_user)])

@router.get("/convenios")
async def listar_convenios(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM convenios_aceitos ORDER BY nome")
            convenios = cur.fetchall()
            return JSONResponse(content={"success": True, "convenios": convenios})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/convenios")
async def criar_convenio(payload: dict, db = Depends(get_db)):
    if not payload or "nome" not in payload:
        raise HTTPException(status_code=400, detail="Nome do convênio é obrigatório")
    with db.cursor() as cur:
        if is_postgres_connection(db):
            cur.execute(
                "INSERT INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s) RETURNING id",
                (payload.get("nome"), payload.get("registro_ans"), payload.get("observacoes"), 1)
            )
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur.execute(
                "INSERT INTO convenios_aceitos (nome, registro_ans, observacoes, ativo) VALUES (%s, %s, %s, %s)",
                (payload.get("nome"), payload.get("registro_ans"), payload.get("observacoes"), 1)
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Convênio criado com sucesso", "id": new_id})

@router.put("/convenios")
async def atualizar_convenio(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    update_fields = []
    params = []
    for field in ("nome", "registro_ans", "observacoes", "ativo"):
        if field in payload:
            update_fields.append(f"{field} = %s")
            params.append(payload.get(field))
    if not update_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar foi fornecido")
    update_fields.append("updated_at = NOW()")
    params.append(payload["id"])
    with db.cursor() as cur:
        cur.execute(f"UPDATE convenios_aceitos SET {', '.join(update_fields)} WHERE id = %s", params)
    return JSONResponse(content={"success": True, "message": "Convênio atualizado com sucesso"})

@router.delete("/convenios")
async def deletar_convenio(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do convênio é obrigatório")
    with db.cursor() as cur:
        cur.execute("DELETE FROM convenios_aceitos WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Convênio não encontrado")
    return JSONResponse(content={"success": True, "message": "Convênio deletado com sucesso"})

