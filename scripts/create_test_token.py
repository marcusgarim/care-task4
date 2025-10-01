# create_test_token.py
# Script para criar um token de teste simulando a autenticação
import json
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_PATH = "../credentials/client_secret_937819787856-slug9sall5g85u08lhdrujf4sm273h6g.apps.googleusercontent.com.json"
TOKEN_PATH = "token_suporte.json"

def criar_token_demo():
    """Cria um token demo para testes (você precisará autorizar uma vez)"""
    
    print("INSTRUÇÕES PARA CRIAR TOKEN:")
    print("1. Abra esta URL no navegador:")
    
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    flow.redirect_uri = 'http://localhost:60817'
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    print(f"\n{auth_url}")
    print("\n2. Faça login com suporte@careintelligence.ai")
    print("3. Copie a URL de redirecionamento completa")
    print("4. Cole abaixo:")
    
    try:
        auth_code_url = input("\nURL de redirecionamento: ").strip()
        
        # Extrair código da URL
        if "code=" in auth_code_url:
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(auth_code_url)
            code = urlparse.parse_qs(parsed.query).get('code', [None])[0]
            
            if code:
                print("Obtendo token...")
                flow.fetch_token(code=code)
                creds = flow.credentials
                
                # Salvar token
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
                
                print(f"Token salvo em {TOKEN_PATH}")
                print("Agora você pode executar: python3 test_calendar_operations.py")
                return True
            else:
                print("Erro: Código não encontrado na URL")
                return False
        else:
            print("Erro: URL inválida")
            return False
            
    except KeyboardInterrupt:
        print("\nOperação cancelada")
        return False
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    print("=== CRIADOR DE TOKEN PARA TESTES ===")
    criar_token_demo()
