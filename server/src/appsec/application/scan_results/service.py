import uuid

from appsec.domain.entities.scan_result import ScanResult
from appsec.domain.exceptions import ForbiddenError
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.scan_result_repository import ScanResultRepository


class ScanResultService:
    def __init__(
        self,
        scan_result_repository: ScanResultRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._scan_results = scan_result_repository
        self._orgs = organization_repository

    async def list_for_scan_job(
        self, scan_job_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[ScanResult]:
        await self._require_member(organization_id, requesting_user_id)
        return await self._scan_results.get_for_scan_job(scan_job_id, organization_id)

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
