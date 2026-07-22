# Quick Start - Get Backend Running

## TL;DR - 3 Minute Setup

### If you have Docker installed:

```bash
cd /vercel/share/v0-project
docker compose up -d
```

**Done!** Both frontend and backend are now running.

Test it:
- Frontend: http://localhost:3000/register
- Create account → ✅ Should work!

---

## If you DON'T have Docker:

### macOS Setup:

```bash
# Install dependencies (if not already installed)
brew install postgresql redis

# Start services
brew services start postgresql
brew services start redis

# Create database
createdb -U postgres appsec

# Setup backend
cd /vercel/share/v0-project/server
cp .env.example .env
# Edit .env if needed (should work as-is for local dev)

# Install & run migrations
uv sync
uv run alembic upgrade head

# Start backend in one terminal
uv run uvicorn appsec.api.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend in another terminal
cd /vercel/share/v0-project/client
npm run dev
```

### Linux (Ubuntu/Debian) Setup:

```bash
# Install dependencies
sudo apt-get install postgresql redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Rest is same as macOS (from "Create database" step above)
```

---

## Verify It's Working

```bash
# Check backend is running
curl http://localhost:8000/

# Check frontend is running
curl http://localhost:3000/

# Try creating an account via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"TestPass123",
    "full_name":"Test User"
  }'

# Should return: {"id": "...", "email": "test@example.com", ...}
```

---

## Test the P0 Fixes

Once backend is running:

### 1. Test Account Creation (should work now):
- Go to http://localhost:3000/register
- Fill in email, password, name
- Click "Create account"
- ✅ Should redirect to dashboard

### 2. Test Unauthenticated Quick Scan (P0 #1 fix):
- Go to http://localhost:3000/
- Enter any domain (e.g., "example.com")
- Click "Start Scan" (no login needed!)
- ✅ Should start scanning and show results

### 3. Verify org_id is stored (P0 #2 fix):
- Open DevTools → Console
- Type: `localStorage.getItem('entropy-org-id')`
- Should show a UUID like: `"12ab34cd-56ef-..."`
- ✅ org_id successfully stored!

---

## Environment Variables Needed

For local development, these are already in `.env.example`:

```
POSTGRES_USER=appsec
POSTGRES_PASSWORD=changeme
POSTGRES_DB=appsec
POSTGRES_HOST=localhost  # Change from 'postgres' if running locally
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://appsec:changeme@localhost:5432/appsec
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=super-secret-change-me-in-prod
```

If you edit them, make sure to:
1. Update `.env` in `/server/`
2. Restart backend (`Ctrl+C` then re-run uvicorn)

---

## Troubleshooting

### "Failed to fetch" on register?
→ Backend not running. See setup above.

### "Database does not exist"?
```bash
createdb -U postgres appsec
```

### "Connection to Redis failed"?
```bash
# Check Redis is running
redis-cli ping
# Should print: PONG

# If not, start it
brew services start redis
```

### Still failing?
→ See full guide: `/vercel/share/v0-project/BACKEND_SETUP_GUIDE.md`

---

## Stop Everything When Done

```bash
# If using Docker:
docker compose down

# If using local services:
brew services stop postgresql  # macOS
brew services stop redis       # macOS
# or
sudo systemctl stop postgresql  # Linux
sudo systemctl stop redis-server  # Linux
```

---

Done! 🎉

All your P0 fixes are ready. Just get the backend running!
