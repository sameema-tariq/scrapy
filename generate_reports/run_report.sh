#!/bin/bash
set -e

echo "=== Canopy Propensity - Report Generation ==="
echo ""

echo "[1/7] Starting Postgres..."
#docker compose up -d --wait

echo "[2/7] Running database migrations..."
#uv run alembic upgrade head

echo "[3/7] Seeding reference data..."
uv run python -m generate_reports.generate_queries
#uv run python -m generate_reports.main

echo ""
echo "=== Report Generation complete ==="
