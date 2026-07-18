from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentUserIdDep, get_quick_scan_service
from appsec.application.quick_scan.schemas import QuickScanRequest, QuickScanResponse
from appsec.application.quick_scan.service import QuickScanService

router = APIRouter(tags=["quick-scan"])


@router.post("/quick-scan", response_model=QuickScanResponse, status_code=status.HTTP_201_CREATED)
async def quick_scan(
    payload: QuickScanRequest,
    user_id: CurrentUserIdDep,
    quick_scan_service: Annotated[QuickScanService, Depends(get_quick_scan_service)],
) -> QuickScanResponse:
    scan_job = await quick_scan_service.run(
        user_id=user_id,
        target=payload.target,
        target_type=payload.target_type,
        scan_type=payload.scan_type,
        skip_verification=payload.skip_verification,
    )
    return QuickScanResponse(scan_job_id=scan_job.id, status=scan_job.status)
