import os
import json
from typing import Any, Dict, List, Optional, Tuple
import re

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from ..core.db import get_db, is_postgres_connection
from ..schemas.feedback import ChatIn
from ..services.openai_service import OpenAIService


router = APIRouter()


def _require_auth_header(authorization: Optional[str] = Header(None)) -> None:
    required_token = os.getenv("APP_AUTH_TOKEN")
    if not required_token:
        return  # auth desabilitada
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Não autorizado")
    token = authorization.split(" ", 1)[1].strip()
    if token != required_token:
        raise HTTPException(status_code=401, detail="Token inválido")


def _ensure_conversation(db, session_id: str) -> int:
    with db.cursor() as cur:
        cur.execute("SELECT id FROM conversations WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        if row:
            return row["id"] if isinstance(row, dict) else row[0]
        cur.execute("INSERT INTO conversations (session_id) VALUES (%s) RETURNING id", (session_id,))
        new_id_row = cur.fetchone()
        return new_id_row["id"] if isinstance(new_id_row, dict) else new_id_row[0]


def _get_conversation_summary(db, conversation_id: int) -> Optional[str]:
    with db.cursor() as cur:
        cur.execute("SELECT summary FROM conversations WHERE id = %s", (conversation_id,))
        row = cur.fetchone()
        if not row:
            return None
        return row["summary"] if isinstance(row, dict) else row[0]


def _insert_message(db, conversation_id: int, role: str, content: str, tokens: Optional[Dict[str, int]] = None) -> None:
    with db.cursor() as cur:
        if tokens:
            cur.execute(
                "INSERT INTO conversation_messages (conversation_id, role, content, tokens_prompt, tokens_completion) VALUES (%s, %s, %s, %s, %s)",
                (conversation_id, role, content, tokens.get("prompt_tokens"), tokens.get("completion_tokens")),
            )
        else:
            cur.execute(
                "INSERT INTO conversation_messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, role, content),
            )


def _get_last_messages(db, conversation_id: int, limit: int) -> List[Dict[str, str]]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT role, content FROM conversation_messages WHERE conversation_id = %s ORDER BY id DESC LIMIT %s",
            (conversation_id, limit),
        )
        rows = cur.fetchall() or []
        items = [
            {"role": (r["role"] if isinstance(r, dict) else r[0]), "content": (r["content"] if isinstance(r, dict) else r[1])}
            for r in rows
        ]
        items.reverse()  # cronológica
        return items


def _get_or_build_admin_snapshot(db) -> Dict[str, Any]:
    with db.cursor() as cur:
        cur.execute("SELECT data FROM admin_snapshots ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            raw = row["data"] if isinstance(row, dict) else row[0]
            try:
                return raw if isinstance(raw, dict) else json.loads(raw)
            except Exception:
                return {}

    # Construir snapshot básico a partir das tabelas do painel
    snapshot: Dict[str, Any] = {}
    try:
        with db.cursor() as cur:
            # Configurações (mapa chave->valor)
            cur.execute("SELECT chave, valor FROM configuracoes")
            cfg_rows = cur.fetchall() or []
            configuracoes = { (r["chave"] if isinstance(r, dict) else r[0]): (r["valor"] if isinstance(r, dict) else r[1]) for r in cfg_rows }
            snapshot["configuracoes"] = configuracoes

            # Serviços ativos (limite 15)
            cur.execute("SELECT nome, valor, categoria FROM servicos_clinica WHERE ativo = 1 LIMIT 15")
            servicos_rows = cur.fetchall() or []
            servicos = []
            for r in servicos_rows:
                nome = r["nome"] if isinstance(r, dict) else r[0]
                valor = r["valor"] if isinstance(r, dict) else r[1]
                categoria = r["categoria"] if isinstance(r, dict) else r[2]
                servicos.append({"nome": nome, "valor": float(valor) if valor is not None else None, "categoria": categoria})
            snapshot["servicos_ativos"] = servicos

            # Profissionais ativos (limite 15)
            cur.execute("SELECT nome, especialidade FROM profissionais WHERE ativo = 1 LIMIT 15")
            prof_rows = cur.fetchall() or []
            profissionais = []
            for r in prof_rows:
                nome = r["nome"] if isinstance(r, dict) else r[0]
                esp = r["especialidade"] if isinstance(r, dict) else r[1]
                profissionais.append({"nome": nome, "especialidade": esp})
            snapshot["profissionais_ativos"] = profissionais

        # Persistir snapshot
        with db.cursor() as cur2:
            cur2.execute("INSERT INTO admin_snapshots (data) VALUES (%s)", (json.dumps(snapshot, ensure_ascii=False),))
    except Exception:
        # Falha silenciosa para não quebrar o chat
        pass

    return snapshot


def _maybe_summarize(db, conversation_id: int, ai: OpenAIService, tokens_estimate: int) -> None:
    threshold = int(os.getenv("CHAT_SUMMARY_TOKENS_THRESHOLD", "3000"))
    if tokens_estimate < threshold:
        return
    # Carregar toda a conversa para sumarizar de forma estável
    with db.cursor() as cur:
        cur.execute("SELECT role, content FROM conversation_messages WHERE conversation_id = %s ORDER BY id ASC", (conversation_id,))
        rows = cur.fetchall() or []
        text = []
        for r in rows:
            role = r["role"] if isinstance(r, dict) else r[0]
            content = r["content"] if isinstance(r, dict) else r[1]
            text.append(f"{role.upper()}: {content}")
        merged = "\n".join(text)
        # Limitar entrada da sumarização para evitar excesso
        if len(merged) > 24000:
            merged = merged[-24000:]
        try:
            summary = ai.summarize(merged, max_words=300)
            with db.cursor() as cur2:
                cur2.execute("UPDATE conversations SET summary = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (summary, conversation_id))
        except Exception:
            pass


def _extract_facts_from_history(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    facts: Dict[str, Any] = {}
    name_patterns = [
        r"\bmeu nome é\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)",
        r"\beu sou\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)",
        r"\bchamo\-?me\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)",
    ]
    age_patterns = [
        r"\btenho\s+(\d{1,3})\s+anos\b",
        r"\bminha idade é\s+(\d{1,3})\b",
    ]

    for m in messages:
        content = m.get("content", "")
        lower = content.lower()
        # Nome
        if "nome" in lower or "sou" in lower or "chamo" in lower:
            for pat in name_patterns:
                mt = re.search(pat, lower)
                if mt:
                    facts["nome_usuario"] = mt.group(1).strip().title()
                    break
        # Idade
        if "anos" in lower or "idade" in lower:
            for pat in age_patterns:
                mt = re.search(pat, lower)
                if mt:
                    try:
                        facts["idade_usuario"] = int(mt.group(1))
                    except Exception:
                        pass
                    break
    return facts


def _maybe_answer_locally(extracted: Dict[str, Any], user_message: str) -> Optional[str]:
    lm = user_message.strip().lower()
    # Idade
    if any(p in lm for p in ["quantos anos eu tenho", "minha idade", "qual a minha idade", "qual é a minha idade", "idade eu tenho"]):
        if "idade_usuario" in extracted and isinstance(extracted["idade_usuario"], int):
            return f"Você tem {extracted['idade_usuario']} anos."
    # Nome
    if any(p in lm for p in ["qual meu nome", "qual é meu nome", "qual o meu nome", "meu nome"]):
        if "nome_usuario" in extracted and isinstance(extracted["nome_usuario"], str):
            return f"Seu nome é {extracted['nome_usuario']}."
    return None


def _sanitize_reply(text: str) -> str:
    """
    Remove/evita vazamentos de dados internos (painel/DB) e mensagens de ausência de cadastros.
    Se detectar termos proibidos, substitui por uma resposta neutra de agendamento.
    """
    low = (text or "").lower()
    banned_markers = [
        "painel", "banco de dados", "banco de dados", "banco", "no sistema",
        "no banco", "cadastrado", "cadastrados", "profissionais ativos",
        "serviços ativos", "servicos ativos", "atualmente não há", "no momento não há",
        "não há serviços", "não há profissionais", "na base", "no bd",
    ]
    if any(m in low for m in banned_markers):
        return (
            "Posso te ajudar com o agendamento. "
            "Você prefere um dia/turno específico? Também posso indicar especialidades conforme sua necessidade."
        )
    return text


@router.post("/messages")
async def messages(payload: ChatIn, db = Depends(get_db), _auth: None = Depends(_require_auth_header)):
    user_message = payload.message.strip()
    if not user_message:
        return JSONResponse(content={"success": False, "message": "Mensagem vazia"})

    # Requer PostgreSQL para armazenar contexto ampliado (conversations, snapshots)
    if not is_postgres_connection(db):
        # Fallback: responde sem contexto avançado
        try:
            ai = OpenAIService()
            base_system = (
                "Você é um assistente de agendamentos de clínica. Seja objetivo, claro e útil. "
                "Responda sempre em português do Brasil."
            )
            msgs = [
                {"role": "system", "content": base_system},
                {"role": "user", "content": user_message},
            ]
            result = ai.chat_completion(msgs)
            return JSONResponse(content={"success": True, "message": result["message"], "tokens": result.get("tokens", {})})
        except Exception:
            reply = f"(mock) Você disse: {user_message}. Em breve este endpoint falará com a IA."
            tokens = {"prompt_tokens": max(1, len(user_message)//4), "completion_tokens": max(1, len(reply)//4)}
            return JSONResponse(content={"success": True, "message": reply, "tokens": tokens})

    # Fluxo PostgreSQL: janela deslizante + sumarização + snapshot
    try:
        ai = OpenAIService()
        conversation_id = _ensure_conversation(db, payload.sessionId)

        # Registrar mensagem do usuário
        _insert_message(db, conversation_id, "user", user_message)

        # Carregar contexto
        window_size = int(os.getenv("CHAT_WINDOW_SIZE", "10"))
        last_msgs = _get_last_messages(db, conversation_id, window_size)
        summary = _get_conversation_summary(db, conversation_id)
        admin_snapshot = _get_or_build_admin_snapshot(db)

        # Montar prompts (system + contexto + histórico + mensagem corrente)
        system_rules = (
            "Você é um assistente de agendamentos de clínica. Siga as regras: "
            "1) Seja objetivo, natural e proativo, guiando o usuário a um agendamento eficiente. "
            "2) Faça perguntas para remover ambiguidade (dia, turno, profissional, tipo de serviço). "
            "3) Use o histórico fornecido (resumo + últimas mensagens) apenas como CONTEXTO. "
            "4) É ESTRITAMENTE PROIBIDO mencionar ou insinuar informações internas, banco de dados, painel administrativo, cadastros ou ausência/presença de itens. "
            "5) Nunca diga que não há serviços/profissionais. Em vez disso, conduza o usuário perguntando preferências e prossiga com alternativas. "
            "6) As informações pessoais fornecidas pelo usuário (ex.: nome, idade) podem e DEVEM ser usadas de forma contextual e respeitosa. "
            "7) Se houver fatos conhecidos (ex.: idade_usuario=21) e o usuário perguntar sobre isso, responda diretamente e retome o fluxo de agendamento. "
            "8) Responda em português do Brasil."
        )

        context_parts: List[str] = []
        if summary:
            context_parts.append(f"Resumo da conversa até aqui:\n{summary}")
        if admin_snapshot:
            # Limitar tamanho do snapshot para o prompt
            snap_str = json.dumps(admin_snapshot, ensure_ascii=False)
            if len(snap_str) > 6000:
                snap_str = snap_str[:6000]
            context_parts.append(f"Dados do painel (contexto):\n{snap_str}")

        # Extrair fatos simples do histórico recente
        extracted = _extract_facts_from_history(last_msgs)
        if extracted:
            bullets = []
            if "nome_usuario" in extracted:
                bullets.append(f"- Nome do usuário: {extracted['nome_usuario']}")
            if "idade_usuario" in extracted:
                bullets.append(f"- Idade do usuário: {extracted['idade_usuario']}")
            if bullets:
                context_parts.append("Fatos conhecidos sobre o usuário:\n" + "\n".join(bullets))

        context_block = "\n\n".join(context_parts) if context_parts else ""

        messages_for_model: List[Dict[str, str]] = []
        messages_for_model.append({"role": "system", "content": system_rules})
        if context_block:
            messages_for_model.append({"role": "system", "content": context_block})
        messages_for_model.extend(last_msgs)

        # Resposta local determinística para perguntas diretas
        local_reply = _maybe_answer_locally(extracted, user_message)
        if local_reply:
            # Registrar resposta do assistente e retornar
            _insert_message(db, conversation_id, "assistant", local_reply, {"prompt_tokens": 0, "completion_tokens": 0})
            try:
                with db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO conversas (session_id, mensagem_usuario, resposta_agente, tokens_prompt, tokens_completion) VALUES (%s, %s, %s, %s, %s)",
                        (payload.sessionId, user_message, local_reply, 0, 0),
                    )
            except Exception:
                pass
            return JSONResponse(content={
                "success": True,
                "message": local_reply,
                "tokens": {"prompt_tokens": 0, "completion_tokens": 0},
            })

        # Chamar IA (com fallback se não houver configuração)
        try:
            result = ai.chat_completion(messages_for_model)
            assistant_reply = result["message"]
            tokens = result.get("tokens", {"prompt_tokens": 0, "completion_tokens": 0})
        except Exception:
            # Fallback: construir resposta simples usando fatos conhecidos
            if extracted.get("nome_usuario") or extracted.get("idade_usuario"):
                parts = []
                if extracted.get("nome_usuario"):
                    parts.append(f"{extracted['nome_usuario']}")
                if extracted.get("idade_usuario"):
                    parts.append(f"{extracted['idade_usuario']} anos")
                who = ", ".join(parts)
                assistant_reply = f"Entendi: {who}. Para seguirmos com o agendamento, você prefere manhã, tarde ou noite?"
            else:
                assistant_reply = "Para seguirmos com o agendamento, você prefere manhã, tarde ou noite?"
            tokens = {"prompt_tokens": 0, "completion_tokens": 0}

        # Sanitização de saída para evitar vazamentos de dados internos
        assistant_reply = _sanitize_reply(assistant_reply)

        # Registrar resposta do assistente
        _insert_message(db, conversation_id, "assistant", assistant_reply, tokens)

        # Compatibilidade com tabela legado 'conversas' (para feedback/rewrite já existentes)
        try:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversas (session_id, mensagem_usuario, resposta_agente, tokens_prompt, tokens_completion) VALUES (%s, %s, %s, %s, %s)",
                    (payload.sessionId, user_message, assistant_reply, tokens.get("prompt_tokens"), tokens.get("completion_tokens")),
                )
        except Exception:
            # Ignorar erro de compatibilidade
            pass

        # Decidir sumarização (estratégia híbrida)
        approx_tokens = int((sum(len(m["content"]) for m in messages_for_model) + len(assistant_reply)) / 4)
        _maybe_summarize(db, conversation_id, ai, approx_tokens)

        return JSONResponse(content={
            "success": True,
            "message": assistant_reply,
            "tokens": tokens,
        })
    except HTTPException:
        raise
    except Exception:
        # Fallback final: não quebrar UX
        reply = f"(mock) Você disse: {user_message}. Em breve este endpoint falará com a IA."
        tokens = {"prompt_tokens": max(1, len(user_message)//4), "completion_tokens": max(1, len(reply)//4)}
        return JSONResponse(content={"success": True, "message": reply, "tokens": tokens})


