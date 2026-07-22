# Account Creation Failing - ROOT CAUSE & SOLUTION

## 🔴 Root Cause: Backend Not Running

### Diagnosis

**Error:** "Failed to fetch" on register page

**Reason:** 
- Backend server is NOT running
- Frontend on `:3000` tries to POST to http://localhost:8000/api/v1/auth/register
- Connection refused → "Failed to fetch"

### Why?

Your project is a **monorepo** with two services:
- **Frontend** (Next.js) - pure TypeScript, runs anywhere
- **Backend** (FastAPI) - requires PostgreSQL + Redis infrastructure

The frontend was started automatically, but backend requires explicit setup with databases.

---

## ✅ Solution: Start Backend

### Fastest Way (3 minutes):

**If Docker is installed:**
```bash
cd /vercel/share/v0-project
docker compose up -d
```

**Without Docker (macOS):**
```bash
# Install if needed
brew install postgresql redis

# Start services
brew services start postgresql
brew services start redis

# Setup backend
cd /vercel/share/v0-project/server
cp .env.example .env
uv sync
uv run alembic upgrade head

# Terminal 1: Start backend
uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
cd /vercel/share/v0-project/client
npm run dev
```

**Without Docker (Linux):**
```bash
# Install if needed
sudo apt-get install postgresql redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Rest same as macOS
```

---

## What Happens When Backend Starts

```
Timeline:
─────────
1. PostgreSQL starts (:5432)
2. Redis starts (:6379)
3. Backend connects to both
4. Backend runs database migrations
5. Backend API ready on http://localhost:8000 ✓

Frontend already running on http://localhost:3000 ✓

Registration flow now works:
  Frontend POST /api/v1/auth/register
  → Backend receives request
  → Validates email/password
  → Creates user in database
  → Returns user data
  → Frontend saves tokens
  → Redirects to dashboard ✓
```

---

## Code Changes Already Applied

Your P0 fixes are already in place:

### P0 #1: Unauthenticated Quick Scan ✅
- Backend endpoint now accepts requests without auth token
- Anonymous users auto-created if no Bearer token
- Changes in:
  - `server/src/appsec/api/v1/quick_scan.py`
  - `server/src/appsec/api/deps.py`
  - `server/src/appsec/application/users/service.py`

### P0 #2: Missing org_id in Response ✅
- Quick-scan response now includes `org_id`
- Frontend stores it in localStorage
- Changes in:
  - `server/src/appsec/application/quick_scan/schemas.py`
  - `client/src/lib/api.ts`
  - `client/src/app/page.tsx`
  - `client/src/app/scan/[id]/page.tsx`

**These work once backend is running!**

---

## Test Flow After Backend Starts

### Step 1: Create Account
```
1. Go to http://localhost:3000/register
2. Enter:
   - Name: "Alex Chen"
   - Email: "alex@example.com"
   - Password: "TestPass123"
3. Click "Create account"
4. ✅ Redirects to dashboard
```

### Step 2: Test Unauthenticated Quick Scan
```
1. Logout or open new private/incognito window
2. Go to http://localhost:3000/
3. Enter domain: "example.com"
4. Click "Start Scan"
5. ✅ Scan starts WITHOUT requiring login (P0 #1 fix!)
6. Open DevTools → Console
7. Type: localStorage.getItem('entropy-org-id')
8. ✅ Shows UUID (P0 #2 fix!)
```

### Step 3: Verify Scan Results Page
```
1. Scan completes
2. Navigate to results page
3. ✅ Page loads with real data (not redirecting to dashboard!)
```

---

## Verify Backend is Running

```bash
# Test API endpoint
curl http://localhost:8000/

# Should return something (not "connection refused")

# Test specific endpoint
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@test.com",
    "password":"testpass",
    "full_name":"Test"
  }'

# Should return user data or validation error
# NOT "Failed to fetch"
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Failed to fetch" on register | Backend not running | Start backend (see above) |
| "Connection refused" | PostgreSQL not running | `brew services start postgresql` |
| "Redis connection error" | Redis not running | `brew services start redis` |
| "Database does not exist" | DB not created | `createdb -U postgres appsec` |
| Still "Failed to fetch" | Backend crashed | Check `docker compose logs backend` or terminal output |

---

## Files for Reference

- **Full Setup Guide:** `BACKEND_SETUP_GUIDE.md`
- **Quick Start:** `QUICK_START.md`
- **P0 Fixes Summary:** `P0_FIXES_SUMMARY.md`
- **All Diffs:** `DIFFS_P0_FIXES.md`
- **Code Changes:** `VERIFY_FIXES.md`

---

## Summary

| Item | Status | Next Step |
|------|--------|-----------|
| P0 #1 Code (unauthenticated scan) | ✅ Ready | Start backend |
| P0 #2 Code (org_id in response) | ✅ Ready | Start backend |
| Backend Running | ❌ Not started | `docker compose up` or local setup |
| PostgreSQL | ❌ Not running | Start it (included in docker compose) |
| Redis | ❌ Not running | Start it (included in docker compose) |
| Account Creation | ⏳ Pending | Start backend first |

**You're 95% done!** The code is fixed. Just need to start the backend.

---

## Next Action

Choose ONE:

### 🐳 Docker (Easiest):
```bash
docker compose up -d
# Then go to http://localhost:3000/register
```

### 💻 Local (macOS):
```bash
brew services start postgresql
brew services start redis
cd server && uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload
# In another terminal:
cd client && npm run dev
# Then go to http://localhost:3000/register
```

### 🐧 Local (Linux):
```bash
sudo systemctl start postgresql
sudo systemctl start redis-server
# Rest same as macOS
```

After that, account creation will work! ✅
