import os
from typing import Generator
from dotenv import load_dotenv

# Opção MySQL (legado)
import pymysql

# Opção PostgreSQL (novo)
try:
    import psycopg
    from psycopg.rows import dict_row as pg_dict_row
except Exception:
    psycopg = None
    pg_dict_row = None


def is_postgres_connection(conn: object) -> bool:
    try:
        return psycopg is not None and isinstance(conn, psycopg.Connection)
    except Exception:
        return False

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))


def get_db() -> Generator[object, None, None]:
    """
    Retorna conexão com banco.
    - Se PGHOST estiver definido, conecta em PostgreSQL (psycopg) com row_factory dict.
    - Caso contrário, usa MySQL (PyMySQL) como fallback.
    """
    pghost = os.getenv("PGHOST")
    if pghost and psycopg is not None:
        connection = psycopg.connect(
            host=pghost,
            port=int(os.getenv("PGPORT", "5432")),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            dbname=os.getenv("PGDATABASE"),
            sslmode=os.getenv("PGSSLMODE", "require"),
            row_factory=pg_dict_row,
        )
        connection.autocommit = True
        try:
            yield connection
        finally:
            try:
                connection.close()
            except Exception:
                pass
        return

    # Fallback MySQL
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "andreia"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    try:
        yield connection
    finally:
        try:
            connection.close()
        except Exception:
            pass

