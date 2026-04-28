# Sentinel Forge API Examples

This guide provides examples for interacting with the Sentinel Forge API using `curl` (Linux/Mac) and PowerShell (Windows).

**Base URL:** `http://127.0.0.1:8000`
**Auth:** Add header `X-API-Key: <your-key>` if configured.

---

## 1. System Status
Check if the system is running and healthy.

**Curl:**
```bash
curl -X GET http://127.0.0.1:8000/api/status
```

**PowerShell:**
```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/status"
```

---

## 2. AI Chat
Send a message to the neuro-symbolic agent.

**Curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the status of the memory lattice?"}
    ],
    "temperature": 0.7
  }'
```

**PowerShell:**
```powershell
$body = @{
    messages = @(
        @{ role = "user"; content = "What is the status of the memory lattice?" }
    )
    temperature = 0.7
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/ai/chat" -Body $body -ContentType "application/json"
```

---

## 3. Upsert Note (Memory)
Save a piece of information to the Cosmos DB backing store.

**Curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/notes/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sector 7 sensors are detecting anomalous signal drift.",
    "tag": "sector-7-logs"
  }'
```

**PowerShell:**
```powershell
$body = @{
    text = "Sector 7 sensors are detecting anomalous signal drift."
    tag = "sector-7-logs"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/notes/upsert" -Body $body -ContentType "application/json"
```

---

## 4. Cognitive Process
Run raw data through the cognitive pipeline (EntropyAnalyzer / PatternSuggestion).

**Curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/cog/process \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Analyze entropy levels in the local subnet."
  }'
```
