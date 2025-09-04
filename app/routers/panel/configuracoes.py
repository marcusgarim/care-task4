from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...core.db import get_db

router = APIRouter(prefix="/panel", tags=["panel-configuracoes"])

@router.get("/configuracoes")
async def listar_configuracoes(db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT chave, valor FROM configuracoes ORDER BY id")
            configuracoes = cur.fetchall()
            return JSONResponse(content={"success": True, "configuracoes": configuracoes})
    except Exception as e:
        return JSONResponse(content={"error": "Erro na conexão com banco de dados"}, status_code=500)

@router.post("/configuracoes")
async def atualizar_configuracoes(payload: dict, db = Depends(get_db)):
    if not payload:
        raise HTTPException(status_code=400, detail="Dados inválidos")
    try:
        with db.cursor() as cur:
            for chave, valor in payload.items():
                cur.execute(
                    "UPDATE configuracoes SET valor = %s, updated_at = NOW() WHERE chave = %s",
                    (valor, chave)
                )
        try:
            db.commit()
        except Exception:
            pass
        return JSONResponse(content={"success": True, "message": "Configurações atualizadas com sucesso"})
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse(content={"success": False, "message": "Erro ao atualizar configurações"})

