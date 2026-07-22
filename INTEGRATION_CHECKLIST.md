# Frontend-Backend Integration Checklist

## ✅ Working Integrations

### Auth Flow
- [x] User registration endpoint working
- [x] User login endpoint working
- [x] Frontend saves tokens to localStorage
- [x] Frontend includes Authorization header
- [x] Backend validates JWT tokens
- [x] Token refresh endpoint exists (not used)
- [x] Logout endpoint exists with token blacklist

### Scan Flow
- [x] Quick scan endpoint (POST /api/v1/quick-scan)
- [x] Get scan job endpoint (GET /api/v1/scan-jobs/{id})
- [x] List scans endpoint (GET /api/v1/scan-jobs)
- [x] Get scan results endpoint (GET /api/v1/scan-jobs/{id}/results)
- [x] Frontend polls scan status every 5s
- [x] Frontend displays findings with severity

### User Management
- [x] Get current user endpoint (GET /api/v1/users/me)
- [x] Get organizations endpoint (GET /api/v1/organizations)
- [x] Frontend stores active org ID in localStorage
- [x] Frontend passes X-Organization-ID header on org-scoped requests

---

## ❌ **BROKEN/MISSING - CRITICAL**

### 1. **Unauthenticated Quick Scan**
- **Status**: 🔴 BROKEN
- **Location**: `client/src/app/page.tsx` → `quickScan(domain)`
- **Issue**: Landing page calls `quickScan()` without auth, but backend requires `CurrentUserIdDep`
- **Error Message**: User gets "Unable to start scanning" error
- **Root Cause**: Backend endpoint requires Bearer token, but unauthenticated users can't provide one
- **Solution**: 
  - Option A: Redirect unauthenticated users to login
  - Option B: Create anonymous org/user on first scan
  - Option C: Remove X-Organization-ID requirement for quick-scan

### 2. **Missing Org ID After Quick Scan**
- **Status**: 🔴 BROKEN
- **Location**: `client/src/app/page.tsx` → redirects to `/scan/{id}`
- **Issue**: Response only returns `scan_job_id`, not `organization_id`
- **Error**: When navigating to scan page, `getActiveOrgId()` is null → redirect to dashboard
- **Failure Point**: 
  ```typescript
  const orgId = getActiveOrgId();  // null for unauthenticated users!
  if (!orgId) {
    router.replace("/dashboard");  // redirect instead of showing results
  }
  ```
- **Solution**: Store org ID in response OR pass as URL param

### 3. **Missing GET Domain Endpoint**
- **Status**: 🟡 PARTIALLY BROKEN
- **Location**: `client/src/app/scan/[id]/page.tsx` → `getDomain("", orgId)`
- **Issue**: Frontend passes empty string as domain ID
- **Error**: API returns 404 because domain_id is invalid
- **Impact**: Domain hostname not displayed (falls back to scan's `domain_id`)
- **Solution**: Either fix frontend to not call getDomain with empty ID, or handle gracefully

### 4. **No Token Refresh Logic**
- **Status**: 🟡 DEGRADED
- **Location**: `client/src/lib/api.ts` → `request()` function
- **Issue**: When access token expires, frontend doesn't refresh it
- **Behavior**: User gets "Unauthorized" error and must login again
- **Solution**: Add token refresh interceptor in request function

### 5. **No Error Recovery for Scan Polls**
- **Status**: 🟡 DEGRADED
- **Location**: `client/src/app/scan/[id]/page.tsx` → polling logic
- **Issue**: If network fails during poll, no retry or exponential backoff
- **Behavior**: User sees stale results indefinitely
- **Solution**: Add retry logic with exponential backoff

---

## ⚠️ **BROKEN/MISSING - MINOR**

### 6. **No Logout Button**
- **Status**: 🟡 INCOMPLETE
- **Location**: Frontend Navbar component
- **Issue**: No UI button to logout
- **Workaround**: Users manually clear localStorage
- **Solution**: Add logout button that calls `logout()` API

### 7. **CORS Not Configured**
- **Status**: 🟡 POTENTIAL ISSUE
- **Location**: Backend middleware
- **Issue**: If frontend/backend on different origins, requests fail
- **Status**: Check if `middleware.py` handles CORS
- **Solution**: Ensure CORS allows frontend origin

### 8. **No Input Validation**
- **Status**: 🟡 NICE-TO-HAVE
- **Location**: Frontend form inputs
- **Issue**: No validation before sending to API
- **Example**: Domain input accepts any string
- **Solution**: Add basic validation (domain format, email format)

### 9. **Missing Error Boundary**
- **Status**: 🟡 NICE-TO-HAVE
- **Location**: Frontend pages
- **Issue**: Uncaught errors crash the page
- **Solution**: Add React error boundary

### 10. **Inefficient Polling**
- **Status**: 🟡 NICE-TO-HAVE
- **Location**: `client/src/app/scan/[id]/page.tsx`
- **Issue**: Polls every 5s regardless of scan stage
- **Better**: Use exponential backoff or WebSocket

---

## 🔧 Fix Priority

### **MUST FIX (P0)** - Blocks core functionality
1. Unauthenticated quick scan flow
2. Org ID handling after quick scan
3. Token refresh on expiration

### **SHOULD FIX (P1)** - Improves reliability
4. Error handling on scan polls
5. Domain endpoint error handling
6. CORS configuration check

### **NICE-TO-HAVE (P2)** - UX/Performance
7. Logout button
8. Input validation
9. Error boundary
10. Polling optimization

---

## 🧪 Testing the Integration

### Test Scenario 1: Unauthenticated Quick Scan (Currently Broken)
```
1. Open http://localhost:3000
2. Enter "example.com" in landing page form
3. Click "Start Scan"
❌ Expected: Scan starts
✅ Actual: Error "Unable to start scanning"
```

### Test Scenario 2: Authenticated Flow (Working)
```
1. Open http://localhost:3000/register
2. Create account (email@test.com)
3. Auto-redirects to /dashboard
4. Org loads and scan history displays
5. Enter domain and click "New Scan"
6. Redirects to /scan/[id]
7. Findings display with poll updates
✅ Should work end-to-end
```

### Test Scenario 3: Login/Logout (Partial)
```
1. Open http://localhost:3000/login
2. Enter credentials
3. Auto-redirects to /dashboard
✅ Login works
❌ No logout button exists
```

### Test Scenario 4: Token Expiration (Not Handled)
```
1. Login successfully
2. Wait for access token to expire (or set TTL to 5s for testing)
3. Try to access /dashboard
❌ Expected: Automatic refresh + continue
✅ Actual: "Unauthorized" error, must login again
```

---

## 📋 API Endpoint Verification

### ✅ Working Endpoints
- POST `/api/v1/auth/register` - Creates user
- POST `/api/v1/auth/login` - Issues tokens
- GET `/api/v1/users/me` - Get current user (requires auth)
- GET `/api/v1/organizations` - List orgs (requires auth)
- GET `/api/v1/scan-jobs` - List scans (requires auth + org header)
- GET `/api/v1/scan-jobs/{id}` - Get scan (requires auth + org header)
- GET `/api/v1/scan-jobs/{id}/results` - Get results (requires auth + org header)

### ⚠️ Problematic Endpoints
- POST `/api/v1/quick-scan` - Requires auth, but frontend calls unauthenticated
- GET `/api/v1/domains/{id}` - Frontend passes empty ID sometimes

### ❓ Untested/Not Used by Frontend
- POST `/api/v1/auth/refresh` - Exists but never called
- POST `/api/v1/auth/logout` - Exists but no UI button
- POST `/api/v1/scan-jobs/{id}/cancel` - Exists but no UI
- Project endpoints - Not used by frontend
- Report endpoints - Not used by frontend
- Notification endpoints - Not used by frontend

---

## 🚀 Next Steps to Fix

### Immediate (1-2 hours)
1. [ ] Fix unauthenticated quick scan (choose solution A/B/C)
2. [ ] Fix org ID handling after quick scan
3. [ ] Add token refresh interceptor

### Short Term (2-4 hours)
4. [ ] Improve error handling on polls
5. [ ] Check CORS configuration
6. [ ] Add logout button

### Future (Nice-to-have)
7. [ ] Input validation
8. [ ] Error boundary
9. [ ] Polling optimization
10. [ ] WebSocket for real-time updates

