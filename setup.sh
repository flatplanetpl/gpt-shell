#!/usr/bin/env bash
set -euo pipefail
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo "Gotowe. Ustaw .env i uruchom ./run.sh"
