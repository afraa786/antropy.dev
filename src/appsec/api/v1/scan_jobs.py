import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_scan_job_service
from appsec.application.scan_jobs.schemas import CreateScanJobRequest, ScanJobResponse
from appsec.application.scan_jobs.service import ScanJobService

router = APIRouter(tags=["scan-jobs"])


def _to_response(scan_job) -> ScanJobResponse:  # noqa: ANN001
    return ScanJobResponse(
        id=scan_job.id,
        project_id=scan_job.project_id,
        organization_id=scan_job.organization_id,
        domain_id=scan_job.domain_id,
        status=scan_job.status,
        scan_type=scan_job.scan_type,
        created_by=scan_job.created_by,
        created_at=scan_job.created_at,
        started_at=scan_job.started_at,
        completed_at=scan_job.completed_at,
    )


@router.post(
    "/projects/{project_id}/scan-jobs",
    response_model=ScanJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scan_job(
    project_id: uuid.UUID,
    payload: CreateScanJobRequest,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    scan_job_service: Annotated[ScanJobService, Depends(get_scan_job_service)],
) -> ScanJobResponse:
    scan_job = await scan_job_service.create(
        project_id, organization_id, user_id, payload.domain_id, payload.scan_type
    )
    return _to_response(scan_job)


@router.get("/scan-jobs/{scan_job_id}", response_model=ScanJobResponse)
async def get_scan_job(
    scan_job_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    scan_job_service: Annotated[ScanJobService, Depends(get_scan_job_service)],
) -> ScanJobResponse:
    scan_job = await scan_job_service.get_by_id(scan_job_id, organization_id, user_id)
    return _to_response(scan_job)


@router.get("/scan-jobs", response_model=list[ScanJobResponse])
async def list_scan_jobs(
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    scan_job_service: Annotated[ScanJobService, Depends(get_scan_job_service)],
) -> list[ScanJobResponse]:
    scan_jobs = await scan_job_service.list_for_organization(organization_id, user_id)
    return [_to_response(s) for s in scan_jobs]


@router.post("/scan-jobs/{scan_job_id}/cancel", response_model=ScanJobResponse)
async def cancel_scan_job(
    scan_job_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    scan_job_service: Annotated[ScanJobService, Depends(get_scan_job_service)],
) -> ScanJobResponse:
    scan_job = await scan_job_service.cancel(scan_job_id, organization_id, user_id)
    return _to_response(scan_job)
