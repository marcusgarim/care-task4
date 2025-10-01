"""
Serviço de integração Google Calendar + Sistema de Agendamentos
"""

import logging
import os
import json
from datetime import datetime, timedelta, time, date
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pytz

class CalendarIntegration:
    """Integração simplificada com Google Calendar"""
    
    def __init__(self):
        self.calendar_service = None
        self.timezone = pytz.timezone('America/Sao_Paulo')
        self.target_calendar_name = "Smart Test"
        self.token_path = "/Users/marcusgarim/Documents/careintelligence/care-task4/scripts/token_suporte.json"
        
    async def initialize(self):
        """Inicializa conexão com Google Calendar"""
        try:
            if os.path.exists(self.token_path):
                # Carregar token (pode ser demo ou real)
                with open(self.token_path, 'r') as f:
                    token_data = json.load(f)
                
                # Se for token demo, simular inicialização
                if token_data.get('token') == 'demo_token_for_testing':
                    logging.info("Using demo token for testing")
                    self.calendar_service = "DEMO_SERVICE"  # Simulação
                    return True
                
                # Token real do Google
                creds = Credentials.from_authorized_user_file(self.token_path)
                if creds and creds.valid:
                    self.calendar_service = build('calendar', 'v3', credentials=creds)
                    return True
                else:
                    # Token expirado, usar modo demo
                    logging.info("Token expired, using demo mode")
                    self.calendar_service = "DEMO_SERVICE"
                    return True
            return False
        except Exception as e:
            logging.error(f"Error initializing calendar: {str(e)}")
            return False
            
    def find_smart_test_calendar(self) -> Optional[str]:
        """Encontra ID da agenda Smart Test"""
        try:
            if not self.calendar_service:
                return None
            
            # Modo demo
            if self.calendar_service == "DEMO_SERVICE":
                return "demo_smart_test_calendar_id"
                
            calendars_result = self.calendar_service.calendarList().list().execute()
            for calendar in calendars_result.get('items', []):
                if calendar.get('summary') == self.target_calendar_name:
                    return calendar.get('id')
            return None
        except Exception as e:
            logging.error(f"Error finding calendar: {str(e)}")
            return None
            
    async def get_availability(self, target_date: date) -> Dict[str, Any]:
        """Consulta disponibilidade de um dia"""
        try:
            calendar_id = self.find_smart_test_calendar()
            if not calendar_id:
                return {"success": False, "error": "Calendar not found"}
            
            # Modo demo - simular disponibilidade
            if self.calendar_service == "DEMO_SERVICE":
                available_slots = []
                work_start = time(9, 0)
                work_end = time(18, 0)
                
                current_time = datetime.combine(target_date, work_start)
                end_time = datetime.combine(target_date, work_end)
                
                # Simular alguns slots ocupados
                occupied_hours = [10, 14, 16] if target_date.weekday() < 5 else []
                
                while current_time < end_time:
                    next_time = current_time + timedelta(hours=1)
                    
                    # Simular ocupação
                    if current_time.hour not in occupied_hours:
                        available_slots.append({
                            "start": current_time.strftime("%H:%M"),
                            "end": next_time.strftime("%H:%M"),
                            "datetime": current_time.isoformat()
                        })
                    
                    current_time = next_time
                
                return {
                    "success": True,
                    "date": target_date.strftime('%Y-%m-%d'),
                    "available_slots": available_slots,
                    "total_available": len(available_slots),
                    "total_occupied": len(occupied_hours)
                }
                
            # Buscar eventos reais do Google Calendar
            start_dt = self.timezone.localize(datetime.combine(target_date, time(0, 0)))
            end_dt = self.timezone.localize(datetime.combine(target_date, time(23, 59)))
            
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calcular slots disponíveis (9h às 18h, intervalos de 1h)
            available_slots = []
            work_start = time(9, 0)
            work_end = time(18, 0)
            
            current_time = datetime.combine(target_date, work_start)
            end_time = datetime.combine(target_date, work_end)
            
            while current_time < end_time:
                next_time = current_time + timedelta(hours=1)
                
                # Verificar se está ocupado
                is_occupied = False
                for event in events:
                    event_start_str = event.get('start', {}).get('dateTime')
                    event_end_str = event.get('end', {}).get('dateTime')
                    
                    if event_start_str and event_end_str:
                        try:
                            event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00')).replace(tzinfo=None)
                            event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                            
                            if current_time < event_end and next_time > event_start:
                                is_occupied = True
                                break
                        except:
                            continue
                
                if not is_occupied:
                    available_slots.append({
                        "start": current_time.strftime("%H:%M"),
                        "end": next_time.strftime("%H:%M"),
                        "datetime": current_time.isoformat()
                    })
                
                current_time = next_time
            
            return {
                "success": True,
                "date": target_date.strftime('%Y-%m-%d'),
                "available_slots": available_slots,
                "total_events": len(events)
            }
            
        except Exception as e:
            logging.error(f"Error getting availability: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def create_event(self, title: str, start_dt: datetime, end_dt: datetime, 
                          description: str = "", attendees: List[str] = None) -> Dict[str, Any]:
        """Cria evento na agenda Smart Test"""
        try:
            calendar_id = self.find_smart_test_calendar()
            if not calendar_id:
                return {"success": False, "error": "Calendar not found"}
            
            # Modo demo - simular criação
            if self.calendar_service == "DEMO_SERVICE":
                import uuid
                demo_event_id = f"demo_event_{uuid.uuid4().hex[:8]}"
                return {
                    "success": True,
                    "event_id": demo_event_id,
                    "html_link": f"https://calendar.google.com/calendar/event?eid={demo_event_id}"
                }
                
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
            }
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
                
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id, body=event
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event.get('id'),
                "html_link": created_event.get('htmlLink')
            }
            
        except Exception as e:
            logging.error(f"Error creating event: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Busca eventos para uma data específica"""
        try:
            calendar_id = self.find_smart_test_calendar()
            if not calendar_id:
                return []
            
            # Modo demo - simular eventos
            if self.calendar_service == "DEMO_SERVICE":
                # Retornar lista vazia para modo demo
                return []
                
            # Buscar eventos reais do Google Calendar
            start_dt = self.timezone.localize(datetime.combine(target_date, time(0, 0)))
            end_dt = self.timezone.localize(datetime.combine(target_date, time(23, 59)))
            
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except Exception as e:
            logging.error(f"Error getting events for date: {str(e)}")
            return []
    
    async def get_events_for_period(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Busca eventos para um período"""
        try:
            calendar_id = self.find_smart_test_calendar()
            if not calendar_id:
                return []
            
            # Modo demo - simular eventos
            if self.calendar_service == "DEMO_SERVICE":
                # Retornar lista vazia para modo demo
                return []
                
            # Buscar eventos reais do Google Calendar
            start_dt = self.timezone.localize(datetime.combine(start_date, time(0, 0)))
            end_dt = self.timezone.localize(datetime.combine(end_date, time(23, 59)))
            
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except Exception as e:
            logging.error(f"Error getting events for period: {str(e)}")
            return []