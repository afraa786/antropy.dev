import uuid
from typing import Protocol

from appsec.domain.entities.report import Report


class ReportRepository(Protocol):
    async def get_by_id(self, report_id: uuid.UUID, organization_id: uuid.UUID) -> Report | None: ...

    async def create(self, report: Report) -> Report: ...

    async def update(self, report: Report) -> Report: ...
