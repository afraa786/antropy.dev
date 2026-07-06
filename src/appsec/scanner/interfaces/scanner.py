"""The one contract every scanner engine must implement. The FastAPI backend
and orchestrator depend only on this interface — never on a concrete engine.
Whoever builds the Nuclei/Katana/etc adapters implements this class and
registers it; nothing else in the codebase needs to change.
"""

from abc import ABC, abstractmethod

from appsec.scanner.interfaces.models import ScanEngineCategory, ScanResult, Target


class Scanner(ABC):
    """Base class for all scanner engine adapters.

    Implementations wrap a single external tool (CLI binary, API, etc.) and
    translate its output into the common `ScanResult`/`Finding` schema. They
    must not perform vulnerability detection themselves — only invoke the
    underlying tool and normalize what it reports.
    """

    #: Unique engine identifier used for registry lookup, e.g. "nuclei".
    name: str

    #: Capability category, used by the orchestrator to pick engines for a job.
    category: ScanEngineCategory

    @abstractmethod
    async def validate(self, target: Target) -> bool:
        """Return True if this engine can run against the given target
        (e.g. target type supported, required options present). Must not
        perform network calls — cheap, local checks only.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the underlying tool/binary is installed, reachable,
        and ready to execute (e.g. `nuclei -version` succeeds).
        """
        raise NotImplementedError

    @abstractmethod
    async def scan(self, target: Target) -> ScanResult:
        """Execute the scan against `target` and return a normalized
        `ScanResult`. Implementations own their own subprocess/CLI
        invocation and JSON parsing — callers only see the normalized shape.
        """
        raise NotImplementedError
