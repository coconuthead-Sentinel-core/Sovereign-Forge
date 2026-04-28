Quickstart

Prereqs

- Docker and docker compose
- Optional: Python 3.11+ for local scripts

Run (one command)

- docker compose up --build
- Open http://localhost:8000/api/ops

Exercise the API (PowerShell examples)

- Status: Invoke-RestMethod http://localhost:8000/api/status
- Seed symbols (optional pack): Invoke-RestMethod -Method POST http://localhost:8000/api/symbols/pack -ContentType 'application/json' -Body (Get-Content data/symbols_pack.sample.json -Raw)
- Cognition: Invoke-RestMethod -Method POST http://localhost:8000/api/cog/process -ContentType 'application/json' -Body (@{data='apex ignite core process launch'} | ConvertTo-Json)
- Stress: Invoke-RestMethod -Method POST http://localhost:8000/api/stress -ContentType 'application/json' -Body (@{iterations=250; concurrent=$true} | ConvertTo-Json)
- Metrics (Prom): Invoke-WebRequest http://localhost:8000/api/metrics/prom | Select-Object -Expand Content

Local demo script

- python scripts/load.py --stress 250 --concurrent

WebSocket stream

- Connect to ws://localhost:8000/ws/sync (add ?api_key= if QNF_API_KEY is set)

Security env (optional)

- QNF_API_KEY=yourkey (enforce API key for REST/WS)
- QNF_ENV=prod (tighten default CORS)
