from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/panel", tags=["panel-horarios"], dependencies=[Depends(get_current_user)])

@router.get("/horarios")
async def listar_horarios(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT h.*, p.nome as profissional_nome
                FROM horarios_disponiveis h
                LEFT JOIN profissionais p ON h.profissional_id = p.id
                ORDER BY h.dia_semana, h.manha_inicio
                """
            )
            horarios = cur.fetchall()
            return JSONResponse(content={"success": True, "horarios": horarios})
    except Exception:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.put("/horarios")
async def atualizar_horario(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID é obrigatório")

    def prep_time(value):
        return None if value in (None, "", "00:00", "00:00:00") else value

    update_fields = []
    params = []
    if "dia_semana" in payload:
        update_fields.append("dia_semana = %s")
        params.append(payload.get("dia_semana"))
    # sempre incluir campos de horário
    update_fields += [
        "manha_inicio = %s",
        "manha_fim = %s",
        "tarde_inicio = %s",
        "tarde_fim = %s",
        "intervalo_minutos = %s",
    ]
    params += [
        prep_time(payload.get("manha_inicio")),
        prep_time(payload.get("manha_fim")),
        prep_time(payload.get("tarde_inicio")),
        prep_time(payload.get("tarde_fim")),
        (None if (payload.get("intervalo_minutos") in (None, "")) else payload.get("intervalo_minutos")),
    ]
    if "ativo" in payload:
        update_fields.append("ativo = %s")
        params.append(payload.get("ativo"))
    if "profissional_id" in payload:
        update_fields.append("profissional_id = %s")
        params.append(payload.get("profissional_id"))

    params.append(payload["id"])
    with db.cursor() as cur:
        cur.execute(f"UPDATE horarios_disponiveis SET {', '.join(update_fields)} WHERE id = %s", params)
    return JSONResponse(content={"success": True, "message": "Horário atualizado com sucesso"})

@router.delete("/horarios")
async def deletar_horario(payload: dict, db = Depends(get_db)):
    if not payload or "id" not in payload:
        raise HTTPException(status_code=400, detail="ID do horário é obrigatório")
    with db.cursor() as cur:
        cur.execute("DELETE FROM horarios_disponiveis WHERE id = %s", (payload["id"],))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="Horário não encontrado")
    return JSONResponse(content={"success": True, "message": "Horário deletado com sucesso"})

