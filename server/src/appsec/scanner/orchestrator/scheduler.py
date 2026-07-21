"""Decides *which* registered engines should run for a given scan job. Pure
selection logic — no execution, no I/O. Kept separate from the dispatcher so
"which engines run" and "how they're invoked" can evolve independently
(e.g. later: per-org engine allowlists, paid-tier gating, scan_type presets).
"""

from appsec.scanner.interfaces.models import ScanEngineCategory
from appsec.scanner.interfaces.registry import list_scanners, list_scanners_by_category

#: Engines that run as their own progressive Celery task rather than inline in
#: the main scan. Excluded from `select_engines` so they never block the fast
#: engines from completing the job. Their findings are appended when they land.
PROGRESSIVE_ENGINES: frozenset[str] = frozenset({"urlscan"})

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
    selected = selected or list_scanners()
    return [name for name in selected if name not in PROGRESSIVE_ENGINES]


#: Ordered pipeline stages. Engines in an earlier stage run before later ones so
#: their output can feed downstream (e.g. katana's crawled URLs -> nuclei).
#: Engines in the SAME stage run concurrently. Recon/crawl first, then probing,
#: then vulnerability scanning last so it can target everything discovered.
_STAGE_ORDER: list[list[ScanEngineCategory]] = [
    [ScanEngineCategory.SUBDOMAIN_ENUM, ScanEngineCategory.PORT_SCAN],
    [ScanEngineCategory.HTTP_PROBE, ScanEngineCategory.WEB_CRAWL],
    [ScanEngineCategory.VULNERABILITY_SCAN, ScanEngineCategory.SECRET_SCAN],
]


def select_stages(scan_type: str) -> list[list[str]]:
    """Like `select_engines`, but groups the selected engines into ordered
    stages for the staged dispatcher. Only engines actually selected for
    `scan_type` (and registered, non-progressive) appear. Empty stages are
    dropped, so a scan_type with just one category still runs cleanly.
    """
    selected = set(select_engines(scan_type))
    stages: list[list[str]] = []
    placed: set[str] = set()

    for categories in _STAGE_ORDER:
        stage: list[str] = []
        for category in categories:
            for name in list_scanners_by_category(category):
                if name in selected and name not in placed:
                    stage.append(name)
                    placed.add(name)
        if stage:
            stages.append(stage)

    # Any selected engine whose category isn't in _STAGE_ORDER runs in a final
    # catch-all stage so nothing is silently dropped.
    leftover = [name for name in selected if name not in placed]
    if leftover:
        stages.append(sorted(leftover))

    return stages
