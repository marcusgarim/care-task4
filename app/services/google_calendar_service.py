"""
Serviço de integração com Google Calendar API
Gerencia eventos, disponibilidade e sincronização de agendamentos
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

class GoogleCalendarService:
    """Service para integração com Google Calendar API"""
    
    # Escopo necessário para leitura e escrita de calendários
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
    def get_oauth_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Gera URL para autorização OAuth2 do Google Calendar
        
        Args:
            redirect_uri: URL de callback após autorização
            state: Estado opcional para validação
            
        Returns:
            URL de autorização do Google
        """
        try:
            # Configuração OAuth2
            flow = Flow.from_client_secrets_file(
                'credentials/google_calendar_credentials.json',
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            
            if state:
                flow.state = state
                
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            return auth_url
            
        except Exception as e:
            logging.error(f"Erro ao gerar URL OAuth: {str(e)}")
            raise Exception(f"Erro na configuração OAuth: {str(e)}")
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Troca código de autorização por token de acesso
        
        Args:
            code: Código de autorização retornado pelo Google
            redirect_uri: URL de callback utilizada
            
        Returns:
            Dicionário com informações do token
        """
        try:
            flow = Flow.from_client_secrets_file(
                'credentials/google_calendar_credentials.json',
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Salvar credenciais para uso posterior
            self.credentials = credentials
            self._build_service()
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
        except Exception as e:
            logging.error(f"Erro ao trocar código por token: {str(e)}")
            raise Exception(f"Erro na autenticação: {str(e)}")
    
    def load_credentials_from_token(self, token_data: Dict[str, Any]) -> bool:
        """
        Carrega credenciais a partir de dados de token salvos
        
        Args:
            token_data: Dicionário com dados do token
            
        Returns:
            True se credenciais carregadas com sucesso
        """
        try:
            self.credentials = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=self.SCOPES
            )
            
            # Verificar se o token precisa ser renovado
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                
            self._build_service()
            return True
            
        except Exception as e:
            logging.error(f"Erro ao carregar credenciais: {str(e)}")
            return False
    
    def _build_service(self):
        """Constrói o serviço do Google Calendar"""
        try:
            self.service = build('calendar', 'v3', credentials=self.credentials)
        except Exception as e:
            logging.error(f"Erro ao construir serviço Calendar: {str(e)}")
            raise Exception(f"Erro na inicialização do serviço: {str(e)}")
    
    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de calendários do usuário
        
        Returns:
            Lista de calendários disponíveis
        """
        try:
            if not self.service:
                raise Exception("Serviço não inicializado. Faça autenticação primeiro.")
                
            calendar_list = self.service.calendarList().list().execute()
            
            calendars = []
            for calendar_item in calendar_list.get('items', []):
                calendars.append({
                    'id': calendar_item['id'],
                    'summary': calendar_item.get('summary', 'Sem nome'),
                    'description': calendar_item.get('description', ''),
                    'primary': calendar_item.get('primary', False),
                    'access_role': calendar_item.get('accessRole', 'reader')
                })
                
            return calendars
            
        except HttpError as e:
            logging.error(f"Erro HTTP ao buscar calendários: {str(e)}")
            raise Exception(f"Erro ao acessar calendários: {str(e)}")
        except Exception as e:
            logging.error(f"Erro ao listar calendários: {str(e)}")
            raise Exception(f"Erro inesperado: {str(e)}")
    
    def check_availability(self, calendar_id: str, start_datetime: datetime, 
                          end_datetime: datetime, interval_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Verifica disponibilidade em um calendário específico
        
        Args:
            calendar_id: ID do calendário para verificar
            start_datetime: Data/hora de início da verificação
            end_datetime: Data/hora de fim da verificação
            interval_minutes: Intervalo em minutos para slots
            
        Returns:
            Lista de slots disponíveis
        """
        try:
            if not self.service:
                raise Exception("Serviço não inicializado. Faça autenticação primeiro.")
            
            # Converter para UTC para API
            start_utc = start_datetime.astimezone(pytz.UTC)
            end_utc = end_datetime.astimezone(pytz.UTC)
            
            # Buscar eventos existentes
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_utc.isoformat(),
                timeMax=end_utc.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calcular slots disponíveis
            available_slots = []
            current_time = start_datetime
            interval = timedelta(minutes=interval_minutes)
            
            while current_time + interval <= end_datetime:
                slot_end = current_time + interval
                
                # Verificar se há conflito com eventos existentes
                has_conflict = False
                for event in events:
                    event_start_str = event['start'].get('dateTime', event['start'].get('date'))
                    event_end_str = event['end'].get('dateTime', event['end'].get('date'))
                    
                    if 'T' in event_start_str:  # Evento com hora específica
                        event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                        event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                        
                        # Converter para timezone local
                        event_start = event_start.astimezone(self.timezone)
                        event_end = event_end.astimezone(self.timezone)
                        
                        # Verificar sobreposição
                        if (current_time < event_end and slot_end > event_start):
                            has_conflict = True
                            break
                
                if not has_conflict:
                    available_slots.append({
                        'start': current_time.isoformat(),
                        'end': slot_end.isoformat(),
                        'available': True
                    })
                
                current_time += interval
            
            return available_slots
            
        except HttpError as e:
            logging.error(f"Erro HTTP ao verificar disponibilidade: {str(e)}")
            raise Exception(f"Erro ao verificar disponibilidade: {str(e)}")
        except Exception as e:
            logging.error(f"Erro ao verificar disponibilidade: {str(e)}")
            raise Exception(f"Erro inesperado: {str(e)}")
    
    def create_event(self, calendar_id: str, title: str, start_datetime: datetime,
                    end_datetime: datetime, description: str = "", 
                    attendees: List[str] = None) -> Dict[str, Any]:
        """
        Cria um evento no calendário
        
        Args:
            calendar_id: ID do calendário
            title: Título do evento
            start_datetime: Data/hora de início
            end_datetime: Data/hora de fim
            description: Descrição do evento
            attendees: Lista de emails dos participantes
            
        Returns:
            Dados do evento criado
        """
        try:
            if not self.service:
                raise Exception("Serviço não inicializado. Faça autenticação primeiro.")
            
            # Preparar dados do evento
            event_data = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                }
            }
            
            # Adicionar participantes se fornecidos
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
                event_data['sendUpdates'] = 'all'
            
            # Criar evento
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            return {
                'event_id': event['id'],
                'html_link': event.get('htmlLink'),
                'status': event.get('status'),
                'created': event.get('created'),
                'updated': event.get('updated')
            }
            
        except HttpError as e:
            logging.error(f"Erro HTTP ao criar evento: {str(e)}")
            raise Exception(f"Erro ao criar evento: {str(e)}")
        except Exception as e:
            logging.error(f"Erro ao criar evento: {str(e)}")
            raise Exception(f"Erro inesperado: {str(e)}")
    
    def update_event(self, calendar_id: str, event_id: str, title: str = None,
                    start_datetime: datetime = None, end_datetime: datetime = None,
                    description: str = None) -> Dict[str, Any]:
        """
        Atualiza um evento existente
        
        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            title: Novo título (opcional)
            start_datetime: Nova data/hora de início (opcional)
            end_datetime: Nova data/hora de fim (opcional)
            description: Nova descrição (opcional)
            
        Returns:
            Dados do evento atualizado
        """
        try:
            if not self.service:
                raise Exception("Serviço não inicializado. Faça autenticação primeiro.")
            
            # Buscar evento atual
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Atualizar campos fornecidos
            if title is not None:
                event['summary'] = title
            if description is not None:
                event['description'] = description
            if start_datetime is not None:
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                }
            if end_datetime is not None:
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                }
            
            # Salvar alterações
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'event_id': updated_event['id'],
                'html_link': updated_event.get('htmlLink'),
                'status': updated_event.get('status'),
                'updated': updated_event.get('updated')
            }
            
        except HttpError as e:
            logging.error(f"Erro HTTP ao atualizar evento: {str(e)}")
            raise Exception(f"Erro ao atualizar evento: {str(e)}")
        except Exception as e:
            logging.error(f"Erro ao atualizar evento: {str(e)}")
            raise Exception(f"Erro inesperado: {str(e)}")
    
    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """
        Exclui um evento do calendário
        
        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            
        Returns:
            True se excluído com sucesso
        """
        try:
            if not self.service:
                raise Exception("Serviço não inicializado. Faça autenticação primeiro.")
            
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 410:  # Evento já foi excluído
                return True
            logging.error(f"Erro HTTP ao excluir evento: {str(e)}")
            raise Exception(f"Erro ao excluir evento: {str(e)}")
        except Exception as e:
            logging.error(f"Erro ao excluir evento: {str(e)}")
            raise Exception(f"Erro inesperado: {str(e)}")

# Instância global do serviço
google_calendar_service = GoogleCalendarService()
