# P0 Fixes: All Diffs

## Fix 1: Unauthenticated Quick Scan & Return org_id

---

### Diff 1: Backend Response Schema

**File:** `server/src/appsec/application/quick_scan/schemas.py`

```diff
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from appsec.domain.enums import ScanStatus


class QuickScanRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    target_type: Literal["domain", "repo"] = "domain"
    scan_type: str = Field(default="default", max_length=64)
    skip_verification: bool = False


class QuickScanResponse(BaseModel):
    scan_job_id: uuid.UUID
+   org_id: uuid.UUID
    status: ScanStatus
```

**Reason:** The response must include `org_id` so the frontend knows which org to use for subsequent API calls.

---

### Diff 2: Optional Auth Dependency

**File:** `server/src/appsec/api/deps.py`

```diff
 CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]

+
+async def get_optional_current_user_id(
+    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
+    token_blacklist: TokenBlacklistDep,
+    user_service: Annotated[UserService, Depends(get_user_service)],
+) -> uuid.UUID:
+    """Get current user ID if authenticated, otherwise create an anonymous user."""
+    if credentials is None:
+        # Create anonymous user for quick-scan demo flow
+        anon_user = await user_service.create_anonymous()
+        return anon_user.id
+
+    payload = decode_token(credentials.credentials)
+    if payload.type != "access":
+        raise UnauthorizedError("Invalid token type")
+    if await token_blacklist.is_revoked(payload.jti):
+        raise UnauthorizedError("Token has been revoked")
+    return payload.sub
+
+
+OptionalCurrentUserIdDep = Annotated[uuid.UUID, Depends(get_optional_current_user_id)]
```

**Reason:** This new dependency handles the "unauthenticated but create a user anyway" pattern. If no Bearer token is provided, it creates a temporary anonymous user instead of failing.

---

### Diff 3: Quick Scan Endpoint

**File:** `server/src/appsec/api/v1/quick_scan.py`

```diff
 from typing import Annotated

 from fastapi import APIRouter, Depends, status

-from appsec.api.deps import CurrentUserIdDep, get_quick_scan_service
+from appsec.api.deps import OptionalCurrentUserIdDep, get_quick_scan_service
 from appsec.application.quick_scan.schemas import QuickScanRequest, QuickScanResponse
 from appsec.application.quick_scan.service import QuickScanService

 router = APIRouter(tags=["quick-scan"])


 @router.post("/quick-scan", response_model=QuickScanResponse, status_code=status.HTTP_201_CREATED)
 async def quick_scan(
     payload: QuickScanRequest,
-    user_id: CurrentUserIdDep,
+    user_id: OptionalCurrentUserIdDep,
     quick_scan_service: Annotated[QuickScanService, Depends(get_quick_scan_service)],
 ) -> QuickScanResponse:
     scan_job = await quick_scan_service.run(
         user_id=user_id,
         target=payload.target,
         target_type=payload.target_type,
         scan_type=payload.scan_type,
         skip_verification=payload.skip_verification,
     )
-    return QuickScanResponse(scan_job_id=scan_job.id, status=scan_job.status)
+    return QuickScanResponse(scan_job_id=scan_job.id, org_id=scan_job.organization_id, status=scan_job.status)
```

**Reason:** Switch to optional auth and include `org_id` in the response so the frontend can store and use it.

---

### Diff 4: Anonymous User Creation

**File:** `server/src/appsec/application/users/service.py`

```diff
 import uuid

 from sqlalchemy.ext.asyncio import AsyncSession

 from appsec.domain.entities.user import User
 from appsec.domain.exceptions import NotFoundError
 from appsec.domain.repositories.user_repository import UserRepository
+from appsec.infrastructure.security.password import hash_password


 class UserService:
     def __init__(self, session: AsyncSession, user_repository: UserRepository) -> None:
         self._session = session
         self._users = user_repository

     async def get_by_id(self, user_id: uuid.UUID) -> User:
         user = await self._users.get_by_id(user_id)
         if user is None:
             raise NotFoundError(f"User {user_id} not found")
         return user

     async def update_profile(self, user_id: uuid.UUID, full_name: str | None) -> User:
         user = await self.get_by_id(user_id)
         user.full_name = full_name
         updated = await self._users.update(user)
         await self._session.commit()
         return updated
+
+    async def create_anonymous(self) -> User:
+        """Create a temporary anonymous user for demo/quick-scan flows."""
+        user = User(
+            id=uuid.uuid4(),
+            email=f"anon-{uuid.uuid4().hex[:8]}@demo.local",
+            hashed_password=hash_password("demo-" + uuid.uuid4().hex[:16]),
+            is_active=True,
+            full_name="Demo User",
+        )
+        created = await self._users.create(user)
+        await self._session.commit()
+        return created
```

**Reason:** Implements the anonymous user creation. These are temporary demo users that exist for the quick-scan flow.

---

### Diff 5: Frontend API Client

**File:** `client/src/lib/api.ts`

```diff
 export async function quickScan(target: string) {
-  return request<{ scan_job_id: string; status: string }>(
+  return request<{ scan_job_id: string; org_id: string; status: string }>(
     "/api/v1/quick-scan",
     {
       method: "POST",
       body: JSON.stringify({
         target,
         target_type: "domain",
         scan_type: "default",
         skip_verification: true,
       }),
     },
+    false,
   );
 }
```

**Reason:** 
- Add `org_id` to the response type to match the backend
- Pass `false` as `requireAuth` so the request doesn't fail if no token is stored

---

### Diff 6: Landing Page

**File:** `client/src/app/page.tsx`

```diff
 import Link from "next/link";
 import { useState } from "react";
 import { Button, Input, Navbar } from "@/components/entropy-ui";
-import { quickScan } from "@/lib/api";
+import { quickScan, setActiveOrgId } from "@/lib/api";

 const features = [
   {
     title: "Attack Surface Discovery",
     description: "Map exposed assets, TLS posture, and external dependencies before attackers do.",
   },
   // ...
 ];

 export default function Home() {
   const [domain, setDomain] = useState("");
   const [loading, setLoading] = useState(false);
   const [error, setError] = useState<string | null>(null);

   const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
     event.preventDefault();
     setLoading(true);
     setError(null);

     try {
       const response = await quickScan(domain.trim());
+      setActiveOrgId(response.org_id);
       window.location.assign(`/scan/${response.scan_job_id}`);
     } catch (err) {
       setError(err instanceof Error ? err.message : "Unable to start scanning");
     } finally {
       setLoading(false);
     }
   };

   // ... rest of component
 }
```

**Reason:** Store the `org_id` in localStorage before navigating to the scan results page so it can be used for API calls.

---

### Diff 7: Scan Results Page

**File:** `client/src/app/scan/[id]/page.tsx`

```diff
 'use client';

 import { useEffect, useMemo, useState } from "react";
 import { useParams, useRouter } from "next/navigation";
 import { Button, Navbar, SeverityBadge } from "@/components/entropy-ui";
-import { getActiveOrgId, getAuthToken, getDomain, getScanJob, getScanResults, clearAuth } from "@/lib/api";
+import { getActiveOrgId, getDomain, getScanJob, getScanResults } from "@/lib/api";

 type FindingItem = {
   title: string;
   description: string;
   severity: string;
 };

 export default function ScanPage() {
   const params = useParams<{ id: string }>();
   const router = useRouter();
   const [loading, setLoading] = useState(true);
   // ... state definitions

   useEffect(() => {
-    if (!getAuthToken()) {
-      router.replace(`/login?next=/scan/${params.id}`);
-      return;
-    }
-
     const orgId = getActiveOrgId();
     if (!orgId) {
-      router.replace("/dashboard");
+      router.replace("/");
       return;
     }

     let mounted = true;
     const load = async () => {
       try {
         const [scanJob, domainResponse, scanResults] = await Promise.all([
           getScanJob(params.id, orgId),
           getDomain("", orgId).catch(() => null),
           getScanResults(params.id, orgId),
         ]);

         if (!mounted) return;

         setJob(scanJob);
         setResults(scanResults);
         setDomain((domainResponse as { hostname?: string } | null | undefined)?.hostname ?? scanJob.domain_id);
       } catch (err) {
         if (!mounted) return;
         setError(err instanceof Error ? err.message : "Unable to load scan results");
       } finally {
         if (mounted) setLoading(false);
       }
     };

     load();
     // ... polling logic
   }, [job?.status, params.id, router]);

   // ... rest of component
 }
```

**Reason:**
- Remove the auth requirement check so unauthenticated users can view scan results
- Remove the redirect to dashboard if no org_id; instead redirect to home to start a new scan

---

## Summary of Changes

| File | Changes | Reason |
|------|---------|--------|
| `quick_scan/schemas.py` | +1 field (`org_id`) | Backend returns org_id to frontend |
| `api/deps.py` | +1 new dependency function | Support optional auth (auto-create user if none) |
| `api/v1/quick_scan.py` | +1 param change, +1 return field | Use optional auth, include org_id |
| `users/service.py` | +1 new method | Create temporary anonymous users |
| `lib/api.ts` | +1 response field, +1 param | Handle org_id and allow unauthenticated calls |
| `app/page.tsx` | +1 import, +1 line | Store org_id after successful scan |
| `app/scan/[id]/page.tsx` | +1 import change, -6 lines | Remove auth requirement, adjust redirect |

**Total: 7 files, ~35 lines changed**

---

## Flow After Fixes

```
┌─────────────────────────────────────────────────────────┐
│ User (not logged in) opens https://app.local/          │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Landing Page (/):                                       │
│ - Domain input visible                                  │
│ - User enters "example.com" → clicks "Start Scan"      │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: POST /api/v1/quick-scan                       │
│ - NO Authorization header (requireAuth=false)           │
│ - Body: { target: "example.com", ... }                 │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Backend: get_optional_current_user_id()                 │
│ - No Bearer token detected                              │
│ - Create anonymous user: anon-abc123@demo.local        │
│ - Returns user_id (anon user)                           │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Backend: QuickScanService.run()                         │
│ - Create workspace: ws-abc123def456                     │
│ - Create project, domain, scan_job                      │
│ - Return scan_job with org_id                           │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Backend: quick_scan() endpoint                          │
│ - Response: {                                            │
│     scan_job_id: "uuid-here",                           │
│     org_id: "uuid-here",  ◄── NEW FIELD               │
│     status: "pending"                                   │
│   }                                                     │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: Handle response                               │
│ - Call setActiveOrgId(response.org_id)                 │
│ - Store org_id to localStorage                          │
│ - Navigate to /scan/{response.scan_job_id}              │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Scan Results Page (/scan/{id}):                         │
│ - Read org_id from localStorage                         │
│ - NO redirect to dashboard (org_id exists)             │
│ - NO redirect to login (no auth required)              │
│ - Fetch: getScanJob(id, orgId)                         │
│ - Fetch: getScanResults(id, orgId)                     │
│ - Display results successfully ✓                        │
└─────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. Verify all files are modified correctly
2. Run backend tests to ensure `create_anonymous()` works
3. Rebuild frontend (TypeScript compilation should pass)
4. Test the full flow:
   - Open landing page (unauthenticated)
   - Submit domain
   - Verify no 401 error
   - Verify scan results page loads with data
   - Check localStorage has `entropy-org-id` key
5. Commit changes with message: "Fix: Allow unauthenticated quick-scans and include org_id in response"
