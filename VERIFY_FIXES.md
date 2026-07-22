# P0 Fixes: Verification Checklist

This document helps you verify that all fixes have been correctly implemented.

---

## File Verification

### Backend Files (4 total)

#### ✅ File 1: `server/src/appsec/application/quick_scan/schemas.py`
- [ ] Contains line: `org_id: uuid.UUID`
- [ ] Located after `scan_job_id` field
- [ ] QuickScanResponse has 3 fields: scan_job_id, org_id, status

**Quick Check:**
```bash
grep -A 3 "class QuickScanResponse" server/src/appsec/application/quick_scan/schemas.py
# Should show: org_id: uuid.UUID
```

---

#### ✅ File 2: `server/src/appsec/api/deps.py`
- [ ] Contains function: `get_optional_current_user_id()`
- [ ] Function checks `if credentials is None`
- [ ] If no token, calls `user_service.create_anonymous()`
- [ ] Returns `OptionalCurrentUserIdDep` annotation at end
- [ ] UserService import is present

**Quick Check:**
```bash
grep -A 5 "async def get_optional_current_user_id" server/src/appsec/api/deps.py
# Should show the anonymous user creation logic
```

---

#### ✅ File 3: `server/src/appsec/api/v1/quick_scan.py`
- [ ] Import changed to `OptionalCurrentUserIdDep`
- [ ] Endpoint parameter: `user_id: OptionalCurrentUserIdDep`
- [ ] Response includes: `org_id=scan_job.organization_id`
- [ ] Response line: `QuickScanResponse(scan_job_id=scan_job.id, org_id=scan_job.organization_id, status=scan_job.status)`

**Quick Check:**
```bash
grep "org_id=scan_job.organization_id" server/src/appsec/api/v1/quick_scan.py
# Should find the line in the return statement
```

---

#### ✅ File 4: `server/src/appsec/application/users/service.py`
- [ ] Import added: `from appsec.infrastructure.security.password import hash_password`
- [ ] Contains method: `async def create_anonymous(self) -> User:`
- [ ] Method creates User with email pattern: `f"anon-{uuid.uuid4().hex[:8]}@demo.local"`
- [ ] Method calls `await self._users.create(user)`
- [ ] Method calls `await self._session.commit()`

**Quick Check:**
```bash
grep -A 8 "async def create_anonymous" server/src/appsec/application/users/service.py
# Should show the full method
```

---

### Frontend Files (3 total)

#### ✅ File 5: `client/src/lib/api.ts`
- [ ] `quickScan()` function has response type: `{ scan_job_id: string; org_id: string; status: string }`
- [ ] Function call includes parameter: `false` (requireAuth=false)
- [ ] Last line before closing brace: `);` with false as final argument

**Quick Check:**
```bash
grep -A 10 "export async function quickScan" client/src/lib/api.ts
# Should show org_id in response type and false param
```

---

#### ✅ File 6: `client/src/app/page.tsx`
- [ ] Import includes: `setActiveOrgId`
- [ ] Import line: `import { quickScan, setActiveOrgId } from "@/lib/api";`
- [ ] In handleSubmit: `setActiveOrgId(response.org_id);`
- [ ] Line appears BEFORE: `window.location.assign()`

**Quick Check:**
```bash
grep "setActiveOrgId" client/src/app/page.tsx
# Should find at least 1 result (the function call)
```

---

#### ✅ File 7: `client/src/app/scan/[id]/page.tsx`
- [ ] Imports DO NOT include: `getAuthToken` or `clearAuth`
- [ ] Removed auth check block (should NOT have: `if (!getAuthToken())`)
- [ ] Redirect changed: `router.replace("/");` (NOT `/dashboard`)
- [ ] getActiveOrgId() check remains

**Quick Check:**
```bash
grep "getAuthToken" client/src/app/scan/[id]/page.tsx
# Should find NO results (removed)

grep 'router.replace("/"' client/src/app/scan/[id]/page.tsx
# Should find result (new redirect)
```

---

## Syntax Verification

### Backend

```bash
# Python syntax check
python -m py_compile server/src/appsec/application/quick_scan/schemas.py
python -m py_compile server/src/appsec/api/deps.py
python -m py_compile server/src/appsec/api/v1/quick_scan.py
python -m py_compile server/src/appsec/application/users/service.py
```

### Frontend

```bash
# TypeScript syntax check (requires tsc)
cd client
npx tsc --noEmit app/page.tsx
npx tsc --noEmit app/scan/[id]/page.tsx
npx tsc --noEmit lib/api.ts
```

---

## Integration Points

### Backend Integration

#### ✅ UserService has create_anonymous()
```bash
grep -c "async def create_anonymous" server/src/appsec/application/users/service.py
# Should return: 1
```

#### ✅ deps.py has optional auth dependency
```bash
grep -c "async def get_optional_current_user_id" server/src/appsec/api/deps.py
# Should return: 1
```

#### ✅ Quick scan endpoint uses optional auth
```bash
grep "OptionalCurrentUserIdDep" server/src/appsec/api/v1/quick_scan.py
# Should find the parameter in endpoint
```

### Frontend Integration

#### ✅ Landing page imports setActiveOrgId
```bash
grep "setActiveOrgId" client/src/app/page.tsx
# Should find in import and in handleSubmit
```

#### ✅ API client returns org_id
```bash
grep "org_id: string" client/src/lib/api.ts
# Should find in response type for quickScan
```

#### ✅ Scan page uses org_id from localStorage
```bash
grep "getActiveOrgId()" client/src/app/scan/[id]/page.tsx
# Should find the call in useEffect
```

---

## Data Flow Verification

### Response Flow

Check that the backend returns org_id:

```python
# In server/src/appsec/api/v1/quick_scan.py
# The return statement should be:
# return QuickScanResponse(scan_job_id=scan_job.id, org_id=scan_job.organization_id, status=scan_job.status)
```

Check that frontend receives and stores it:

```typescript
// In client/src/app/page.tsx
// After quickScan() returns:
// setActiveOrgId(response.org_id);
// window.location.assign(`/scan/${response.scan_job_id}`);
```

Check that scan results page uses it:

```typescript
// In client/src/app/scan/[id]/page.tsx
// Should have:
// const orgId = getActiveOrgId();
// if (!orgId) router.replace("/");
// Then use orgId in API calls
```

---

## Type Safety Verification

### Backend Types

#### QuickScanResponse Schema
```python
# Should have:
class QuickScanResponse(BaseModel):
    scan_job_id: uuid.UUID    # ✓
    org_id: uuid.UUID         # ✓ NEW
    status: ScanStatus        # ✓
```

### Frontend Types

#### quickScan() Return Type
```typescript
// Should be:
{ scan_job_id: string; org_id: string; status: string }
//                     ^^^^^^^ NEW FIELD
```

---

## Behavioral Verification

### Test 1: Unauthenticated Request
```bash
curl -X POST http://localhost:8000/api/v1/quick-scan \
  -H "Content-Type: application/json" \
  -d '{
    "target": "example.com",
    "target_type": "domain",
    "scan_type": "default",
    "skip_verification": true
  }'

# Expected: 201 Created with:
# {
#   "scan_job_id": "UUID",
#   "org_id": "UUID",      ← NEW FIELD
#   "status": "pending"
# }

# NOT 401 Unauthorized (before fix)
```

### Test 2: localStorage Storage
```javascript
// In browser DevTools console:
localStorage.getItem('entropy-org-id')
// Should return a UUID string, e.g.:
// "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Test 3: API Headers
```
// In browser DevTools → Network tab
// After landing page scan completes, check scan-jobs request
// Should have header:
X-Organization-ID: UUID-HERE
```

---

## Backward Compatibility Check

### Authenticated Users Still Work
```bash
# Login flow should still work
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Response: { access_token, refresh_token, token_type }
```

### Authenticated Quick Scan Still Works
```bash
# Get token from login response, then:
curl -X POST http://localhost:8000/api/v1/quick-scan \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com", ...}'

# Should return scan_job_id, org_id, status (same response)
```

---

## Error Handling

### Missing org_id on Scan Results Page
```
// Scenario: User deletes localStorage before navigating
// Expected: Redirect to / (home page)
// NOT: Crash, NOT: Redirect to /dashboard
```

### Invalid Target Format
```
// Scenario: User submits empty or invalid domain
// Expected: "Unable to start scanning" error on frontend
// NOT: 500 Server Error
```

---

## Performance Considerations

### No Performance Regression
- [ ] Landing page loads in <1s
- [ ] Quick scan returns response in <2s
- [ ] Scan results page loads in <2s
- [ ] No additional database queries introduced
- [ ] No memory leaks from anonymous user creation

### Scalability
- [ ] Anonymous user creation is fast (UUID + hash)
- [ ] localStorage has 5-10MB limit (org_id is ~36 bytes)
- [ ] No bulk operations required

---

## Edge Cases

### Test 1: Rapid Consecutive Scans
```
1. Click "Start Scan" on domain A
2. Before first completes, submit domain B
3. Expected: Both work, separate org_ids
```

### Test 2: Multiple Tabs
```
1. Open tab A: scan example1.com
2. Open tab B: scan example2.com
3. Expected: Each has own org_id in localStorage (last write wins)
```

### Test 3: Refresh on Scan Results Page
```
1. Submit quick scan → navigate to results
2. F5 refresh
3. Expected: Results reload (org_id still in localStorage)
```

### Test 4: Back Button
```
1. Submit quick scan → results page
2. Browser back button
3. Expected: Go to landing page (not broken)
```

---

## Deployment Verification

After deploying to production:

- [ ] Landing page accessible without login
- [ ] "Start Scan" button works
- [ ] Quick scan completes without 401 error
- [ ] Scan results page loads
- [ ] No 5xx errors in logs
- [ ] No database connection errors
- [ ] Anonymous users created successfully
- [ ] org_id stored and retrieved correctly

---

## Quick Verification Command

Run this to verify all key changes exist:

```bash
# Backend changes
echo "=== Backend Checks ===" && \
grep -q "org_id: uuid.UUID" server/src/appsec/application/quick_scan/schemas.py && echo "✓ Schema has org_id" || echo "✗ Schema missing org_id" && \
grep -q "async def get_optional_current_user_id" server/src/appsec/api/deps.py && echo "✓ Optional auth added" || echo "✗ Optional auth missing" && \
grep -q "OptionalCurrentUserIdDep" server/src/appsec/api/v1/quick_scan.py && echo "✓ Endpoint uses optional auth" || echo "✗ Endpoint not updated" && \
grep -q "async def create_anonymous" server/src/appsec/application/users/service.py && echo "✓ Anonymous user method added" || echo "✗ Anonymous method missing" && \

# Frontend changes
echo && echo "=== Frontend Checks ===" && \
grep -q "org_id: string" client/src/lib/api.ts && echo "✓ API type includes org_id" || echo "✗ API type missing org_id" && \
grep -q "setActiveOrgId" client/src/app/page.tsx && echo "✓ Landing page saves org_id" || echo "✗ Landing page not updated" && \
! grep -q "getAuthToken" client/src/app/scan/[id]/page.tsx && echo "✓ Auth check removed from scan page" || echo "✗ Auth check still present" && \
grep -q 'router.replace("/"' client/src/app/scan/[id]/page.tsx && echo "✓ Scan page redirects to home" || echo "✗ Scan page redirect wrong"
```

---

## Summary

When all checks pass ✓:

✅ **P0 #1 Fixed:** Unauthenticated quick scan works
✅ **P0 #2 Fixed:** org_id returned and stored
✅ **End-to-End Works:** Landing → Scan → Results
✅ **Ready for Production:** All changes verified

---

## Still Having Issues?

1. **Review FILES:**
   - All 7 files listed above modified?
   - No syntax errors?
   - Imports correct?

2. **Check LOGIC:**
   - Backend creates anonymous user when no token
   - Frontend receives org_id in response
   - Frontend stores org_id in localStorage
   - Scan page retrieves org_id and uses it

3. **Verify FLOW:**
   - Unauthenticated request → 201 response (not 401)
   - Response includes org_id (not missing)
   - localStorage has org_id key
   - Scan page doesn't redirect to dashboard

4. **Run TESTS:**
   - Follow TEST_FIXES.md for manual flow
   - Check browser console for errors
   - Check network requests for headers

5. **Refer to DOCS:**
   - P0_FIXES_SUMMARY.md - Why these changes
   - DIFFS_P0_FIXES.md - Exact diffs
   - ARCHITECTURE.md - System design
