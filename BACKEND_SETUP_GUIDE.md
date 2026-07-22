# Backend Setup Guide - Account Creation Failing

## Problem Summary

**Why Registration is Failing:**
- ❌ Backend server is NOT running
- Backend requires PostgreSQL and Redis (not available in this environment)
- Frontend is running on port 3000, but POST requests to http://localhost:8000 fail with "Failed to fetch"

---

## Current Environment Status

```
✅ Frontend: Running on http://localhost:3000
❌ Backend: NOT running (requires PostgreSQL + Redis)
❌ Database: PostgreSQL not available
❌ Cache: Redis not available
```

---

## Why This Happened

Your project is a **full-stack monorepo** with:
- **Frontend**: Next.js 16 (TypeScript) - no external dependencies
- **Backend**: FastAPI (Python) - requires PostgreSQL + Redis + external services

The v0 preview environment is primarily JavaScript/TypeScript based. Running Python backends with PostgreSQL/Redis requires additional setup.

---

## Solution: Local Development Setup

### Option 1: Docker Compose (Recommended for Development)

**Prerequisites:**
- Docker and Docker Compose installed
- 15GB disk space (images: postgres, redis, python dependencies)

**Steps:**

```bash
cd /vercel/share/v0-project
docker compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- Backend on port 8000 (automatically after DB ready)

**Verify Setup:**
```bash
# Check containers are running
docker compose ps

# View backend logs
docker compose logs -f backend

# Stop when done
docker compose down
```

**Frontend + Backend Flow:**
1. Backend starts and runs migrations automatically
2. Frontend communicates with backend on http://localhost:8000
3. Test registration: http://localhost:3000/register

---

### Option 2: Manual Local Setup (Linux/macOS)

**Prerequisites:**
- PostgreSQL 14+ installed locally
- Redis installed locally  
- Python 3.12+ with uv

**Steps:**

1. **Start PostgreSQL:**
```bash
# macOS with Homebrew
brew services start postgresql

# Or manually
postgres -D /usr/local/var/postgres &

# Ubuntu/Debian
sudo systemctl start postgresql
```

2. **Start Redis:**
```bash
# macOS
brew services start redis

# Or manually
redis-server &
```

3. **Create Database:**
```bash
createdb -U postgres appsec
# Or use psql:
psql -U postgres -c "CREATE DATABASE appsec;"
```

4. **Setup Backend Environment:**
```bash
cd /vercel/share/v0-project/server

# Copy env file
cp .env.example .env

# Edit .env with your local credentials
# DATABASE_URL=postgresql+asyncpg://appsec:changeme@localhost:5432/appsec
# REDIS_URL=redis://localhost:6379/0
# etc.
```

5. **Install Dependencies & Run Migrations:**
```bash
cd /vercel/share/v0-project/server

# Install with uv
uv sync

# Run migrations
uv run alembic upgrade head
```

6. **Start Backend:**
```bash
cd /vercel/share/v0-project/server
uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload
```

7. **Start Frontend (in another terminal):**
```bash
cd /vercel/share/v0-project/client
npm run dev
# or
pnpm dev
```

8. **Test Registration:**
- Open http://localhost:3000/register
- Fill in email, password, name
- Click "Create account"
- ✅ Should succeed!

---

### Option 3: Deploy to Vercel (Automatic)

If your project is connected to GitHub and a Vercel project:

```bash
# Push changes to GitHub
git add .
git commit -m "Fix: Allow unauthenticated quick-scans and include org_id"
git push origin main

# Vercel automatically:
# - Detects monorepo structure
# - Deploys frontend to Vercel (http://your-app.vercel.app)
# - Requires backend to be deployed separately (see below)
```

**For Backend Deployment:**

Backend needs to run on a platform that supports Python + PostgreSQL:
- **Recommended**: Railway, Render, Heroku, AWS, DigitalOcean App Platform
- Requires environment variables for PostgreSQL connection

---

## Fixing Account Creation

Once the backend is running (via Docker or local setup), registration will work:

### Test Flow:

1. **Backend Running?**
```bash
curl http://localhost:8000/api/v1/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'

# Should return error (user not found), not "Failed to fetch"
```

2. **Register New Account:**
```bash
curl http://localhost:8000/api/v1/auth/register -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "email":"newuser@example.com",
    "password":"SecurePass123!",
    "full_name":"Alex Chen"
  }'

# Should return:
# {"id": "UUID", "email": "newuser@example.com", "full_name": "Alex Chen", "is_active": true}
```

3. **Frontend Registration:**
- Navigate to http://localhost:3000/register
- Enter email, password, name
- Click "Create account"
- ✅ Should redirect to dashboard

---

## Troubleshooting

### "Failed to fetch" on Register

**Cause**: Backend not running or not accessible

**Fix**:
```bash
# Check if backend is running
curl http://localhost:8000/

# Should return something. If "connection refused":
# 1. Start PostgreSQL
# 2. Start Redis
# 3. Run backend (see Option 1 or 2 above)
```

### "Connection refused" Backend

**Cause**: PostgreSQL or Redis not running

**Fix**:
```bash
# Check PostgreSQL
psql -U appsec -d appsec -c "SELECT 1;"

# Check Redis
redis-cli ping
# Should return: PONG

# If not, start them (see Option 2)
```

### "Database does not exist"

**Cause**: Database not created

**Fix**:
```bash
# Create database
createdb -U postgres appsec

# Or in psql
psql -U postgres -c "CREATE DATABASE appsec;"

# Run migrations
cd /vercel/share/v0-project/server
uv run alembic upgrade head
```

### "Migration error"

**Cause**: Database schema issues

**Fix**:
```bash
# Reset database (WARNING: deletes all data)
dropdb -U postgres appsec
createdb -U postgres appsec

# Rerun migrations
cd /vercel/share/v0-project/server
uv run alembic upgrade head
```

### Frontend still says "Failed to fetch"

**Cause**: CORS error or incorrect API URL

**Fix**:
```bash
# Check API URL in frontend
# Open DevTools → Console
# Run: console.log(localStorage.getItem('entropy-auth'))
# Should show auth state after login

# Check Network tab:
# POST http://localhost:8000/api/v1/auth/register
# Should see 201 Created response (not 0 Network Error)
```

---

## Project Files You Modified

These are already fixed for the P0 issues:
- ✅ `server/src/appsec/api/v1/quick_scan.py` - Optional auth, org_id in response
- ✅ `server/src/appsec/api/deps.py` - Anonymous user creation
- ✅ `server/src/appsec/application/users/service.py` - create_anonymous() method
- ✅ `client/src/lib/api.ts` - Updated response types
- ✅ `client/src/app/page.tsx` - setActiveOrgId call
- ✅ `client/src/app/scan/[id]/page.tsx` - Removed auth requirement

These changes work once backend is running.

---

## Next Steps

1. **Choose Setup Method:**
   - Docker Compose (easiest)
   - Local setup (need PG + Redis)
   - Deploy to cloud (production-ready)

2. **Set Up Backend:**
   - Follow Option 1 (Docker), Option 2 (Local), or Option 3 (Cloud)

3. **Verify Both Servers Running:**
   - Frontend: http://localhost:3000 ✓
   - Backend: http://localhost:8000 ✓

4. **Test Registration:**
   - Go to http://localhost:3000/register
   - Create account
   - ✅ Should work!

5. **Test Quick Scan (P0 Fix):**
   - Go to http://localhost:3000/
   - Enter domain
   - Click "Start Scan"
   - ✅ Should scan without login!

---

## Docker Compose File

If you don't have one yet, create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: appsec
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: appsec
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appsec"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://appsec:changeme@postgres:5432/appsec
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: demo-secret-change-me
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
```

---

## Summary

| Step | Status | Command |
|------|--------|---------|
| Backend code changes | ✅ Done | Already applied |
| Frontend code changes | ✅ Done | Already applied |
| Backend running | ❌ Required | `docker compose up` or local setup |
| PostgreSQL | ❌ Required | `docker compose up` or `brew services start postgresql` |
| Redis | ❌ Required | `docker compose up` or `brew services start redis` |
| Account creation | ⏳ Pending | Start backend first |
| Quick scan demo | ⏳ Pending | Start backend first |

**You're almost there!** Just need to get the backend running. Choose your preferred method above and follow the steps.
