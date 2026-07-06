"""Decides *which* registered engines should run for a given scan job. Pure
selection logic — no execution, no I/O. Kept separate from the dispatcher so
"which engines run" and "how they're invoked" can evolve independently
(e.g. later: per-org engine allowlists, paid-tier gating, scan_type presets).
"""

from appsec.scanner.interfaces.models import ScanEngineCategory
from appsec.scanner.interfaces.registry import list_scanners, list_scanners_by_category

#: scan_type -> categories it should run. Placeholder mapping; real presets
#: (and per-org overrides) can replace this once engines exist to test against.
_SCAN_TYPE_PRESETS: dict[str, list[ScanEngineCategory]] = {
    "default": [
        ScanEngineCategory.SUBDOMAIN_ENUM,
        ScanEngineCategory.HTTP_PROBE,
        ScanEngineCategory.WEB_CRAWL,
        ScanEngineCategory.VULNERABILITY_SCAN,
    ],
    "quick": [ScanEngineCategory.HTTP_PROBE, ScanEngineCategory.VULNERABILITY_SCAN],
    "full": list(ScanEngineCategory),
}


def select_engines(scan_type: str) -> list[str]:
    """Returns the names of registered engines that should run for
    `scan_type`. Falls back to the "default" preset for unknown scan types.
    If no engines are registered yet (current state — adapters not built),
    returns an empty list rather than raising.
    """
    categories = _SCAN_TYPE_PRESETS.get(scan_type, _SCAN_TYPE_PRESETS["default"])
    selected: list[str] = []
    for category in categories:
        selected.extend(list_scanners_by_category(category))
    return selected or list_scanners()
