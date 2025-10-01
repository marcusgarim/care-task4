#!/usr/bin/env python3
"""
Migração para adicionar campos de Google Calendar na tabela profissionais
"""

import sys
import os
sys.path.append('/Users/marcusgarim/Documents/careintelligence/care-task4')

from app.core.db import get_db
import logging

def migrate_profissionais_table():
    """Adiciona campos necessários para integração Google Calendar"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        with db.cursor() as cur:
            print("Verificando estrutura atual da tabela profissionais...")
            
            # Verificar se as colunas já existem (PostgreSQL)
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'profissionais' 
                AND column_name IN ('email', 'horas_trabalho_semana')
            """)
            existing_columns = [row['column_name'] for row in cur.fetchall()]
            
            # Adicionar coluna email se não existir
            if 'email' not in existing_columns:
                print("Adicionando coluna 'email'...")
                cur.execute("""
                    ALTER TABLE profissionais 
                    ADD COLUMN email VARCHAR(255) UNIQUE
                """)
                print("✓ Coluna 'email' adicionada")
            else:
                print("✓ Coluna 'email' já existe")
            
            # Adicionar coluna horas_trabalho_semana se não existir
            if 'horas_trabalho_semana' not in existing_columns:
                print("Adicionando coluna 'horas_trabalho_semana'...")
                cur.execute("""
                    ALTER TABLE profissionais 
                    ADD COLUMN horas_trabalho_semana INTEGER DEFAULT 40
                """)
                print("✓ Coluna 'horas_trabalho_semana' adicionada")
            else:
                print("✓ Coluna 'horas_trabalho_semana' já existe")
            
            # Verificar se precisamos de updated_at (PostgreSQL)
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'profissionais' 
                AND column_name = 'updated_at'
            """)
            
            if not cur.fetchone():
                print("Adicionando coluna 'updated_at'...")
                cur.execute("""
                    ALTER TABLE profissionais 
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                print("✓ Coluna 'updated_at' adicionada")
            else:
                print("✓ Coluna 'updated_at' já existe")
            
            db.commit()
            print("\nMigração concluída com sucesso!")
            print("Tabela profissionais agora suporta integração Google Calendar")
            
    except Exception as e:
        print(f"Erro na migração: {str(e)}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        try:
            db.close()
        except:
            pass

def migrate_agendamentos_table():
    """Adiciona campo event_id para vincular com Google Calendar"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        with db.cursor() as cur:
            print("Verificando tabela agendamentos...")
            
            # Verificar se coluna event_id existe (PostgreSQL)
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'agendamentos' 
                AND column_name = 'event_id'
            """)
            
            if not cur.fetchone():
                print("Adicionando coluna 'event_id' em agendamentos...")
                cur.execute("""
                    ALTER TABLE agendamentos 
                    ADD COLUMN event_id VARCHAR(255)
                """)
                print("✓ Coluna 'event_id' adicionada")
            else:
                print("✓ Coluna 'event_id' já existe")
            
            db.commit()
            print("✓ Tabela agendamentos atualizada")
            
    except Exception as e:
        print(f"Erro na migração agendamentos: {str(e)}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        try:
            db.close()
        except:
            pass

if __name__ == "__main__":
    print("Iniciando migração para Google Calendar Integration")
    print("="*60)
    
    try:
        migrate_profissionais_table()
        migrate_agendamentos_table()
        
        print("\n" + "="*60)
        print("MIGRAÇÃO COMPLETA!")
        print("Sistema pronto para integração Google Calendar")
        print("\nPróximos passos:")
        print("1. Reinicie o servidor backend")
        print("2. Configure autenticação OAuth do Google Calendar")
        print("3. Teste a nova aba 'Agenda' no painel")
        
    except Exception as e:
        print(f"\nMIGRAÇÃO FALHOU: {str(e)}")
        sys.exit(1)
