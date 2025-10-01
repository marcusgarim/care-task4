#!/usr/bin/env python3
"""
Script para criar tabelas necessárias para integração com Google Calendar
"""

import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def create_google_calendar_tables():
    """Cria as tabelas necessárias para Google Calendar integration"""
    
    # Configurações do banco de dados
    config = {
        'host': os.getenv('PGHOST'),
        'port': os.getenv('PGPORT', '5432'),
        'dbname': os.getenv('PGDATABASE'),
        'user': os.getenv('PGUSER'),
        'password': os.getenv('PGPASSWORD')
    }
    
    connection = None
    try:
        # Conectar ao banco
        connection = psycopg.connect(**config)
        cursor = connection.cursor()
        
        print("Criando tabelas para integração Google Calendar...")
        
        # 1. Tabela para armazenar credenciais OAuth dos profissionais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profissional_google_credentials (
                id SERIAL PRIMARY KEY,
                profissional_id INTEGER NOT NULL REFERENCES profissionais(id),
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_uri TEXT,
                client_id TEXT,
                client_secret TEXT,
                expires_at TIMESTAMP,
                scopes TEXT,
                calendar_id TEXT,
                calendar_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1,
                UNIQUE(profissional_id)
            )
        """)
        
        # 2. Adicionar campos para controle de eventos do Google Calendar na tabela agendamentos
        cursor.execute("""
            ALTER TABLE agendamentos 
            ADD COLUMN IF NOT EXISTS google_event_id TEXT,
            ADD COLUMN IF NOT EXISTS google_calendar_id TEXT,
            ADD COLUMN IF NOT EXISTS google_event_link TEXT,
            ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending'
        """)
        
        # 3. Tabela para log de sincronização
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_calendar_sync_log (
                id SERIAL PRIMARY KEY,
                agendamento_id INTEGER REFERENCES agendamentos(id),
                profissional_id INTEGER REFERENCES profissionais(id),
                action VARCHAR(20) NOT NULL, -- 'create', 'update', 'delete'
                google_event_id TEXT,
                status VARCHAR(20) NOT NULL, -- 'success', 'error', 'pending'
                error_message TEXT,
                sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 4. Tabela para configurações globais do Google Calendar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_calendar_settings (
                id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 5. Inserir configurações padrão
        default_settings = [
            ('oauth_client_id', '', 'Client ID para OAuth2 do Google'),
            ('oauth_client_secret', '', 'Client Secret para OAuth2 do Google'),
            ('oauth_redirect_uri', 'http://127.0.0.1:8000/api/google-calendar/callback', 'URI de callback OAuth'),
            ('default_event_duration', '30', 'Duração padrão dos eventos em minutos'),
            ('auto_sync_enabled', '1', 'Sincronização automática habilitada (1) ou não (0)'),
            ('sync_interval_minutes', '15', 'Intervalo de sincronização em minutos'),
            ('calendar_timezone', 'America/Sao_Paulo', 'Timezone padrão dos calendários')
        ]
        
        for key, value, description in default_settings:
            cursor.execute("""
                INSERT INTO google_calendar_settings (setting_key, setting_value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (setting_key) DO NOTHING
            """, (key, value, description))
        
        # 6. Adicionar campo para controle de integração na tabela profissionais
        cursor.execute("""
            ALTER TABLE profissionais 
            ADD COLUMN IF NOT EXISTS google_calendar_enabled INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS google_calendar_sync_last TIMESTAMP
        """)
        
        # 7. Índices para performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agendamentos_google_event_id 
            ON agendamentos(google_event_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_google_sync_log_agendamento 
            ON google_calendar_sync_log(agendamento_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_google_sync_log_profissional 
            ON google_calendar_sync_log(profissional_id);
        """)
        
        # Commit das alterações
        connection.commit()
        
        print("Tabelas criadas com sucesso!")
        
        # Mostrar resumo das tabelas criadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%google%'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print("\nTabelas relacionadas ao Google Calendar:")
        for table in tables:
            print(f"  - {table[0]}")
            
    except Exception as e:
        print(f"Erro ao criar tabelas: {str(e)}")
        if connection:
            connection.rollback()
    
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    create_google_calendar_tables()
