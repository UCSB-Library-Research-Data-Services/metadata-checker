#!/usr/bin/env bash

set -e

VENV_DIR=".venv"
METADIG_PY_URL="git+https://github.com/UCSB-Library-Research-Data-Services/metadig-py.git@metadata-checker-install"

# These need their own dependency trees resolved normally (e.g. pandas needs
# numpy) - installed as one pip call, no --no-deps here.
packages=(
    "lxml"
    "pandas"
    "chardet"
    "pyyaml"
    "git+https://github.com/dataoneorg/hashstore.git"

)

echo "==> Setting up virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip

echo "==> Installing dependencies..."
pip install "${packages[@]}"

echo "==> Installing metadig-py..."
pip install --no-deps "$METADIG_PY_URL"

echo "==> Verifying install..."
python3 -c "from metadig import suites; print('metadig imported OK')"

echo "==> Installation complete!"

