#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

if [[ -d "$VENV_PATH" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
else
  python3 -m venv "$VENV_PATH"
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
fi

pip install -r "$PROJECT_ROOT/requirements.txt"
cd "$PROJECT_ROOT"
python test_suite.py
