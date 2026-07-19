"""Central place engines register themselves. Adding a new scanner never
touches the orchestrator or backend — it only adds a module under
`scanner/engines/<name>/` that calls `register_scanner()` at import time.
"""

from appsec.scanner.interfaces.models import ScanEngineCategory
from appsec.scanner.interfaces.scanner import Scanner

_REGISTRY: dict[str, type[Scanner]] = {}


class ScannerAlreadyRegisteredError(Exception):
    pass


class ScannerNotFoundError(Exception):
    pass


def register_scanner(scanner_cls: type[Scanner]) -> type[Scanner]:
    """Class decorator engines use to register themselves, e.g.:

    @register_scanner
    class NucleiScanner(Scanner):
        name = "nuclei"
        ...
    """
    name = scanner_cls.name
    if name in _REGISTRY:
        raise ScannerAlreadyRegisteredError(f"Scanner '{name}' is already registered")
    _REGISTRY[name] = scanner_cls
    return scanner_cls


def get_scanner(name: str) -> type[Scanner]:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ScannerNotFoundError(f"No scanner registered under '{name}'") from exc


def list_scanners() -> list[str]:
    return sorted(_REGISTRY.keys())


def list_scanners_by_category(category: ScanEngineCategory) -> list[str]:
    return sorted(name for name, cls in _REGISTRY.items() if cls.category == category)


def clear_registry() -> None:
    """Test-only helper — resets registrations between test runs."""
    _REGISTRY.clear()
