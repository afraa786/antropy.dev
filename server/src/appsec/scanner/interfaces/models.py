"""Common DTOs every scanner engine must produce/consume. Engine-agnostic — no
Nuclei/Katana/etc-specific fields belong here. Adapters translate their own
tool's output into these shapes; nothing downstream ever sees a raw tool schema.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanEngineCategory(StrEnum):
    """What kind of job an engine performs — lets the orchestrator pick
    engines by capability instead of hardcoding names."""

    VULNERABILITY_SCAN = "vulnerability_scan"
    WEB_CRAWL = "web_crawl"
    HTTP_PROBE = "http_probe"
    SUBDOMAIN_ENUM = "subdomain_enum"
    PORT_SCAN = "port_scan"
    SECRET_SCAN = "secret_scan"


@dataclass(slots=True)
class Target:
    """A verified-ownership scan target handed to an engine. The engine
    receives only what it needs to run — never raw domain-ownership state."""

    hostname: str
    scan_job_id: uuid.UUID
    organization_id: uuid.UUID
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Evidence:
    """Raw proof backing a finding — request/response snippet, matched line,
    file path, etc. Kept generic so any engine can populate it."""

    description: str
    raw_data: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Finding:
    """One normalized security observation, regardless of which engine
    produced it."""

    id: uuid.UUID
    title: str
    severity: Severity
    description: str
    engine: str
    matched_at: str | None = None
    evidence: list[Evidence] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScanResult:
    """What every `Scanner.scan()` implementation must return — the
    orchestrator and normalizer only ever deal with this shape."""

    scan_job_id: uuid.UUID
    engine: str
    findings: list[Finding] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    success: bool = True
    error_message: str | None = None
    raw_output: str | None = None
