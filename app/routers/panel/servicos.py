from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection
from ..auth import get_current_user

router = APIRouter(prefix="/panel", tags=["panel-servicos"], dependencies=[Depends(get_current_user)])

@router.get("/servicos")
async def listar_servicos(request: Request, db = Depends(get_db)):
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
            return JSONResponse(content={"success": True, "servicos": servicos})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/servicos")
async def criar_servico(payload: dict, db = Depends(get_db)):
    if not payload or "nome" not in payload:
        raise HTTPException(status_code=400, detail="Nome do serviço é obrigatório")
    with db.cursor() as cur:
        if is_postgres_connection(db):
            cur.execute(
                """
                INSERT INTO servicos_clinica (
                    nome, descricao, valor, ativo, palavras_chave, categoria, observacoes, preparo_necessario, anestesia_tipo, local_realizacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (
                    payload.get("nome"), payload.get("descricao"),
                    (None if payload.get("valor", None) == "" else payload.get("valor")),
                    payload.get("ativo", 1), payload.get("palavras_chave"), payload.get("categoria"),
                    payload.get("observacoes"), payload.get("preparo_necessario"), payload.get("anestesia_tipo"),
                    payload.get("local_realizacao")
                )
            )
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur.execute(
                """
                INSERT INTO servicos_clinica (
                    nome, descricao, valor, ativo, palavras_chave, categoria, observacoes, preparo_necessario, anestesia_tipo, local_realizacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload.get("nome"), payload.get("descricao"),
                    (None if payload.get("valor", None) == "" else payload.get("valor")),
                    payload.get("ativo", 1), payload.get("palavras_chave"), payload.get("categoria"),
                    payload.get("observacoes"), payload.get("preparo_necessario"), payload.get("anestesia_tipo"),
                    payload.get("local_realizacao")
                )
            )
            new_id = cur.lastrowid
        return JSONResponse(content={"success": True, "message": "Serviço criado com sucesso", "id": new_id})

@router.put("/servicos")
async def atualizar_servico(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")
    update_fields = []
    params = []
    def set_field(field: str):
        nonlocal update_fields, params
        if field in payload:
            update_fields.append(f"{field} = %s")
            if payload.get(field) == "":
                params.append(None)
            else:
                params.append(payload.get(field))
    for f in ["nome", "descricao", "valor", "ativo", "palavras_chave", "categoria", "observacoes", "preparo_necessario", "anestesia_tipo", "local_realizacao"]:
        set_field(f)
    if not update_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar foi fornecido")
    update_fields.append("updated_at = NOW()")
    params.append(payload["id"])
    with db.cursor() as cur:
        cur.execute(f"UPDATE servicos_clinica SET {', '.join(update_fields)} WHERE id = %s", params)
    return JSONResponse(content={"success": True, "message": "Serviço atualizado com sucesso"})

@router.delete("/servicos")
async def deletar_servico(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do serviço é obrigatório")
    with db.cursor() as cur:
        cur.execute("DELETE FROM servicos_clinica WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Serviço não encontrado")
    return JSONResponse(content={"success": True, "message": "Serviço deletado com sucesso"})

