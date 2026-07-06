from enum import StrEnum


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class VerificationMethod(StrEnum):
    DNS_TXT = "dns_txt"
    HTTP_FILE = "http_file"


class ScanStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportFormat(StrEnum):
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class NotificationType(StrEnum):
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    DOMAIN_VERIFIED = "domain_verified"
    DOMAIN_VERIFICATION_FAILED = "domain_verification_failed"
    REPORT_READY = "report_ready"
    MEMBER_INVITED = "member_invited"
