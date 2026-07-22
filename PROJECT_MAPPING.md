# Antropy.dev - Frontend & Backend Architecture Map

## Project Overview
This is a full-stack security scanning application with a Next.js 16 frontend and Python FastAPI backend. The system allows users to register, authenticate, and run security scans on domains.

---

## 📋 Frontend Architecture

### Tech Stack
- **Framework**: Next.js 16.2.11 (App Router)
- **Runtime**: React 19.2.4
- **Styling**: Tailwind CSS 4
- **API Client**: Custom fetch-based HTTP client with localStorage for auth
- **State Management**: React hooks + localStorage for auth tokens and org ID

### Directory Structure
```
client/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Homepage (landing/quick scan)
│   │   ├── login/page.tsx          # Login page
│   │   ├── register/page.tsx       # Registration page
│   │   ├── dashboard/page.tsx      # Authenticated dashboard (scan history)
│   │   └── scan/[id]/page.tsx      # Scan detail/results page
│   ├── components/
│   │   └── entropy-ui.tsx          # Shared UI components (Navbar, Button, Input, ScanRow, etc.)
│   └── lib/
│       └── api.ts                  # API client & auth helpers
├── public/                         # Static assets
└── package.json
```

### Frontend Pages & Features

#### 1. **Landing Page** (`/`)
- **File**: `src/app/page.tsx`
- **Purpose**: Public homepage showing product features
- **UI Components**: Navbar, Input, Button
- **Key Functions**:
  - Display features overview
  - Quick scan form (unauthenticated)
  - `quickScan()` API call → redirects to `/scan/[id]`
- **Auth Required**: NO
- **Storage Used**: None (unauthenticated scan)

#### 2. **Register Page** (`/register`)
- **File**: `src/app/register/page.tsx`
- **Purpose**: User account creation
- **UI Components**: Navbar, Input, Button
- **Key Functions**:
  - `register(email, password, fullName)` → creates user
  - `login(email, password)` → auto-login after registration
  - `saveAuth()` → stores tokens in localStorage
  - Redirects to `/dashboard` on success
- **Auth Required**: NO
- **Storage Used**: localStorage (`entropy-auth` - auth tokens)

#### 3. **Login Page** (`/login`)
- **File**: `src/app/login/page.tsx`
- **Purpose**: User authentication
- **UI Components**: Navbar, Input, Button
- **Key Functions**:
  - `login(email, password)` → authenticates user
  - `saveAuth()` → stores tokens
  - Optional redirect via `?next` query param
- **Auth Required**: NO
- **Storage Used**: localStorage (`entropy-auth`)

#### 4. **Dashboard Page** (`/dashboard`)
- **File**: `src/app/dashboard/page.tsx`
- **Purpose**: Authenticated workspace showing scan history
- **UI Components**: Navbar, Input, Button, ScanRow
- **Key Functions**:
  - Auth check: redirects to `/login?next=/dashboard` if not authenticated
  - `getMe()` → validates current user
  - `getOrganizations()` → fetches user's orgs
  - `listScanJobs(orgId)` → fetches scan history
  - `quickScan(domain)` → initiates new scan
  - `setActiveOrgId()` → stores selected org in localStorage
- **Auth Required**: YES
- **Storage Used**: localStorage (`entropy-auth`, `entropy-org-id`)
- **Error Handling**: Clears auth and redirects to login on auth failure

#### 5. **Scan Detail Page** (`/scan/[id]`)
- **File**: `src/app/scan/[id]/page.tsx`
- **Purpose**: View scan results and findings
- **UI Components**: Navbar, Button, SeverityBadge
- **Key Functions**:
  - Auth check: redirects to `/login?next=/scan/[id]` if not authenticated
  - `getScanJob(scanJobId, orgId)` → fetches scan status
  - `getDomain(domainId, orgId)` → fetches domain info
  - `getScanResults(scanJobId, orgId)` → fetches scan findings
  - Auto-refresh every 5s if scan is `pending` or `running`
  - Renders findings with severity badges
  - Displays screenshot if available
  - AI summary from results
- **Auth Required**: YES
- **Storage Used**: localStorage (`entropy-auth`, `entropy-org-id`)
- **Polling**: 5-second intervals for incomplete scans

### API Client (`src/lib/api.ts`)

#### Configuration
```typescript
DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
```

#### Authentication Helpers
- `saveAuth(tokens)` → Store auth tokens in localStorage
- `clearAuth()` → Remove auth tokens
- `getAuthToken()` → Get access token
- `getActiveOrgId()` → Get selected organization ID
- `setActiveOrgId(orgId)` → Save selected organization

#### Core Request Function
```typescript
async request<T>(path, init, requireAuth = true): Promise<T>
```
- Adds `Content-Type: application/json` header
- Auto-includes `Authorization: Bearer {token}` if authenticated
- Throws descriptive errors from API responses
- Handles 204 No Content responses

#### API Endpoints Called

| Method | Endpoint | Purpose | Auth | Org Header |
|--------|----------|---------|------|-----------|
| POST | `/api/v1/auth/register` | Register new user | NO | NO |
| POST | `/api/v1/auth/login` | User login | NO | NO |
| GET | `/api/v1/users/me` | Get current user | YES | NO |
| GET | `/api/v1/organizations` | List user's organizations | YES | NO |
| POST | `/api/v1/quick-scan` | Start quick scan | YES | NO |
| GET | `/api/v1/scan-jobs/{id}` | Get scan status | YES | YES |
| GET | `/api/v1/scan-jobs` | List scans | YES | YES |
| GET | `/api/v1/domains/{id}` | Get domain info | YES | YES |
| GET | `/api/v1/scan-jobs/{id}/results` | Get scan findings | YES | YES |

### UI Components (`src/components/entropy-ui.tsx`)
- **Navbar**: Top navigation bar with branding
- **Button**: Styled button with loading state
- **Input**: Text input field
- **ScanRow**: Table row for scan history
- **SeverityBadge**: Color-coded severity indicator

### Environment Variables
```
NEXT_PUBLIC_API_URL = http://localhost:8000  # Backend API URL
```

---

## 🔌 Backend Architecture

### Tech Stack
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis (for token blacklist)
- **Auth**: JWT tokens (access + refresh)
- **Async**: AsyncIO throughout

### Directory Structure
```
server/
├── src/appsec/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py            # Auth endpoints (register, login, refresh, logout)
│   │   │   ├── users.py           # User info endpoints
│   │   │   ├── organizations.py   # Org management
│   │   │   ├── projects.py        # Project management
│   │   │   ├── domains.py         # Domain management
│   │   │   ├── quick_scan.py      # Quick scan endpoint
│   │   │   ├── scan_jobs.py       # Scan job management
│   │   │   ├── scan_results.py    # Scan results retrieval
│   │   │   ├── reports.py         # Report generation
│   │   │   ├── notifications.py   # Notifications
│   │   │   ├── health.py          # Health check
│   │   │   └── router.py          # Main router (includes all endpoints)
│   │   ├── deps.py                # FastAPI dependencies (auth, services, repos)
│   │   ├── middleware.py          # CORS, error handling
│   │   └── error_handlers.py      # Exception handling
│   ├── application/
│   │   ├── auth/
│   │   │   ├── service.py         # Auth business logic
│   │   │   └── schemas.py         # Request/response models
│   │   ├── users/
│   │   ├── organizations/
│   │   ├── projects/
│   │   ├── domains/
│   │   ├── quick_scan/
│   │   ├── scan_jobs/
│   │   ├── scan_results/
│   │   ├── reports/
│   │   └── notifications/
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py         # Database session management
│   │   │   ├── models.py          # SQLAlchemy models
│   │   │   └── repositories/      # Data access layer
│   │   ├── redis_client.py        # Redis connection
│   │   └── security/
│   │       ├── jwt.py             # JWT token handling
│   │       └── redis_blacklist.py # Token revocation
│   └── domain/
│       └── exceptions.py          # Custom exceptions
├── tests/
├── alembic/                       # Database migrations
└── docker-compose.yml             # Local development stack
```

### Backend API Endpoints

#### Authentication (`/api/v1/auth`)
```
POST /api/v1/auth/register
  Request: { email, password, full_name? }
  Response: { id, email, full_name, is_active }
  
POST /api/v1/auth/login
  Request: { email, password }
  Response: { access_token, refresh_token, token_type }
  
POST /api/v1/auth/refresh
  Request: { refresh_token }
  Response: { access_token, refresh_token, token_type }
  
POST /api/v1/auth/logout
  Request: { refresh_token }
  Response: 204 No Content
```

#### Users (`/api/v1/users`)
```
GET /api/v1/users/me
  Headers: Authorization: Bearer {token}
  Response: { id, email, full_name, is_active }
```

#### Organizations (`/api/v1/organizations`)
```
GET /api/v1/organizations
  Headers: Authorization: Bearer {token}
  Response: [{ id, name, slug, created_at }]
```

#### Quick Scan (`/api/v1/quick-scan`)
```
POST /api/v1/quick-scan
  Headers: Authorization: Bearer {token}
  Request: {
    target,                    # e.g., "example.com"
    target_type,              # "domain"
    scan_type,                # "default"
    skip_verification         # boolean
  }
  Response: { scan_job_id, status }
  Status Code: 201 Created
```

#### Scan Jobs (`/api/v1/scan-jobs`)
```
GET /api/v1/scan-jobs/{scan_job_id}
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Response: {
    id, domain_id, project_id, organization_id,
    status, scan_type, created_by,
    created_at, started_at, completed_at
  }

GET /api/v1/scan-jobs
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Response: [{ ... same fields ... }]

POST /api/v1/scan-jobs/{scan_job_id}/cancel
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Response: { ... same fields ... }

POST /api/v1/projects/{project_id}/scan-jobs
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Request: { domain_id, scan_type }
  Response: { ... same fields ... }
  Status Code: 201 Created
```

#### Scan Results (`/api/v1/scan-jobs/{scan_job_id}/results`)
```
GET /api/v1/scan-jobs/{scan_job_id}/results
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Response: [{
    id, scan_job_id, organization_id,
    summary: Record<string, unknown>,  # Contains findings, ai_summary, etc.
    severity_counts: Record<string, number>,
    created_at
  }]
```

#### Domains (`/api/v1/domains/{domain_id}`)
```
GET /api/v1/domains/{domain_id}
  Headers: 
    Authorization: Bearer {token}
    X-Organization-ID: {orgId}
  Response: { id, hostname, verification_status }
```

#### Other Endpoints
- **Projects** - Project management
- **Reports** - Report generation
- **Notifications** - User notifications
- **Health** - Health check `/api/v1/health`

### Authentication Flow

#### How JWT Works
1. User registers/logs in → backend generates access + refresh tokens
2. Frontend stores tokens in localStorage
3. Frontend sends access token in `Authorization: Bearer {token}` header
4. Backend validates token using JWT signature
5. Token blacklist (Redis) tracks revoked tokens (for logout)

#### Token Claims
- `sub`: User ID (UUID)
- `type`: Token type ("access" or "refresh")
- `jti`: JWT ID for revocation tracking

#### Required Headers for Authenticated Endpoints
- `Authorization: Bearer {accessToken}` - Always required for protected routes
- `X-Organization-ID: {orgId}` - Required for org-scoped resources (scan jobs, results, domains)

### Dependency Injection (deps.py)

The backend uses FastAPI's dependency injection to wire services, repositories, and middleware:

```
Request → Authentication → User ID Extraction
       ↓
Organization ID from Header
       ↓
Service Layer (business logic)
       ↓
Repository Layer (data access)
       ↓
SQLAlchemy Session → PostgreSQL
```

### Database Schema Overview

**Key Entities**:
- **User**: email, password_hash, full_name, is_active
- **Organization**: name, slug, created_at
- **Project**: belongs to org
- **Domain**: hostname, belongs to project
- **ScanJob**: scan request, status, belongs to domain
- **ScanResult**: findings/results of scan, belongs to scan job

---

## 🔄 Frontend-Backend Integration Flow

### Happy Path: Quick Scan → Results

```
[Landing Page]
    ↓ (Enter domain)
    ↓ POST /api/v1/quick-scan (unauthenticated, requires org auto-create)
    ↓
[/scan/[id] page loaded]
    ↓ GET /api/v1/scan-jobs/{id}
    ↓ GET /api/v1/scan-jobs/{id}/results (with org header)
    ↓
[Display findings & summary]
```

### Happy Path: Authenticated Workflow

```
[Register Page]
    ↓ POST /api/v1/auth/register
    ↓ POST /api/v1/auth/login (auto-login)
    ↓ localStorage.setItem('entropy-auth', tokens)
    ↓
[Redirect to /dashboard]
    ↓ GET /api/v1/users/me (verify auth)
    ↓ GET /api/v1/organizations (get org list)
    ↓ localStorage.setItem('entropy-org-id', firstOrgId)
    ↓
[Display scan history]
    ↓ GET /api/v1/scan-jobs?X-Organization-ID={orgId}
    ↓
[User clicks scan]
    ↓ POST /api/v1/quick-scan (with auth token)
    ↓
[Redirect to /scan/[id]]
    ↓ Poll GET /api/v1/scan-jobs/{id}/results every 5s
    ↓
[Display completed results]
```

---

## ⚠️ Integration Issues & Gaps

### Critical Issues Found

1. **Missing Organization Handling in Quick Scan**
   - Frontend calls `quickScan()` on landing page (unauthenticated)
   - Backend requires `CurrentUserIdDep` (authenticated)
   - **Issue**: Unauthenticated users can't start scans on landing page
   - **Fix Needed**: Either require login before scan or create anonymous org

2. **Missing Org ID on Quick Scan Response**
   - Frontend doesn't know which org to use after unauthenticated quick scan
   - When redirecting to `/scan/[id]`, org ID is needed but not stored
   - **Issue**: `getScanJob()` calls fail without org header
   - **Fix Needed**: Quick scan should return org_id, or create logic to fetch it

3. **Incomplete Error Handling**
   - Frontend error messages show raw API errors
   - No retry logic for network failures
   - **Fix Needed**: Add error boundary and retry logic

4. **No Token Refresh Logic**
   - Frontend doesn't handle expired access tokens
   - `refresh_token` exists but never used
   - **Fix Needed**: Implement token refresh interceptor

5. **Missing GET Domain Endpoint**
   - Frontend calls `getDomain(domainId, orgId)` 
   - Backend expects `domain_id` in path but frontend sometimes passes empty string
   - **Issue**: Empty domain ID causes 404s
   - **Fix Needed**: Handle missing domain ID gracefully

6. **Scan Status Polling**
   - Frontend polls every 5s but no exponential backoff
   - Could spam backend if many scans running
   - **Fix Needed**: Implement smart polling or WebSocket

### Minor Issues

- **No logout button** in frontend - user can only clear localStorage
- **CORS not configured** - if frontend/backend on different origins
- **No loading states** during async operations
- **No input validation** for domain names
- **No rate limiting** on quick-scan endpoint

---

## 🔐 Security Considerations

### Current Implementation
- ✅ JWT tokens for stateless auth
- ✅ Token blacklist (Redis) for logout
- ✅ Password hashing (assumed in auth service)
- ✅ Organization-scoped queries (X-Organization-ID header)
- ⚠️ LocalStorage for tokens (vulnerable to XSS, not httpOnly)

### Recommended Improvements
- Use httpOnly, Secure, SameSite cookies instead of localStorage
- Implement CSRF protection
- Add rate limiting on auth endpoints
- Add CORS configuration
- Add request validation & sanitization

---

## 🚀 Environment Setup

### Frontend
```bash
cd client
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Backend
```bash
docker-compose up  # PostgreSQL + Redis
cd server
pip install -r requirements.txt
alembic upgrade head  # Run migrations
uvicorn main:app --reload
```

### Local Development
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger)

---

## 📊 Summary

| Component | Status | Issues |
|-----------|--------|--------|
| Landing Page | ✅ | Unauthenticated quick scan broken |
| Auth (Register/Login) | ✅ | No token refresh |
| Dashboard | ✅ | Org selection not persistent across pages |
| Scan Results | ✅ | Polling inefficient, missing error handling |
| API Client | ⚠️ | Needs retry logic, error handling improvements |
| Backend Auth | ✅ | Proper JWT + blacklist |
| Database Models | ✅ | Proper schema with repos |
| Quick Scan Logic | ⚠️ | Missing org auto-creation for unauthenticated users |

