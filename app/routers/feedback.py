
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ..core.db import get_db
from ..schemas.feedback import FeedbackIn, RewriteIn, ChatIn
from ..services.openai_service import OpenAIService

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

@router.post("/chat")
async def chat(payload: ChatIn):
    user_message = payload.message.strip()
    if not user_message:
        return JSONResponse(content={"success": False, "message": "Mensagem vazia"})

    # Sempre tentar IA quando configurada; se falhar, responder mock para não quebrar o front
    try:
        ai = OpenAIService()
        if ai.is_configured():
            try:
                result = ai.generate_reply(user_message, payload.sessionId, payload.isFirst)
                return JSONResponse(content={
                    "success": Truzxe,
                    "message": result["message"],
                    "tokens": result["tokens"],
                })
            except Exception:
                pass  # Fallback para mock logo abaixo
        # Mock (sem IA configurada ou erro na chamada)
        reply = f"(mock) Você disse: {user_message}. Em breve este endpoint falará com a IA."
        tokens = {"prompt_tokens": max(1, len(user_message)//4), "completion_tokens": max(1, len(reply)//4)}
        return JSONResponse(content={
            "success": True,
            "message": reply,
            "tokens": tokens
        })
    except Exception:
        # Falha inesperada: ainda assim retorna mock para manter UX
        reply = f"(mock) Você disse: {user_message}. Em breve este endpoint falará com a IA."
        tokens = {"prompt_tokens": max(1, len(user_message)//4), "completion_tokens": max(1, len(reply)//4)}
        return JSONResponse(content={
            "success": True,
            "message": reply,
            "tokens": tokens
        })
        