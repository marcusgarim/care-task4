from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db, is_postgres_connection
from ..auth import get_current_user, verify_admin_user


router = APIRouter(prefix="/panel", tags=["panel-usuarios"], dependencies=[Depends(verify_admin_user)])


@router.get("/usuarios")
async def listar_usuarios(db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, full_name AS nome, email, photo_url AS foto_url, google_id, is_admin, ativo, last_access FROM users ORDER BY id DESC")
        rows = cur.fetchall() or []
        return JSONResponse(content={"success": True, "usuarios": rows})


@router.get("/usuarios/{user_id}")
async def detalhe_usuario(user_id: int, db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, full_name AS nome, email, photo_url AS foto_url, google_id, is_admin, ativo, last_access FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return JSONResponse(content={"success": True, "usuario": row})


@router.put("/usuarios/{user_id}/admin")
async def alternar_admin(user_id: int, db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT is_admin FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        is_admin = (row.get("is_admin") if isinstance(row, dict) else row[0])
        new_val = 0 if is_admin in (1, True) else 1
        cur.execute("UPDATE users SET is_admin=%s WHERE id=%s", (new_val, user_id))
    return JSONResponse(content={"success": True, "message": "Status admin atualizado", "is_admin": bool(new_val)})


@router.put("/usuarios/{user_id}/ativo")
async def alternar_ativo(user_id: int, db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT ativo FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        ativo = (row.get("ativo") if isinstance(row, dict) else row[0])
        new_val = 0 if ativo in (1, True) else 1
        cur.execute("UPDATE users SET ativo=%s WHERE id=%s", (new_val, user_id))
    return JSONResponse(content={"success": True, "message": "Status ativo atualizado", "ativo": bool(new_val)})


