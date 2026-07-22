# System Architecture Diagram

## High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL USERS                                     │
└─────────────────────┬──────────────────────────────────────────┬────────────┘
                      │                                          │
                      │ HTTP/HTTPS                               │
                      │                                          │
        ┌─────────────▼───────────────────┐        ┌────────────▼──────────────┐
        │   FRONTEND (Next.js 16)         │        │  BACKEND (FastAPI)        │
        │   http://localhost:3000        │        │  http://localhost:8000    │
        │                                │        │                           │
        │  ┌────────────────────────────┐│        │ ┌──────────────────────┐  │
        │  │  Pages (React Components) ││        │ │ API Router (v1)      │  │
        │  │ ├─ /                       ││        │ ├─ /auth              │  │
        │  │ ├─ /login                 ││        │ ├─ /users             │  │
        │  │ ├─ /register              ││        │ ├─ /organizations     │  │
        │  │ ├─ /dashboard             ││        │ ├─ /quick-scan        │  │
        │  │ └─ /scan/[id]             ││        │ ├─ /scan-jobs         │  │
        │  └────────────────────────────┘│        │ ├─ /domains           │  │
        │                                │        │ ├─ /scan-results      │  │
        │  ┌────────────────────────────┐│        │ ├─ /reports           │  │
        │  │ API Client (lib/api.ts)    ││        │ └─ /notifications     │  │
        │  │ ├─ login()                 ││        │                       │  │
        │  │ ├─ register()              ││        │ ┌──────────────────────┐  │
        │  │ ├─ quickScan()             ││◄──────►│ │ Middleware/Auth      │  │
        │  │ ├─ getScanJob()            ││        │ ├─ JWT Validation     │  │
        │  │ ├─ getScanResults()        ││        │ ├─ CORS               │  │
        │  │ └─ getMe()                 ││        │ ├─ Error Handlers     │  │
        │  └────────────────────────────┘│        │ └─ Logging            │  │
        │                                │        │                       │  │
        │  ┌────────────────────────────┐│        │ ┌──────────────────────┐  │
        │  │ LocalStorage               ││        │ │ Services Layer       │  │
        │  │ ├─ entropy-auth            ││        │ ├─ AuthService        │  │
        │  │ │  (access+refresh tokens) ││        │ ├─ QuickScanService   │  │
        │  │ └─ entropy-org-id          ││        │ ├─ ScanJobService     │  │
        │  └────────────────────────────┘│        │ └─ (+ 8 more)         │  │
        │                                │        │                       │  │
        │  ┌────────────────────────────┐│        │ ┌──────────────────────┐  │
        │  │ UI Components              ││        │ │ Repository Layer     │  │
        │  │ ├─ Navbar                  ││        │ ├─ UserRepository     │  │
        │  │ ├─ Button                  ││        │ ├─ OrgRepository      │  │
        │  │ ├─ Input                   ││        │ ├─ ScanJobRepository  │  │
        │  │ ├─ ScanRow                 ││        │ ├─ DomainRepository   │  │
        │  │ └─ SeverityBadge           ││        │ └─ (+ 5 more)         │  │
        │  └────────────────────────────┘│        │                       │  │
        │                                │        │ ┌──────────────────────┐  │
        │  Styling: Tailwind CSS 4       │        │ │ SQLAlchemy ORM       │  │
        │  Runtime: React 19             │        │ │ (Async)              │  │
        │                                │        │ └──────────────────────┘  │
        └────────────────────────────────┘        │                           │
                                                   │ ┌──────────────────────┐  │
                                                   │ │ PostgreSQL Database  │  │
                                                   │ │ (Port 5432)          │  │
                                                   │ └──────────────────────┘  │
                                                   │                           │
                                                   │ ┌──────────────────────┐  │
                                                   │ │ Redis Cache          │  │
                                                   │ │ (Token Blacklist)    │  │
                                                   │ │ (Port 6379)          │  │
                                                   │ └──────────────────────┘  │
                                                   │                           │
        ┌──────────────────────────────────────────┤ Framework: FastAPI       │
        │ Environment:                             │ Runtime: Python 3.11+    │
        │ - NEXT_PUBLIC_API_URL=...               │ Async: AsyncIO           │
        │   (Backend endpoint)                     │                           │
        └──────────────────────────────────────────┴───────────────────────────┘
```

---

## Authentication Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION FLOW                          │
└────────────────────────────────────────────────────────────────────┘

[New User]
    │
    ├─→ /register (form)
    │       │
    │       ├─ Fills: email, password, fullName
    │       │
    │       └─→ POST /api/v1/auth/register
    │           ├─ Backend validates email, hashes password
    │           ├─ Creates user in database
    │           └─ Returns: { id, email, full_name, is_active }
    │
    ├─→ Auto-login: POST /api/v1/auth/login
    │       │
    │       └─ Returns: { access_token, refresh_token, token_type }
    │
    ├─→ localStorage.setItem('entropy-auth', tokens)
    │
    └─→ Redirect to /dashboard ✅

[Existing User]
    │
    ├─→ /login (form)
    │       │
    │       └─→ POST /api/v1/auth/login
    │           ├─ Backend validates credentials
    │           └─ Returns: { access_token, refresh_token, token_type }
    │
    ├─→ localStorage.setItem('entropy-auth', tokens)
    │
    └─→ Redirect to /dashboard or ?next param ✅

[Protected Route Access]
    │
    ├─→ useEffect checks: getAuthToken() != null
    │       │
    │       ├─ Yes: Proceed to page
    │       │
    │       └─ No: Redirect to /login?next={current_path}
    │
    ├─→ GET /api/v1/users/me
    │       ├─ Header: Authorization: Bearer {accessToken}
    │       ├─ Backend validates JWT
    │       └─ Returns user info or 401 Unauthorized
    │
    └─→ If valid: load page data ✅
        If invalid: redirect to /login

[Logout - NOT IMPLEMENTED]
    │
    ├─→ (No logout button in UI)
    │
    ├─→ Manual: localStorage.removeItem('entropy-auth')
    │
    └─→ Backend: POST /api/v1/auth/logout (never called)
        ├─ Adds refresh_token to Redis blacklist
        └─ Next refresh attempt fails

[Token Expiration - NOT HANDLED]
    │
    ├─→ Access token expires (default: 15 min)
    │
    ├─→ Frontend makes request without token refresh
    │
    ├─→ Backend returns 401 Unauthorized
    │
    └─→ Frontend shows error (should call refresh first!)
        POST /api/v1/auth/refresh
        ├─ Header: { refresh_token }
        └─ Returns: { access_token, refresh_token, token_type }
```

---

## Data Flow: Quick Scan Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│              QUICK SCAN FLOW (Current Implementation)             │
└──────────────────────────────────────────────────────────────────┘

LANDING PAGE FLOW (Unauthenticated) - 🔴 BROKEN
═════════════════════════════════════════════════

User: domain.com
    ↓
[Frontend] page.tsx
    │
    ├─ domain = "domain.com"
    │
    ├─ POST /api/v1/quick-scan {
    │   target: "domain.com",
    │   target_type: "domain",
    │   scan_type: "default",
    │   skip_verification: true
    │  }
    │
    ├─ NO Authorization header sent ❌
    │
    └─→ [Backend] quick_scan.py
        ├─ Requires: @Depends(CurrentUserIdDep)
        ├─ But request has no Bearer token
        └─ Returns: 401 Unauthorized ❌

Error: "Unable to start scanning"
    ↓
[No redirect] ❌


AUTHENTICATED FLOW (After Login) - ✅ WORKING
═══════════════════════════════════════════════

User login → dashboard
    ↓
[Frontend] dashboard/page.tsx
    │
    ├─ domain = "domain.com"
    │
    ├─ POST /api/v1/quick-scan {
    │   target: "domain.com",
    │   target_type: "domain",
    │   scan_type: "default",
    │   skip_verification: true
    │  }
    │
    ├─ Authorization: Bearer {accessToken} ✅
    │
    └─→ [Backend] quick_scan.py
        ├─ Validates JWT token ✅
        ├─ Extracts user_id from token
        ├─ Gets org_id from localStorage or first org
        ├─ Creates organization (if needed)
        ├─ Creates project (if needed)
        ├─ Creates domain record
        ├─ Creates scan job with status="pending"
        └─ Returns: { scan_job_id, status } ✅

Response: { scan_job_id: "abc-123", status: "pending" }
    ↓
[Frontend] Redirects to /scan/abc-123
    │
    ├─ useEffect checks: getAuthToken() ✅
    ├─ useEffect gets: getActiveOrgId() 
    │   (May be NULL if from landing page!) ❌
    │
    ├─ If orgId is null:
    │   └─ router.replace("/dashboard") ❌
    │       (Results never displayed!)
    │
    └─→ If orgId exists:
        │
        ├─ Promise.all([
        │   GET /api/v1/scan-jobs/abc-123
        │   GET /api/v1/domains/{domainId}
        │   GET /api/v1/scan-jobs/abc-123/results
        │  ])
        │
        ├─ Headers: 
        │   Authorization: Bearer {token} ✅
        │   X-Organization-ID: {orgId} ✅
        │
        └─→ [Backend] Validates and returns data
            │
            ├─ scan_jobs.py returns ScanJobResponse
            ├─ domains.py returns DomainResponse (or error)
            └─ scan_results.py returns ScanResultResponse[]

[Frontend] Displays Results
    │
    ├─ Status: pending/running → Poll every 5s
    │  (setInterval → load() every 5000ms)
    │
    ├─ Status: completed → Stop polling
    │  (Check: job?.status === "running" || "pending")
    │
    ├─ Render findings with severity badges
    ├─ Display AI summary from scan
    └─ Show screenshot if available ✅
```

---

## Database Schema Relationships

```
┌─────────────────┐
│     Users       │
├─────────────────┤
│ id (UUID, PK)   │
│ email (str)     │ ◄──────────┐
│ password_hash   │            │
│ full_name       │            │ 1:N (one user, many orgs)
│ is_active       │            │
│ created_at      │            │
└─────────────────┘            │
                               │
                               │
                    ┌──────────────────────┐
                    │   Organizations      │
                    ├──────────────────────┤
                    │ id (UUID, PK)        │
                    │ user_id (FK) ────────┤ (created_by)
                    │ name (str)           │
                    │ slug (str)           │
                    │ created_at           │
                    └──────────────────────┘
                               ▲
                               │ 1:N
                               │
                               │
                    ┌──────────────────────┐
                    │     Projects         │
                    ├──────────────────────┤
                    │ id (UUID, PK)        │
                    │ organization_id (FK) │
                    │ name (str)           │
                    │ created_at           │
                    └──────────────────────┘
                               ▲
                               │ 1:N
                               │
                               │
┌──────────────────┐           │
│    Domains       │◄──────────┤
├──────────────────┤           │
│ id (UUID, PK)    │           │ (all domains in project)
│ project_id (FK)  │──────────►│
│ hostname (str)   │           │
│ verification     │           │
│ created_at       │           │
└──────────────────┘
        ▲
        │ 1:N
        │
        │
┌──────────────────┐
│    ScanJobs      │
├──────────────────┤
│ id (UUID, PK)    │
│ domain_id (FK)   │ ────────► Links to domain
│ organization_id  │ ────────► Links to org
│ status (enum)    │
│ scan_type (str)  │
│ created_by (FK)  │ ────────► Links to user
│ created_at       │
│ started_at       │
│ completed_at     │
└──────────────────┘
        ▲
        │ 1:N
        │
        │
┌──────────────────┐
│  ScanResults     │
├──────────────────┤
│ id (UUID, PK)    │
│ scan_job_id (FK) │
│ summary (JSON)   │ ◄─── Findings, AI summary, etc.
│ severity_counts  │ ◄─── { critical: 2, high: 5, ... }
│ created_at       │
└──────────────────┘

```

---

## Request/Response Cycle Example

### Example: Quick Scan Endpoint

```
REQUEST (Frontend → Backend):
═══════════════════════════════

POST /api/v1/quick-scan HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "target": "example.com",
  "target_type": "domain",
  "scan_type": "default",
  "skip_verification": true
}


BACKEND PROCESSING:
═════════════════════════════════════════════════════

1. FastAPI receives request → router.py

2. Middleware runs:
   ├─ CORS check
   ├─ Request logging
   └─ Error handling setup

3. Dependency injection resolves:
   ├─ JWT token validation → get_current_user_id()
   │  ├─ Decodes JWT
   │  ├─ Validates signature
   │  ├─ Checks token type
   │  └─ Checks Redis blacklist
   │  Result: user_id = UUID("...")
   │
   ├─ Quick scan service injection
   │  ├─ Organization service
   │  ├─ Project service
   │  ├─ Domain service
   │  ├─ Scan job service
   │  └─ All repositories
   │
   └─ Database session injected

4. Handler executes: quick_scan()
   ├─ QuickScanService.run()
   │  ├─ Get user's org (from DB)
   │  ├─ Create project if needed
   │  ├─ Create domain record
   │  │  ├─ INSERT into domains table
   │  │  └─ Commit to PostgreSQL
   │  ├─ Create scan job
   │  │  ├─ INSERT into scan_jobs table
   │  │  ├─ Set status = "pending"
   │  │  └─ Commit to PostgreSQL
   │  └─ Return scan job object
   │
   ├─ Handler converts to response model
   │  └─ QuickScanResponse(
   │      scan_job_id="...",
   │      status="pending"
   │     )
   │
   └─ Status code 201 Created


RESPONSE (Backend → Frontend):
═════════════════════════════════════

HTTP/1.1 201 Created
Content-Type: application/json
X-Process-Time: 0.234

{
  "scan_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}


FRONTEND HANDLING:
═════════════════════════════════════════════════════

1. Response received by api.ts request()
   ├─ Check response.ok (201 is OK)
   ├─ Parse JSON
   └─ Return as Promise<QuickScanResponse>

2. page.tsx receives response
   ├─ Extract scan_job_id
   ├─ Call: window.location.assign(`/scan/${scan_job_id}`)
   └─ Browser navigates to /scan/550e8400-e29b-41d4-a716-446655440000

3. [id]/page.tsx mounts
   ├─ useEffect runs
   ├─ Checks auth token
   ├─ Gets org ID (PROBLEM: may be null!)
   ├─ Fetches scan job data
   ├─ Fetches scan results
   └─ Displays findings

```

---

## Error Handling Flow

```
┌────────────────────────────────────────────────────────┐
│              ERROR HANDLING (Current)                  │
└────────────────────────────────────────────────────────┘

FRONTEND ERROR SOURCES:
═════════════════════════════════════════════════════

1. Network Error
   ├─ fetch() throws (offline, timeout, etc.)
   ├─ Caught in try/catch
   └─ Shows: err.message || "Unable to..."

2. API Error Response
   ├─ Backend returns non-2xx status
   ├─ request() reads response.json()
   ├─ Extracts error from: response.detail or [0].msg
   └─ Throws new Error(detail)

3. Invalid Token
   ├─ Backend returns 401 Unauthorized
   └─ Frontend shows: "Unauthorized"
      (Should: refresh token and retry)

4. Missing Org Header
   ├─ Backend returns 403 Forbidden
   └─ Frontend shows: "X-Organization-ID header is required"

5. Invalid Domain ID
   ├─ Backend returns 404 Not Found
   └─ Frontend shows: "Not found"
      (Should: handle gracefully)


BACKEND ERROR HANDLING:
═════════════════════════════════════════════════════

1. Validation Error
   ├─ Request body invalid
   ├─ FastAPI validation fails
   └─ Returns: 422 Unprocessable Entity
      {
        "detail": [{
          "loc": ["body", "target"],
          "msg": "field required",
          "type": "value_error.missing"
        }]
      }

2. Authentication Error
   ├─ Missing/invalid Bearer token
   └─ Returns: 401 Unauthorized
      { "detail": "Missing bearer token" }

3. Authorization Error
   ├─ Wrong organization ID
   ├─ User lacks permissions
   └─ Returns: 403 Forbidden
      { "detail": "X-Organization-ID header is required" }

4. Business Logic Error
   ├─ Resource not found
   ├─ Invalid state transition
   └─ Returns: 404 Not Found or 400 Bad Request

5. Server Error
   ├─ Unhandled exception
   └─ Returns: 500 Internal Server Error
      (logged to server)


RECOMMENDED ERROR FLOW:
═════════════════════════════════════════════════════

Request → Check Response Status
    │
    ├─ 401: Check token expiration
    │  ├─ If expired: Call refresh()
    │  ├─ Retry request with new token
    │  └─ If refresh fails: Redirect to login
    │
    ├─ 403: Check if org header missing
    │  └─ Redirect to dashboard (get fresh org)
    │
    ├─ 4xx: Show user-friendly error
    │  └─ Log to error tracking
    │
    ├─ 5xx: Retry with exponential backoff
    │  └─ Eventually show: "Server unavailable"
    │
    └─ Network error: Retry with backoff

```

---

## Summary: What Works vs. What's Broken

```
┌─────────────────────────────────────────────────────────────────┐
│                     INTEGRATION STATUS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ WORKING                                                     │
│  ├─ User registration & login                                  │
│  ├─ JWT token management & validation                          │
│  ├─ Authenticated dashboard                                    │
│  ├─ Scan history display                                       │
│  ├─ Scan results polling (after login)                         │
│  ├─ Findings & severity display                                │
│  └─ Organization switching                                     │
│                                                                 │
│  ❌ BROKEN                                                      │
│  ├─ Unauthenticated quick scan (landing page)                  │
│  ├─ Org ID handling after unauthenticated scan                 │
│  ├─ Token refresh on expiration                                │
│  ├─ Logout button                                              │
│  └─ Error recovery on network failures                         │
│                                                                 │
│  ⚠️  PARTIALLY WORKING / RISKY                                 │
│  ├─ Domain info endpoint (sometimes gets empty ID)             │
│  ├─ Polling strategy (no backoff, may spam server)             │
│  ├─ CORS configuration (not verified)                          │
│  └─ Error messages (raw API errors shown to users)             │
│                                                                 │
│  📋 NOT IMPLEMENTED / NOT USED                                 │
│  ├─ Logout endpoint (exists, no UI)                            │
│  ├─ Token refresh endpoint (exists, never called)              │
│  ├─ Cancel scan endpoint (exists, no UI)                       │
│  ├─ Project management (backend only)                          │
│  ├─ Report generation (backend only)                           │
│  ├─ Notifications system (backend only)                        │
│  └─ Error boundary in React                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

