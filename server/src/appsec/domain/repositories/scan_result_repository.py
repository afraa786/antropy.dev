import uuid
from typing import Protocol

from appsec.domain.entities.scan_result import ScanResult


class ScanResultRepository(Protocol):
    async def get_for_scan_job(
        self, scan_job_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ScanResult]: ...

    async def create(self, scan_result: ScanResult) -> ScanResult: ...
