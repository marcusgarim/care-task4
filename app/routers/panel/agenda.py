"""
API de Agenda com Integração do Google Calendar
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import date as date_type, datetime, time, timedelta
import pytz

router = APIRouter(prefix="/panel", tags=["panel-agenda"])

@router.get("/agenda/disponibilidade")
async def consultar_disponibilidade_real(
    data: str = Query(..., description="Data no formato YYYY-MM-DD")
):
    """Consulta disponibilidade do Google Calendar"""
    
    # Validar formato da data
    try:
        date_type.fromisoformat(data)
    except ValueError:
        return JSONResponse(
            content={"success": False, "message": "Formato de data inválido. Use YYYY-MM-DD"},
            status_code=400
        )
    
    try:
        # Carregar token
        creds = Credentials.from_authorized_user_file('/Users/marcusgarim/Documents/careintelligence/care-task4/scripts/token_suporte.json')
        service = build('calendar', 'v3', credentials=creds)
        
        target_date = date_type.fromisoformat(data)
        
        # Buscar eventos do Google Calendar
        tz = pytz.timezone('America/Sao_Paulo')
        start_dt = tz.localize(datetime.combine(target_date, time(0, 0)))
        end_dt = tz.localize(datetime.combine(target_date, time(23, 59)))
        
        calendar_id = 'c_e61ace7a78718aa82e52a67ffeaa756cf39650eb27641ff29968048d97a9a4db@group.calendar.google.com'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Calcular slots baseado nos eventos
        available_slots = []
        occupied_slots = []
        
        # Horário de trabalho: 9h às 18h
        work_hours = list(range(9, 18))
        
        for hour in work_hours:
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            
            # Verificar se há evento neste horário
            is_occupied = False
            event_title = ""
            
            for event in events:
                event_start = event.get('start', {}).get('dateTime', '')
                event_end = event.get('end', {}).get('dateTime', '')
                
                if event_start and event_end:
                    try:
                        # Converter para datetime e verificar sobreposição
                        event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00')).replace(tzinfo=None)
                        event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00')).replace(tzinfo=None)
                        
                        slot_start_dt = datetime.combine(target_date, datetime.strptime(start_time, '%H:%M').time())
                        slot_end_dt = datetime.combine(target_date, datetime.strptime(end_time, '%H:%M').time())
                        
                        # Verificar sobreposição
                        if slot_start_dt < event_end_dt and slot_end_dt > event_start_dt:
                            is_occupied = True
                            event_title = event.get('summary', 'Evento')
                            break
                    except:
                        continue
            
            if is_occupied:
                occupied_slots.append({
                    "start": start_time,
                    "end": end_time,
                    "datetime": f"{data}T{start_time}:00",
                    "title": event_title
                })
            else:
                available_slots.append({
                    "start": start_time,
                    "end": end_time,
                    "datetime": f"{data}T{start_time}:00"
                })
        
        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "message": "Disponibilidade consultada com sucesso",
            "agenda": "Smart Test",
            "timezone": "America/Sao_Paulo",
            "data": data,
            "available_slots": available_slots,
            "occupied_slots": occupied_slots,
            "total_available": len(available_slots),
            "total_occupied": len(occupied_slots),
            "consulta_realizada_em": datetime.now().isoformat()
        }))
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Erro ao consultar disponibilidade: {str(e)}"},
            status_code=500
        )

@router.get("/agenda/proximos-horarios")
async def proximos_horarios_disponiveis(
    limite: int = Query(10, description="Número máximo de horários a retornar"),
    dias_futuro: int = Query(30, description="Quantos dias no futuro buscar")
):
    """Lista próximos horários disponíveis na agenda Smart Test"""
    try:
        # Carregar token
        creds = Credentials.from_authorized_user_file('/Users/marcusgarim/Documents/careintelligence/care-task4/scripts/token_suporte.json')
        service = build('calendar', 'v3', credentials=creds)
        
        # Buscar próximos horários disponíveis
        tz = pytz.timezone('America/Sao_Paulo')
        hoje = date_type.today()
        fim_periodo = hoje + timedelta(days=dias_futuro)
        
        proximos_horarios = []
        
        # Buscar eventos para os próximos dias
        for i in range(dias_futuro):
            data_atual = hoje + timedelta(days=i)
            
            start_dt = tz.localize(datetime.combine(data_atual, time(0, 0)))
            end_dt = tz.localize(datetime.combine(data_atual, time(23, 59)))
            
            calendar_id = 'c_e61ace7a78718aa82e52a67ffeaa756cf39650eb27641ff29968048d97a9a4db@group.calendar.google.com'
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Horário de trabalho: 9h às 18h
            work_hours = list(range(9, 18))
            
            for hour in work_hours:
                start_time = f"{hour:02d}:00"
                end_time = f"{hour+1:02d}:00"
                
                # Verificar se há evento neste horário
                is_occupied = False
                
                for event in events:
                    event_start = event.get('start', {}).get('dateTime', '')
                    event_end = event.get('end', {}).get('dateTime', '')
                    
                    if event_start and event_end:
                        try:
                            event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00')).replace(tzinfo=None)
                            event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00')).replace(tzinfo=None)
                            
                            slot_start_dt = datetime.combine(data_atual, datetime.strptime(start_time, '%H:%M').time())
                            slot_end_dt = datetime.combine(data_atual, datetime.strptime(end_time, '%H:%M').time())
                            
                            if slot_start_dt < event_end_dt and slot_end_dt > event_start_dt:
                                is_occupied = True
                                break
                        except:
                            continue
                
                if not is_occupied:
                    proximos_horarios.append({
                        "data": data_atual.strftime("%Y-%m-%d"),
                        "data_formatada": data_atual.strftime("%d/%m/%Y"),
                        "dia_semana": data_atual.strftime("%A"),
                        "horario_inicio": start_time,
                        "horario_fim": end_time,
                        "datetime_completo": f"{data_atual.strftime('%Y-%m-%d')}T{start_time}:00"
                    })
                    
                    if len(proximos_horarios) >= limite:
                        break
            
            if len(proximos_horarios) >= limite:
                break
        
        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "proximos_horarios": proximos_horarios[:limite],
            "total_encontrados": len(proximos_horarios[:limite]),
            "periodo_consultado": {
                "inicio": hoje.strftime("%Y-%m-%d"),
                "fim": fim_periodo.strftime("%Y-%m-%d"),
                "dias": dias_futuro
            }
        }))
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Erro ao buscar próximos horários: {str(e)}"},
            status_code=500
        )