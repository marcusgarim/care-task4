# calendar_support_to_marcus.py
import os
import sys
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==== CONFIGURAÇÃO ====
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_PATH = "credentials/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json"
TOKEN_PATH = "token_suporte.json"
TARGET_CALENDAR_NAME = "Smart Test"  # Nome da agenda específica
TARGET_CALENDAR_ID = None  # Será descoberto automaticamente
# =======================

def carregar_credenciais():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERRO: não encontrei o arquivo de credenciais em: {CREDENTIALS_PATH}")
        print("INSTRUÇÕES:")
        print("1. Copie o arquivo client_secret JSON do caminho:")
        print("   /mnt/data/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json")
        print("2. Para o diretório credentials/ do projeto:")
        print(f"   {os.path.abspath(CREDENTIALS_PATH)}")
        print("3. Execute o script novamente")
        print("4. Faça login com suporte@careintelligence.ai quando solicitado")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    else:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # run_local_server tenta abrir um browser; se falhar, o InstalledAppFlow
            # fornece uma URL que o usuário deve abrir manualmente.
            print("Tentando abrir o navegador para autenticação...")
            try:
                creds = flow.run_local_server(port=0)
            except Exception as browser_error:
                print("Não foi possível abrir o navegador automaticamente.")
                print("INSTRUÇÕES ALTERNATIVAS:")
                print("1. Execute o comando abaixo em um terminal com interface gráfica:")
                print(f"   python3 -c \"from google_auth_oauthlib.flow import InstalledAppFlow; flow = InstalledAppFlow.from_client_secrets_file('{CREDENTIALS_PATH}', {SCOPES}); flow.run_console()\"")
                print("2. Ou copie manualmente a URL de autorização que aparecerá")
                print("3. Faça login com suporte@careintelligence.ai")
                raise browser_error
            
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            print(f"Token salvo em {TOKEN_PATH}")
        except Exception as e:
            print("Erro durante o fluxo OAuth:", str(e))
            print("Se aparecer 'redirect_uri_mismatch', verifique os URIs de redirecionamento na console do Google Cloud.")
            print("URIs de redirecionamento recomendados:")
            print("- http://localhost")
            print("- http://127.0.0.1")
            raise

    return creds

def construir_servico(creds):
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print("Erro ao construir serviço Google Calendar:", str(e))
        raise

def encontrar_agenda_smart_test(service):
    """Encontra a agenda Smart Test nas agendas acessíveis"""
    try:
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        print(f"\nAgendas acessíveis:")
        for calendar in calendars:
            calendar_name = calendar.get('summary', 'Sem nome')
            calendar_id = calendar.get('id')
            print(f"- {calendar_name} ({calendar_id})")
            
            if calendar_name == TARGET_CALENDAR_NAME:
                print(f"✓ Agenda '{TARGET_CALENDAR_NAME}' encontrada: {calendar_id}")
                return calendar_id
        
        print(f"\nERRO: Agenda '{TARGET_CALENDAR_NAME}' não encontrada!")
        print("Verifique se:")
        print("1. A agenda Smart Test está compartilhada com suporte@careintelligence.ai")
        print("2. O usuário tem permissão de edição na agenda")
        print("3. O nome da agenda está correto (case-sensitive)")
        return None
        
    except HttpError as err:
        print("Erro ao listar agendas:", err)
        raise

def listar_proximos_eventos(service, calendar_id, max_results=5):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now,
            maxResults=max_results, singleEvents=True, orderBy="startTime"
        ).execute()
        items = events_result.get("items", [])
        if not items:
            print(f"Nenhum evento futuro encontrado na agenda '{TARGET_CALENDAR_NAME}'.")
        else:
            print(f"\nPróximos {len(items)} eventos na agenda '{TARGET_CALENDAR_NAME}':")
            for e in items:
                start = e["start"].get("dateTime", e["start"].get("date"))
                print(f"- {start}  |  {e.get('summary','(sem título)')}")
    except HttpError as err:
        print("HTTP error ao listar eventos:", err)
        raise

def criar_evento_teste(service, calendar_id):
    event = {
        "summary": "Teste: edição por Suporte via API na Smart Test",
        "description": "Evento criado automaticamente pelo script de testes na agenda Smart Test",
        "start": {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=10, minute=0, second=0).isoformat()},
        "end":   {"dateTime": (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=11, minute=0, second=0).isoformat()},
    }
    try:
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"\nEvento criado com sucesso na agenda '{TARGET_CALENDAR_NAME}'!")
        print("Link do evento:", created.get("htmlLink"))
        return created
    except HttpError as err:
        print("HTTP error ao criar evento:", err)
        raise

def main():
    print("Iniciando autenticação (faça login como suporte@careintelligence.ai)...")
    print(f"Objetivo: acessar a agenda '{TARGET_CALENDAR_NAME}' para testes")
    
    creds = carregar_credenciais()
    service = construir_servico(creds)

    # Encontrar a agenda Smart Test
    calendar_id = encontrar_agenda_smart_test(service)
    if not calendar_id:
        print("Script interrompido: agenda Smart Test não encontrada.")
        return

    # Executar testes na agenda encontrada
    listar_proximos_eventos(service, calendar_id)
    criar_evento_teste(service, calendar_id)
    print(f"\nConcluído. Se não apareceram erros, o Suporte conseguiu listar/criar eventos na agenda '{TARGET_CALENDAR_NAME}'.")

if __name__ == "__main__":
    main()
