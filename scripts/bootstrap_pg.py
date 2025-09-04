import os
import sys
from typing import List

import psycopg
from dotenv import load_dotenv


def load_env() -> None:
    project_root = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)


def read_sql_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_sql_statements(sql_text: str) -> List[str]:
    statements: List[str] = []
    current: List[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False

    i = 0
    while i < len(sql_text):
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < len(sql_text) else ""

        if in_line_comment:
            current.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            current.append(ch)
            if ch == "*" and nxt == "/":
                current.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        # Enter/exit comments
        if not in_single_quote and not in_double_quote:
            if ch == "-" and nxt == "-":
                in_line_comment = True
                current.append(ch)
                current.append(nxt)
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                current.append(ch)
                current.append(nxt)
                i += 2
                continue

        # Toggle quotes
        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(ch)
            i += 1
            continue

        # Statement boundary
        if ch == ";" and not in_single_quote and not in_double_quote:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    # Remove empty statements
    return [s for s in statements if s.strip()]


def main() -> int:
    load_env()
    project_root = os.path.dirname(os.path.dirname(__file__))
    sql_path = os.path.join(project_root, "doc", "bootstrap_pg.sql")

    if not os.path.exists(sql_path):
        print(f"Arquivo SQL não encontrado: {sql_path}")
        return 1

    sql_text = read_sql_file(sql_path)
    statements = split_sql_statements(sql_text)
    if not statements:
        print("Nenhuma instrução SQL encontrada no arquivo.")
        return 1

    conn = psycopg.connect(
        host=os.getenv("PGHOST"),
        user=os.getenv("PGUSER"),
        port=os.getenv("PGPORT"),
        password=os.getenv("PGPASSWORD"),
        dbname=os.getenv("PGDATABASE"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

    try:
        with conn:
            with conn.cursor() as cur:
                for idx, stmt in enumerate(statements, start=1):
                    s = stmt.strip()
                    if not s:
                        continue
                    try:
                        cur.execute(s)
                        # Se for DML, deixa o commit do context manager
                        print(f"[OK] {idx}: {s.splitlines()[0][:100]}...")
                    except Exception as e:
                        print(f"[ERRO] {idx}: {e}\nSQL: {s}")
                        raise
        print("Bootstrap PostgreSQL concluído com sucesso.")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())


