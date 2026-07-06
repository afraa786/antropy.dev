import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_report_service
from appsec.application.reports.schemas import CreateReportRequest, ReportResponse
from appsec.application.reports.service import ReportService

router = APIRouter(tags=["reports"])


def _to_response(report) -> ReportResponse:  # noqa: ANN001
    return ReportResponse(
        id=report.id,
        organization_id=report.organization_id,
        project_id=report.project_id,
        scan_job_id=report.scan_job_id,
        format=report.format,
        status=report.status,
        file_path=report.file_path,
        generated_at=report.generated_at,
        created_at=report.created_at,
    )


@router.post(
    "/scan-jobs/{scan_job_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
async def create_report(
    scan_job_id: uuid.UUID,
    payload: CreateReportRequest,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    report = await report_service.create_for_scan_job(
        scan_job_id, organization_id, user_id, payload.format
    )
    return _to_response(report)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    report = await report_service.get_by_id(report_id, organization_id, user_id)
    return _to_response(report)
