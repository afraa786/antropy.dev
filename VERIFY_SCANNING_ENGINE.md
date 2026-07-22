# Scanning Engine Fix - Verification Checklist

## Pre-Deployment Checklist

### Code Review
- [ ] `server/src/appsec/main.py` has import statement
- [ ] `server/src/appsec/infrastructure/celery_app.py` has import statement
- [ ] Both imports are: `from appsec.scanner import engines as _`
- [ ] No syntax errors in modified files
- [ ] Imports placed after existing imports

### Environment Setup
- [ ] Backend database running (PostgreSQL)
- [ ] Redis/broker running for Celery
- [ ] Nuclei CLI installed on worker machine
- [ ] Katana CLI installed on worker machine

## Deployment Checklist

### Backend Startup
- [ ] FastAPI app starts without errors
  ```bash
  cd server && uv run uvicorn appsec.main:app --host 0.0.0.0 --port 8000
  # Should see: Uvicorn running on http://0.0.0.0:8000
  ```
- [ ] No import errors in logs
- [ ] API docs accessible: http://localhost:8000/docs

### Celery Worker Startup
- [ ] Celery worker starts without errors
  ```bash
  cd server && uv run celery -A appsec.infrastructure.celery_app worker -l info
  # Should see: Connected to redis://... and ready to accept tasks
  ```
- [ ] No import errors for scanner.engines
- [ ] Worker accepts tasks

## Runtime Verification

### Registry Verification

**Method 1: Python REPL**
```bash
cd server
uv run python
```
```python
from appsec.scanner.interfaces.registry import list_scanners
scanners = list_scanners()
print(f"Registered scanners: {scanners}")
# Expected output: ['katana', 'nuclei', 'ssl_tls', 'urlscan']
assert len(scanners) >= 2, "Not enough scanners registered"
assert 'nuclei' in scanners, "Nuclei not registered"
assert 'katana' in scanners, "Katana not registered"
print("✅ Registry verification passed")
```

**Method 2: Backend API (if endpoint exists)**
```bash
curl http://localhost:8000/api/v1/health/scanners 2>/dev/null | jq
# Or check via documentation
```

### Quick Scan Flow Test

**Step 1: Create Account (Optional, can use existing)**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test Operator"
  }'
```

**Step 2: Initiate Quick Scan**
```bash
curl -X POST http://localhost:8000/api/v1/quick-scan \
  -H "Content-Type: application/json" \
  -d '{
    "target": "example.com",
    "target_type": "domain",
    "scan_type": "default",
    "skip_verification": true
  }' | jq
```

Expected response:
```json
{
  "scan_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "org_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "pending"
}
```

**Verify:**
- [ ] Response includes `scan_job_id`
- [ ] Response includes `org_id`
- [ ] Status is `pending`

**Step 3: Monitor Scan Execution**

Check Celery worker logs:
```
Should see:
[scan.execute] Task started
[nuclei] Running nuclei scan
[katana] Running katana crawl
[scan.execute] Task completed
```

**Step 4: Verify Scan Completes**

Wait 30-60 seconds, then:
```bash
SCAN_JOB_ID="550e8400-e29b-41d4-a716-446655440000"
ORG_ID="660e8400-e29b-41d4-a716-446655440001"
TOKEN="<your-auth-token>"

curl -X GET "http://localhost:8000/api/v1/scan-jobs/${SCAN_JOB_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Organization-ID: ${ORG_ID}" | jq '.status'
```

Expected progression:
```
"pending"  ← immediately after scan starts
"running"  ← after ~5 seconds
"completed" ← after ~30-60 seconds
```

**Step 5: Retrieve Findings**

Once status is `completed`:
```bash
curl -X GET "http://localhost:8000/api/v1/scan-jobs/${SCAN_JOB_ID}/results" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Organization-ID: ${ORG_ID}" | jq
```

Expected response structure:
```json
{
  "findings": [
    {
      "id": "...",
      "title": "SSL Certificate Issue",
      "severity": "HIGH",
      "engine": "nuclei",
      "description": "...",
      "remediation": "...",
      "references": []
    },
    {
      "id": "...",
      "title": "Missing Security Headers",
      "severity": "MEDIUM",
      "engine": "nuclei",
      "description": "...",
      "remediation": "...",
      "references": []
    }
  ],
  "severity_counts": {
    "CRITICAL": 0,
    "HIGH": 2,
    "MEDIUM": 5,
    "LOW": 8,
    "INFO": 3
  }
}
```

**Verify:**
- [ ] `findings` array is not empty
- [ ] At least one finding has `engine: "nuclei"`
- [ ] Findings have proper structure (title, severity, etc.)
- [ ] `severity_counts` shows distribution

### Frontend Integration Test

**Test 1: Unauthenticated Quick Scan**
1. [ ] Open http://localhost:3000/ in private/incognito window
2. [ ] Enter domain: `example.com`
3. [ ] Click "Start Scan"
4. [ ] Verify:
   - [ ] No login required
   - [ ] Redirects to scan results page
   - [ ] Results page shows "Scanning in progress"
   - [ ] After 30-60 seconds, findings appear

**Test 2: Authenticated Scan**
1. [ ] Login to http://localhost:3000/login
2. [ ] Go to dashboard
3. [ ] Start a new scan
4. [ ] Verify:
   - [ ] Scan appears in list
   - [ ] Status shows: pending → running → completed
   - [ ] Results display with findings

**Test 3: Results Display**
1. [ ] Click on a completed scan
2. [ ] Verify:
   - [ ] Finding list displays
   - [ ] Severity badges visible (with colors)
   - [ ] Multiple findings shown
   - [ ] Can click on findings for details

## Troubleshooting

### Registry Empty After Fix

**Symptom:** `list_scanners()` returns `[]`

**Diagnosis:**
```bash
# Check if engine modules are being imported
grep -r "from appsec.scanner import engines" /vercel/share/v0-project/server/src/
# Should see 2 results: main.py and celery_app.py
```

**Fix:**
1. Verify both files have exact import statement
2. Restart FastAPI and Celery
3. Check for import errors: `python -c "from appsec.scanner import engines"`

### Nuclei/Katana Not Found

**Symptom:** Worker logs show command not found

**Diagnosis:**
```bash
which nuclei
which katana
# Both should return paths
```

**Fix:**
```bash
# macOS
brew install nuclei katana

# Linux
sudo apt-get install nuclei katana

# Docker
docker exec entropy-worker apt-get update && apt-get install -y nuclei katana
```

### Scan Stuck in Running State

**Symptom:** Scan stays `running` for >5 minutes

**Diagnosis:**
```bash
# Check worker logs
docker logs entropy-worker --tail 50
# Look for engine timeouts or errors
```

**Fix:**
1. Check if engine tools are responsive: `nuclei -version`
2. Try simpler target (e.g., `google.com`)
3. Increase scan timeouts in config if needed

### No Findings Returned

**Symptom:** Scan completes but findings array is empty

**Diagnosis:**
1. Check if target is valid: `ping example.com`
2. Check worker logs for engine output
3. Verify Nuclei templates installed: `ls ~/.nuclei/`

**Fix:**
1. Download Nuclei templates: `nuclei -update-templates`
2. Try different target domain
3. Check engine logs: `nuclei -v https://example.com`

## Performance Expectations

| Metric | Expected | Max Acceptable |
|--------|----------|-----------------|
| Quick scan duration | 30-60 sec | 120 sec |
| Finding count | 5-20 | 1000+ |
| Memory usage | <500MB | <2GB |
| CPU usage (per engine) | 20-40% | 80% |

## Rollback Plan

If critical issues found:

1. Revert the 2 one-line changes
2. Restart FastAPI and Celery
3. Existing scans will still fail to complete but new ones won't start
4. No data loss

## Success Criteria

All of the following must be true:

- [ ] Registry contains both `nuclei` and `katana`
- [ ] Quick scan completes: PENDING → RUNNING → COMPLETED
- [ ] Findings returned from Nuclei
- [ ] Frontend displays findings with proper styling
- [ ] Multiple severity levels shown
- [ ] Unauthenticated quick-scans work
- [ ] Authenticated scans work
- [ ] No console errors in browser
- [ ] No Python errors in backend logs
- [ ] No Celery worker errors

## Sign-Off

- [ ] All checks passed
- [ ] Scans executing properly
- [ ] Findings displayed accurately
- [ ] Ready for production deployment
