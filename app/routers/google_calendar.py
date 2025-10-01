"""
Router para integração com Google Calendar
Gerencia autenticação OAuth, sincronização e configurações
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional, List, Dict, Any
import logging
import json
from datetime import datetime, timedelta
import pytz

from ..core.db import get_db
from .auth import verify_admin_user, get_current_user
from ..services.google_calendar_service import google_calendar_service

router = APIRouter(prefix="/google-calendar", tags=["google-calendar"])

@router.get("/oauth/url")
async def get_oauth_url(
    profissional_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Gera URL para autorização OAuth2 do Google Calendar
    """
    try:
        # Verificar se o profissional existe
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("SELECT nome FROM profissionais WHERE id = %s AND ativo = 1", (profissional_id,))
                profissional = cur.fetchone()
                
                if not profissional:
                    raise HTTPException(status_code=404, detail="Profissional não encontrado")
                
                # Gerar URL OAuth
                redirect_uri = "http://127.0.0.1:8000/api/google-calendar/callback"
                state = f"profissional_id:{profissional_id}"
                
                oauth_url = google_calendar_service.get_oauth_url(redirect_uri, state)
                
                return JSONResponse(content={
                    "success": True,
                    "oauth_url": oauth_url,
                    "profissional": profissional[0]
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro ao gerar URL OAuth: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao gerar URL de autorização"},
            status_code=500
        )

@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None)
):
    """
    Callback para processar autorização OAuth2
    """
    try:
        if error:
            return RedirectResponse(
                url=f"/panel.html#google-calendar?error={error}",
                status_code=302
            )
        
        # Extrair profissional_id do state
        if not state.startswith("profissional_id:"):
            raise HTTPException(status_code=400, detail="State inválido")
        
        profissional_id = int(state.split(":", 1)[1])
        
        # Trocar código por token
        redirect_uri = "http://127.0.0.1:8000/api/google-calendar/callback"
        token_data = google_calendar_service.exchange_code_for_token(code, redirect_uri)
        
        # Obter informações dos calendários
        calendars = google_calendar_service.get_calendar_list()
        primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
        
        if not primary_calendar:
            raise HTTPException(status_code=400, detail="Nenhum calendário primário encontrado")
        
        # Salvar credenciais no banco
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Verificar se já existe credencial para este profissional
                cur.execute("""
                    SELECT id FROM profissional_google_credentials 
                    WHERE profissional_id = %s
                """, (profissional_id,))
                
                existing = cur.fetchone()
                
                if existing:
                    # Atualizar credenciais existentes
                    cur.execute("""
                        UPDATE profissional_google_credentials 
                        SET access_token = %s, refresh_token = %s, token_uri = %s,
                            client_id = %s, client_secret = %s, expires_at = %s,
                            calendar_id = %s, calendar_name = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE profissional_id = %s
                    """, (
                        token_data['access_token'],
                        token_data.get('refresh_token'),
                        token_data.get('token_uri'),
                        token_data.get('client_id'),
                        token_data.get('client_secret'),
                        token_data.get('expires_at'),
                        primary_calendar['id'],
                        primary_calendar['summary'],
                        profissional_id
                    ))
                else:
                    # Inserir novas credenciais
                    cur.execute("""
                        INSERT INTO profissional_google_credentials (
                            profissional_id, access_token, refresh_token, token_uri,
                            client_id, client_secret, expires_at, scopes,
                            calendar_id, calendar_name
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        profissional_id,
                        token_data['access_token'],
                        token_data.get('refresh_token'),
                        token_data.get('token_uri'),
                        token_data.get('client_id'),
                        token_data.get('client_secret'),
                        token_data.get('expires_at'),
                        json.dumps(google_calendar_service.SCOPES),
                        primary_calendar['id'],
                        primary_calendar['summary']
                    ))
                
                # Ativar integração para o profissional
                cur.execute("""
                    UPDATE profissionais 
                    SET google_calendar_enabled = 1, google_calendar_sync_last = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (profissional_id,))
                
                db.commit()
                
        finally:
            try:
                db.close()
            except Exception:
                pass
        
        # Redirecionar para painel com sucesso
        return RedirectResponse(
            url="/panel.html#google-calendar?success=1",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro no callback OAuth: {str(e)}")
        return RedirectResponse(
            url=f"/panel.html#google-calendar?error=callback_error",
            status_code=302
        )

@router.get("/status/{profissional_id}")
async def get_integration_status(
    profissional_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Verifica status da integração Google Calendar para um profissional
    """
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Buscar dados do profissional e integração
                cur.execute("""
                    SELECT 
                        p.nome, p.google_calendar_enabled, p.google_calendar_sync_last,
                        gc.calendar_id, gc.calendar_name, gc.expires_at, gc.ativo
                    FROM profissionais p
                    LEFT JOIN profissional_google_credentials gc ON p.id = gc.profissional_id
                    WHERE p.id = %s AND p.ativo = 1
                """, (profissional_id,))
                
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Profissional não encontrado")
                
                nome, enabled, last_sync, calendar_id, calendar_name, expires_at, cred_ativo = result
                
                status = {
                    "profissional_id": profissional_id,
                    "profissional_nome": nome,
                    "google_calendar_enabled": bool(enabled),
                    "has_credentials": bool(calendar_id and cred_ativo),
                    "calendar_id": calendar_id,
                    "calendar_name": calendar_name,
                    "last_sync": last_sync.isoformat() if last_sync else None,
                    "credentials_expired": False
                }
                
                # Verificar se credenciais expiraram
                if expires_at:
                    expires_dt = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
                    status["credentials_expired"] = expires_dt < datetime.now(pytz.UTC)
                
                return JSONResponse(content={
                    "success": True,
                    "status": status
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro ao verificar status: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao verificar status"},
            status_code=500
        )

@router.post("/sync/{profissional_id}")
async def sync_calendar(
    profissional_id: int,
    current_user: dict = Depends(verify_admin_user)
):
    """
    Força sincronização manual do calendário de um profissional
    """
    try:
        # Implementar lógica de sincronização
        # Esta função irá sincronizar agendamentos existentes com o Google Calendar
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Buscar credenciais do profissional
                cur.execute("""
                    SELECT access_token, refresh_token, token_uri, client_id, 
                           client_secret, calendar_id
                    FROM profissional_google_credentials
                    WHERE profissional_id = %s AND ativo = 1
                """, (profissional_id,))
                
                credentials = cur.fetchone()
                
                if not credentials:
                    raise HTTPException(status_code=404, detail="Credenciais não encontradas")
                
                # Carregar credenciais no serviço
                token_data = {
                    'access_token': credentials[0],
                    'refresh_token': credentials[1],
                    'token_uri': credentials[2],
                    'client_id': credentials[3],
                    'client_secret': credentials[4]
                }
                
                google_calendar_service.load_credentials_from_token(token_data)
                calendar_id = credentials[5]
                
                # Buscar agendamentos pendentes de sincronização
                cur.execute("""
                    SELECT id, cliente_id, data_inicio, data_fim, observacoes,
                           google_event_id, sync_status
                    FROM agendamentos
                    WHERE profissional_id = %s 
                    AND status IN (0, 1, 2)  -- Agendado, Confirmado, Realizado
                    AND (sync_status = 'pending' OR sync_status IS NULL)
                    ORDER BY data_inicio
                """, (profissional_id,))
                
                agendamentos = cur.fetchall()
                sync_results = []
                
                for agendamento in agendamentos:
                    try:
                        agend_id, cliente_id, data_inicio, data_fim, observacoes, event_id, sync_status = agendamento
                        
                        # Buscar dados do cliente
                        cur.execute("SELECT nome, email FROM clientes WHERE id = %s", (cliente_id,))
                        cliente = cur.fetchone()
                        
                        if not cliente:
                            continue
                        
                        cliente_nome, cliente_email = cliente
                        
                        # Criar evento no Google Calendar
                        title = f"Consulta com {cliente_nome}"
                        description = f"Agendamento ID: {agend_id}\n"
                        if observacoes:
                            description += f"Observações: {observacoes}"
                        
                        attendees = [cliente_email] if cliente_email else []
                        
                        event_result = google_calendar_service.create_event(
                            calendar_id=calendar_id,
                            title=title,
                            start_datetime=data_inicio,
                            end_datetime=data_fim,
                            description=description,
                            attendees=attendees
                        )
                        
                        # Atualizar agendamento com dados do evento
                        cur.execute("""
                            UPDATE agendamentos 
                            SET google_event_id = %s, google_calendar_id = %s,
                                google_event_link = %s, sync_status = 'synced'
                            WHERE id = %s
                        """, (
                            event_result['event_id'],
                            calendar_id,
                            event_result.get('html_link'),
                            agend_id
                        ))
                        
                        # Log da sincronização
                        cur.execute("""
                            INSERT INTO google_calendar_sync_log (
                                agendamento_id, profissional_id, action, 
                                google_event_id, status
                            ) VALUES (%s, %s, 'create', %s, 'success')
                        """, (agend_id, profissional_id, event_result['event_id']))
                        
                        sync_results.append({
                            "agendamento_id": agend_id,
                            "status": "success",
                            "event_id": event_result['event_id']
                        })
                        
                    except Exception as sync_error:
                        logging.error(f"Erro ao sincronizar agendamento {agend_id}: {str(sync_error)}")
                        
                        # Log do erro
                        cur.execute("""
                            INSERT INTO google_calendar_sync_log (
                                agendamento_id, profissional_id, action, 
                                status, error_message
                            ) VALUES (%s, %s, 'create', 'error', %s)
                        """, (agend_id, profissional_id, str(sync_error)))
                        
                        sync_results.append({
                            "agendamento_id": agend_id,
                            "status": "error",
                            "error": str(sync_error)
                        })
                
                # Atualizar último sync
                cur.execute("""
                    UPDATE profissionais 
                    SET google_calendar_sync_last = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (profissional_id,))
                
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Sincronização concluída. {len([r for r in sync_results if r['status'] == 'success'])} agendamentos sincronizados.",
                    "results": sync_results
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro na sincronização: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro na sincronização"},
            status_code=500
        )

@router.delete("/disconnect/{profissional_id}")
async def disconnect_calendar(
    profissional_id: int,
    current_user: dict = Depends(verify_admin_user)
):
    """
    Desconecta integração Google Calendar de um profissional
    """
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                # Desativar credenciais
                cur.execute("""
                    UPDATE profissional_google_credentials 
                    SET ativo = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE profissional_id = %s
                """, (profissional_id,))
                
                # Desabilitar integração
                cur.execute("""
                    UPDATE profissionais 
                    SET google_calendar_enabled = 0
                    WHERE id = %s
                """, (profissional_id,))
                
                db.commit()
                
                return JSONResponse(content={
                    "success": True,
                    "message": "Integração desconectada com sucesso"
                })
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao desconectar: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao desconectar integração"},
            status_code=500
        )

@router.get("/professionals")
async def list_professionals_calendar_status(
    current_user: dict = Depends(verify_admin_user)
):
    """
    Lista todos os profissionais e seus status de integração
    """
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            with db.cursor() as cur:
                cur.execute("""
                    SELECT 
                        p.id, p.nome, p.especialidade, p.google_calendar_enabled,
                        p.google_calendar_sync_last,
                        gc.calendar_name, gc.expires_at, gc.ativo as cred_ativo
                    FROM profissionais p
                    LEFT JOIN profissional_google_credentials gc ON p.id = gc.profissional_id
                    WHERE p.ativo = 1
                    ORDER BY p.nome
                """)
                
                profissionais = []
                for row in cur.fetchall():
                    pid, nome, especialidade, enabled, last_sync, cal_name, expires_at, cred_ativo = row
                    
                    credentials_expired = False
                    if expires_at:
                        expires_dt = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
                        credentials_expired = expires_dt < datetime.now(pytz.UTC)
                    
                    profissionais.append({
                        "id": pid,
                        "nome": nome,
                        "especialidade": especialidade,
                        "google_calendar_enabled": bool(enabled),
                        "has_credentials": bool(cal_name and cred_ativo),
                        "calendar_name": cal_name,
                        "last_sync": last_sync.isoformat() if last_sync else None,
                        "credentials_expired": credentials_expired
                    })
                
                return JSONResponse(content=jsonable_encoder({
                    "success": True,
                    "profissionais": profissionais
                }))
                
        finally:
            try:
                db.close()
            except Exception:
                pass
                
    except Exception as e:
        logging.error(f"Erro ao listar profissionais: {str(e)}")
        return JSONResponse(
            content={"success": False, "message": "Erro ao carregar dados"},
            status_code=500
        )
