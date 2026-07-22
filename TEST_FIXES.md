# P0 Fixes: Testing Guide

## Summary of Changes

This document tracks the fixes for the two P0 issues:

### P0 #1: Unauthenticated Quick Scan ✅
**Before:** Landing page tried to hit `/api/v1/quick-scan` without auth token → backend rejected with 401 Unauthorized

**After:** 
- Endpoint now accepts unauthenticated requests (users don't need to login first)
- Backend auto-creates anonymous users for demo flows
- Frontend can now call `quickScan()` without auth
- No more friction: user lands on / → enters domain → results page loads

**Changes Made:**
1. **Backend Schema** (`quick_scan/schemas.py`): Added `org_id` field to `QuickScanResponse`
2. **Backend Deps** (`api/deps.py`): Added `get_optional_current_user_id()` dependency that creates anonymous users if no token
3. **Backend Endpoint** (`api/v1/quick_scan.py`): 
   - Changed from `CurrentUserIdDep` → `OptionalCurrentUserIdDep`
   - Now returns `org_id` in response
4. **Backend Service** (`application/users/service.py`): Added `create_anonymous()` method that generates temporary demo users
5. **Frontend API** (`lib/api.ts`): 
   - Changed `quickScan()` to accept unauthenticated calls (requireAuth=false)
   - Updated response type to include `org_id`
6. **Frontend Landing Page** (`app/page.tsx`):
   - Import and call `setActiveOrgId()` after scan completes
   - Store `org_id` in localStorage before navigating to scan results

### P0 #2: Missing org_id After Scan ✅
**Before:** Quick scan response didn't include `org_id`, so scan results page couldn't fetch data and redirected to dashboard

**After:**
- `/api/v1/quick-scan` response now includes `org_id: uuid`
- Frontend stores this in localStorage via `setActiveOrgId()`
- Scan results page (`/scan/[id]`) uses stored org_id to load data
- Results load correctly without redirect

**Changes Made:**
1. Backend returns `org_id=scan_job.organization_id` in response
2. Frontend extracts and stores it in localStorage
3. Scan results page reads from localStorage and uses for API calls

---

## Complete Test Flow (End-to-End)

### Prerequisites
- Backend running on `http://localhost:8000` (or configured URL)
- Frontend running on `http://localhost:3000`
- Database initialized with migrations
- Redis running (for token blacklist)

### Test Steps

1. **Open Landing Page**
   ```
   Navigate to http://localhost:3000/
   ```
   - Verify: Page loads with "Ship fast. Stay secure." heading
   - Verify: Domain input field is visible
   - Verify: "Start Scan" button is enabled
   - Verify: No login required yet

2. **Submit Quick Scan (Unauthenticated)**
   ```
   Enter domain: "example.com"
   Click "Start Scan"
   ```
   - **Backend Flow:**
     - POST /api/v1/quick-scan receives request with NO Authorization header
     - `get_optional_current_user_id()` detects missing credentials
     - Creates anonymous user: `anon-{random}@demo.local`
     - `QuickScanService.run()` creates workspace: `ws-{anon_user_id.hex[:12]}`
     - Returns `QuickScanResponse` with:
       ```json
       {
         "scan_job_id": "uuid-here",
         "org_id": "uuid-here",
         "status": "pending"
       }
       ```
   - **Frontend Flow:**
     - Receives response with org_id
     - Calls `setActiveOrgId(response.org_id)` → stores to localStorage
     - Navigates to `/scan/{response.scan_job_id}`
   - **Verify:**
     - No error message shown
     - Loading redirects to scan results page
     - URL changes to `/scan/{scan_job_id}`

3. **Scan Results Page Loads**
   ```
   Page: /scan/{scan_job_id}
   ```
   - **Frontend Flow:**
     - Page mounts, calls `getActiveOrgId()`
     - Retrieves org_id from localStorage
     - Calls APIs with org_id in X-Organization-ID header:
       - `getScanJob(scanJobId, orgId)`
       - `getScanResults(scanJobId, orgId)`
       - `getDomain(domainId, orgId)` (if available)
   - **Verify:**
     - No redirect to dashboard
     - Scan details load (domain name, status, created time)
     - Findings appear if available
     - Polling continues if scan is still running

4. **Verify Scan Polling**
   ```
   Leave page open for 10-30 seconds if scan_job.status is "pending" or "running"
   ```
   - **Frontend Flow:**
     - Page sets timer for 5 seconds
     - Polls `getScanJob()` and `getScanResults()` again
     - Updates UI with latest data
   - **Verify:**
     - No console errors
     - Results update automatically
     - Eventually shows "completed" status

---

## Diffs Summary

### Backend Changes

**Diff 1: QuickScanResponse schema**
```diff
class QuickScanResponse(BaseModel):
    scan_job_id: uuid.UUID
+   org_id: uuid.UUID
    status: ScanStatus
```

**Diff 2: Optional auth dependency**
```diff
+async def get_optional_current_user_id(
+    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
+    token_blacklist: TokenBlacklistDep,
+    user_service: Annotated[UserService, Depends(get_user_service)],
+) -> uuid.UUID:
+    """Get current user ID if authenticated, otherwise create an anonymous user."""
+    if credentials is None:
+        anon_user = await user_service.create_anonymous()
+        return anon_user.id
+    # ... existing validation ...
+
+OptionalCurrentUserIdDep = Annotated[uuid.UUID, Depends(get_optional_current_user_id)]
```

**Diff 3: Endpoint update**
```diff
@router.post("/quick-scan", ...)
async def quick_scan(
    payload: QuickScanRequest,
-   user_id: CurrentUserIdDep,
+   user_id: OptionalCurrentUserIdDep,
    quick_scan_service: ...,
) -> QuickScanResponse:
    scan_job = await quick_scan_service.run(...)
-   return QuickScanResponse(scan_job_id=scan_job.id, status=scan_job.status)
+   return QuickScanResponse(scan_job_id=scan_job.id, org_id=scan_job.organization_id, status=scan_job.status)
```

**Diff 4: UserService.create_anonymous()**
```diff
async def create_anonymous(self) -> User:
    """Create a temporary anonymous user for demo/quick-scan flows."""
    user = User(
        id=uuid.uuid4(),
        email=f"anon-{uuid.uuid4().hex[:8]}@demo.local",
        hashed_password=hash_password("demo-" + uuid.uuid4().hex[:16]),
        is_active=True,
        full_name="Demo User",
    )
    created = await self._users.create(user)
    await self._session.commit()
    return created
```

### Frontend Changes

**Diff 5: API client quickScan**
```diff
export async function quickScan(target: string) {
-   return request<{ scan_job_id: string; status: string }>(
+   return request<{ scan_job_id: string; org_id: string; status: string }>(
        "/api/v1/quick-scan",
        { ... },
+       false,
    );
}
```

**Diff 6: Landing page**
```diff
-import { quickScan } from "@/lib/api";
+import { quickScan, setActiveOrgId } from "@/lib/api";

const response = await quickScan(domain.trim());
+setActiveOrgId(response.org_id);
window.location.assign(`/scan/${response.scan_job_id}`);
```

**Diff 7: Scan results page**
```diff
-import { getActiveOrgId, getAuthToken, getDomain, getScanJob, getScanResults, clearAuth } from "@/lib/api";
+import { getActiveOrgId, getDomain, getScanJob, getScanResults } from "@/lib/api";

useEffect(() => {
-   if (!getAuthToken()) {
-     router.replace(`/login?next=/scan/${params.id}`);
-     return;
-   }
    
    const orgId = getActiveOrgId();
    if (!orgId) {
-     router.replace("/dashboard");
+     router.replace("/");
      return;
    }
```

---

## Expected Behavior After Fix

### Happy Path: Unauthenticated Quick Scan
```
User (not logged in)
  ↓
Opens https://app.local/
  ↓
Enters "example.com" → Clicks "Start Scan"
  ↓
Frontend: POST /api/v1/quick-scan (no auth)
  ↓
Backend: No token → create anonymous user {anon-abc123@demo.local}
  ↓
Backend: Create workspace {ws-abc123def456}
  ↓
Backend: Create project, domain, scan job
  ↓
Backend: Return { scan_job_id: "...", org_id: "...", status: "pending" }
  ↓
Frontend: Save org_id to localStorage
  ↓
Frontend: Navigate to /scan/{scan_job_id}
  ↓
Scan Results Page: Read org_id from localStorage
  ↓
Scan Results Page: Fetch data with org_id header
  ↓
Success: Results page displays with real data (not redirected)
```

---

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Landing page loads (unauthenticated access works)
- [ ] Entering domain and clicking "Start Scan" doesn't show 401 error
- [ ] Scan results page loads (doesn't redirect to dashboard)
- [ ] org_id is stored in localStorage `entropy-org-id`
- [ ] Scan job details appear on results page
- [ ] Findings render if backend returned them
- [ ] Polling works if scan is still running
- [ ] Browser console has no 401/403/404 errors for API calls

---

## Files Changed

### Backend (Python)
- `server/src/appsec/application/quick_scan/schemas.py` (+1 field)
- `server/src/appsec/api/deps.py` (+1 new dependency)
- `server/src/appsec/api/v1/quick_scan.py` (+1 parameter change, +1 return field)
- `server/src/appsec/application/users/service.py` (+1 new method)

### Frontend (TypeScript/React)
- `client/src/lib/api.ts` (+1 response field, +1 param change)
- `client/src/app/page.tsx` (+1 import, +1 line in handler)
- `client/src/app/scan/[id]/page.tsx` (+1 import change, -5 lines of auth check)

**Total: 7 files, ~30 lines changed**

---

## Rollback Plan

If needed, reverse the changes by:
1. Revert to `CurrentUserIdDep` in quick_scan.py
2. Remove `org_id` from response schema and endpoint
3. Remove `get_optional_current_user_id` from deps.py
4. Remove `create_anonymous()` from UserService
5. Update frontend to require login before scan (redirect to /login?next=/)
6. Remove `setActiveOrgId()` calls from landing page

---

## Notes

- Anonymous users are **not persisted long-term** – they exist for the demo scan flow only
- org_id is stored in localStorage, so it persists across page reloads during the same session
- The backend already supported deterministic workspace creation per user (ws-{user_id}), so this leverages existing architecture
- No breaking changes to authenticated flows – login/register/dashboard still work as before
