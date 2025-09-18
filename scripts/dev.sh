#!/usr/bin/env bash
set -euo pipefail

# Configurações
BACK_HOST=${BACK_HOST:-127.0.0.1}
BACK_PORT=${BACK_PORT:-8000}
FRONT_PORT=${FRONT_PORT:-5500}

# Raiz do projeto (baseado na localização deste script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[dev] Raiz do projeto: $ROOT_DIR"

# Preparar venv
VENV_DIR="$ROOT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "[dev] Criando ambiente virtual em $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "[dev] Instalando dependências do backend (se necessário)"
python -m pip install --upgrade pip >/dev/null
pip install -r "$ROOT_DIR/requirements.txt" >/dev/null

# Carrega variáveis de ambiente do .env (se existir)
if [ -f "$ROOT_DIR/.env" ]; then
  echo "[dev] Carregando variáveis de ambiente do .env"
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

# Liberar portas ocupadas (opcional)
for PORT in "$BACK_PORT" "$FRONT_PORT"; do
  PIDS=$(lsof -ti tcp:$PORT || true)
  if [ -n "$PIDS" ]; then
    echo "[dev] Encerrando processos nas portas $PORT: $PIDS"
    kill -9 $PIDS || true
  fi
done

# Encerramento limpo
cleanup() {
  echo "\n[dev] Encerrando serviços..."
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[dev] Iniciando backend em http://$BACK_HOST:$BACK_PORT"
cd "$ROOT_DIR"
uvicorn app.main:app --host "$BACK_HOST" --port "$BACK_PORT" --reload &

echo "[dev] Iniciando frontend estático em http://127.0.0.1:$FRONT_PORT"
cd "$ROOT_DIR/src"
python3 -m http.server "$FRONT_PORT" &

echo "\n[dev] Pronto!"
echo "[dev] Backend:  http://$BACK_HOST:$BACK_PORT"
echo "[dev] Frontend: http://127.0.0.1:$FRONT_PORT"
echo "[dev] Pressione Ctrl+C para parar ambos."

# Mantém script vivo enquanto processos rodam
wait