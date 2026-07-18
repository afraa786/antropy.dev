import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_scan_result_service
from appsec.application.scan_results.schemas import ScanResultResponse
from appsec.application.scan_results.service import ScanResultService

router = APIRouter(tags=["scan-results"])


@router.get("/scan-jobs/{scan_job_id}/results", response_model=list[ScanResultResponse])
async def list_scan_results(
    scan_job_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    scan_result_service: Annotated[ScanResultService, Depends(get_scan_result_service)],
) -> list[ScanResultResponse]:
    results = await scan_result_service.list_for_scan_job(scan_job_id, organization_id, user_id)
    return [
        ScanResultResponse(
            id=r.id,
            scan_job_id=r.scan_job_id,
            organization_id=r.organization_id,
            summary=r.summary,
            severity_counts=r.severity_counts,
            created_at=r.created_at,
        )
        for r in results
    ]
