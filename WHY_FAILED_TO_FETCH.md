# "Failed to Fetch" Error - Complete Diagnosis

## What's Happening

When you try to create an account, you get **"Failed to fetch"** error.

This is a **network error** that means the frontend can't reach the backend.

---

## Why It's Happening

### Current State:

```
Frontend (Next.js)        Backend (FastAPI)
http://3000 ✅ RUNNING    http://8000 ❌ NOT RUNNING

                    POST /api/v1/auth/register
                    ↓
                    [Connection Refused]
                    ↓
                    Error: "Failed to fetch"
```

### The Problem:

Backend requires **external services** to run:
- PostgreSQL (database)
- Redis (cache)

These aren't started, so backend can't start.

---

## How Registration Works

### Normal Flow (When Backend Running):

```
1. User fills register form
   email: "alex@example.com"
   password: "SecurePass123"
   name: "Alex Chen"

2. JavaScript calls frontend function:
   register(email, password, name)

3. Frontend API client sends:
   POST http://localhost:8000/api/v1/auth/register
   Content-Type: application/json
   {
     "email": "alex@example.com",
     "password": "SecurePass123",
     "full_name": "Alex Chen"
   }

4. Backend receives request:
   ✓ Validates email format
   ✓ Hashes password
   ✓ Stores in database (PostgreSQL)
   ✓ Creates workspace automatically
   ✓ Returns user data + org_id

5. Frontend receives response:
   ✓ Saves tokens to localStorage
   ✓ Redirects to /dashboard
   ✓ ✅ SUCCESS!
```

### Broken Flow (Current - Backend Not Running):

```
1. User fills register form

2. JavaScript calls:
   register(email, password, name)

3. Frontend API client tries:
   POST http://localhost:8000/api/v1/auth/register
   
   ❌ Connection Refused!
   Browser can't reach port 8000
   (Backend not listening)

4. JavaScript fetch() fails:
   Error: "Failed to fetch"

5. Frontend catch block:
   Shows error message
   ❌ FAIL!
```

---

## Why Backend Isn't Running

### The Backend Stack:

```
Backend (FastAPI)
├─ Depends on: PostgreSQL (database)
├─ Depends on: Redis (cache)
├─ Requires: .env configuration
├─ Requires: Database migrations
└─ Requires: Manual startup (not automatic)

Frontend (Next.js)
├─ No external dependencies
├─ Can run standalone
├─ Auto-started ✅
```

### What You See:

```
$ npm run dev

# Starts frontend only
# Backend requires separate setup:
# - Install dependencies
# - Start PostgreSQL
# - Start Redis  
# - Run migrations
# - Start backend manually
```

---

## The Solution

Backend just needs to be started. Your code is already fixed.

### Step 1: Choose Setup Method

**Option A: Docker (Easiest)**
- Start: `docker compose up -d`
- Time: 1 minute
- Requirements: Docker installed

**Option B: Local macOS**
- Start: `brew services start postgresql && brew services start redis`
- Setup: 10 minutes
- Requirements: Homebrew, PostgreSQL, Redis

**Option C: Local Linux**
- Start: `systemctl start postgresql && systemctl start redis-server`
- Setup: 10 minutes  
- Requirements: Ubuntu/Debian, PostgreSQL, Redis

### Step 2: Start Backend

After prerequisites are installed:

```bash
cd /vercel/share/v0-project/server

# Install dependencies
uv sync

# Run migrations (sets up database schema)
uv run alembic upgrade head

# Start backend server
uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Test

```bash
# Backend should respond
curl http://localhost:8000/

# Should NOT say:
# curl: (7) Failed to connect to localhost port 8000: Connection refused

# Frontend should work
http://localhost:3000/register

# Register should work
# ✅ No more "Failed to fetch"!
```

---

## Detailed Setup Instructions

### Docker Setup (Recommended)

**Check if Docker installed:**
```bash
docker --version
docker compose --version
```

**If not installed:**
- macOS: `brew install docker-desktop`
- Linux: `sudo apt-get install docker.io docker-compose`
- Windows: Download Docker Desktop

**Run it:**
```bash
cd /vercel/share/v0-project
docker compose up -d

# Wait 30 seconds for containers to start
# Check: docker compose ps
# Should show 3 containers running (postgres, redis, backend)
```

**Test it:**
```bash
# Backend should respond
curl http://localhost:8000/
```

---

### macOS Local Setup

**Install dependencies:**
```bash
brew install postgresql redis python@3.12
```

**Start services:**
```bash
# Terminal stays open, services run in background
brew services start postgresql
brew services start redis

# Verify they're running
brew services list
```

**Setup backend:**
```bash
cd /vercel/share/v0-project/server

# Copy config
cp .env.example .env

# Install Python dependencies
uv sync

# Create database schema
uv run alembic upgrade head
```

**Start backend (Terminal A):**
```bash
cd /vercel/share/v0-project/server
uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start frontend (Terminal B):**
```bash
cd /vercel/share/v0-project/client
npm run dev
```

**Test:**
```bash
# In Terminal C
curl http://localhost:8000/
# Should respond

http://localhost:3000/register
# Should load and work!
```

---

### Linux Setup

Same as macOS, but:

```bash
# Instead of brew:
sudo apt-get install postgresql redis-server python3.12

# Instead of brew services:
sudo systemctl start postgresql
sudo systemctl start redis-server

# Rest is identical
```

---

## How to Know It's Working

### Before (Backend Not Running):

```
$ curl http://localhost:8000/
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

### After (Backend Running):

```
$ curl http://localhost:8000/
[HTML page or JSON response - something came back!]
```

### Frontend Test:

**Before:** `http://localhost:3000/register` → "Failed to fetch"

**After:** `http://localhost:3000/register` → Works, can create account

---

## Verify Code Changes Are Working

Once backend is running:

### Test 1: Account Creation Works
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"TestPass123",
    "full_name":"Test User"
  }'

# Response:
# {"id": "UUID", "email": "test@example.com", "full_name": "Test User", "is_active": true}
```

### Test 2: P0 #1 - Unauthenticated Quick Scan
```bash
# No Authorization header
curl -X POST http://localhost:8000/api/v1/quick-scan \
  -H "Content-Type: application/json" \
  -d '{
    "target":"example.com",
    "target_type":"domain",
    "scan_type":"default",
    "skip_verification":true
  }'

# Response includes org_id:
# {"scan_job_id": "UUID", "org_id": "UUID", "status": "pending"}
# ✅ Anonymous user created, scan started!
```

### Test 3: P0 #2 - org_id in Response
```bash
# Check response above - org_id is there!
# {"scan_job_id": "...", "org_id": "...", "status": "..."}
# ✅ org_id successfully included!
```

---

## Troubleshooting

### Error: "Failed to fetch" Still Showing?

```bash
# Check backend is running
curl http://localhost:8000/

# If "Connection refused":
# ❌ Backend not started
# Fix: Go back to setup section, start backend

# If you get a response:
# ✅ Backend running
# Problem might be frontend-specific
# Check DevTools Network tab for actual error
```

### Error: "Cannot connect to database"

```bash
# PostgreSQL not running
# Fix for macOS:
brew services start postgresql

# Fix for Linux:
sudo systemctl start postgresql

# Verify:
psql -U postgres -c "SELECT 1;"
# Should print: 1
```

### Error: "Redis connection refused"

```bash
# Redis not running
# Fix for macOS:
brew services start redis

# Fix for Linux:
sudo systemctl start redis-server

# Verify:
redis-cli ping
# Should print: PONG
```

### Error: "Database does not exist"

```bash
# Migrations didn't run
# Fix:
cd /vercel/share/v0-project/server
uv run alembic upgrade head

# Verify:
psql -U postgres -d appsec -c "SELECT COUNT(*) FROM users;"
```

### Error: "Database migrations failed"

```bash
# Database might be corrupted
# Fix (WARNING: DELETES ALL DATA):
dropdb -U postgres appsec
createdb -U postgres appsec
uv run alembic upgrade head
```

---

## Summary

| State | Symptom | Fix |
|-------|---------|-----|
| Backend not running | "Failed to fetch" on register | Start backend (see setup) |
| PostgreSQL not running | "Database connection refused" | `brew/systemctl start postgresql` |
| Redis not running | "Redis connection refused" | `brew/systemctl start redis-server` |
| Migrations not run | "Database does not exist" | `uv run alembic upgrade head` |
| All running | Everything works ✅ | Test account creation |

---

## Next Steps

1. **Pick a setup method:** Docker (easiest) or Local
2. **Follow the setup instructions** for your method
3. **Verify backend is running:** `curl http://localhost:8000/`
4. **Test account creation:** `http://localhost:3000/register`
5. **Test P0 fixes:** Quick scan without login, org_id stored

Your code is already fixed. Backend just needs to run!
