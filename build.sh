#!/usr/bin/env bash
set -o errexit

uv sync --frozen --no-dev
uv run python manage.py collectstatic --no-input
uv run python manage.py migrate

if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]]; then
  uv run python manage.py createsuperuser --no-input || true
fi