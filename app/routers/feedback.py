from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ..core.db import get_db
from ..schemas.feedback import FeedbackIn, RewriteIn

router = APIRouter()

@router.post("/feedback")
async def feedback(payload: FeedbackIn, db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            # Buscar conversa mais recente desta sessão
            cur.execute(
                "SELECT id FROM conversas WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                (payload.sessionId,)
            )
            row = cur.fetchone()
            conversa_id = row["id"] if row else None

            if conversa_id:
                tipo = "feedback_positivo" if payload.feedbackType == "positivo" else "feedback_negativo"
                sql = (
                    "INSERT INTO conversas_treinamento (conversa_id, tipo, resposta_original, contexto_conversa, feedback_tipo) "
                    "SELECT id, %s, resposta_agente, mensagem_usuario, %s FROM conversas WHERE id = %s"
                )
                cur.execute(sql, (tipo, payload.feedbackType, conversa_id))
                return JSONResponse(content={"success": True, "message": "Feedback registrado com sucesso"})
            else:
                return JSONResponse(content={"success": False, "message": "Conversa não encontrada"})
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao registrar feedback")

@router.post("/rewrite")
async def rewrite(payload: RewriteIn, db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM conversas WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                (payload.sessionId,)
            )
            row = cur.fetchone()
            conversa_id = row["id"] if row else None

            if conversa_id:
                sql = (
                    "INSERT INTO conversas_treinamento (conversa_id, tipo, resposta_original, resposta_reescrita, contexto_conversa, feedback_tipo) "
                    "SELECT id, 'reescrita', resposta_agente, %s, mensagem_usuario, 'positivo' FROM conversas WHERE id = %s"
                )
                cur.execute(sql, (payload.rewrittenText, conversa_id))
                return JSONResponse(content={"success": True, "message": "Resposta reescrita salva com sucesso"})
            else:
                return JSONResponse(content={"success": False, "message": "Conversa não encontrada"})
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar resposta reescrita")

