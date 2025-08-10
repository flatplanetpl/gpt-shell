#!/usr/bin/env bash
set -euo pipefail
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo "Gotowe. Ustaw jeszcze zmienne i uruchom:"
echo '  export OPENAI_API_KEY="..."; export OPENAI_MODEL="gpt-5"; export WORKDIR="$PWD"; ./run.sh'
