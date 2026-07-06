"""Renders a formatted report dict into a specific output format. Only JSON
is implemented for the foundation — PDF/HTML rendering is deferred (matches
`Report.status` staying PENDING until generation is actually built).
"""

import json
from typing import Any

from appsec.domain.enums import ReportFormat
from appsec.domain.exceptions import ValidationAppError


def export(report_data: dict[str, Any], report_format: ReportFormat) -> str:
    if report_format == ReportFormat.JSON:
        return json.dumps(report_data, indent=2)

    raise ValidationAppError(
        f"Report format '{report_format.value}' is not yet implemented — only JSON export exists."
    )
