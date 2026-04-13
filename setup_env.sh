#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
fi

export FLASK_APP=run.py

if [[ ! -d migrations ]]; then
  flask db init
fi

flask db migrate -m "initial schema" || true
flask db upgrade

echo "Environnement prêt."
echo "Activation: source .venv/bin/activate"
echo "Lancement API: flask --app run.py run --debug"
