#!/usr/bin/env bash
export FLASK_APP=app.py
export FLASK_ENV=development
# load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
flask run --host=0.0.0.0 --port=5000
