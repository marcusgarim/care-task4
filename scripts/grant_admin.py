import sys
from pathlib import Path

# Permite importar app.core.db
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.db import get_db, is_postgres_connection  # type: ignore


def grant_admin(email: str) -> int:
    db_gen = get_db()  # type: ignore
    db = next(db_gen)
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                print(f"Usuário não encontrado: {email}")
                return 1

            if is_postgres_connection(db):
                cur.execute("UPDATE users SET is_admin=TRUE, ativo=TRUE WHERE email=%s", (email,))
            else:
                cur.execute("UPDATE users SET is_admin=1, ativo=1 WHERE email=%s", (email,))

            print(f"Usuário promovido a admin e ativado: {email}")
            return 0
    finally:
        try:
            db_gen.close()  # type: ignore
        except Exception:
            pass


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/grant_admin.py <email>")
        return 2
    email = sys.argv[1].strip()
    if not email:
        print("Email inválido")
        return 2
    return grant_admin(email)


if __name__ == "__main__":
    raise SystemExit(main())